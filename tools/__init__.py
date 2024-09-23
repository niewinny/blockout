import bpy
from . import blockout
from . import block2d


class Scene(bpy.types.PropertyGroup):
    blockout: bpy.props.PointerProperty(type=blockout.Scene)
    block2d: bpy.props.PointerProperty(type=block2d.Scene)


types_classes = (
    *blockout.types_classes,
    *block2d.types_classes,
    Scene,
)
