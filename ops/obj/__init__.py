import bpy

from . import draw

class Theme(bpy.types.PropertyGroup):
    draw: bpy.props.PointerProperty(type=draw.Theme)


types_classes = (
    *draw.types_classes,
    Theme,
)


classes = (
    *draw.classes,
)
