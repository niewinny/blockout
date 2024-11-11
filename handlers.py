import bpy
from . tools.sketch import custom


def bout_depsgraph_handler(scene, depsgraph):
    '''Handler called after the dependency graph is updated'''
    custom.update(bpy.context)


def register():
    bpy.app.handlers.depsgraph_update_pre.append(bout_depsgraph_handler)


def unregister():
    bpy.app.handlers.depsgraph_update_pre.remove(bout_depsgraph_handler)
