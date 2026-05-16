def draw_align(layout, context, block):
    """Draw align properties"""

    layout.use_property_split = False
    row = layout.row(align=True)
    row.scale_y = 0.8
    row.scale_x = 0.8
    row.prop(context.scene.bout.align, "mode", expand=True)
    layout.separator()
    layout.use_property_split = True
    layout.prop(block.align, "offset")
    layout.prop(block.align, "increments")
    layout.prop(block.align, "absolute", text="Absolute increments snap")
    layout.use_property_split = True
    col = layout.column(align=True)
    if context.scene.bout.align.mode == "FACE":
        col.prop(block.align, "face")
    if context.scene.bout.align.mode == "CUSTOM":
        col = layout.column(align=True, heading="Location")
        col.prop(context.scene.bout.align, "location", text="Location", expand=True)
        col = layout.column(align=True, heading="Rotation")
        col.prop(context.scene.bout.align, "rotation", text="Rotation", expand=True)

    layout.separator()
    layout.prop(block.align, "solver")


def draw_type(layout, block):
    """Draw type properties"""

    layout.use_property_split = False
    col = layout.column(align=True)
    col.scale_y = 1.6
    col.prop(block, "mode", expand=True)


shapes_2d = [
    ("RECTANGLE", "MESH_PLANE"),
    ("NGON", "LIGHTPROBE_PLANE"),
    ("CIRCLE", "MESH_CIRCLE"),
    ("TRIANGLE", "MARKER"),
]

shapes_3d = [
    ("BOX", "MESH_CUBE"),
    ("CYLINDER", "MESH_CYLINDER"),
    ("NHEDRON", "LIGHTPROBE_SPHERE"),
    ("SPHERE", "MESH_UVSPHERE"),
    ("CORNER", "AREA_DOCK"),
    ("PRISM", "MESH_CONE"),
]


def draw_shape(layout, block):
    """Draw type properties as two columns: 2D | 3D"""

    layout.use_property_split = False

    header = layout.split(factor=0.5, align=True)
    header.label(text="2D")
    header.label(text="3D")

    body = layout.split(factor=0.5, align=True)

    col_2d = body.column(align=True)
    col_2d.scale_y = 1.6
    for shape, icon in shapes_2d:
        col_2d.prop_enum(block, "shape", shape, icon=icon)

    col_3d = body.column(align=True)
    col_3d.scale_y = 1.6
    for shape, icon in shapes_3d:
        col_3d.prop_enum(block, "shape", shape, icon=icon)
