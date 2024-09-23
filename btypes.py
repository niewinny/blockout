import bpy
from . import ops, tools


class Tools(bpy.types.PropertyGroup):
    block2d: bpy.props.PointerProperty(type=tools.block2d.Pref)


class Scene(bpy.types.PropertyGroup):
    tools: bpy.props.PointerProperty(type=tools.Scene)


class Theme(bpy.types.PropertyGroup):
    ops: bpy.props.PointerProperty(type=ops.Theme)


classes = [
    *ops.types_classes,
    *tools.types_classes,
    Tools,
    Scene,
    Theme,
]


def register():
    bpy.types.Scene.nsolve = bpy.props.PointerProperty(type=Scene)


def unregister():

    del bpy.types.Scene.nsolve
