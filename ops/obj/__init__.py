import bpy
from . import bevel
from . import boolean
from . import custom_plane


class Theme(bpy.types.PropertyGroup):
    bevel: bpy.props.PointerProperty(type=bevel.Theme)


class Scene(bpy.types.PropertyGroup):
    bevel: bpy.props.PointerProperty(type=bevel.Scene)


types_classes = (
    *bevel.types_classes,
    Theme,
    Scene,
)


classes = (
    *bevel.classes,
    *boolean.classes,
    *custom_plane.classes,
)
