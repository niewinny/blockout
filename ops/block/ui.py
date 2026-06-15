from dataclasses import dataclass, field

import bpy

from ...shaders import handle
from ...utils import addon, infobar
from .data import CONVERTABLE

@dataclass
class DrawUI(handle.Common):
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
        axis = bpy.context.scene.bout.axis
        axis.highlight.x, axis.highlight.y = (False, False)

def clear_phase(op):
    """Clear UI elements carried over from prior CREATE/EDIT/EXTRUDE/MODIFY phases.

    Called from each phase entry (extrude, bevel, translate/rotate/scale) so
    stale handles from the previous phase (colored axes, guide polylines,
    vert markers, active highlights, text) don't leak into the new phase's
    drawing. The entering phase re-populates only the handles it owns.
    """
    op.ui.xaxis.callback.clear()
    op.ui.yaxis.callback.clear()
    op.ui.zaxis.callback.clear()
    op.ui.guid.callback.clear()
    op.ui.vert.callback.clear()
    op.ui.active.callback.clear()
    op.ui.interface.callback.clear()

def setup(self, context):
    color = addon.pref().theme.axis
    self.ui.zaxis.create(context, color=color.z)
    self.ui.xaxis.create(context, color=color.x)
    self.ui.yaxis.create(context, color=color.y)
    color = addon.pref().theme.ops.block
    match self.config.mode:
        case "CUT":
            face_color = color.cut
        case "SLICE":
            face_color = color.slice
        case "UNION":
            face_color = color.union
        case "INTERSECT":
            face_color = color.intersect
        case "CARVE":
            face_color = color.carve
        case _:
            face_color = (0.0, 0.0, 0.0, 0.0)

    obj = self.data.obj
    self.ui.faces.create(context, obj=obj, color=face_color)
    self.ui.guid.create(context, color=color.guid)

    self.ui.vert.create(context, size=10.0, color=color.guid)
    self.ui.active.create(context, size=10.0, color=color.active)

    bisec_color = color.cut
    self.ui.bisect_line.create(context, width=1.6, color=bisec_color, depth=True)
    self.ui.bisect_polyline.create(context, width=1.6, color=color.guid)
    self.ui.bisect_gradient.create(
        context,
        colors=[bisec_color, bisec_color, (0.0, 0.0, 0.0, 0.0), (0.0, 0.0, 0.0, 0.0)],
    )
    self.ui.bisect_gradient_flip.create(
        context,
        colors=[bisec_color, bisec_color, (0.0, 0.0, 0.0, 0.0), (0.0, 0.0, 0.0, 0.0)],
    )

    lines = []
    self.ui.interface.create(context, lines=lines)

def update(self, context, event):
    infobar.draw(context, event, self._infobar, blank=True)

_PHASE_LABEL = {
    "DRAW": "Draw",
    "EDIT": "Edit",
    "EXTRUDE": "Extrude",
    "BEVEL": "Bevel",
    "TRANSLATE": "Translate",
    "ROTATE": "Rotate",
    "SCALE": "Scale",
    "BISECT": "Bisect",
}


def _hk(row, factor, text, icon):
    row.label(text=text, icon=icon)
    row.separator(factor=factor)


def _shape_specific(row, factor, op, name, is_draw):
    """Phase-specific hotkeys (X/Y/Z/F/S). EXTRUDE: Z toggles extrude-symmetry."""
    sd = op.shape.data
    if is_draw:
        if hasattr(sd, "symmetry_x"):
            _hk(row, factor, "X Symmetry", "EVENT_X")
            _hk(row, factor, "Y Symmetry", "EVENT_Y")
        elif hasattr(sd, "flip"):
            _hk(row, factor, "X Symmetry", "EVENT_X")
            _hk(row, factor, "Flip", "EVENT_F")
        if hasattr(sd, "symmetry_extrude"):
            _hk(row, factor, "Z Symmetry", "EVENT_Z")
        if hasattr(sd, "subdivisions"):
            _hk(row, factor, "Subd", "EVENT_S")
        if op.config.shape in CONVERTABLE:
            _hk(row, factor, "Edit", "EVENT_TAB")
    if name == "EDIT" and hasattr(sd, "points"):
        _hk(row, factor, "Delete", "EVENT_X")
    if name == "EXTRUDE":
        _hk(row, factor, "Z Symmetry", "EVENT_Z")


