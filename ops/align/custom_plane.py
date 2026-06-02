"""Modal operator to interactively re-position or re-orient the custom plane.

Replaces the non-modal Alt+Space "move custom plane" binding. The user aims at any
visible mesh: a 50%-alpha ghost of the plane shows where it lands when confirmed -
the in-plane X/Y axes in the gizmo theme colours plus a blue arrow along the plane
normal. It runs whether or not the custom plane is already on - confirming turns
custom mode on.

Three interactive sub-modes, cycled with Tab (starts in COMBINED):
- MOVE     - relocate the plane to the hovered element, keep orientation.
- ROTATE   - re-orient the plane to the element normal, keep location.
- COMBINED - relocate AND re-orient the plane to the hovered element.
"""

import bpy
import bmesh
from mathutils import Vector

from ...utils import addon
from ...utils.scene import ray_cast
from ...utils.types import DrawMatrix
from ...utilsbmesh.orientation import set_align_rotation_from_vectors
from ...shaders.draw import DrawPolyline, DrawLine
from . import snap


# The plane ghost uses the gizmo axis theme (X/Y in-plane, Z/blue normal arrow);
# the mode is conveyed by the status text.
MODE_ORDER = ("MOVE", "ROTATE", "COMBINED")
MODE_LABEL = {
    "MOVE": "Move (position)",
    "ROTATE": "Orient (rotation)",
    "COMBINED": "Move + Orient",
}
AXIS_ALPHA = 0.5  # ghost axes use the gizmo theme hue at this alpha


