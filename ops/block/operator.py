import math

import bmesh
import bpy
from mathutils import Matrix, Vector

from ...utils import addon, infobar, scene, view3d
from ...utils.operator import safe
from ...utilsbmesh import facet
from . import (
    bevel,
    bisect,
    draw,
    edit,
    extrude,
    numeric_input,
    orientation,
    ui,
)
from .data import (
    CREATE,
    Config,
    CreatedData,
    ModalState,
    Modifiers,
    Mouse,
    Objects,
    Pref,
    Shape,
)
from .transform import common as transform_common
from .transform import rotate, scale, translate


class Block(bpy.types.Operator):
    pref: bpy.props.PointerProperty(type=Pref)
    shape: bpy.props.PointerProperty(type=Shape)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ui = ui.DrawUI()
        self.ray = scene.ray_cast.Ray()
        self.mouse = Mouse()
        self.data = CreatedData()
        self.config = Config()
        self.objects = Objects()
        self.modifiers = Modifiers()
        self.state = ModalState()
        self.edit_mode = "NONE"
        self._offset_applied = False

    @property
    def is_3d(self):
        """True iff the cutter is 3D — volumetric shapes always, others
        once ``extrude.faces`` has been populated.
        """
        sd = self.shape.data
        if sd.volumetric:
            return True
        return bool(self.data.extrude.faces)

    @property
    def cutter_extrusion(self):
        """``sd.extrusion`` or 0.0 for shapes without it (Sphere)."""
        return getattr(self.shape.data, "extrusion", 0.0)

    @property
    def symmetry_extrude(self):
        return bool(getattr(self.shape.data, "symmetry_extrude", False))

    def set_config(self, context):
        raise NotImplementedError("Subclasses must implement the set_options method")

    def get_tool_prpoerties(self):
        self.data.bevel.round.segments = addon.pref().tools.block.form.bevel_segments
        self.data.bevel.fill.segments = addon.pref().tools.block.form.bevel_segments
        verts = addon.pref().tools.block.form.circle_verts
        self.shape.circle.verts = verts
        self.shape.cylinder.verts = verts

    def get_object(self, context):
        raise NotImplementedError("Subclasses must implement the get_object method")

    def build_bmesh(self, obj):
        raise NotImplementedError("Subclasses must implement the get_object method")

    def build_geometry(self, obj, bm):
        raise NotImplementedError("Subclasses must implement the build_geometry method")

    def _redo_finish(self, context, obj):
        """Finish step for the F9-redo path, after build + pref transforms
        (mesh is final). Mirrors the modal ``_finish``.

        Base no-op; subclasses may re-frame the object. The edit-mesh tool
        overrides execute() and never reaches it.
        """
        pass

    def update_bmesh(self, obj, bm, loop_triangles=False, destructive=False):
        raise NotImplementedError("Subclasses must implement the update_bmesh method")

    def ray_cast(self, context):
        raise NotImplementedError("Subclasses must implement the ray_cast method")

    def _invoke(self, context, event):
        raise NotImplementedError("Subclasses must implement the _invoke method")

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True

        if self.pref.bisect.running:
            col = layout.column(align=True)
            col.prop(self.pref.bisect.plane, "location", text="Location")
            col.prop(self.pref.bisect.plane, "normal", text="Normal")
            layout.prop(self.pref.bisect, "mode", text="Mode")
            layout.prop(self.pref.bisect, "flip", text="Flip")
            return

        shape = self.shape.active
        match shape:
            case "RECTANGLE":
                rect = self.shape.rectangle
                col = layout.column(align=True)
                col.prop(rect, "size", text="Dimensions")
                col = layout.column(align=True, heading="Symmetry")
                row = col.row(align=True)
                row.prop(rect, "symmetry_x", toggle=True)
                row.prop(rect, "symmetry_y", toggle=True)
                layout.prop(self.pref, "offset", text="Offset")
                col = layout.column(align=True, heading="Bevel")
                row = col.row(align=True)
                row.prop(self.pref.bevel.round, "enable", text="Round", toggle=True)
                row.prop(self.pref.bevel.round, "offset", text="")
                row.prop(self.pref.bevel.round, "segments", text="")
            case "TRIANGLE":
                tri = self.shape.triangle
                col = layout.column(align=True)
                col.prop(tri, "height")
                col.prop(tri, "angle")
                col = layout.column(align=True, heading="Equilateral")
                row = col.row(align=True)
                row.prop(tri, "equilateral", toggle=True)
                col.prop(tri, "flip", toggle=True)
                layout.prop(self.pref, "offset", text="Offset")
                col = layout.column(align=True, heading="Bevel")
                row = col.row(align=True)
                row.prop(self.pref.bevel.round, "enable", text="Round", toggle=True)
                row.prop(self.pref.bevel.round, "offset", text="")
                row.prop(self.pref.bevel.round, "segments", text="")
            case "PRISM":
                pri = self.shape.prism
                col = layout.column(align=True)
                col.prop(pri, "height")
                col.prop(pri, "angle")
                col.prop(pri, "extrusion", text="Z")
                col = layout.column(align=True, heading="Equilateral")
                row = col.row(align=True)
                row.prop(pri, "equilateral", toggle=True)
                col.prop(pri, "flip", toggle=True)
                row.prop(pri, "symmetry_extrude", toggle=True)
                layout.prop(self.pref, "offset", text="Offset")
                col = layout.column(align=True, heading="Bevel")
                row = col.row(align=True)
                row.prop(self.pref.bevel.round, "enable", text="Round", toggle=True)
                row.prop(self.pref.bevel.round, "offset", text="")
                row.prop(self.pref.bevel.round, "segments", text="")
                row = col.row(align=True)
                row.prop(self.pref.bevel.fill, "enable", text="Fill", toggle=True)
                row.prop(self.pref.bevel.fill, "offset", text="")
                row.prop(self.pref.bevel.fill, "segments", text="")
            case "BOX":
                box = self.shape.box
                col = layout.column(align=True)
                col.prop(box, "size", text="Dimensions")
                col.prop(box, "extrusion", text="Z")
                col = layout.column(align=True, heading="Symmetry")
                row = col.row(align=True)
                row.prop(box, "symmetry_x", toggle=True)
                row.prop(box, "symmetry_y", toggle=True)
                row.prop(box, "symmetry_extrude", toggle=True)
                layout.prop(self.pref, "offset", text="Offset")
                col = layout.column(align=True, heading="Bevel")
                row = col.row(align=True)
                row.prop(self.pref.bevel.round, "enable", text="Round", toggle=True)
                row.prop(self.pref.bevel.round, "offset", text="")
                row.prop(self.pref.bevel.round, "segments", text="")
                row = col.row(align=True)
                row.prop(self.pref.bevel.fill, "enable", text="Fill", toggle=True)
                row.prop(self.pref.bevel.fill, "offset", text="")
                row.prop(self.pref.bevel.fill, "segments", text="")
            case "CIRCLE":
                cir = self.shape.circle
                layout.prop(cir, "radius", text="Radius")
                layout.prop(cir, "verts", text="Verts")
                layout.prop(self.pref, "offset", text="Offset")
            case "CYLINDER":
                cyl = self.shape.cylinder
                layout.prop(cyl, "radius", text="Radius")
                layout.prop(cyl, "extrusion", text="Dimensions Z")
                col = layout.column(align=True, heading="Symmetry")
                col.prop(cyl, "symmetry_extrude", toggle=True)
                layout.prop(cyl, "verts", text="Verts")
                layout.prop(self.pref, "offset", text="Offset")
                col = layout.column(align=True, heading="Bevel")
                row = col.row(align=True)
                row.prop(self.pref.bevel.fill, "enable", text="Fill", toggle=True)
                row.prop(self.pref.bevel.fill, "offset", text="")
                row.prop(self.pref.bevel.fill, "segments", text="")
            case "SPHERE":
                sph = self.shape.sphere
                layout.prop(sph, "radius", text="Radius")
                layout.prop(sph, "subdivisions", text="Subdivisions")
            case "CORNER":
                cor = self.shape.corner
                layout.prop(cor, "size", text="Dimensions")
                layout.prop(cor, "extrusion", text="Dimensions Z")
                layout.prop(self.pref, "offset", text="Offset")
                col = layout.column(align=True, heading="Bevel")
                row = col.row(align=True)
                row.prop(self.pref.bevel.round, "enable", text="Round", toggle=True)
                row.prop(self.pref.bevel.round, "offset", text="")
                row.prop(self.pref.bevel.round, "segments", text="")
                col = layout.column(align=True, heading="Rotation")
                col.prop(cor, "rotation_a", text="Rotation A")
                col.prop(cor, "rotation_b", text="B")
            case "NGON":
                layout.prop(self.pref, "offset", text="Offset")
                col = layout.column(align=True, heading="Bevel")
                row = col.row(align=True)
                row.prop(self.pref.bevel.round, "enable", text="Round", toggle=True)
                row.prop(self.pref.bevel.round, "offset", text="")
                row.prop(self.pref.bevel.round, "segments", text="")
            case "NHEDRON":
                nhe = self.shape.nhedron
                col = layout.column(align=True)
                col.prop(nhe, "extrusion", text="Z")
                layout.prop(self.pref, "offset", text="Offset")
                col = layout.column(align=True, heading="Bevel")
                row = col.row(align=True)
                row.prop(self.pref.bevel.round, "enable", text="Round", toggle=True)
                row.prop(self.pref.bevel.round, "offset", text="")
                row.prop(self.pref.bevel.round, "segments", text="")
                row = col.row(align=True)
                row.prop(self.pref.bevel.fill, "enable", text="Fill", toggle=True)
                row.prop(self.pref.bevel.fill, "offset", text="")
                row.prop(self.pref.bevel.fill, "segments", text="")

        col = layout.column(align=True)
        row = col.row(align=True)
        row.prop(self.pref, "origin_local", index=0, text="Origin")
        row.prop(self.pref, "origin_local", index=1, text="")
        row.prop(self.pref, "origin_local", index=2, text="")
        row = col.row(align=True)
        row.prop(self.pref, "rotate_x", text="Rotation")
        row.prop(self.pref, "rotate_y", text="")
        row.prop(self.pref, "rotate_z", text="")
        row = col.row(align=True)
        row.prop(self.pref, "scale_factor", index=0, text="Scale")
        row.prop(self.pref, "scale_factor", index=1, text="")
        row.prop(self.pref, "scale_factor", index=2, text="")

        if self.pref.mode != "ADD":
            col = layout.column(align=True)
            align = addon.pref().tools.block.align
            col.prop(align, "solver", text="Boolean Solver")

    def _hide_transform_gizmo(self, context):
        self.pref.transform_gizmo = context.space_data.show_gizmo_context
        context.space_data.show_gizmo_context = False

    def _restore_transform_gizmo(self, context):
        context.space_data.show_gizmo_context = self.pref.transform_gizmo

    def _infobar(self, layout, context, event):
        ui.hotkeys(self, layout, context, event)

    def _recalculate_normals(self, bm, faces_indexes):
        bm.faces.ensure_lookup_table()
        faces = [
            bm.faces[index] for index in faces_indexes if 0 <= index < len(bm.faces)
        ]
        if faces:
            bmesh.ops.recalc_face_normals(bm, faces=faces)

    def store_props(self):
        self.pref.bisect.plane.origin = self.data.bisect.plane[0]
        self.pref.bisect.plane.normal = self.data.bisect.plane[1]
        self.pref.bisect.flip = self.data.bisect.flip
        self.pref.bisect.mode = self.data.bisect.mode
        self.pref.plane.origin = self.data.draw.matrix.location
        self.pref.plane.normal = self.data.draw.matrix.normal
        self.pref.direction = self.data.draw.matrix.direction
        sd = self.shape.data
        if hasattr(sd, "extrusion"):
            sd.extrusion = self.data.extrude.value
        if hasattr(sd, "symmetry_extrude"):
            sd.symmetry_extrude = self.data.extrude.symmetry
        self.pref.mode = self.config.mode
        self.pref.bevel.round.enable = self.data.bevel.round.enable
        self.pref.bevel.round.offset = self.data.bevel.round.offset
        self.pref.bevel.round.segments = self.data.bevel.round.segments
        self.pref.bevel.fill.enable = self.data.bevel.fill.enable
        self.pref.bevel.fill.offset = self.data.bevel.fill.offset
        self.pref.bevel.fill.segments = self.data.bevel.fill.segments
        self.pref.detected = self.objects.detected
        if self.config.mode != "ADD":
            self.pref.offset = self.config.align.offset

    def save_props(self):
        addon.pref().tools.block.form.bevel_segments = self.pref.bevel.round.segments
        verts = getattr(self.shape.data, "verts", None)
        if verts is not None:
            addon.pref().tools.block.form.circle_verts = verts

    def set_offset(self):
        if self.state.is_bisect:
            return

        # CORNER has two draw faces at different normals; ``corner.offset``
        # (called from ``extrude.invoke``) handles its bottom offset per-face,
        # so skip the single-face base-normal shift here.
        if self.config.shape == "CORNER":
            self._offset_applied = True
            return

        bm = self.data.bm
        obj = self.data.obj
        face = self.data.bm.faces[self.data.draw.faces[0]]
        normal = self.data.draw.matrix.normal
        offset = self.config.align.offset

        if self.config.mode != "ADD":
            facet.set_z(face, normal, offset)

        self.update_bmesh(obj, bm, loop_triangles=True, destructive=True)
        self._offset_applied = True

    def _apply_offset_if_needed(self):
        """Apply the 2D draw-plane offset once, when exiting a 2D CREATE stage.

        Called before each MODIFY entry (via B/G/R/S) and at the top of
        `_advance_spine` (EDIT/EXTRUDE/finalize). Skipped in BISECT and once
        the offset has already been baked. Idempotent via `_offset_applied`.
        """
        if getattr(self, "_offset_applied", False):
            return
        if self.state.is_bisect:
            return
        if self.state.phase not in {"DRAW", "EDIT"}:
            return
        if self.is_3d:
            return
        self.set_offset()

    def invoke(self, context, event):

        # Exit rule: the first LMB event (press OR release) after phase
        # entry advances the spine. Second/later LMB events in the same
        # phase are ignored. Keyboard confirm (SPACE/RET/NUMPAD_ENTER)
        # always advances on press.
        self._lmb_advance_fired = False
        self._last_phase = ""

        self._hide_transform_gizmo(context)
        self.config = self.set_config(context)
        self.shape.active = self.config.shape
        self.pref.type = self.config.type
        self.get_tool_prpoerties()

        if self.config.type == "EDIT_MESH":
            if context.active_object and context.active_object.type == "MESH":
                context.active_object.select_set(True)

        mouse_region_prev_x, mouse_region_prev_y = view3d.get_mouse_region_prev(event)
        self.mouse.init = Vector((mouse_region_prev_x, mouse_region_prev_y))
        self.ray = self.ray_cast(context)

        self.objects.selected = [
            obj for obj in context.selected_objects if obj.type == "MESH"
        ]
        self.objects.active = (
            context.active_object
            if context.active_object
            and context.active_object.type == "MESH"
            and context.active_object.select_get()
            else None
        )
        self.objects.detected = (
            self.ray.obj.name
            if self.ray.hit
            else self.objects.active.name
            if self.objects.active
            else self.objects.selected[0].name
            if self.objects.selected
            else ""
        )

        if len(self.objects.selected) > 0:
            if not context.scene.bout.align.mode == "CUSTOM" and not self.ray.hit:
                self.state.phase = "BISECT"
                self.pref.bisect.running = True
        else:
            if not self.ray.hit:
                if self.config.mode != "ADD":
                    if self.config.type == "OBJECT":
                        self.report(
                            {"WARNING"}, "No mesh detected: Please select object"
                        )
                        return {"CANCELLED"}

        self.data.obj = self.get_object(context)
        self.data.bm = self.build_bmesh(self.data.obj)

        self._invoke(context, event)
        orientation.build(self, context)
        ui.setup(self, context)

        if not self.state.is_bisect:
            self.state.phase = "DRAW"
            # Capture the draw plane's world origin as the base for local
            # translate coordinates in the F9 redo panel (see Pref.origin_local).
            self.pref.plane.origin_local = tuple(self.data.draw.matrix.location)
            draw.update_ui(self, context)
            orientation.make_local(self)

            if self.config.type == "EDIT_MESH" and self.config.mode != "ADD":
                bpy.ops.mesh.select_all(action="DESELECT")
            created_mesh = self._draw_invoke(context, event)
            if not created_mesh:
                self._end(context)
                return {"CANCELLED"}

            sd = self.shape.data
            if sd is None or not getattr(sd, "stages", None):
                self.report({"ERROR"}, f"Unknown shape: {self.config.shape}")
                return {"CANCELLED"}

        context.window.cursor_set("SCROLL_XY")
        self._header(context)
        infobar.draw(context, event, self._infobar, blank=True)
        context.window_manager.modal_handler_add(self)
        return {"RUNNING_MODAL"}

    def execute(self, context):
        depsgraph = context.view_layer.depsgraph
        depsgraph.update()

        obj = self.get_object(context)
        bm = self.build_bmesh(obj)

        if self.pref.bisect.running:
            bisect_data = (
                self.pref.bisect.plane.origin,
                self.pref.bisect.plane.normal,
                self.pref.bisect.flip,
                self.pref.bisect.mode,
            )
            bisect.execute(self, context, obj, bm, bisect_data)
        else:
            # Capture the vert count before build so we can identify the
            # cutter's full range (self.data is None after _end, so
            # _apply_pref_transforms can't fall back to draw/extrude faces).
            bm.verts.ensure_lookup_table()
            verts_before = len(bm.verts)
            self.build_geometry(obj, bm)
            bm.verts.ensure_lookup_table()
            cutter_verts = list(range(verts_before, len(bm.verts)))
            self._apply_pref_transforms(obj, bm, vert_indices=cutter_verts)
            # Re-frame LAST, after _apply_pref_transforms' final bm.to_mesh.
            self._redo_finish(context, obj)
        self.save_props()

        return {"FINISHED"}

    def _apply_pref_transforms(self, obj, bm, vert_indices=None):
        """Re-apply committed rotate/scale pref values to the block's verts.

        `vert_indices` — explicit list of bmesh vert indices to transform.
        Use this from edit-mode rebuild flows that capture the cutter's full
        vert range (including bevel-added geometry). When None, falls back to
        walking draw+extrude faces.
        """
        rx = self.pref.rotate_x
        ry = self.pref.rotate_y
        rz = self.pref.rotate_z

        has_r = abs(rx) > 1e-9 or abs(ry) > 1e-9 or abs(rz) > 1e-9
        has_s = any(abs(c - 1.0) > 1e-9 for c in self.pref.scale_factor)
        if not (has_r or has_s):
            return

        factor = transform_common.safe_scale_factor(self.pref.scale_factor)

        bm.faces.ensure_lookup_table()
        bm.verts.ensure_lookup_table()
        bm.verts.index_update()

        n_verts = len(bm.verts)
        block_verts = []
        if vert_indices is not None:
            # Explicit list: caller knows the full cutter vert range
            # (including bevel-added geometry not in draw/extrude.faces).
            seen = set()
            for i in vert_indices:
                if 0 <= i < n_verts and i not in seen:
                    seen.add(i)
                    block_verts.append(bm.verts[i])
        elif self.data is not None:
            face_indices = list(self.data.draw.faces) + list(self.data.extrude.faces)
            n_faces = len(bm.faces)
            seen = set()
            for fi in face_indices:
                if 0 <= fi < n_faces:
                    for v in bm.faces[fi].verts:
                        key = id(v)
                        if key in seen:
                            continue
                        seen.add(key)
                        block_verts.append(v)
        if not block_verts:
            return

        x, y, z = transform_common.plane_basis_from_vectors(
            Vector(self.pref.plane.normal), Vector(self.pref.direction)
        )

        pivot = transform_common.pivot_from_verts(block_verts)
        if pivot is None:
            return

        # Compose rotate-then-scale to match live order: in modal each commit
        # operates on the bmesh state left by the previous commit, so a live
        # R then S sequence yields S(R(v)). Matrix multiplication on the
        # right composes inversely, so apply rotation first into M and scale
        # last on the outside.
        M = Matrix.Identity(4)
        if has_r:
            rot_m = Matrix.Identity(4)
            if abs(rx) > 1e-9:
                rot_m = Matrix.Rotation(rx, 4, x) @ rot_m
            if abs(ry) > 1e-9:
                rot_m = Matrix.Rotation(ry, 4, y) @ rot_m
            if abs(rz) > 1e-9:
                rot_m = Matrix.Rotation(rz, 4, z) @ rot_m
            M = Matrix.Translation(pivot) @ rot_m @ Matrix.Translation(-pivot) @ M
        if has_s:
            basis = Matrix(
                (
                    (x.x, y.x, z.x, 0.0),
                    (x.y, y.y, z.y, 0.0),
                    (x.z, y.z, z.z, 0.0),
                    (0.0, 0.0, 0.0, 1.0),
                )
            )
            basis_inv = basis.inverted_safe()
            S = Matrix.Diagonal(Vector((factor.x, factor.y, factor.z, 1.0)))
            scale_m = basis @ S @ basis_inv
            M = Matrix.Translation(pivot) @ scale_m @ Matrix.Translation(-pivot) @ M

        for v in block_verts:
            v.co = M @ v.co
        self.update_bmesh(obj, bm, loop_triangles=True, destructive=False)

    @safe
    def modal(self, context, event):
        if event.type == "MIDDLEMOUSE":
            return {"PASS_THROUGH"}

        # Phase entry: reset the LMB advance latch so the next LMB event
        # (press or release) advances the new phase. Also refresh the
        # infobar so G/R/S/B hotkey hints reflect the new phase (e.g.
        # "Move" only shows up when not already in TRANSLATE).
        # Note: numeric-input accept (`_force_advance` path) bypasses this
        # latch intentionally so typed values commit immediately.
        if self._last_phase != self.state.phase:
            self._lmb_advance_fired = False
            self._last_phase = self.state.phase
            ui.update(self, context, event)

        # Handle numeric input events
        result = numeric_input.modal(self, context, event)
        if result is not None:
            return result

        ni = self.data.numeric_input

        if event.type == "LEFT_CTRL":
            if event.value in {"PRESS", "RELEASE"}:
                self.config.snap = not self.config.snap

        # Skip mouse-based adjustments when in numeric input mode
        if event.type == "MOUSEMOVE" and not ni.active:
            self.mouse.co = Vector((event.mouse_region_x, event.mouse_region_y))

            match self.state.phase:
                case "DRAW":
                    self._draw_modal(context, event)
                case "EDIT":
                    edit.modal(self, context, event)
                case "EXTRUDE":
                    self._extrude_modal(context, event)
                case "BEVEL":
                    self._bevel_modal(context, event)
                case "TRANSLATE":
                    self._translate_modal(context, event)
                case "ROTATE":
                    self._rotate_modal(context, event)
                case "SCALE":
                    self._scale_modal(context, event)
                case "BISECT":
                    bisect.modal(self, context, event)

            self._header(context)

        elif event.type in {"LEFTMOUSE", "SPACE", "RET", "NUMPAD_ENTER"}:
            # Suppress the trailing release of the click that accepted a
            # numeric input — otherwise it would re-advance the phase we
            # just entered via the numeric accept.
            if (
                event.type == "LEFTMOUSE"
                and event.value == "RELEASE"
                and getattr(self, "_suppress_next_lmb_release", False)
            ):
                self._suppress_next_lmb_release = False
                return {"RUNNING_MODAL"}
            return self._advance_or_finalize(context, event)

        elif (
            event.type == "Q"
            and event.value == "PRESS"
            and self.config.type == "OBJECT"
        ):
            self.pref.reveal = True
            ui.update(self, context, event)

        elif event.type == "Q" and event.value == "RELEASE":
            self.pref.reveal = False
            ui.update(self, context, event)

        elif event.type == "B" and event.value == "PRESS":
            if self._enter_modify_bevel(context, event) is not None:
                return {"RUNNING_MODAL"}

        elif event.type == "G" and event.value == "PRESS":
            if self._enter_modify(context, event, "TRANSLATE") is not None:
                return {"RUNNING_MODAL"}

        elif event.type == "R" and event.value == "PRESS":
            if self._enter_modify(context, event, "ROTATE") is not None:
                return {"RUNNING_MODAL"}

        elif event.type == "S" and event.value == "PRESS":
            # S stays as bevel-segments while BEVEL sub is active.
            if self.state.phase == "BEVEL":
                if ni.active:
                    ni.stop()
                    self._header(context)
                    context.area.tag_redraw()
                self.data.bevel.mode = "SEGMENTS"
                self._bevel_invoke(context, event)
            else:
                if self._enter_modify(context, event, "SCALE") is not None:
                    return {"RUNNING_MODAL"}

        elif event.type in {"X", "Y", "Z"} and event.value == "PRESS":
            if self._handle_axis_key(context, event):
                return {"RUNNING_MODAL"}

        elif event.type == "WHEELUPMOUSE":
            if event.value == "PRESS":
                if self.state.phase == "BEVEL":
                    if self.data.bevel.mode != "SEGMENTS":
                        if self.data.bevel.type == "ROUND":
                            self.data.bevel.round.segments = min(
                                32, self.data.bevel.round.segments + 1
                            )
                        elif self.data.bevel.type == "FILL":
                            self.data.bevel.fill.segments = min(
                                32, self.data.bevel.fill.segments + 1
                            )
                        bevel.refresh(self, context)

        elif event.type == "WHEELDOWNMOUSE":
            if event.value == "PRESS":
                if self.state.phase == "BEVEL":
                    if self.data.bevel.mode != "SEGMENTS":
                        if self.data.bevel.type == "ROUND":
                            self.data.bevel.round.segments = max(
                                1, self.data.bevel.round.segments - 1
                            )
                        elif self.data.bevel.type == "FILL":
                            self.data.bevel.fill.segments = max(
                                1, self.data.bevel.fill.segments - 1
                            )
                        bevel.refresh(self, context)

        elif event.type == "F":
            if event.value == "PRESS":
                if self.state.is_bisect:
                    self.data.bisect.flip = not self.data.bisect.flip
                elif self.state.phase == "DRAW" and self.config.shape in {
                    "TRIANGLE",
                    "PRISM",
                }:
                    sd = self.shape.data
                    sd.flip = not sd.flip
                    self._header(context)
                    return {"RUNNING_MODAL"}

        elif event.type in {"RIGHTMOUSE", "ESC"} and event.value == "PRESS":
            self._cancel(context)
            return {"CANCELLED"}

        context.area.tag_redraw()
        return {"RUNNING_MODAL"}

    def _handle_axis_key(self, context, event):
        """Axis key routing.

        MODIFY: toggle shared axis_lock (X/Y/Z) following Blender's convention.
        Press X to constrain TO X (lock Y/Z); Shift+X to lock X (free Y/Z).
        Pressing the same combo again toggles the lock off. Axes unavailable
        in the current stage/phase are silently rejected — 2D TRANSLATE/SCALE
        rejects Z, and 2D ROTATE rejects all axis keys (rotation is fixed to
        the plane normal). Rotate ignores the Shift modifier.
        CREATE/DRAW: legacy symmetry toggles for rectangle/box/triangle/prism,
                     extrude symmetry on Z, edit-mode delete on X.
        """
        key = event.type

        if self.state.is_modify:
            is_2d = not self.is_3d
            if is_2d:
                if self.state.phase == "ROTATE":
                    # 2D rotate is always around the plane normal; X/Y/Z are no-ops.
                    return True
                if key == "Z":
                    return True
            # Rotate intentionally ignores Shift — axis always means "rotate
            # around this axis". For translate/scale, Shift flips to exclude.
            exclude = event.shift and self.state.phase != "ROTATE"
            current = self.data.transform.axis_lock
            current_exclude = self.data.transform.axis_lock_exclude
            if current == key and current_exclude == exclude:
                self.data.transform.axis_lock = ""
                self.data.transform.axis_lock_exclude = False
            else:
                self.data.transform.axis_lock = key
                self.data.transform.axis_lock_exclude = exclude
            self._refresh_active_modify(context)
            self._header(context)
            return True

        if (
            self.state.phase == "EDIT"
            and key == "X"
            and self.config.shape in {"NGON", "NHEDRON"}
        ):
            if getattr(self, "highlight_type", None) == "VERTEX":
                self.edit_mode = "DELETE"
                edit.modal(self, context, event)
                return True
            self._header(context)
            return True

        if self.state.phase == "DRAW":
            sd = self.shape.data
            if key == "X" and hasattr(sd, "symmetry_x"):
                sd.symmetry_x = not sd.symmetry_x
                self._header(context)
                return True
            if key == "X" and hasattr(sd, "equilateral"):
                sd.equilateral = not sd.equilateral
                self._header(context)
                return True
            if key == "Y" and hasattr(sd, "symmetry_y"):
                sd.symmetry_y = not sd.symmetry_y
                self._header(context)
                return True
            if key == "Z":
                self.data.extrude.symmetry = not self.data.extrude.symmetry
                return True

        if self.state.phase == "EXTRUDE" and key == "Z":
            self.data.extrude.symmetry = not self.data.extrude.symmetry
            return True

        return False

    def _refresh_active_modify(self, context):
        """Re-apply current modify sub-op after axis-lock change."""
        match self.state.phase:
            case "TRANSLATE":
                translate.refresh(self, context)
            case "ROTATE":
                rotate.refresh(self, context)
            case "SCALE":
                scale.refresh(self, context)
            case "BEVEL":
                bevel.refresh(self, context)

    def _enter_modify(self, context, event, sub):
        """Enter a MODIFY sub-op (TRANSLATE/ROTATE/SCALE).

        Blocked only in BISECT. Re-invoking the same sub re-baselines mouse.
        Commits the prior sub-op's values into pref first.
        """
        if self.state.is_bisect:
            return None

        ni = self.data.numeric_input
        if ni.active:
            ni.stop()
            self._header(context)
            context.area.tag_redraw()

        self._apply_offset_if_needed()

        if self.state.is_modify and self.state.phase != sub:
            self._commit_active_modify()

        # Stash CREATE phase for restore-on-commit.
        if self.state.phase in CREATE:
            self.data.transform.origin_phase = self.state.phase

        match sub:
            case "TRANSLATE":
                translate.invoke(self, context, event)
            case "ROTATE":
                rotate.invoke(self, context, event)
            case "SCALE":
                scale.invoke(self, context, event)

        self._header(context)
        ui.update(self, context, event)
        return True

    def _enter_modify_bevel(self, context, event):
        """Enter BEVEL; ``sd.bevel_*`` flags drive type/eligibility."""
        if self.state.is_bisect:
            return None

        ni = self.data.numeric_input
        if ni.active:
            ni.stop()
            self._header(context)
            context.area.tag_redraw()

        info = self.shape.data.bevel
        if info is None:
            return None

        if info.needs_3d and not self.is_3d:
            return True

        self.data.bevel.mode = "OFFSET"

        if info.type is not None:
            self.data.bevel.type = info.type
        elif info.toggles and self.state.phase == "BEVEL":
            self.data.bevel.type = (
                "ROUND" if self.data.bevel.type == "FILL" else "FILL"
            )

        if self.data.bevel.type != "ROUND":
            self.data.bevel.fill.segments = self.data.bevel.round.segments

        self._apply_offset_if_needed()

        if self.state.is_modify and self.state.phase != "BEVEL":
            self._commit_active_modify()

        # Stash CREATE phase for restore-on-commit.
        if self.state.phase in CREATE:
            self.data.transform.origin_phase = self.state.phase

        self._bevel_invoke(context, event)
        ui.update(self, context, event)
        return True

    def _force_advance(self, context, event):
        """Numeric-accept path: advance the spine immediately.

        Same phase-specific work as `_advance_or_finalize` (EXTRUDE normal
        recalc, MODIFY commit), but skips the LMB latch — numeric input is
        its own sub-modal and its accept gesture always advances.
        """
        if self.state.is_bisect:
            return {"RUNNING_MODAL"}
        if self.state.phase == "EDIT":
            return {"RUNNING_MODAL"}
        if self.state.phase == "EXTRUDE":
            self._recalculate_normals(self.data.bm, self.data.extrude.faces)
            self.update_bmesh(
                self.data.obj,
                self.data.bm,
                loop_triangles=True,
                destructive=True,
            )
            return self._advance_spine(context, event)
        if self.state.is_modify:
            self._commit_active_modify()
            return self._advance_spine(context, event)
        if self.state.phase == "DRAW":
            return self._advance_spine(context, event)
        return {"RUNNING_MODAL"}

    def _advance_or_finalize(self, context, event):
        """Advance the spine or finalize.

        LMB: the first press-or-release in the phase advances; subsequent
        LMB events are ignored (latched by `_lmb_advance_fired`, reset on
        phase change). Keyboard confirm (SPACE/RET/NUMPAD_ENTER) advances
        on press. EDIT keeps its own sub-FSM; BISECT fires immediately.
        """
        ni = self.data.numeric_input
        if ni.active:
            ni.stop()
            self._header(context)

        value = event.value

        if self.state.is_bisect:
            bisect_data = (
                self.data.bisect.plane[0],
                self.data.bisect.plane[1],
                self.data.bisect.flip,
                self.data.bisect.mode,
            )
            bisect.execute(self, context, self.data.obj, self.data.bm, bisect_data)
            return self._finalize(context)

        if self.state.phase == "EDIT":
            return self._edit_advance(context, event, value)

        if event.type == "LEFTMOUSE":
            if self._lmb_advance_fired:
                return {"RUNNING_MODAL"}
            self._lmb_advance_fired = True
        else:  # SPACE / RET / NUMPAD_ENTER
            if value != "PRESS":
                return {"RUNNING_MODAL"}

        if self.state.phase == "DRAW":
            return self._advance_spine(context, event)

        if self.state.phase == "EXTRUDE":
            self._recalculate_normals(self.data.bm, self.data.extrude.faces)
            self.update_bmesh(
                self.data.obj,
                self.data.bm,
                loop_triangles=True,
                destructive=True,
            )
            return self._advance_spine(context, event)

        if self.state.is_modify:
            self._commit_active_modify()
            return self._advance_spine(context, event)

        return {"RUNNING_MODAL"}

    def _edit_advance(self, context, event, value):
        """EDIT meta state transitions."""
        if value == "PRESS":
            self.edit_mode = "GET"
            return {"RUNNING_MODAL"}
        # RELEASE
        if self.config.shape == "NHEDRON" and self.edit_mode == "END":
            return self._advance_spine(context, event)
        if self.edit_mode != "END":
            self.edit_mode = "NONE"
            return {"RUNNING_MODAL"}
        # NGON end-of-edit
        return self._advance_spine(context, event)

    def _commit_active_modify(self):
        """Persist current modify sub-op values to pref, and restore
        ``state.phase`` to the CREATE phase the detour was entered from.
        """
        match self.state.phase:
            case "TRANSLATE":
                translate.commit(self)
            case "ROTATE":
                rotate.commit(self)
            case "SCALE":
                scale.commit(self)
        if self.data.transform.origin_phase:
            self.state.phase = self.data.transform.origin_phase
            self.data.transform.origin_phase = ""

    def _advance_spine(self, context, event):
        """Step to the next CREATE stage for the current shape, or finalize.

        MODIFY is not in the spine; it's reached only by B/G/R/S and always
        leaves back to the *next* CREATE stage (or finalize) on LMB press.
        Calls go through `self._*_invoke` so subclass overrides (e.g. obj.py
        adding boolean modifiers, mesh.py snapshotting) fire.

        Offset is applied here — the single exit point from every 2D CREATE
        stage — so it always runs before the next stage or finalize.
        """
        self._apply_offset_if_needed()

        sd = self.shape.data
        next_sub = sd.next_phase(self.state.phase)
        if next_sub is None:
            return self._finalize(context)

        if next_sub == "EDIT":
            edit.invoke(self, context)
        elif next_sub == "EXTRUDE":
            self._extrude_invoke(context, event)
            # Fixed-depth extrude: skip straight to BEVEL so the user can
            # dial in the round on the mid edge instead. Stash EXTRUDE as
            # origin_phase so commit's spine walk still terminates here.
            if sd.bevel and sd.bevel.after_extrude and self.config.mode in {"CUT", "CARVE"}:
                self.data.transform.origin_phase = "EXTRUDE"
                self._bevel_invoke(context, event)
        else:
            self.state.phase = next_sub
        ui.update(self, context, event)
        return {"RUNNING_MODAL"}

    def _finalize(self, context):
        self.store_props()
        self.save_props()
        self._finish(context)
        return {"FINISHED"}

    def _finish(self, context):
        self._end(context)

    def _cancel(self, context):
        self._end(context)

    def _end(self, context):
        self._restore_transform_gizmo(context)

        # Hygiene: clear modify-layer state so the next invocation starts
        # without stale axis-lock or active sub-op carried over.
        self.data.transform.axis_lock = ""
        self.data.transform.axis_lock_exclude = False
        self.data.transform.active = ""

        for mesh in self.data.copy.all:
            bpy.data.meshes.remove(mesh)

        self.mouse = None
        self.ray = None
        self.data = None
        self.config = None
        self.objects = None
        self.modifiers = None

        self.ui.clear()
        self.ui.clear_higlight()

        context.window.cursor_set("CROSSHAIR")
        context.area.header_text_set(text=None)
        infobar.remove(context)

    def _set_parent(self, child_obj, parent_obj):
        parent_world = parent_obj.matrix_world.copy()
        child_obj.parent = parent_obj
        child_obj.matrix_parent_inverse = parent_world.inverted()

    def _header_text(self):
        raise NotImplementedError("Subclasses must implement the _header method")

    def _header(self, context):
        if self.state.is_bisect:
            header = (
                f"Bisec: mode:{self.data.bisect.mode}, flip:{self.data.bisect.flip}"
            )
            context.area.header_text_set(text=header)
            return

        text = self._header_text()
        ni = self.data.numeric_input

        shape = self.config.shape
        sd = self.shape.data
        z_length = self.data.extrude.value
        dimensions = ""

        phase = self.state.phase
        in_draw = phase == "DRAW"

        if phase == "BEVEL":
            text = "Bevel"
            offset = numeric_input._get_bevel_value(self, is_offset=True)
            segments = numeric_input._get_bevel_value(self, is_offset=False)
            offset_str = ni.format_value(0, offset)
            seg_str = ni.format_value(1, segments, is_int=True)
            dimensions = (
                f"Type:{self.data.bevel.type}, Offset:{offset_str}, Segments:{seg_str}"
            )
        elif phase == "TRANSLATE":
            text = "Translate"
            tr = self.data.transform.translate
            lock = self.data.transform.axis_lock
            exclude = self.data.transform.axis_lock_exclude
            is_2d = not self.is_3d
            lock_idx = {"X": 0, "Y": 1, "Z": 2}.get(lock)
            all_axes = ["X", "Y"] if is_2d else ["X", "Y", "Z"]
            if lock:
                active = [a for a in all_axes if a != lock] if exclude else [lock]
            else:
                active = all_axes
            axis_label = "".join(active) if active else "Free"

            def fmt(idx, v):
                if lock_idx is not None:
                    fixed = (idx == lock_idx) if exclude else (idx != lock_idx)
                    if fixed:
                        return "locked"
                return ni.format_value(idx, v)

            dx = fmt(0, tr.delta.x)
            dy = fmt(1, tr.delta.y)
            if is_2d:
                dimensions = f"[{axis_label}] Dx:{dx}, Dy:{dy}"
            else:
                dz = fmt(2, tr.delta.z)
                dimensions = f"[{axis_label}] Dx:{dx}, Dy:{dy}, Dz:{dz}"
        elif phase == "ROTATE":
            text = "Rotate"
            ro = self.data.transform.rotate
            lock = self.data.transform.axis_lock
            is_2d = not self.is_3d
            # 2D rotate is always around the plane normal; lock is ignored there.
            axis_label = "Z" if is_2d else (lock if lock else "Free")
            a_str = ni.format_value(0, math.degrees(ro.angle))
            dimensions = f"[{axis_label}] Angle:{a_str}°"
        elif phase == "SCALE":
            text = "Scale"
            sc = self.data.transform.scale
            lock = self.data.transform.axis_lock
            exclude = self.data.transform.axis_lock_exclude
            is_2d = not self.is_3d
            lock_idx = {"X": 0, "Y": 1, "Z": 2}.get(lock)
            all_axes = ["X", "Y"] if is_2d else ["X", "Y", "Z"]
            if lock:
                active = [a for a in all_axes if a != lock] if exclude else [lock]
            else:
                active = all_axes
            axis_label = "".join(active) if active else "XYZ"

            def fmt(idx, v):
                if lock_idx is not None:
                    fixed = (idx == lock_idx) if exclude else (idx != lock_idx)
                    if fixed:
                        return "locked"
                return ni.format_value(idx, v)

            sx = fmt(0, sc.factor.x)
            sy = fmt(1, sc.factor.y)
            if is_2d:
                dimensions = f"[{axis_label}] Sx:{sx}, Sy:{sy}"
            else:
                sz = fmt(2, sc.factor.z)
                dimensions = f"[{axis_label}] Sx:{sx}, Sy:{sy}, Sz:{sz}"
        else:
            match shape:
                case "RECTANGLE":
                    x_length, y_length = sd.size
                    x_str = ni.format_value(0, x_length)
                    y_str = ni.format_value(1, y_length)
                    dimensions = f" Dx:{x_str},  Dy:{y_str}"
                case "TRIANGLE":
                    h_str = ni.format_value(0, sd.height)
                    a_str = ni.format_value(1, sd.angle)
                    dimensions = f" Height:{h_str},  Angle:{a_str}"
                case "CIRCLE":
                    r_str = ni.format_value(0, sd.radius)
                    dimensions = f" Radius:{r_str}"
                case "BOX":
                    x_length, y_length = sd.size
                    if in_draw:
                        x_str = ni.format_value(0, x_length)
                        y_str = ni.format_value(1, y_length)
                        dimensions = f" Dx:{x_str},  Dy:{y_str},  Dz:{z_length:.4f}"
                    else:
                        z_str = ni.format_value(0, z_length)
                        dimensions = (
                            f" Dx:{x_length:.4f},  Dy:{y_length:.4f},  Dz:{z_str}"
                        )
                case "CYLINDER":
                    radius = sd.radius
                    if in_draw:
                        r_str = ni.format_value(0, radius)
                        dimensions = f" Radius:{r_str},  Dz:{z_length:.4f}"
                    else:
                        z_str = ni.format_value(0, z_length)
                        dimensions = f" Radius:{radius:.4f},  Dz:{z_str}"
                case "PRISM":
                    height = sd.height
                    angle = sd.angle
                    if in_draw:
                        h_str = ni.format_value(0, height)
                        a_str = ni.format_value(1, angle)
                        dimensions = (
                            f" Height:{h_str},  Angle:{a_str},  Dz:{z_length:.4f}"
                        )
                    else:
                        z_str = ni.format_value(0, z_length)
                        dimensions = (
                            f" Height:{height:.4f},  Angle:{angle:.4f},  Dz:{z_str}"
                        )
                case "SPHERE":
                    r_str = ni.format_value(0, sd.radius)
                    dimensions = f" Radius:{r_str}"
                case "CORNER":
                    cx, cy = sd.size
                    x_str = ni.format_value(0, cx)
                    y_str = ni.format_value(1, cy)
                    dimensions = f" Dx:{x_str},  Dy:{y_str}"
                case _:
                    # NGON, NHEDRON, or other shapes without numeric display
                    dimensions = ""

        header = f"{text} {dimensions}"
        context.area.header_text_set(text=header)

    def _draw_invoke(self, context, event):
        raise NotImplementedError("Subclasses must implement the _draw_invoke method")

    def _draw_modal(self, context, event):
        draw.modal(self, context, event)

    def _extrude_invoke(self, context, event):
        extrude.invoke(self, context, event)

    def _extrude_modal(self, context, event):
        extrude.modal(self, context, event)

    def _bevel_invoke(self, context, event):
        bevel.invoke(self, context, event)

    def _bevel_modal(self, context, event):
        bevel.modal(self, context, event)

    def _translate_modal(self, context, event):
        translate.modal(self, context, event)

    def _rotate_modal(self, context, event):
        rotate.modal(self, context, event)

    def _scale_modal(self, context, event):
        scale.modal(self, context, event)
