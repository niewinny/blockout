import bpy
from . import mesh
from . import obj
from . import custom


class Custom(bpy.types.PropertyGroup):
    location: bpy.props.FloatVectorProperty(name="Location", default=(0, 0, 0), subtype='XYZ', update=custom.redraw)
    normal: bpy.props.FloatVectorProperty(name="Normal", default=(0, 0, 1), subtype='XYZ', update=custom.redraw)
    direction: bpy.props.FloatVectorProperty(name="Direction", default=(1, 0, 0), subtype='XYZ', update=custom.redraw)


class Grid(bpy.types.PropertyGroup):
    enable: bpy.props.BoolProperty(name="Enable", default=False, update=custom.redraw)
    spacing: bpy.props.FloatProperty(name="Spacing", default=0.1, min=0.001, subtype='DISTANCE', update=custom.redraw)
    size: bpy.props.FloatProperty(name="Size", default=4, min=0, subtype='DISTANCE', update=custom.redraw)


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
    grid: bpy.props.PointerProperty(type=Grid)
    offset: bpy.props.FloatProperty(name="Offset", description="Offset the mesh above the drawing plane", default=0.001, subtype='DISTANCE')


class Form(bpy.types.PropertyGroup):
    increments: bpy.props.FloatProperty(name="Increments", description="Round the values to the nearest increment", default=0.1, subtype='DISTANCE')
    origin: bpy.props.EnumProperty(
        name="Origin",
        description="Origin",
        items=[('CENTER', 'Center', 'Center'),
                ('CORNER', 'Corner', 'Corner'),
                ('PARENT', 'Parent', 'Parent')],
        default='CENTER')
    segments: bpy.props.IntProperty(name="Bevel Segments", description="Number of bevel segments", default=1, min=1, max=32)


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
    Grid,
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