class BOUT_OT_AlignCustomPlane(bpy.types.Operator):
    bl_idname = "object.bout_align_custom_plane"
    bl_label = "Align Custom Plane"
    bl_description = (
        "Interactively move or re-orient the custom plane by snapping to geometry\n"
        " • Move mouse - snap to vert/edge/face under cursor\n"
        " • TAB - cycle Move / Orient / Move+Orient\n"
        " • LMB / SPACE - confirm\n"
        " • RMB / ESC - cancel"
    )
    bl_options = {"REGISTER", "UNDO"}

    mode: bpy.props.EnumProperty(
        name="Mode",
        description="Initial interactive mode",
        items=[
            ("MOVE", "Move", "Move the plane, keep its orientation"),
            ("ROTATE", "Orient", "Re-orient the plane, keep its location"),
            ("COMBINED", "Move + Orient", "Move the plane and re-orient it to the element"),
        ],
        default="COMBINED",
    )

    @classmethod
    def poll(cls, context):
        # Runs whether or not the custom plane is already on; confirming turns it on.
        return context.mode in {"OBJECT", "EDIT_MESH"}

    def invoke(self, context, event):
        align = context.scene.bout.align

        # Snapshot the stored plane matrix (it persists even when custom is off) so
        # MOVE can keep its orientation and ROTATE can keep its location.
        m = DrawMatrix.from_property(align.matrix)
        self.orig_location = m.location.copy()
        self.orig_normal = m.normal.copy()
        self.orig_direction = m.direction.copy()

        self._mode = self.mode
        self.preview = None  # (location, normal, direction) or None when no hit
        self.mouse = (event.mouse_region_x, event.mouse_region_y)

        self._setup_handlers(context)
        self._update_snap(context)
        self._set_status(context)

        context.window_manager.modal_handler_add(self)
        return {"RUNNING_MODAL"}

    def modal(self, context, event):
        context.area.tag_redraw()

        if event.type == "MOUSEMOVE":
            self.mouse = (event.mouse_region_x, event.mouse_region_y)
            self._update_snap(context)
            return {"RUNNING_MODAL"}

        if event.type == "TAB" and event.value == "PRESS":
            i = MODE_ORDER.index(self._mode)
            self._mode = MODE_ORDER[(i + 1) % len(MODE_ORDER)]
            self._update_snap(context)
            self._set_status(context)
            return {"RUNNING_MODAL"}

        if event.type in {"LEFTMOUSE", "SPACE", "RET", "NUMPAD_ENTER"} and event.value == "PRESS":
            self._commit(context)
            self._cleanup(context)
            return {"FINISHED"}

        if event.type in {"RIGHTMOUSE", "ESC"} and event.value == "PRESS":
            self._cleanup(context)
            return {"CANCELLED"}

        # No passthrough: consume every other event (including MMB navigation).
        return {"RUNNING_MODAL"}

    # --- snapping -----------------------------------------------------------

    def _update_snap(self, context):
        """Raycast under the cursor and rebuild the preview + highlight batches.

        Guarded as a whole: a degenerate hit can never crash the modal (which
        would abort it without cleanup and leak the draw handlers).
        """
        try:
            ray = ray_cast.visible(context, self.mouse, modes=("OBJECT", "EDIT"))

            if not ray.hit or ray.obj is None:
                self.preview = None
                self._draw_clear()
                return

            obj = ray.obj
            depsgraph = context.evaluated_depsgraph_get()
            obj_eval = obj.evaluated_get(depsgraph)
            me_eval = obj_eval.to_mesh()
            bm = bmesh.new()
            bm.from_mesh(me_eval)
            obj_eval.to_mesh_clear()
            bm.verts.ensure_lookup_table()
            bm.edges.ensure_lookup_table()
            bm.faces.ensure_lookup_table()

            try:
                element_type, element = snap.find_closest_element(
                    context, obj, ray.location, ray.index, bm
                )
                location, normal, direction, _ = snap.element_plane(
                    obj.matrix_world, element_type, element, ray
                )
            finally:
                bm.free()
                del obj_eval

            if self._mode == "MOVE":
                self.preview = (location, self.orig_normal, self.orig_direction)
            elif self._mode == "ROTATE":
                self.preview = (self.orig_location, normal, direction)
            else:  # COMBINED - take both position and orientation from the element
                self.preview = (location, normal, direction)

            self._draw_axes()
        except Exception:
            self.preview = None
            self._draw_clear()

    # --- drawing ------------------------------------------------------------

    @staticmethod
    def _axis_colors():
        """Ghost colours from the gizmo theme (X/Y in-plane, Z normal), at ghost alpha."""
        theme = addon.pref().theme.axis
        return (
            (*theme.x[:3], AXIS_ALPHA),
            (*theme.y[:3], AXIS_ALPHA),
            (*theme.z[:3], AXIS_ALPHA),
        )

    @staticmethod
    def _arrow_segments(origin, n_dir, x_dir, y_dir, length=1.0, head=0.18, width=0.07):
        """Finite normal arrow: a shaft plus a 4-pronged head visible from any angle."""
        tip = origin + n_dir * length
        base = origin + n_dir * (length - head)
        segments = [[origin, tip]]
        for perp in (x_dir, -x_dir, y_dir, -y_dir):
            segments.append([tip, base + perp * width])
        return segments

    def _setup_handlers(self, context):
        x_color, y_color, z_color = self._axis_colors()
        self._axis_x = DrawLine(points=[], width=2.0, color=x_color)
        self._axis_y = DrawLine(points=[], width=2.0, color=y_color)
        self._normal = DrawPolyline(points=[], width=2.5, color=z_color)

        self._handles = []
        for d in (self._axis_x, self._axis_y, self._normal):
            self._handles.append(
                bpy.types.SpaceView3D.draw_handler_add(
                    d.draw, (context,), "WINDOW", "POST_VIEW"
                )
            )

    def _draw_axes(self):
        if self.preview is None:
            self._axis_x.update_batch(points=[])
            self._axis_y.update_batch(points=[])
            self._normal.update_batch(points=[])
            return

        location, normal, direction = self.preview
        dm = DrawMatrix.new()
        dm.from_plane((location, normal.normalized()), direction.normalized())
        origin = dm.location
        x_dir = dm.direction.normalized()
        n_dir = dm.normal.normalized()
        y_dir = n_dir.cross(x_dir).normalized()

        x_color, y_color, z_color = self._axis_colors()
        self._axis_x.update_batch(points=[origin, origin + x_dir], color=x_color)
        self._axis_y.update_batch(points=[origin, origin + y_dir], color=y_color)
        self._normal.update_batch(
            points=self._arrow_segments(origin, n_dir, x_dir, y_dir), color=z_color
        )

    def _draw_clear(self):
        self._axis_x.update_batch(points=[])
        self._axis_y.update_batch(points=[])
        self._normal.update_batch(points=[])

    # --- commit / teardown --------------------------------------------------

    def _commit(self, context):
        if self.preview is None:
            return
        location, normal, direction = self.preview
        align = context.scene.bout.align

        draw_matrix = DrawMatrix.new()
        draw_matrix.from_plane((location, normal), direction)
        align.matrix = draw_matrix.to_property()
        align.location = location
        align.rotation = set_align_rotation_from_vectors(normal, direction)
        align.mode = "CUSTOM"

    def _set_status(self, context):
        context.workspace.status_text_set(
            f"Align Custom Plane: {MODE_LABEL[self._mode]}    "
            "[TAB] cycle mode    [LMB/SPACE] confirm    [RMB/ESC] cancel"
        )

    def _cleanup(self, context):
        for handle in getattr(self, "_handles", []):
            bpy.types.SpaceView3D.draw_handler_remove(handle, "WINDOW")
        self._handles = []
        context.workspace.status_text_set(None)
        context.area.tag_redraw()


classes = (BOUT_OT_AlignCustomPlane,)
