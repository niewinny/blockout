import bpy


class BOUT_MT_BevelMenu(bpy.types.Menu):
    bl_idname = "BOUT_MT_BevelMenu"
    bl_label = "Bevel"

    def draw(self, _context):
        layout = self.layout
        layout.operator_context = "INVOKE_DEFAULT"

        op = layout.operator("bout.mod_bevel", text="Bevel Single (Unpinned)")
        op.all_mode = False
        
        op = layout.operator("bout.mod_bevel", text="Bevel All (Unpinned)")
        op.all_mode = True
        layout.separator()
        layout.operator("bout.mod_bevel_pinned", text="Bevel Pinned")


classes = (
    BOUT_MT_BevelMenu,
)