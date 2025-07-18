import bpy


class BOUT_MT_BevelMenu(bpy.types.Menu):
    bl_idname = "BOUT_MT_BevelMenu"
    bl_label = "Bevel"

    def draw(self, _context):
        layout = self.layout
        layout.operator_context = "INVOKE_DEFAULT"

        layout.operator("bout.mod_bevel_single", text="Bevel Single (Unpinned)")
        layout.operator("bout.mod_bevel_all", text="Bevel All (Unpinned)")
        layout.separator()
        layout.operator("bout.mod_bevel_pinned", text="Bevel Pinned")


classes = (
    BOUT_MT_BevelMenu,
)