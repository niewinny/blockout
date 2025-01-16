import bpy
from . import mesh
from . import obj
from . import tools
from . import block


class Theme(bpy.types.PropertyGroup):
    mesh: bpy.props.PointerProperty(type=mesh.Theme)
    obj: bpy.props.PointerProperty(type=obj.Theme)
    block: bpy.props.PointerProperty(type=block.ui.Theme)


class Scene(bpy.types.PropertyGroup):
    obj: bpy.props.PointerProperty(type=obj.Scene)


types_classes = (
    *mesh.types_classes,
    *obj.types_classes,
    *block.types_classes,
    Scene,
    Theme,
)


classes = (
    *mesh.classes,
    *obj.classes,
    *block.classes,
    *tools.classes,
)
