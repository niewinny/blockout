import bpy
from . import blockout
from . import block2d
from . import sketch
from . import sketch_obj


class Scene(bpy.types.PropertyGroup):
    blockout: bpy.props.PointerProperty(type=blockout.Scene)
    block2d: bpy.props.PointerProperty(type=block2d.Scene)
    sketch: bpy.props.PointerProperty(type=sketch.Scene)
    sketch_obj: bpy.props.PointerProperty(type=sketch_obj.Scene)


types_classes = (
    *blockout.types_classes,
    *block2d.types_classes,
    *sketch.types_classes,
    *sketch_obj.types_classes,
    Scene,
)
