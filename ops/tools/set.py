import bpy


class BOUT_OT_SetActiveToolOperator(bpy.types.Operator):
    """Set Active Tool to Brush Select"""

    bl_idname = "edit_mesh.bout_set_active_tool"
    bl_label = "Set Active Tool"

    edit_mode: bpy.props.BoolProperty(name="Edit Mode", default=False)

    def execute(self, context):
        active_tool = context.workspace.tools.from_space_view3d_mode(
            context.mode, create=False
        ).idname

        tools = ["object.bout_block_obj", "object.bout_block_mesh"]

        if self.edit_mode:
            if active_tool not in tools:
                bpy.ops.wm.tool_set_by_id(name="object.bout_block_mesh")

        else:
            if active_tool not in tools:
                bpy.ops.wm.tool_set_by_id(name="object.bout_block_obj")

        return {"FINISHED"}