def hotkeys(self, layout, _context, _event):
    factor = 4.0
    row = layout.row(align=True)

    ni = self.data.numeric_input
    if ni.active:
        _hk(row, factor, "Input", "LINENUMBERS_ON")
        _hk(row, factor, "Apply", "EVENT_RETURN")
        _hk(row, factor, "Cancel", "EVENT_ESC")
        _hk(row, factor, "Next", "EVENT_TAB")
        _hk(row, factor, "Delete", "EVENT_BACKSPACE")
        return

    name = self.state.phase
    is_draw = name == "DRAW"
    is_modify = self.state.is_modify

    _hk(row, factor, _PHASE_LABEL.get(name, name.capitalize()), "MOUSE_MOVE")
    _hk(row, factor, "Extrude" if is_draw else "Finish", "MOUSE_LMB")
    _hk(row, factor, "Cancel", "MOUSE_RMB")
    _hk(row, factor, "Snap", "EVENT_CTRL")

    # BISECT is its own branch — only flip applies, and G/R/S are blocked.
    if name == "BISECT":
        _hk(row, factor, "Flip", "EVENT_F")
        return

    # Phase-specific keys (X/Y/Z/F/S used for non-transform purposes).
    # Skipped for MODIFY (TRANSLATE/ROTATE/SCALE) — there X/Y/Z are axis locks.
    if not is_modify:
        _shape_specific(row, factor, self, name, is_draw)

    sd = self.shape.data
    # BEVEL owns B (round/fill) and S (segments); no "Bevel"/"Scale"
    # hotkey hint here to avoid confusion.
    if name == "BEVEL":
        if sd.bevel and sd.bevel.toggles:
            label = "Round" if self.data.bevel.type == "FILL" else "Fill"
            _hk(row, factor, f"Bevel:{label}", "EVENT_B")
        if self.data.bevel.mode == "OFFSET":
            _hk(row, factor, "Segments", "EVENT_S")
    else:
        # B enters BEVEL sub-op in all non-BEVEL, non-BISECT phases.
        _hk(row, factor, "Bevel", "EVENT_B")

    # G/R/S enter MODIFY (skip current). S is taken by BEVEL segments and
    # by Sphere's Subdivisions during DRAW.
    if name != "TRANSLATE":
        _hk(row, factor, "Move", "EVENT_G")
    if name != "ROTATE":
        _hk(row, factor, "Rotate", "EVENT_R")
    s_taken = name == "BEVEL" or (is_draw and hasattr(sd, "subdivisions"))
    if name != "SCALE" and not s_taken:
        _hk(row, factor, "Scale", "EVENT_S")

    # Axis keys in MODIFY TRANSLATE/ROTATE/SCALE (Z only in 3D).
    if name in {"TRANSLATE", "ROTATE", "SCALE"}:
        axes = ("X", "Y", "Z") if self.is_3d else ("X", "Y")
        for k in axes:
            _hk(row, factor, "Axis", f"EVENT_{k}")

    if not self.pref.reveal:
        _hk(row, factor, "Reveal", "EVENT_Q")

class Theme(bpy.types.PropertyGroup):
    cut: bpy.props.FloatVectorProperty(
        name="Cut",
        description="Mesh indicator color",
        default=(0.5, 0.1, 0.1, 0.12),
        subtype="COLOR",
        size=4,
        min=0.0,
        max=1.0,
    )
    slice: bpy.props.FloatVectorProperty(
        name="Slice",
        description="Mesh indicator color",
        default=(0.7, 0.7, 0.08, 0.12),
        subtype="COLOR",
        size=4,
        min=0.0,
        max=1.0,
    )
    union: bpy.props.FloatVectorProperty(
        name="Union",
        description="Mesh indicator color",
        default=(0.1, 0.8, 0.1, 0.12),
        subtype="COLOR",
        size=4,
        min=0.0,
        max=1.0,
    )
    intersect: bpy.props.FloatVectorProperty(
        name="Intersect",
        description="Mesh indicator color",
        default=(0.1, 0.6, 0.6, 0.12),
        subtype="COLOR",
        size=4,
        min=0.0,
        max=1.0,
    )
    carve: bpy.props.FloatVectorProperty(
        name="Carve",
        description="Mesh indicator color",
        default=(0.9, 0.5, 0.1, 0.08),
        subtype="COLOR",
        size=4,
        min=0.0,
        max=1.0,
    )
    guid: bpy.props.FloatVectorProperty(
        name="Guid",
        description="Guid indicator color",
        default=(0.1, 0.1, 0.1, 0.8),
        subtype="COLOR",
        size=4,
        min=0.0,
        max=1.0,
    )
    active: bpy.props.FloatVectorProperty(
        name="Active",
        description="Active indicator color",
        default=(85.0, 75.0, 0.0, 0.8),
        subtype="COLOR",
        size=4,
        min=0.0,
        max=1.0,
    )

classes = (Theme,)
