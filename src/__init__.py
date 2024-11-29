import bpy
from . import block


class Theme(bpy.types.PropertyGroup):
    block: bpy.props.PointerProperty(type=block.Theme)


types_classes = (
    *block.types_classes,
    Theme,
)
