import bmesh
import bpy
from mathutils import Vector

from ...utils import addon, infobar, scene, view3d
from ...utilsbmesh import facet
from . import bevel, bisect, draw, edit, extrude, numeric_input, orientation, ui
from .data import Config, CreatedData, Modifiers, Mouse, Objects, Pref, Shape


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
        self.mode = "DRAW"
        self.edit_mode = "NONE"

    def set_config(self, context):
        """Set the options"""
        raise NotImplementedError("Subclasses must implement the set_options method")

    def get_tool_prpoerties(self):
        """Get the tool properties"""
        self.data.bevel.round.segments = addon.pref().tools.block.form.bevel_segments
        self.data.bevel.fill.segments = addon.pref().tools.block.form.bevel_segments
        self.shape.circle.verts = addon.pref().tools.block.form.circle_verts

    def get_object(self, context):
        """Set the object data"""
        raise NotImplementedError("Subclasses must implement the get_object method")

    def build_bmesh(self, obj):
        """Set the object data"""
        raise NotImplementedError("Subclasses must implement the get_object method")

    def build_geometry(self, obj, bm):
        """Build the geometry"""
        raise NotImplementedError("Subclasses must implement the build_geometry method")

    def update_bmesh(self, obj, bm, loop_triangles=False, destructive=False):
        """Update the bmesh data"""
        raise NotImplementedError("Subclasses must implement the update_bmesh method")

    def ray_cast(self, context):
        """Ray cast the scene"""
        raise NotImplementedError("Subclasses must implement the ray_cast method")

    def _invoke(self, context, event):
        """Invoke the operator"""
        raise NotImplementedError("Subclasses must implement the _invoke method")

    def draw(self, context):
        """Draw the operator"""
        layout = self.layout
        layout.use_property_split = True

        if self.pref.bisect.running:
            col = layout.column(align=True)
            col.prop(self.pref.bisect.plane, "location", text="Location")
            col.prop(self.pref.bisect.plane, "normal", text="Normal")
            layout.prop(self.pref.bisect, "mode", text="Mode")
            layout.prop(self.pref.bisect, "flip", text="Flip")
            return

        shape = self.pref.shape
        match shape:
            case "RECTANGLE":
                col = layout.column(align=True)
                col.prop(self.shape.rectangle, "co", text="Dimensions")
                col = layout.column(align=True, heading="Symmetry")
                row = col.row(align=True)
                row.prop(self.pref, "symmetry_draw_x", toggle=True)
                row.prop(self.pref, "symmetry_draw_y", toggle=True)
                layout.prop(self.pref, "offset", text="Offset")
                col = layout.column(align=True, heading="Bevel")
                row = col.row(align=True)
                row.prop(self.pref.bevel.round, "enable", text="Round", toggle=True)
                row.prop(self.pref.bevel.round, "offset", text="")
                row.prop(self.pref.bevel.round, "segments", text="")
            case "TRIANGLE":
                col = layout.column(align=True)
                col.prop(self.shape.triangle, "height")
                col.prop(self.shape.triangle, "angle")
                col = layout.column(align=True, heading="Symmetry")
                row = col.row(align=True)
                row.prop(self.shape.triangle, "symmetry", toggle=True)
                col.prop(self.shape.triangle, "flip", toggle=True)
                layout.prop(self.pref, "offset", text="Offset")
                col = layout.column(align=True, heading="Bevel")
                row = col.row(align=True)
                row.prop(self.pref.bevel.round, "enable", text="Round", toggle=True)
                row.prop(self.pref.bevel.round, "offset", text="")
                row.prop(self.pref.bevel.round, "segments", text="")
            case "PRISM":
                col = layout.column(align=True)
                col.prop(self.shape.triangle, "height")
                col.prop(self.shape.triangle, "angle")
                col.prop(self.pref, "extrusion", text="Z")
                col = layout.column(align=True, heading="Symmetry")
                row = col.row(align=True)
                row.prop(self.shape.triangle, "symmetry", toggle=True)
                col.prop(self.shape.triangle, "flip", toggle=True)
                row.prop(self.pref, "symmetry_extrude", toggle=True)
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
                col = layout.column(align=True)
                col.prop(self.shape.rectangle, "co", text="Dimensions")
                col.prop(self.pref, "extrusion", text="Z")
                col = layout.column(align=True, heading="Symmetry")
                row = col.row(align=True)
                row.prop(self.pref, "symmetry_draw_x", toggle=True)
                row.prop(self.pref, "symmetry_draw_y", toggle=True)
                row.prop(self.pref, "symmetry_extrude", toggle=True)
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
                layout.prop(self.shape.circle, "radius", text="Radius")
                layout.prop(self.shape.circle, "verts", text="Verts")
                layout.prop(self.pref, "offset", text="Offset")
            case "CYLINDER":
                layout.prop(self.shape.circle, "radius", text="Radius")
                layout.prop(self.pref, "extrusion", text="Dimensions Z")
                col = layout.column(align=True, heading="Symmetry")
                col.prop(self.pref, "symmetry_extrude", toggle=True)
                layout.prop(self.shape.circle, "verts", text="Verts")
                layout.prop(self.pref, "offset", text="Offset")
                col = layout.column(align=True, heading="Bevel")
                row = col.row(align=True)
                row.prop(self.pref.bevel.fill, "enable", text="Fill", toggle=True)
                row.prop(self.pref.bevel.fill, "offset", text="")
                row.prop(self.pref.bevel.fill, "segments", text="")
            case "SPHERE":
                layout.prop(self.shape.sphere, "radius", text="Radius")
                layout.prop(self.shape.sphere, "subd", text="Subdivisions")
            case "CORNER":
                layout.prop(self.shape.corner, "co", text="Dimensions")
                layout.prop(self.pref, "extrusion", text="Dimensions Z")
                layout.prop(self.pref, "offset", text="Offset")
                col = layout.column(align=True, heading="Bevel")
                row = col.row(align=True)
                row.prop(self.pref.bevel.round, "enable", text="Round", toggle=True)
                row.prop(self.pref.bevel.round, "offset", text="")
                row.prop(self.pref.bevel.round, "segments", text="")
                col = layout.column(align=True, heading="Rotation")
                col.prop(self.shape.corner, "min", text="Rotation Min")
                col.prop(self.shape.corner, "max", text="Max")
            case "NGON":
                layout.prop(self.pref, "offset", text="Offset")
                col = layout.column(align=True, heading="Bevel")
                row = col.row(align=True)
                row.prop(self.pref.bevel.round, "enable", text="Round", toggle=True)
                row.prop(self.pref.bevel.round, "offset", text="")
                row.prop(self.pref.bevel.round, "segments", text="")
            case "NHEDRON":
                col = layout.column(align=True)
                col.prop(self.pref, "extrusion", text="Z")
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
        """Draw the infobar hotkeys"""
        ui.hotkeys(self, layout, context, event)

    def _recalculate_normals(self, bm, faces_indexes):
        """Recalculate the normals"""
        faces = [bm.faces[index] for index in faces_indexes]
        bmesh.ops.recalc_face_normals(bm, faces=faces)

    def store_props(self):
        """Finish the operator"""
        self.pref.bisect.plane.location = self.data.bisect.plane[0]
        self.pref.bisect.plane.normal = self.data.bisect.plane[1]
        self.pref.bisect.flip = self.data.bisect.flip
        self.pref.bisect.mode = self.data.bisect.mode
        self.pref.plane.location = self.data.draw.matrix.location
        self.pref.plane.normal = self.data.draw.matrix.normal
        self.pref.direction = self.data.draw.matrix.direction
        self.pref.extrusion = self.data.extrude.value
        self.pref.symmetry_extrude = self.data.extrude.symmetry
        self.pref.symmetry_draw_x, self.pref.symmetry_draw_y = self.data.draw.symmetry
        self.pref.shape = self.config.shape
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
        """Store the properties"""
        addon.pref().tools.block.form.bevel_segments = self.pref.bevel.round.segments
        addon.pref().tools.block.form.circle_verts = self.shape.circle.verts

    def set_offset(self):
        """Set the offset"""
        if self.mode == "BISECT":
            return

        bm = self.data.bm
        obj = self.data.obj
        face = self.data.bm.faces[self.data.draw.faces[0]]
        normal = self.data.draw.matrix.normal
        offset = self.config.align.offset

        if self.config.mode != "ADD":
            facet.set_z(face, normal, offset)

        self.update_bmesh(obj, bm, loop_triangles=True, destructive=True)

    def invoke(self, context, event):
        """Start the operator"""

        self._hide_transform_gizmo(context)
        self.config = self.set_config(context)
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
                self.mode = "BISECT"
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

        if self.mode != "BISECT":
            draw.update_ui(self, context)
            orientation.make_local(self)

            if self.config.type == "EDIT_MESH" and self.config.mode != "ADD":
                bpy.ops.mesh.select_all(action="DESELECT")
            created_mesh = self._draw_invoke(context, event)
            if not created_mesh:
                self._end(context)
                return {"CANCELLED"}

        context.window.cursor_set("SCROLL_XY")
        self._header(context)
        infobar.draw(context, event, self._infobar, blank=True)
        context.window_manager.modal_handler_add(self)
        return {"RUNNING_MODAL"}

    def execute(self, context):
        """Execute the operator"""

        depsgraph = context.view_layer.depsgraph
        depsgraph.update()

        obj = self.get_object(context)
        bm = self.build_bmesh(obj)

        if self.pref.bisect.running:
            bisect_data = (
                self.pref.bisect.plane.location,
                self.pref.bisect.plane.normal,
                self.pref.bisect.flip,
                self.pref.bisect.mode,
            )
            bisect.execute(self, context, obj, bm, bisect_data)
        else:
            self.build_geometry(obj, bm)
        self.save_props()

        return {"FINISHED"}

    def modal(self, context, event):
        """Run the operator modal"""
        if event.type == "MIDDLEMOUSE":
            return {"PASS_THROUGH"}

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

            match self.mode:
                case "DRAW":
                    self._draw_modal(context, event)
                case "EXTRUDE":
                    self._extrude_modal(context, event)
                case "BEVEL":
                    self._bevel_modal(context, event)
                case "BISECT":
                    bisect.modal(self, context, event)
                case "EDIT":
                    edit.modal(self, context, event)

            self._header(context)

        elif event.type in {"LEFTMOUSE", "SPACE", "RET", "NUMPAD_ENTER"}:
            return self._return(context, event)

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

        elif event.type == "B":
            if event.value == "PRESS":
                if self.mode == "BISECT":
                    return {"RUNNING_MODAL"}
                if ni.active:
                    ni.stop()
                    self._header(context)
                    context.area.tag_redraw()

                if self.config.shape in {
                    "RECTANGLE",
                    "BOX",
                    "CYLINDER",
                    "CORNER",
                    "NGON",
                    "NHEDRON",
                    "TRIANGLE",
                    "PRISM",
                }:
                    self.data.bevel.mode = "OFFSET"

                    if self.config.shape in {"RECTANGLE", "NGON", "TRIANGLE"}:
                        self.data.bevel.type = "ROUND"

                    if self.config.shape == "CYLINDER":
                        if self.shape.volume == "2D":
                            return {"RUNNING_MODAL"}
                        self.data.bevel.type = "FILL"

                    if self.config.shape in {"BOX", "NHEDRON", "PRISM"}:
                        if self.mode == "BEVEL":
                            self.data.bevel.type = (
                                "ROUND" if self.data.bevel.type == "FILL" else "FILL"
                            )

                    if not self.data.bevel.type == "ROUND":
                        self.data.bevel.fill.segments = self.data.bevel.round.segments

                    self._bevel_invoke(context, event)

        elif event.type == "WHEELUPMOUSE":
            if event.value == "PRESS":
                if self.mode == "BEVEL":
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
                if self.mode == "BEVEL":
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

        elif event.type == "S":
            if event.value == "PRESS":
                if self.mode == "BEVEL":
                    if ni.active:
                        ni.stop()
                        self._header(context)
                        context.area.tag_redraw()
                    self.data.bevel.mode = "SEGMENTS"
                    self._bevel_invoke(context, event)

        elif event.type == "F":
            if event.value == "PRESS":
                if self.mode == "BISECT":
                    self.data.bisect.flip = not self.data.bisect.flip
                elif self.mode == "DRAW" and self.config.shape in {"TRIANGLE", "PRISM"}:
                    self.shape.triangle.flip = not self.shape.triangle.flip
                    self._header(context)
                    return {"RUNNING_MODAL"}

        elif event.type == "Z":
            if event.value == "PRESS":
                self.data.extrude.symmetry = not self.data.extrude.symmetry

        elif event.type == "X":
            if event.value == "PRESS":
                if self.mode == "EDIT" and self.config.shape in {"NGON", "NHEDRON"}:
                    # Check if we're highlighting a vertex (not an edge midpoint)
                    if (
                        hasattr(self, "highlight_type")
                        and self.highlight_type == "VERTEX"
                    ):
                        self.edit_mode = "DELETE"
                        edit.modal(self, context, event)
                        return {"RUNNING_MODAL"}
                    self._header(context)
                    return {"RUNNING_MODAL"}

                if self.mode == "DRAW" and self.config.shape in {
                    "RECTANGLE",
                    "BOX",
                }:
                    # Toggle X symmetry for rectangle/box shapes
                    self.data.draw.symmetry = (
                        not self.data.draw.symmetry[0],
                        self.data.draw.symmetry[1],
                    )
                    self._header(context)
                    return {"RUNNING_MODAL"}
                elif self.mode == "DRAW" and self.config.shape in {
                    "TRIANGLE",
                    "PRISM",
                }:
                    # Toggle triangle height symmetry
                    self.shape.triangle.symmetry = not self.shape.triangle.symmetry
                    self._header(context)
                    return {"RUNNING_MODAL"}

        elif event.type == "Y":
            if event.value == "PRESS":
                if self.mode == "DRAW" and self.config.shape in {
                    "RECTANGLE",
                    "BOX",
                }:
                    # Toggle Y symmetry for rectangle/box shapes
                    self.data.draw.symmetry = (
                        self.data.draw.symmetry[0],
                        not self.data.draw.symmetry[1],
                    )
                    self._header(context)
                    return {"RUNNING_MODAL"}

        elif event.type in {"RIGHTMOUSE", "ESC"}:
            self._cancel(context)
            self._end(context)
            return {"CANCELLED"}

        context.area.tag_redraw()
        return {"RUNNING_MODAL"}

    def _return(self, context, event, action=None):
        """Advance to the next mode on RELEASE, handle PRESS for specific modes."""
        # Stop numeric input when transitioning modes
        ni = self.data.numeric_input
        if ni.active:
            ni.stop()
            self._header(context)

        if self.shape.volume == "2D":
            self.set_offset()

        shape = self.config.shape
        value = action if action else event.value

        match (self.mode, value, shape):
            # DRAW RELEASE
            case ("DRAW", "RELEASE", "BOX" | "CYLINDER" | "PRISM"):
                self._extrude_invoke(context, event)
                bevel.update(self)
                return {"RUNNING_MODAL"}
            case ("DRAW", "RELEASE", "CORNER"):
                self._extrude_invoke(context, event)
                self._bevel_invoke(context, event)
                return {"RUNNING_MODAL"}
            case ("DRAW", "RELEASE", "NGON" | "NHEDRON"):
                edit.invoke(self, context)
                return {"RUNNING_MODAL"}

            # BEVEL PRESS - stay in bevel
            case ("BEVEL", "PRESS", "NGON" | "NHEDRON"):
                return {"RUNNING_MODAL"}
            # BEVEL RELEASE - only extrude if not already 3D
            case ("BEVEL", "RELEASE", "BOX" | "CYLINDER" | "PRISM" ) if (
                self.shape.volume != "3D"
            ):
                self._extrude_invoke(context, event)
                bevel.update(self)
                return {"RUNNING_MODAL"}
            case ("BEVEL", "RELEASE", "CORNER") if self.shape.volume != "3D":
                self._extrude_invoke(context, event)
                self._bevel_invoke(context, event)
                return {"RUNNING_MODAL"}
            case ("BEVEL", "RELEASE", "NHEDRON") if self.shape.volume != "3D":
                self._extrude_invoke(context, event)
                bevel.update(self)
                return {"RUNNING_MODAL"}
            case ("BEVEL", "RELEASE", _):
                # Already 3D, finalize
                pass

            # EXTRUDE
            case ("EXTRUDE", _, _):
                if self.config.mode == "ADD":
                    self._recalculate_normals(self.data.bm, self.data.extrude.faces)
                self.update_bmesh(
                    self.data.obj,
                    self.data.bm,
                    loop_triangles=True,
                    destructive=True,
                )

            # EDIT PRESS
            case ("EDIT", "PRESS", _):
                self.edit_mode = "GET"
                return {"RUNNING_MODAL"}
            # EDIT RELEASE
            case ("EDIT", "RELEASE", "NHEDRON") if self.edit_mode == "END":
                self._extrude_invoke(context, event)
                bevel.update(self)
                return {"RUNNING_MODAL"}
            case ("EDIT", "RELEASE", _):
                if self.edit_mode != "END":
                    self.edit_mode = "NONE"
                    return {"RUNNING_MODAL"}

            # BISECT
            case ("BISECT", _, _):
                bisect_data = (
                    self.data.bisect.plane[0],
                    self.data.bisect.plane[1],
                    self.data.bisect.flip,
                    self.data.bisect.mode,
                )
                bisect.execute(self, context, self.data.obj, self.data.bm, bisect_data)

        # Finalize
        self.store_props()
        self.save_props()
        self._finish(context)
        self._end(context)
        return {"FINISHED"}

    def _finish(self, context):
        """Finish the operator"""

    def _cancel(self, context):
        """Cancel the operator"""
        raise NotImplementedError("Subclasses must implement the _cancel method")

    def _end(self, context):
        """End the operator"""

        self._restore_transform_gizmo(context)

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
        """Set the header text"""
        raise NotImplementedError("Subclasses must implement the _header method")

    def _header(self, context):
        """Set the header text"""
        if self.mode == "BISECT":
            header = (
                f"Bisec: mode:{self.data.bisect.mode}, flip:{self.data.bisect.flip}"
            )
            context.area.header_text_set(text=header)
            return

        text = self._header_text()
        ni = self.data.numeric_input

        x_length, y_length = self.shape.rectangle.co
        z_length = self.data.extrude.value
        radius = self.shape.circle.radius
        dimentions = ""

        shape = self.config.shape
        if self.mode == "BEVEL":
            text = "Bevel"
            offset = numeric_input._get_bevel_value(self, is_offset=True)
            segments = numeric_input._get_bevel_value(self, is_offset=False)
            offset_str = ni.format_value(0, offset)
            seg_str = ni.format_value(1, segments, is_int=True)
            dimentions = (
                f"Type:{self.data.bevel.type}, Offset:{offset_str}, Segments:{seg_str}"
            )
        else:
            match shape:
                case "RECTANGLE":
                    x_str = ni.format_value(0, x_length)
                    y_str = ni.format_value(1, y_length)
                    dimentions = f" Dx:{x_str},  Dy:{y_str}"
                case "TRIANGLE":
                    height = self.shape.triangle.height
                    angle = self.shape.triangle.angle
                    h_str = ni.format_value(0, height)
                    a_str = ni.format_value(1, angle)
                    dimentions = f" Height:{h_str},  Angle:{a_str}"
                case "CIRCLE":
                    r_str = ni.format_value(0, radius)
                    dimentions = f" Radius:{r_str}"
                case "BOX":
                    if self.mode == "DRAW":
                        x_str = ni.format_value(0, x_length)
                        y_str = ni.format_value(1, y_length)
                        dimentions = f" Dx:{x_str},  Dy:{y_str},  Dz:{z_length:.4f}"
                    else:
                        z_str = ni.format_value(0, z_length)
                        dimentions = (
                            f" Dx:{x_length:.4f},  Dy:{y_length:.4f},  Dz:{z_str}"
                        )
                case "CYLINDER":
                    if self.mode == "DRAW":
                        r_str = ni.format_value(0, radius)
                        dimentions = f" Radius:{r_str},  Dz:{z_length:.4f}"
                    else:
                        z_str = ni.format_value(0, z_length)
                        dimentions = f" Radius:{radius:.4f},  Dz:{z_str}"
                case "PRISM":
                    height = self.shape.triangle.height
                    angle = self.shape.triangle.angle
                    if self.mode == "DRAW":
                        h_str = ni.format_value(0, height)
                        a_str = ni.format_value(1, angle)
                        dimentions = (
                            f" Height:{h_str},  Angle:{a_str},  Dz:{z_length:.4f}"
                        )
                    else:
                        z_str = ni.format_value(0, z_length)
                        dimentions = (
                            f" Height:{height:.4f},  Angle:{angle:.4f},  Dz:{z_str}"
                        )
                case "SPHERE":
                    r_str = ni.format_value(0, self.shape.sphere.radius)
                    dimentions = f" Radius:{r_str}"
                case "CORNER":
                    cx, cy = self.shape.corner.co
                    x_str = ni.format_value(0, cx)
                    y_str = ni.format_value(1, cy)
                    dimentions = f" Dx:{x_str},  Dy:{y_str}"
                case _:
                    # NGON, NHEDRON, or other shapes without numeric display
                    dimentions = ""

        header = f"{text} {dimentions}"
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
        """Bevel the mesh"""
        bevel.invoke(self, context, event)

    def _bevel_modal(self, context, event):
        """Bevel the mesh"""
        bevel.modal(self, context, event)
