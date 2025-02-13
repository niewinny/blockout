import bpy
from bpy.utils import register_class, unregister_class, register_tool, unregister_tool
from . import btypes, ops, ui, preferences, tools, gizmo, keymap, handlers, assets


classes = (
    *btypes.classes,
    *preferences.classes,
    *ops.classes,
    *tools.classes,
    *assets.classes,
    *gizmo.classes,
    *ui.classes,
)


def register():

    for cls in classes:
        register_class(cls)

    register_tool(tools.block.mesh.BOUT_MT_Block, group=True, separator=True)
    register_tool(tools.sketch.BOUT_MT_Mesh_Sketch, group=False, separator=False, after={'bout.block'})

    register_tool(tools.block.obj.BOUT_MT_BlockObj, group=True, separator=True)


    assets.register()
    btypes.register()
    keymap.register()
    handlers.register()


def unregister():

    handlers.unregister()
    keymap.unregister()

    unregister_tool(tools.block.obj.BOUT_MT_BlockObj)

    unregister_tool(tools.block.mesh.BOUT_MT_Block)
    unregister_tool(tools.sketch.BOUT_MT_Mesh_Sketch)

    for cls in reversed(classes):
        unregister_class(cls)

    btypes.unregister()
    assets.unregister()
