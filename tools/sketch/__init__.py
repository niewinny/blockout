import bpy
from . import mesh
from . import obj

from . import custom


class Custom(bpy.types.PropertyGroup):
    location: bpy.props.FloatVectorProperty(name="Location", default=(0, 0, 0), subtype='XYZ')
    normal: bpy.props.FloatVectorProperty(name="Normal", default=(0, 0, 1), subtype='XYZ')
    direction: bpy.props.FloatVectorProperty(name="Direction", default=(1, 0, 0), subtype='XYZ')


class Align(bpy.types.PropertyGroup):
    mode: bpy.props.EnumProperty(
        name="Mode",
        description="Mode",
        items=[('FACE', 'Face', 'Align the mesh to the face'),
               ('VIEW', 'View', 'Align the mesh to the viewport'),
               ('CUSTOM', 'Custom', 'Align the mesh to a custom plane')],
        default='FACE',
        update=custom.redraw)
    view: bpy.props.EnumProperty(
        name="Orientation",
        description="View Orientation",
        items=[('WORLD', 'World', 'Drawing plane origin is at the world origin'),
               ('OBJECT', 'Object', 'Drawing plane origin is at the object origin'),
               ('CURSOR', 'Cursor', 'Drawing plane origin is at the cursor location')],
        default='WORLD')
    face: bpy.props.EnumProperty(
        name="Orientation",
        description="Face Orientation",
        items=[('CLOSEST', 'Closest Edge', 'Orient drawing plane using the closest edge of the face'),
               ('LONGEST', 'Longest Edge', 'Orient drawing plane using the longest edge of the face'),
               ('PLANAR', 'Planar', 'Orient drawing plane using the face normal and viewport up vector')],
        default='CLOSEST')
    custom: bpy.props.PointerProperty(type=Custom)
    offset: bpy.props.FloatProperty(name="Offset", description="Offset the mesh above the drawing plane", default=0.0, subtype='DISTANCE')


class Form(bpy.types.PropertyGroup):
    increments: bpy.props.FloatProperty(name="Increments", description="Round the values to the nearest increment", default=0.0, subtype='DISTANCE')


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
