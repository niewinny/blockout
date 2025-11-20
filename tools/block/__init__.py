import bpy
from . import mesh
from . import obj
from . import data


class Pref(bpy.types.PropertyGroup):
    shape: bpy.props.EnumProperty(
        name="Shape", description="Shape", items=data.shapes, default="BOX"
    )
    mode: bpy.props.EnumProperty(
        name="Mode", description="Mode", items=data.modes, default="ADD"
    )
    align: bpy.props.PointerProperty(type=data.Align)
    form: bpy.props.PointerProperty(type=data.Form)


types_classes = (
    *data.types_classes,
    Pref,
)

classes = (
    *obj.classes,
    *mesh.classes,
)
