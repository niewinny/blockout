import bpy
from . import blockout
from . import block2d
from . import sketch


class Scene(bpy.types.PropertyGroup):
    blockout: bpy.props.PointerProperty(type=blockout.Scene)
    block2d: bpy.props.PointerProperty(type=block2d.Scene)
    sketch: bpy.props.PointerProperty(type=sketch.Scene)


types_classes = (
    *blockout.types_classes,
    *block2d.types_classes,
    *sketch.types_classes,
    Scene,
)
