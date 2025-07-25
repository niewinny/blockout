import bpy
from . import bevel
from . import boolean
from . import custom_plane
from . import veil
from . import apply_modifiers
from . import matrix_store


class Theme(bpy.types.PropertyGroup):
    bevel: bpy.props.PointerProperty(type=bevel.Theme)


class Scene(bpy.types.PropertyGroup):
    bevel: bpy.props.PointerProperty(type=bevel.Scene)


types_classes = (
    *bevel.types_classes,
    *apply_modifiers.types_classes,
    *matrix_store.types_classes,
    Theme,
    Scene,
)


classes = (
    *bevel.classes,
    *boolean.classes,
    *custom_plane.classes,
    *veil.classes,
    *apply_modifiers.classes,
    *matrix_store.classes,
)
