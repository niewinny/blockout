import bpy
from . import bevel
from . import boolean
from . import custom_plane
from . import veil
from . import apply_modifiers
from . import clean_cutter


class Theme(bpy.types.PropertyGroup):
    bevel: bpy.props.PointerProperty(type=bevel.Theme)


class Scene(bpy.types.PropertyGroup):
    bevel: bpy.props.PointerProperty(type=bevel.Scene)


types_classes = (
    *bevel.types_classes,
    *apply_modifiers.types_classes,
    Theme,
    Scene,
)


classes = (
    *bevel.classes,
    *boolean.classes,
    *custom_plane.classes,
    *veil.classes,
    *apply_modifiers.classes,
    *clean_cutter.classes,
)
