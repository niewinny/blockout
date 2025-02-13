import bpy
import os
from . import shelf


def register():
    # Add asset library to Blender preferences if it doesn't already exist
    assets_path = os.path.dirname(__file__)
    asset_libraries = bpy.context.preferences.filepaths.asset_libraries
    if not any(library.name == "blockout" for library in asset_libraries):
        asset_libraries.new(name="blockout", directory=assets_path)


def unregister():
    # Remove asset library from Blender preferences if it exists
    asset_libraries = bpy.context.preferences.filepaths.asset_libraries
    for library in asset_libraries:
        if library.name == "blockout":
            asset_libraries.remove(library)
            break


classes = (
    shelf.Blockout_AST_AssetShelf,
)
