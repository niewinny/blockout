from dataclasses import dataclass, field
import bpy
from ...shaders import handle
from ...utils import addon


@dataclass
class DrawUI(handle.Common):
    '''Dataclass for the UI  drawing'''
    xaxis: handle.Line = field(default_factory=handle.Line)
    yaxis: handle.Line = field(default_factory=handle.Line)
    faces: handle.BMeshFaces = field(default_factory=handle.BMeshFaces)

    def __post_init__(self):
        self.clear_all()

    def clear_higlight(self):
        '''Clear axis highlight'''
        axis = bpy.context.scene.bout.axis
        axis.highlight.x, axis.highlight.y = (False, False)


def setup(self, context):
    '''Setup the UI drawing'''

    color = addon.pref().theme.axis
    self.ui.xaxis.create(context, color=color.x)
    self.ui.yaxis.create(context, color=color.y)

    color = addon.pref().theme.ops.block
    mode = addon.pref().tools.block.mode
    match mode:
        case 'CUT': face_color = color.cut
        case 'SLICE': face_color = color.slice
        case 'UNION': face_color = color.union
        case 'INTERSECT': face_color = color.intersect
        case 'CARVE': face_color = color.carve
        case _: face_color = (0.0, 0.0, 0.0, 0.0)

    obj = self.data.obj
    self.ui.faces.create(context, obj=obj, color=face_color)
