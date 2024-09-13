import bpy
from . import mesh


class theme(bpy.types.PropertyGroup):
    mesh: bpy.props.PointerProperty(type=mesh.theme)


types_classes = (
    *mesh.types_classes,
    theme,
)


classes = (
    *mesh.classes,
)
