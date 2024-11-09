import bpy

from . import sketch

class Theme(bpy.types.PropertyGroup):
    draw: bpy.props.PointerProperty(type=sketch.Theme)


types_classes = (
    *sketch.types_classes,
    Theme,
)


classes = (
    *sketch.classes,
)
