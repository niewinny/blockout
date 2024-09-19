import bpy
from . import blockout
from . import block2d


class scene(bpy.types.PropertyGroup):
    blockout: bpy.props.PointerProperty(type=blockout.scene)
    block2d: bpy.props.PointerProperty(type=block2d.scene)


types_classes = (
    *blockout.types_classes,
    *block2d.types_classes,
    scene,
)
