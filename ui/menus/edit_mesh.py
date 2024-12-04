import bpy
from ... import bl_info


class BOUT_MT_Edit_Mesh(bpy.types.Menu):
    bl_idname = "BOUT_MT_Edit_Mesh"
    bl_label = f"bout: {bl_info['version'][0]}.{bl_info['version'][1]}.{bl_info['version'][2]}"

    def draw(self, _context):
        layout = self.layout
        layout.operator_context = "INVOKE_DEFAULT"

        layout.operator("bout.bevel", text="Bevel")
        layout.operator("bout.edge_expand", text="Edge Expand")
        layout.operator("bout.loop_bisect", text="Loop Bisect")
        layout.operator("bout.match_face", text="Match Face")
        layout.operator("bout.sweep", text="Sweep")

        layout.separator()

