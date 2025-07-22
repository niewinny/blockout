import bpy
from . import booleans
from . import object
from . import bevel


classes = (
    booleans.BOUT_MT_ObjectBoolean,
    bevel.BOUT_MT_BevelMenu,
    object.BOUT_MT_ObjectMode,
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
