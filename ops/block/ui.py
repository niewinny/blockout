from dataclasses import dataclass, field
import bpy
from ...shaders import handle
from ...utils import addon


@dataclass
class DrawUI(handle.Common):
    '''Dataclass for the UI  drawing'''
    xaxis: handle.Line = field(default_factory=handle.Line)
    yaxis: handle.Line = field(default_factory=handle.Line)
    zaxis: handle.Line = field(default_factory=handle.Line)
    faces: handle.BMeshFaces = field(default_factory=handle.BMeshFaces)
    guid: handle.Polyline = field(default_factory=handle.Polyline)

    vert: handle.Points = field(default_factory=handle.Points)
    active: handle.Points = field(default_factory=handle.Points)

    bisect_line: handle.Line = field(default_factory=handle.Line)
    bisect_polyline: handle.Polyline = field(default_factory=handle.Polyline)
    bisect_gradient: handle.Gradient = field(default_factory=handle.Gradient)
    bisect_gradient_flip: handle.Gradient = field(default_factory=handle.Gradient)

    interface: handle.Interface = field(default_factory=handle.Interface)

    def __post_init__(self):
        self.clear_all()

    def clear_higlight(self):
        '''Clear axis highlight'''
        axis = bpy.context.scene.bout.axis
        axis.highlight.x, axis.highlight.y = (False, False)


def setup(self, context):
    '''Setup the UI drawing'''

    color = addon.pref().theme.axis
    self.ui.zaxis.create(context, color=color.z)
    self.ui.xaxis.create(context, color=color.x)
    self.ui.yaxis.create(context, color=color.y)
    color = addon.pref().theme.ops.block
    match self.config.mode:
        case 'CUT': face_color = color.cut
        case 'SLICE': face_color = color.slice
        case 'UNION': face_color = color.union
        case 'INTERSECT': face_color = color.intersect
        case 'CARVE': face_color = color.carve
        case _: face_color = (0.0, 0.0, 0.0, 0.0)

    obj = self.data.obj
    self.ui.faces.create(context, obj=obj, color=face_color)
    self.ui.guid.create(context, color=color.guid)

    self.ui.vert.create(context, size=10.0, color=color.guid)
    self.ui.active.create(context, size=10.0, color=color.active)

    bisec_color = color.cut
    self.ui.bisect_line.create(context, width=1.6, color=bisec_color, depth=True)
    self.ui.bisect_polyline.create(context, width=1.6, color=color.guid)
    self.ui.bisect_gradient.create(context, colors=[bisec_color, bisec_color, (0.0, 0.0, 0.0, 0.0), (0.0, 0.0, 0.0, 0.0)])
    self.ui.bisect_gradient_flip.create(context, colors=[bisec_color, bisec_color, (0.0, 0.0, 0.0, 0.0), (0.0, 0.0, 0.0, 0.0)])

    lines = []
    self.ui.interface.create(context, lines=lines)


def update(self, context, event):
    '''Update the UI including infobar and viewport'''
    from ...utils import infobar
    
    # Redraw the infobar with updated hotkeys
    infobar.draw(context, event, self._infobar, blank=True)
    
    # Redraw all 3D viewports
    for area in context.window.screen.areas:
        if area.type == 'VIEW_3D':
            area.tag_redraw()


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

    if self.mode == 'BISECT':
        row.label(text='Flip', icon='EVENT_F')
        row.separator(factor=factor)
        return

    if not self.mode == 'BEVEL':
        shape = self.config.shape
        match shape:
            case 'RECTANGLE':
                row.label(text='Bevel', icon='EVENT_B')
                row.separator(factor=factor)
            case 'BOX':
                row.label(text='Symmetry', icon='EVENT_Z')
                row.separator(factor=factor)
                row.label(text='Bevel', icon='EVENT_B')
                row.separator(factor=factor)
            case 'CIRCLE':
                row.separator(factor=factor)
            case 'CYLINDER':
                row.label(text='Symmetry', icon='EVENT_Z')
                row.separator(factor=factor)
                row.label(text='Bevel', icon='EVENT_B')
                row.separator(factor=factor)
            case 'SPHERE':
                row.label(text='Subd', icon='EVENT_S')
                row.separator(factor=factor)
            case 'CORNER':
                row.label(text='Bevel', icon='EVENT_B')
                row.separator(factor=factor)
            case 'NGON' | 'NHEDRON':
                row.label(text='Bevel', icon='EVENT_B')
                row.separator(factor=factor)
                row.label(text='Delete', icon='EVENT_X')
                row.separator(factor=factor)
    else:
        if self.config.shape == 'BOX':
            text = 'Round' if self.data.bevel.type == 'FILL' else 'Fill'
            row.label(text=f"Bevel:{text}", icon='EVENT_B')
            row.separator(factor=factor)
        else:
            if self.data.bevel.mode == 'SEGMENTS':
                row.label(text=f"Bevel", icon='EVENT_B')
                row.separator(factor=factor)
        if self.data.bevel.mode == 'OFFSET':
            row.label(text='Segments', icon='EVENT_S')
            row.separator(factor=factor)

    if not self.pref.reveal:
        row.label(text='Reveal', icon='EVENT_Q')
        row.separator(factor=factor)


class Theme(bpy.types.PropertyGroup):
    cut: bpy.props.FloatVectorProperty(
        name="Cut",
        description="Mesh indicator color",
        default=(0.5, 0.1, 0.1,  0.12),
        subtype='COLOR',
        size=4,
        min=0.0,
        max=1.0
    )
    slice: bpy.props.FloatVectorProperty(
        name="Slice",
        description="Mesh indicator color",
        default=(0.7, 0.7, 0.08, 0.12),
        subtype='COLOR',
        size=4,
        min=0.0,
        max=1.0
    )
    union: bpy.props.FloatVectorProperty(
        name="Union",
        description="Mesh indicator color",
        default=(0.1, 0.8, 0.1, 0.12),
        subtype='COLOR',
        size=4,
        min=0.0,
        max=1.0
    )
    intersect: bpy.props.FloatVectorProperty(
        name="Intersect",
        description="Mesh indicator color",
        default=(0.1, 0.6, 0.6, 0.12),
        subtype='COLOR',
        size=4,
        min=0.0,
        max=1.0
    )
    carve: bpy.props.FloatVectorProperty(
        name="Carve",
        description="Mesh indicator color",
        default=(0.9, 0.5, 0.1, 0.08),
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
    active: bpy.props.FloatVectorProperty(
        name="Active",
        description="Active indicator color",
        default=(85.0, 75.0, 0.0, 0.8),
        subtype='COLOR',
        size=4,
        min=0.0,
        max=1.0
    )


classes = (
    Theme,
)
