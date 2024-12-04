from dataclasses import dataclass, field
import bpy
from ...shaders import handle


@dataclass
class DrawUI(handle.Common):
    '''Dataclass for the UI  drawing'''
    xaxis: handle.Line = field(default_factory=handle.Line)
    yaxis: handle.Line = field(default_factory=handle.Line)
    zaxis: handle.Line = field(default_factory=handle.Line)
    faces: handle.BMeshFaces = field(default_factory=handle.BMeshFaces)
    guid: handle.Polyline = field(default_factory=handle.Polyline)

    def __post_init__(self):
        self.clear_all()


class Theme(bpy.types.PropertyGroup):
    cut: bpy.props.FloatVectorProperty(
        name="Cut",
        description="Mesh indicator color",
        default=(0.5, 0.1, 0.1, 0.2),
        subtype='COLOR',
        size=4,
        min=0.0,
        max=1.0
    )
    slice: bpy.props.FloatVectorProperty(
        name="Slice",
        description="Mesh indicator color",
        default=(0.5, 0.1, 0.3, 0.2),
        subtype='COLOR',
        size=4,
        min=0.0,
        max=1.0
    )
    guid: bpy.props.FloatVectorProperty(
        name="Guid",
        description="Guid indicator color",
        default=(0.1, 0.1, 0.1, 0.8),
        subtype='COLOR',
        size=4,
        min=0.0,
        max=1.0
    )


classes = (
    Theme,
)
