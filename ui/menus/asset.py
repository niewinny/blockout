import bpy


class BOUT_MT_Asset(bpy.types.Menu):
    bl_idname = "BOUT_MT_Asset"
    bl_label = "Assets"

    def draw(self, context):
        layout = self.layout
        layout.operator_context = "INVOKE_DEFAULT"

        layout.operator("bout.set_asset")
        layout.operator("bout.clear_asset")

        layout.separator()

        layout.operator("bout.open_assets_file")
