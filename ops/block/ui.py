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

    bisect_line: handle.Line = field(default_factory=handle.Line)
    bisect_polyline: handle.Polyline = field(default_factory=handle.Polyline)
    bisect_gradient: handle.Gradient = field(default_factory=handle.Gradient)
    bisect_gradient_flip: handle.Gradient = field(default_factory=handle.Gradient)


    def __post_init__(self):
        self.clear_all()

    def clear_higlight(self):
        '''Clear axis highlight'''
        axis = bpy.context.scene.bout.axis
        axis.highlight.x, axis.highlight.y = (False, False)


def hotkeys(self, layout, _context, _event):
    '''Draw the infobar hotkeys'''
    factor = 4.0
    row = layout.row(align=True)
    row.label(text=self.mode.capitalize(), icon='MOUSE_MOVE')
    row.separator(factor=factor)
    lmb = 'Extrude' if self.mode == 'DRAW' else 'Finish'
    row.label(text=lmb, icon='MOUSE_LMB')
    row.separator(factor=factor)
    row.label(text='Cancel', icon='MOUSE_RMB')
    row.separator(factor=factor)
    row.label(text='Snap', icon='EVENT_CTRL')
    row.separator(factor=factor)
    row.label(text='Symmetry', icon='EVENT_Z')
    row.separator(factor=factor)
    bpress = 'Offset' if self.mode == 'BEVEL' else 'BEVEL'
    row.label(text=bpress, icon='EVENT_B')
    row.separator(factor=factor)
    if self.mode == 'BEVEL':
        row.label(text='Segments', icon='EVENT_S')
        row.separator(factor=factor)


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
