import bpy
from . import custom


shapes = [('BOX', 'Box', 'Box', 'MESH_CUBE', 1),
          ('CYLINDER', 'Cylinder', 'Cylinder', 'MESH_CYLINDER', 2),
          ('RECTANGLE', 'Rectangle', 'Rectangle', 'MESH_PLANE', 3),
          ('NGON', 'N-gon', 'N-gon', 'LIGHTPROBE_PLANE', 4),
          ('NHEDRON', 'N-hedron', 'N-hedron', 'LIGHTPROBE_SPHERE', 5),
          ('CIRCLE', 'Circle', 'Circle', 'MESH_CIRCLE', 6),
          ('SPHERE', 'Sphere', 'Sphere', 'MESH_UVSPHERE', 7),
          ('CORNER', 'Corner', 'Corner', 'AREA_DOCK', 8),]


modes = [('CUT', 'Cut', 'Cut'),
         ('ADD', 'Add', 'Add'),
         ('SLICE', 'Slice', 'Slice'),
         ('INTERSECT', 'Intersect', 'Intersect'),
         ('CARVE', 'Carve', 'Carve'),
         ('UNION', 'Union', 'Union')]


class Align(bpy.types.PropertyGroup):
    face: bpy.props.EnumProperty(
        name="Orientation",
        description="Face Orientation",
        items=[('EDGE', 'Edge', 'Orient drawing plane using the closest edge of the face'),
               ('PLANAR', 'Planar', 'Orient drawing plane using the face normal and viewport up vector')],
        default='EDGE')
    absolute: bpy.props.BoolProperty(name="Absolute", default=False)
    offset: bpy.props.FloatProperty(name="Offset", description="Offset the mesh above the drawing plane", default=0.001, subtype='DISTANCE')
    increments: bpy.props.FloatProperty(name="Increments", description="Round the values to the nearest increment", default=0.1, subtype='DISTANCE')


class Form(bpy.types.PropertyGroup):
    bevel_segments: bpy.props.IntProperty(name="Bevel Segments", description="Number of bevel segments", default=1, min=1, max=32)
    circle_verts: bpy.props.IntProperty(name="Verts", description="Circle Verts", default=32, min=3, max=256)


types_classes = (
    Align,
    Form,
)
