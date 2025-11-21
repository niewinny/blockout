import bpy

from ...shaders.draw import DrawLine
from ...utils import addon
from ...utils.types import DrawMatrix
from ..types.axis import BOUT_GT_CustomAxis


class BOUT_GGT_BlockoutAxis(bpy.types.GizmoGroup):
    bl_idname = "BOUT_GGT_BlockoutAxis"
    bl_label = "Blockout Axis Gizmo"
    bl_space_type = "VIEW_3D"
    bl_region_type = "WINDOW"
    bl_options = {"3D", "PERSISTENT", "SHOW_MODAL_ALL"}

    @classmethod
    def poll(cls, context):
        active_tool = context.workspace.tools.from_space_view3d_mode(
            context.mode, create=False
        )
        blockout_tool = active_tool and (
            active_tool.idname == "object.bout_block_obj"
            or active_tool.idname == "object.bout_block_mesh"
        )
        return blockout_tool and context.scene.bout.align.mode == "CUSTOM"

    def setup(self, context):
        self.custom_axis = self.gizmos.new(BOUT_GT_CustomAxis.bl_idname)
        self.custom_axis.use_draw_modal = True

    def refresh(self, context):
        custom_matrix = DrawMatrix.from_property(context.scene.bout.align.matrix)

        highlight = context.scene.bout.axis.highlight
        color = addon.pref().theme.axis

        value = 1.2
        x_color = (
            tuple(c * value if highlight.x else c for c in color.x[:3]) + (1,)
            if highlight.x
            else color.x
        )
        y_color = (
            tuple(c * value if highlight.y else c for c in color.y[:3]) + (1,)
            if highlight.y
            else color.y
        )

        world_origin = custom_matrix.location
        world_x_direction = custom_matrix.direction.normalized()
        world_normal = custom_matrix.normal.normalized()
        world_y_direction = world_normal.cross(world_x_direction).normalized()

        x_axis_point = world_origin + world_x_direction
        y_axis_point = world_origin + world_y_direction

        self.custom_axis.x_axis = DrawLine(
            points=[world_origin, x_axis_point], width=1.6, color=x_color
        )
        self.custom_axis.y_axis = DrawLine(
            points=[world_origin, y_axis_point], width=1.6, color=y_color
        )
