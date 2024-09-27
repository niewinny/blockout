import bpy
from . import mesh
from . import tools


class Theme(bpy.types.PropertyGroup):
    mesh: bpy.props.PointerProperty(type=mesh.Theme)


types_classes = (
    *mesh.types_classes,
    Theme,
)


classes = (
    *mesh.classes,
    *tools.classes,
)
