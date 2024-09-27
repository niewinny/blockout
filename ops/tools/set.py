import bpy


class BOUT_OT_SetActiveToolOperator(bpy.types.Operator):
    """Set Active Tool to Brush Select"""
    bl_idname = "bout.set_active_tool"
    bl_label = "Set Active Tool"

    def execute(self, context):
        bpy.context.workspace.tools.active_tool = bpy.context.workspace.tools['bout.block2d']
        return {'FINISHED'}
