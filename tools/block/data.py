import bpy

shapes = [
    ("BOX", "Box", "Box", "MESH_CUBE", 1),
    ("CYLINDER", "Cylinder", "Cylinder", "MESH_CYLINDER", 2),
    ("RECTANGLE", "Rectangle", "Rectangle", "MESH_PLANE", 3),
    ("NGON", "N-gon", "N-gon", "LIGHTPROBE_PLANE", 4),
    ("NHEDRON", "N-hedron", "N-hedron", "LIGHTPROBE_SPHERE", 5),
    ("CIRCLE", "Circle", "Circle", "MESH_CIRCLE", 6),
    ("SPHERE", "Sphere", "Sphere", "MESH_UVSPHERE", 7),
    ("CORNER", "Corner", "Corner", "AREA_DOCK", 8),
    ("TRIANGLE", "Triangle", "Triangle", "MESH_CONE", 9),
    ("PRISM", "Prism", "Prism", "MESH_CONE", 10),
]


modes = [
    ("CUT", "Cut", "Cut", "STRIP_COLOR_01", 1),
    ("ADD", "Add", "Add", "STRIP_COLOR_09", 2),
    ("SLICE", "Slice", "Slice", "STRIP_COLOR_03", 3),
    ("INTERSECT", "Intersect", "Intersect", "STRIP_COLOR_05", 4),
    ("CARVE", "Carve", "Carve", "STRIP_COLOR_02", 5),
    ("UNION", "Union", "Union", "STRIP_COLOR_04", 6),
]


def get_solver_items(self, context):
    """Get boolean solver items based on Blender version"""
    if bpy.app.version >= (5, 0, 0):
        # Blender 5.0+ uses FLOAT instead of FAST
        return (
            ("FLOAT", "Float", "Float solver"),
            ("EXACT", "Exact", "Exact solver"),
            ("MANIFOLD", "Manifold", "Manifold solver"),
        )
    else:
        # Pre-5.0 uses FAST
        return (
            ("FAST", "Fast", "Fast solver"),
            ("EXACT", "Exact", "Exact solver"),
            ("MANIFOLD", "Manifold", "Manifold solver"),
        )


class Align(bpy.types.PropertyGroup):
    face: bpy.props.EnumProperty(
        name="Orientation",
        description="Face Orientation",
        items=[
            ("EDGE", "Edge", "Orient drawing plane using the closest edge of the face"),
            (
                "PLANAR",
                "Planar",
                "Orient drawing plane using the face normal and viewport up vector",
            ),
        ],
        default="EDGE",
    )
    absolute: bpy.props.BoolProperty(name="Absolute", default=False)
    offset: bpy.props.FloatProperty(
        name="Offset",
        description="Offset the mesh above the drawing plane",
        default=0.001,
        subtype="DISTANCE",
    )
    increments: bpy.props.FloatProperty(
        name="Increments",
        description="Round the values to the nearest increment",
        default=0.1,
        subtype="DISTANCE",
    )
    solver: bpy.props.EnumProperty(
        name="Solver", description="Boolean Solver", items=get_solver_items, default=0
    )


class Form(bpy.types.PropertyGroup):
    bevel_segments: bpy.props.IntProperty(
        name="Bevel Segments",
        description="Number of bevel segments",
        default=1,
        min=1,
        max=32,
    )
    circle_verts: bpy.props.IntProperty(
        name="Verts", description="Circle Verts", default=32, min=3, max=256
    )


types_classes = (
    Align,
    Form,
)
