import bpy
from . import mesh
from . import obj
from . import data


class Scene(bpy.types.PropertyGroup):
    mesh: bpy.props.PointerProperty(type=mesh.Scene)
    obj: bpy.props.PointerProperty(type=obj.Scene)


class Pref(bpy.types.PropertyGroup):
    mesh: bpy.props.PointerProperty(type=mesh.Pref)
    obj: bpy.props.PointerProperty(type=obj.Pref)
    align: bpy.props.PointerProperty(type=data.Align)
    form: bpy.props.PointerProperty(type=data.Form)


types_classes = (
    *data.types_classes,
    *mesh.types_classes,
    *obj.types_classes,
    Pref,
    Scene,
)

classes = (
    *obj.classes,
    *mesh.classes,
)
