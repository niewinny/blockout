import bpy
from . import blockout
from . import block2d
from . import block


class Scene(bpy.types.PropertyGroup):
    blockout: bpy.props.PointerProperty(type=blockout.Scene)
    block2d: bpy.props.PointerProperty(type=block2d.Scene)
    block: bpy.props.PointerProperty(type=block.Scene)


types_classes = (
    *blockout.types_classes,
    *block2d.types_classes,
    *block.types_classes,
    Scene,
)


classes = (
    *block.classes,
)
