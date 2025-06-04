import bpy
from . import edit_mesh
from . import object
from . import asset


classes = (
    edit_mesh.BOUT_MT_Edit_Mesh,
    object.BOUT_MT_ObjectMode,
    asset.BOUT_MT_Asset,
)


def add_to_context_menu(self, context):
    """Add BOUT_MT_ObjectMode to the context menu"""
    if context.mode == 'OBJECT':
        self.layout.separator()
        self.layout.menu("BOUT_MT_ObjectMode")


def register():
    bpy.types.VIEW3D_MT_object_context_menu.append(add_to_context_menu)


def unregister():
    bpy.types.VIEW3D_MT_object_context_menu.remove(add_to_context_menu)
