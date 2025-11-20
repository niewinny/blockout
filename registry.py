from bpy.utils import register_class, unregister_class, register_tool, unregister_tool
from . import btypes, ops, ui, preferences, tools, gizmo, keymap, handlers


classes = (
    *btypes.classes,
    *preferences.classes,
    *ops.classes,
    *tools.classes,
    *gizmo.classes,
    *ui.classes,
)


def register():
    for cls in classes:
        register_class(cls)

    register_tool(tools.block.mesh.BOUT_MT_Block, group=False, separator=True)
    register_tool(tools.block.obj.BOUT_MT_BlockObj, group=False, separator=True)

    btypes.register()
    keymap.register()
    handlers.register()
    ui.register()


def unregister():
    ui.unregister()
    handlers.unregister()
    keymap.unregister()

    unregister_tool(tools.block.obj.BOUT_MT_BlockObj)
    unregister_tool(tools.block.mesh.BOUT_MT_Block)

    for cls in reversed(classes):
        unregister_class(cls)

    btypes.unregister()
