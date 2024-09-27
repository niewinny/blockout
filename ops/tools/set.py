import bpy


class BOUT_OT_SetActiveToolOperator(bpy.types.Operator):
    """Set Active Tool to Brush Select"""
    bl_idname = "bout.set_active_tool"
    bl_label = "Set Active Tool"

    def execute(self, context):
        active_edit_mode_tool = bpy.context.workspace.tools.from_space_view3d_mode('EDIT_MESH', create=False).idname
        if active_edit_mode_tool != 'bout.blockout':
            bpy.ops.wm.tool_set_by_id(name="bout.blockout")
        else:
            bpy.ops.wm.tool_set_by_id(name="bout.block2d")
        return {'FINISHED'}
