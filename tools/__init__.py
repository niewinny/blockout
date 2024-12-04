import bpy
from . import sketch
from . import block


class Scene(bpy.types.PropertyGroup):
    sketch: bpy.props.PointerProperty(type=sketch.Scene)
    block: bpy.props.PointerProperty(type=block.Scene)


types_classes = (
    *sketch.types_classes,
    *block.types_classes,
    Scene,
)


classes = (
    *block.classes,
)
