import bpy
from bpy.utils import register_class, unregister_class, register_tool, unregister_tool
from . import btypes, ops, ui, preferences, tools, gizmo, keymap


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

    register_tool(tools.blockout.BOUT_MT_Blockout, group=True, separator=True)
    register_tool(tools.block2d.BOUT_MT_Mesh_Block2D, group=False, separator=False, after={'bout.blockout'})
    register_tool(tools.sketch.mesh.BOUT_MT_Sketch, group=False, separator=False, after={'bout.block2d'})

    register_tool(tools.sketch.obj.BOUT_MT_SketchObj, group=True, separator=True)

    btypes.register()
    keymap.register()


def unregister():

    keymap.unregister()

    unregister_tool(tools.sketch.obj.BOUT_MT_SketchObj)

    unregister_tool(tools.sketch.mesh.BOUT_MT_Sketch)
    unregister_tool(tools.blockout.BOUT_MT_Blockout)
    unregister_tool(tools.block2d.BOUT_MT_Mesh_Block2D)

    for cls in reversed(classes):
        unregister_class(cls)

    btypes.unregister()
