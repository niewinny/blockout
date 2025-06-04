import bpy
from ... import bl_info


class BOUT_MT_Edit_Mesh(bpy.types.Menu):
    bl_idname = "BOUT_MT_Edit_Mesh"
    bl_label = f"Blockout: {bl_info['version'][0]}.{bl_info['version'][1]}.{bl_info['version'][2]}"

    def draw(self, _context):
        layout = self.layout
        layout.operator_context = "INVOKE_DEFAULT"

        layout.separator()
