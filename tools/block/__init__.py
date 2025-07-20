import bpy
from . import mesh
from . import obj
from . import data


class Pref(bpy.types.PropertyGroup):
    shape: bpy.props.EnumProperty(name="Shape",description="Shape", items=data.shapes, default='BOX')
    mode: bpy.props.EnumProperty(name="Mode",description="Mode", items=data.modes, default='ADD')
    mesh: bpy.props.PointerProperty(type=mesh.Pref)
    obj: bpy.props.PointerProperty(type=obj.Pref)
    align: bpy.props.PointerProperty(type=data.Align)
    form: bpy.props.PointerProperty(type=data.Form)
    settings: bpy.props.PointerProperty(type=data.Settings)


types_classes = (
    *data.types_classes,
    *mesh.types_classes,
    *obj.types_classes,
    Pref,
)

classes = (
    *obj.classes,
    *mesh.classes,
)
