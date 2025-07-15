import bpy


class BOUT_MT_ObjectMode(bpy.types.Menu):
    bl_idname = "BOUT_MT_ObjectMode"
    bl_label = "Blockout"

    def draw(self, _context):
        layout = self.layout
        layout.operator_context = "INVOKE_DEFAULT"

        layout.separator()

        layout.menu("BOUT_MT_ObjectBoolean")
        layout.operator("bout.mod_bevel")
        layout.operator("bout.apply_modifiers")

        layout.separator()

        layout.operator("bout.veil")
        layout.operator("bout.unveil")

        layout.separator()

        layout.menu("BOUT_MT_Asset")
