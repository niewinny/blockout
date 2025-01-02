import bpy

from . import bevel
from . import block
from . import line_cut
from . import edge_expand
from . import loop_bisect
from . import match_face
from . import custom_plane
from . import sweep


class Theme(bpy.types.PropertyGroup):
    bevel: bpy.props.PointerProperty(type=bevel.Theme)
    line_cut: bpy.props.PointerProperty(type=line_cut.Theme)
    loop_bisect: bpy.props.PointerProperty(type=loop_bisect.Theme)
    match_face: bpy.props.PointerProperty(type=match_face.Theme)


types_classes = (
    *bevel.types_classes,
    *line_cut.types_classes,
    *loop_bisect.types_classes,
    *match_face.types_classes,
    Theme,
)

classes = (
    *bevel.classes,
    *block.classes,
    *line_cut.classes,
    *edge_expand.classes,
    *loop_bisect.classes,
    *match_face.classes,
    *custom_plane.classes,
    *sweep.classes,
)
