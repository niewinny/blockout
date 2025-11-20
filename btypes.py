import bpy
from . import ops, tools
from .tools.block import custom


class Tools(bpy.types.PropertyGroup):
    block: bpy.props.PointerProperty(type=tools.block.Pref)


class Highlight(bpy.types.PropertyGroup):
    x: bpy.props.BoolProperty(
        name="X", description="Highlight X axis", default=False, update=custom.redraw
    )
    y: bpy.props.BoolProperty(
        name="Y", description="Highlight Y axis", default=False, update=custom.redraw
    )


class SceneAxis(bpy.types.PropertyGroup):
    highlight: bpy.props.PointerProperty(type=Highlight)


class Align(bpy.types.PropertyGroup):
    mode: bpy.props.EnumProperty(
        name="Mode",
        description="Mode",
        items=[
            ("FACE", "Face", "Align the mesh to the face", "ORIENTATION_NORMAL", 1),
            (
                "CUSTOM",
                "Custom",
                "Align the mesh to a custom plane",
                "OBJECT_ORIGIN",
                2,
            ),
        ],
        default="FACE",
        update=custom.redraw,
    )

    matrix: bpy.props.FloatVectorProperty(
        name="Matrix",
        size=16,
        subtype="MATRIX",
        default=(
            1.0,
            0.0,
            0.0,
            0.0,
            0.0,
            1.0,
            0.0,
            0.0,
            0.0,
            0.0,
            1.0,
            0.0,
            0.0,
            0.0,
            0.0,
            1.0,
        ),
        update=custom.redraw,
    )

    location: bpy.props.FloatVectorProperty(
        name="Location",
        description="Location of the custom plane",
        default=(0.0, 0.0, 0.0),
        subtype="XYZ",
        update=custom.update_location,
    )
    rotation: bpy.props.FloatVectorProperty(
        name="Rotation",
        description="Rotation of the custom plane",
        default=(0.0, 0.0, 0.0),
        subtype="EULER",
        update=custom.update_rotation,
    )


class Scene(bpy.types.PropertyGroup):
    ops: bpy.props.PointerProperty(type=ops.Scene)
    axis: bpy.props.PointerProperty(type=SceneAxis)
    align: bpy.props.PointerProperty(type=Align)


class ThemeAxis(bpy.types.PropertyGroup):
    x: bpy.props.FloatVectorProperty(
        name="Axis X",
        description="X axis color",
        default=(1.0, 0.2, 0.322, 0.4),
        subtype="COLOR",
        size=4,
        min=0.0,
        max=1.0,
    )
    y: bpy.props.FloatVectorProperty(
        name="Y",
        description="Y axis colo",
        default=(0.545, 0.863, 0.0, 0.4),
        subtype="COLOR",
        size=4,
        min=0.0,
        max=1.0,
    )
    z: bpy.props.FloatVectorProperty(
        name="Z",
        description="Z axis colo",
        default=(0.157, 0.564, 1.0, 0.4),
        subtype="COLOR",
        size=4,
        min=0.0,
        max=1.0,
    )


class Theme(bpy.types.PropertyGroup):
    ops: bpy.props.PointerProperty(type=ops.Theme)
    axis: bpy.props.PointerProperty(type=ThemeAxis)


classes = [
    *ops.types_classes,
    *tools.types_classes,
    Tools,
    Highlight,
    SceneAxis,
    Align,
    Scene,
    ThemeAxis,
    Theme,
]


def register():
    bpy.types.Scene.bout = bpy.props.PointerProperty(type=Scene)


def unregister():
    del bpy.types.Scene.bout
