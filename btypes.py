import bpy
from . import ops, tools


class Pref(bpy.types.PropertyGroup):
    tools: bpy.props.PointerProperty(type=tools.pref)


class Scene(bpy.types.PropertyGroup):
    tools: bpy.props.PointerProperty(type=tools.scene)


class Theme(bpy.types.PropertyGroup):
    ops: bpy.props.PointerProperty(type=ops.theme)


classes = [
    *ops.types_classes,
    *tools.types_classes,
    Pref,
    Scene,
    Theme,
]


def register():
    bpy.types.Scene.nsolve = bpy.props.PointerProperty(type=Scene)


def unregister():

    del bpy.types.Scene.nsolve
