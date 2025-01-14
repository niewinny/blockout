import bpy
from . import mesh
from . import obj
from . import tools


class Theme(bpy.types.PropertyGroup):
    mesh: bpy.props.PointerProperty(type=mesh.Theme)
    obj: bpy.props.PointerProperty(type=obj.Theme)


class Scene(bpy.types.PropertyGroup):
    obj: bpy.props.PointerProperty(type=obj.Scene)


types_classes = (
    *mesh.types_classes,
    *obj.types_classes,
    Scene,
    Theme,
)


classes = (
    *mesh.classes,
    *obj.classes,
    *tools.classes,
)
