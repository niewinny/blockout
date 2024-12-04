import bpy
from . import ops, tools, src


class Tools(bpy.types.PropertyGroup):
    sketch: bpy.props.PointerProperty(type=tools.sketch.Pref)
    block: bpy.props.PointerProperty(type=tools.block.Pref)


class Scene(bpy.types.PropertyGroup):
    tools: bpy.props.PointerProperty(type=tools.Scene)


class ThemeAxis(bpy.types.PropertyGroup):
    x: bpy.props.FloatVectorProperty(name="Axis X", description="X axis color", default=(1.0, 0.2, 0.322, 0.4), subtype='COLOR', size=4, min=0.0, max=1.0)
    y: bpy.props.FloatVectorProperty(name="Y", description="Y axis colo", default=(0.545, 0.863, 0.0, 0.4), subtype='COLOR', size=4, min=0.0, max=1.0)
    z: bpy.props.FloatVectorProperty(name="Z", description="Z axis colo", default=(0.157, 0.564, 1.0, 0.4), subtype='COLOR', size=4, min=0.0, max=1.0)


class Theme(bpy.types.PropertyGroup):
    ops: bpy.props.PointerProperty(type=ops.Theme)
    src: bpy.props.PointerProperty(type=src.Theme)
    axis: bpy.props.PointerProperty(type=ThemeAxis)


classes = [
    *src.types_classes,
    *ops.types_classes,
    *tools.types_classes,
    Tools,
    Scene,
    ThemeAxis,
    Theme,
]


def register():
    bpy.types.Scene.nsolve = bpy.props.PointerProperty(type=Scene)


def unregister():

    del bpy.types.Scene.nsolve
