import bpy
from . import mesh
from . import obj


class Custom(bpy.types.PropertyGroup):
    location: bpy.props.FloatVectorProperty(name="Location", default=(0, 0, 0), subtype='XYZ')
    normal: bpy.props.FloatVectorProperty(name="Normal", default=(0, 0, 1), subtype='XYZ')
    angle: bpy.props.FloatProperty(name="Direction", default=0.0, subtype='ANGLE')


class Align(bpy.types.PropertyGroup):
    mode: bpy.props.EnumProperty(
        name="Mode",
        description="Mode",
        items=[('FACE', 'Face', 'Face'),
               ('VIEW', 'View', 'View'),
               ('CUSTOM', 'Custom', 'Custom')],
        default='FACE')
    view: bpy.props.EnumProperty(
        name="Orientation",
        description="View Orientation",
        items=[('WORLD', 'World', 'World'),
               ('OBJECT', 'Object', 'Object'),
               ('CURSOR', 'Cursor', 'Cursor')],
        default='WORLD')
    face: bpy.props.EnumProperty(
        name="Orientation",
        description="Face Orientation",
        items=[('CLOSEST', 'Closest Edge', 'Closest'),
               ('LONGEST', 'Longest Edge', 'Longest'),
               ('NORMAL', 'Normal', 'Normal')],
        default='CLOSEST')
    custom: bpy.props.PointerProperty(type=Custom)
    offset: bpy.props.FloatProperty(name="Offset", default=0.0, subtype='DISTANCE')


class Form(bpy.types.PropertyGroup):
    increments: bpy.props.FloatProperty(name="Increments", default=0.0, min=0.0, subtype='DISTANCE')


class Scene(bpy.types.PropertyGroup):
    mesh: bpy.props.PointerProperty(type=mesh.Scene)
    obj: bpy.props.PointerProperty(type=obj.Scene)


class Pref(bpy.types.PropertyGroup):
    mesh: bpy.props.PointerProperty(type=mesh.Pref)
    obj: bpy.props.PointerProperty(type=obj.Pref)
    align: bpy.props.PointerProperty(type=Align)
    form: bpy.props.PointerProperty(type=Form)


types_classes = (
    Custom,
    Align,
    Form,
    *mesh.types_classes,
    *obj.types_classes,
    Pref,
    Scene,
)


classes = (
    *obj.classes,
    *mesh.classes,
)
