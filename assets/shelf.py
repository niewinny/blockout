import bpy


class Blockout_AST_AssetShelf(bpy.types.AssetShelf):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'ASSET_SHELF'
    bl_idname = "VIEW3D_AST_blockout_shelf"
    bl_label = "Blockout Shelf"
    bl_options = {'DEFAULT_VISIBLE'}
    bl_default_preview_size = 32

    asset_library_reference = 'CUSTOM'

    @classmethod
    def poll(cls, context):
        active_tool = context.workspace.tools.from_space_view3d_mode(context.mode, create=False)
        blockout_tool = active_tool and active_tool.idname == 'bout.block_obj'
        return context.mode == 'OBJECT' and blockout_tool

    @classmethod
    def asset_poll(cls, asset):
        if asset.id_type == 'OBJECT':
            meta = asset.metadata
            if "Blockout" in meta.tags:
                return True
        return False
