import math
from dataclasses import dataclass, field

import bmesh
import bpy
from mathutils import Vector

from ...utils.input import NumericInput
from ...utils.types import DrawMatrix

@dataclass
class Config:
    shape: str = "RECTANGLE"
    mode: str = "ADD"
    type: str = "OBJECT"
    form: bpy.types.PropertyGroup = None
    align: bpy.types.PropertyGroup = None
    snap: bool = False

CREATE = {"DRAW", "EDIT", "EXTRUDE"}
MODIFY = {"BEVEL", "TRANSLATE", "ROTATE", "SCALE"}


@dataclass
class ModalState:
    """``phase`` is one of:
      - CREATE stages: "DRAW", "EDIT", "EXTRUDE"
      - MODIFY detours: "BEVEL", "TRANSLATE", "ROTATE", "SCALE"
      - "BISECT" overrides the pipeline
    """

    phase: str = "DRAW"

    @property
    def is_create(self) -> bool:
        return self.phase in CREATE

    @property
    def is_modify(self) -> bool:
        return self.phase in MODIFY

    @property
    def is_bisect(self) -> bool:
        return self.phase == "BISECT"

@dataclass
class Draw:
    matrix: DrawMatrix = field(default_factory=DrawMatrix)
    faces: list = field(default_factory=list)  # f.index
    verts: list = field(default_factory=list)
    # Per-axis snap flags detected at invoke; not user-controlled symmetry.
    axis_snap: tuple = (False, False)
    corner: Vector = field(default_factory=Vector)

@dataclass
class BevelType:
    enable: bool = False
    offset: float = 0.0
    offset_stored: float = 0.0
    segments: int = 0
    segments_stored: int = 0

@dataclass
class Bevel:
    origin: Vector = field(default_factory=Vector)
    round: BevelType = field(default_factory=BevelType)
    fill: BevelType = field(default_factory=BevelType)
    type: str = "ROUND"
    mode: str = "OFFSET"
    precision: bool = False

@dataclass
class Bisect:
    plane: tuple = field(default_factory=lambda: (Vector(), Vector()))
    mode: str = "CUT"
    flip: bool = False

@dataclass
class ExtrudeEdge:
    index: int = -1
    position: str = "MID"

@dataclass
class Extrude:
    origin: Vector = field(default_factory=Vector)
    verts: list = field(default_factory=list)  # list[DrawVert]
    edges: list = field(default_factory=list)  # list[ExtrudeEdge]
    faces: list = field(default_factory=list)  # f.index
    value: float = 0.0
    symmetry: bool = False

@dataclass
class Translate:
    """``mouse_invoke`` is the 2D mouse at sub-op entry; axis-lock resets
    rewind to it so the full travel re-projects by the new rule.
    """

    delta: Vector = field(default_factory=Vector)
    delta_stored: Vector = field(default_factory=Vector)
    precision: bool = False
    mouse_invoke: Vector = field(default_factory=Vector)
    vert_indices: list = field(default_factory=list)
    orig_coords: list = field(default_factory=list)

@dataclass
class Rotate:
    angle: float = 0.0
    angle_stored: float = 0.0
    pivot: Vector = field(default_factory=Vector)
    axis_vec: Vector = field(default_factory=lambda: Vector((0.0, 0.0, 1.0)))
    precision: bool = False
    mouse_invoke: Vector = field(default_factory=Vector)
    vert_indices: list = field(default_factory=list)
    orig_coords: list = field(default_factory=list)

@dataclass
class Scale:
    factor: Vector = field(default_factory=lambda: Vector((1.0, 1.0, 1.0)))
    factor_stored: Vector = field(default_factory=lambda: Vector((1.0, 1.0, 1.0)))
    pivot: Vector = field(default_factory=Vector)
    precision: bool = False
    mouse_invoke: Vector = field(default_factory=Vector)
    vert_indices: list = field(default_factory=list)
    orig_coords: list = field(default_factory=list)

@dataclass
class Transform:
    """``axis_lock_exclude`` follows Blender's convention: False = constrain
    TO the chosen axis (X), True = lock that axis and move the others
    (Shift+X). Rotate ignores ``axis_lock_exclude``.
    """

    active: str = ""
    axis_lock: str = ""
    axis_lock_exclude: bool = False
    # Stashed CREATE phase; restored on modify commit.
    origin_phase: str = ""
    translate: Translate = field(default_factory=Translate)
    rotate: Rotate = field(default_factory=Rotate)
    scale: Scale = field(default_factory=Scale)

@dataclass
class Copy:
    init: bpy.types.Mesh = None
    draw: bpy.types.Mesh = None
    boolean: bpy.types.Mesh = None
    all: list = field(default_factory=list)

@dataclass
class CreatedData:
    obj: bpy.types.Object = None
    bm: bmesh.types.BMesh = None
    copy: Copy = field(default_factory=Copy)
    extrude: Extrude = field(default_factory=Extrude)
    bevel: Bevel = field(default_factory=Bevel)
    bisect: Bisect = field(default_factory=Bisect)
    draw: Draw = field(default_factory=Draw)
    transform: Transform = field(default_factory=Transform)
    numeric_input: NumericInput = field(default_factory=NumericInput)

@dataclass
class Objects:
    active: bpy.types.Object = None
    selected: list = field(default_factory=list)
    created: bpy.types.Object = None
    duplicated: list = field(default_factory=list)
    detected: str = ""

@dataclass
class Modifier:
    obj: bpy.types.Object = None
    mod: bpy.types.Modifier = None
    type: str = ""

@dataclass
class Modifiers:
    booleans: list = field(default_factory=list)
    bevels: list = field(default_factory=list)
    welds: list = field(default_factory=list)

@dataclass
class Mouse:
    init: Vector = field(default_factory=Vector)
    extrude: Vector = field(default_factory=Vector)
    bevel: Vector = field(default_factory=Vector)
    segment: Vector = field(default_factory=Vector)
    translate: Vector = field(default_factory=Vector)
    rotate: Vector = field(default_factory=Vector)
    scale: Vector = field(default_factory=Vector)
    co: Vector = field(default_factory=Vector)


@dataclass(frozen=True, slots=True)
class BevelInfo:
    """Per-shape bevel behaviour. ``None`` on a shape disables BEVEL entirely.

      ``type``           bevel.type set on first entry, or None to leave alone.
      ``toggles``        re-entering BEVEL flips ROUND ↔ FILL.
      ``after_extrude``  EXTRUDE is fixed-depth — jump straight to BEVEL.
      ``needs_3d``       BEVEL no-ops until the cutter is 3D.
    """

    type: str | None = None
    toggles: bool = False
    after_extrude: bool = False
    needs_3d: bool = False


class ShapeBase(bpy.types.PropertyGroup):
    """Per-shape behavioural attributes:

      ``stages``                 ordered CREATE phases this shape walks.
      ``volumetric``             True iff DRAW yields 3D geometry.
      ``bevel``                  per-shape bevel policy, or None to disable.
      ``draw_editable_indices``  numeric-input indices during DRAW.
    """

    stages = ()
    volumetric = False
    bevel = BevelInfo()
    draw_editable_indices = ()

    @property
    def cutter_buffer_mult(self):
        """2.0 for 2D-final cutters (DRAW-only, non-volumetric); 1.0 otherwise."""
        return 1.0 if "EXTRUDE" in self.stages or self.volumetric else 2.0

    def next_phase(self, phase):
        try:
            idx = self.stages.index(phase)
        except ValueError:
            return None
        return self.stages[idx + 1] if idx + 1 < len(self.stages) else None


class NgonPoint(bpy.types.PropertyGroup):
    co: bpy.props.FloatVectorProperty(
        name="Co",
        description="Vertex coordinate",
        size=3,
        default=(0, 0, 0),
        subtype="XYZ_LENGTH",
    )


class Rectangle(ShapeBase):
    stages = ("DRAW",)
    bevel = BevelInfo(type="ROUND")
    draw_editable_indices = (0, 1)

    size: bpy.props.FloatVectorProperty(
        name="Size",
        description="Rectangle XY dimensions",
        size=2,
        default=(0, 0),
        subtype="XYZ_LENGTH",
    )
    symmetry_x: bpy.props.BoolProperty(name="X", description="Symmetry X", default=False)
    symmetry_y: bpy.props.BoolProperty(name="Y", description="Symmetry Y", default=False)
    extrusion: bpy.props.FloatProperty(
        name="Z", description="Cutter depth (auto-promoted)", default=0.0, subtype="DISTANCE"
    )


class Box(ShapeBase):
    stages = ("DRAW", "EXTRUDE")
    bevel = BevelInfo(toggles=True)
    draw_editable_indices = (0, 1)

    size: bpy.props.FloatVectorProperty(
        name="Size",
        description="Box base XY dimensions",
        size=2,
        default=(0, 0),
        subtype="XYZ_LENGTH",
    )
    symmetry_x: bpy.props.BoolProperty(name="X", description="Symmetry X", default=False)
    symmetry_y: bpy.props.BoolProperty(name="Y", description="Symmetry Y", default=False)
    extrusion: bpy.props.FloatProperty(
        name="Z", description="Extrude depth", default=0.0, subtype="DISTANCE"
    )
    symmetry_extrude: bpy.props.BoolProperty(
        name="Z", description="Symmetry Z", default=False
    )


class Triangle(ShapeBase):
    stages = ("DRAW",)
    bevel = BevelInfo(type="ROUND")
    draw_editable_indices = (0, 1)

    flip: bpy.props.BoolProperty(name="Flip", description="Flip", default=False)
    equilateral: bpy.props.BoolProperty(
        name="Equilateral",
        description="Equilateral (vs right-angle) triangle",
        default=True,
    )
    height: bpy.props.FloatProperty(
        name="Height",
        description="Triangle height",
        default=1.0,
        subtype="DISTANCE",
    )
    angle: bpy.props.FloatProperty(
        name="Angle",
        description="Triangle angle",
        default=0.0,
        subtype="ANGLE",
    )
    extrusion: bpy.props.FloatProperty(
        name="Z", description="Cutter depth (auto-promoted)", default=0.0, subtype="DISTANCE"
    )


class Prism(ShapeBase):
    stages = ("DRAW", "EXTRUDE")
    bevel = BevelInfo(toggles=True)
    draw_editable_indices = (0, 1)

    flip: bpy.props.BoolProperty(name="Flip", description="Flip", default=False)
    equilateral: bpy.props.BoolProperty(
        name="Equilateral",
        description="Equilateral (vs right-angle) triangle",
        default=True,
    )
    height: bpy.props.FloatProperty(
        name="Height",
        description="Prism height",
        default=1.0,
        subtype="DISTANCE",
    )
    angle: bpy.props.FloatProperty(
        name="Angle",
        description="Prism angle",
        default=0.0,
        subtype="ANGLE",
    )
    extrusion: bpy.props.FloatProperty(
        name="Z", description="Extrude depth", default=0.0, subtype="DISTANCE"
    )
    symmetry_extrude: bpy.props.BoolProperty(
        name="Z", description="Symmetry Z", default=False
    )


class Circle(ShapeBase):
    stages = ("DRAW",)
    draw_editable_indices = (0,)

    radius: bpy.props.FloatProperty(
        name="Radius", description="Circle radius", default=0.0, subtype="DISTANCE"
    )
    verts: bpy.props.IntProperty(
        name="Verts", description="Circle Verts", default=32, min=3, max=256
    )
    extrusion: bpy.props.FloatProperty(
        name="Z", description="Cutter depth (auto-promoted)", default=0.0, subtype="DISTANCE"
    )


class Cylinder(ShapeBase):
    stages = ("DRAW", "EXTRUDE")
    bevel = BevelInfo(type="FILL", needs_3d=True)
    draw_editable_indices = (0,)

    radius: bpy.props.FloatProperty(
        name="Radius", description="Cylinder radius", default=0.0, subtype="DISTANCE"
    )
    verts: bpy.props.IntProperty(
        name="Verts", description="Cylinder verts", default=32, min=3, max=256
    )
    extrusion: bpy.props.FloatProperty(
        name="Z", description="Extrude depth", default=0.0, subtype="DISTANCE"
    )
    symmetry_extrude: bpy.props.BoolProperty(
        name="Z", description="Symmetry Z", default=False
    )


class Sphere(ShapeBase):
    stages = ("DRAW",)
    volumetric = True
    bevel = None
    draw_editable_indices = (0,)

    radius: bpy.props.FloatProperty(
        name="Radius", description="Sphere radius", default=0.0, subtype="DISTANCE"
    )
    subdivisions: bpy.props.IntProperty(
        name="Subdivisions", description="Sphere subdivisions", default=3, min=1, max=32
    )


class Corner(ShapeBase):
    stages = ("DRAW", "EXTRUDE")
    bevel = BevelInfo(after_extrude=True)
    draw_editable_indices = (0, 1)

    size: bpy.props.FloatVectorProperty(
        name="Size",
        description="Corner XY dimensions",
        size=2,
        default=(0, 0),
        subtype="XYZ_LENGTH",
    )
    rotation_a: bpy.props.FloatProperty(
        name="Rotation A",
        description="Rotation of the first corner face",
        default=math.radians(0),
        subtype="ANGLE",
    )
    rotation_b: bpy.props.FloatProperty(
        name="Rotation B",
        description="Rotation of the second corner face",
        default=math.radians(0),
        subtype="ANGLE",
    )
    extrusion: bpy.props.FloatProperty(
        name="Z", description="Extrude depth", default=0.0, subtype="DISTANCE"
    )


class Ngon(ShapeBase):
    stages = ("DRAW", "EDIT")
    bevel = BevelInfo(type="ROUND")

    points: bpy.props.CollectionProperty(type=NgonPoint)
    extrusion: bpy.props.FloatProperty(
        name="Z", description="Cutter depth (auto-promoted)", default=0.0, subtype="DISTANCE"
    )


class Nhedron(ShapeBase):
    stages = ("DRAW", "EDIT", "EXTRUDE")
    bevel = BevelInfo(toggles=True)

    points: bpy.props.CollectionProperty(type=NgonPoint)
    extrusion: bpy.props.FloatProperty(
        name="Z", description="Extrude depth", default=0.0, subtype="DISTANCE"
    )


class Plane(bpy.types.PropertyGroup):
    origin: bpy.props.FloatVectorProperty(
        name="Origin",
        description="Plane origin (world-space)",
        size=3,
        default=(0, 0, 0),
        subtype="XYZ",
    )
    normal: bpy.props.FloatVectorProperty(
        name="Normal",
        description="Plane normal",
        size=3,
        default=(0, 0, 0),
        subtype="XYZ",
    )
    origin_local: bpy.props.FloatVectorProperty(
        name="Origin Local",
        description=(
            "Plane world origin captured at draw time; the anchor for "
            "Pref.origin_local (plane-local F9 Origin values)"
        ),
        size=3,
        default=(0, 0, 0),
        subtype="XYZ",
    )


class BevelPrefType(bpy.types.PropertyGroup):
    enable: bpy.props.BoolProperty(name="Enable", description="Enable", default=False)
    offset: bpy.props.FloatProperty(
        name="Offset", description="Offset", default=0.0, subtype="DISTANCE"
    )
    segments: bpy.props.IntProperty(
        name="Segments", description="Segments", default=1, min=1, max=32
    )

class BevelPref(bpy.types.PropertyGroup):
    round: bpy.props.PointerProperty(type=BevelPrefType)
    fill: bpy.props.PointerProperty(type=BevelPrefType)

class BisectPref(bpy.types.PropertyGroup):
    running: bpy.props.BoolProperty(
        name="Running", description="Running", default=False
    )
    mode: bpy.props.EnumProperty(
        name="Mode",
        description="Bisect Mode",
        items=[("CUT", "Cut", "Cut"), ("SPLIT", "Split", "Split")],
        default="CUT",
    )
    flip: bpy.props.BoolProperty(name="Flip", description="Flip", default=False)
    plane: bpy.props.PointerProperty(type=Plane)

class Pref(bpy.types.PropertyGroup):
    type: bpy.props.EnumProperty(
        name="Type",
        description="Type",
        items=[("OBJECT", "Object", "Object"), ("EDIT_MESH", "Edit Mesh", "Edit Mesh")],
        default="OBJECT",
    )

    mode: bpy.props.StringProperty(name="Mode", description="Mode", default="ADD")

    offset: bpy.props.FloatProperty(
        name="Offset", description="Offset", default=0.0, subtype="DISTANCE"
    )

    bevel: bpy.props.PointerProperty(type=BevelPref)
    bisect: bpy.props.PointerProperty(type=BisectPref)

    plane: bpy.props.PointerProperty(type=Plane)
    direction: bpy.props.FloatVectorProperty(
        name="Direction", description="Direction", default=(0, 1, 0), subtype="XYZ"
    )

    def _plane_basis(self):
        from .transform.common import plane_basis_from_vectors
        return plane_basis_from_vectors(Vector(self.plane.normal), Vector(self.direction))

    def _get_origin_local(self):
        x, y, z = self._plane_basis()
        delta = Vector(self.plane.origin) - Vector(self.plane.origin_local)
        return (delta.dot(x), delta.dot(y), delta.dot(z))

    def _set_origin_local(self, value):
        x, y, z = self._plane_basis()
        base = Vector(self.plane.origin_local)
        world = base + x * value[0] + y * value[1] + z * value[2]
        self.plane.origin = tuple(world)

    origin_local: bpy.props.FloatVectorProperty(
        name="Origin",
        description="Origin in draw-plane local space (X=direction, Y=binormal, Z=normal)",
        size=3,
        subtype="XYZ",
        get=_get_origin_local,
        set=_set_origin_local,
    )

    transform_gizmo: bpy.props.BoolProperty(
        name="Transform Gizmo", description="Transform Gizmo", default=False
    )

    detected: bpy.props.StringProperty(
        name="Detected", description="Detected", default=""
    )

    reveal: bpy.props.BoolProperty(name="Reveal", description="Reveal", default=False)

    rotate_x: bpy.props.FloatProperty(
        name="Rotate X",
        description="Rotation around plane X axis",
        default=0.0,
        subtype="ANGLE",
    )
    rotate_y: bpy.props.FloatProperty(
        name="Rotate Y",
        description="Rotation around plane Y axis",
        default=0.0,
        subtype="ANGLE",
    )
    rotate_z: bpy.props.FloatProperty(
        name="Rotate Z",
        description="Rotation around plane Z axis (normal)",
        default=0.0,
        subtype="ANGLE",
    )
    scale_factor: bpy.props.FloatVectorProperty(
        name="Scale",
        description="Scale factor (plane X/Y/Z)",
        size=3,
        default=(1, 1, 1),
        subtype="XYZ",
    )

class Shape(bpy.types.PropertyGroup):
    """``data`` resolves ``active`` to its sub-PG."""

    active: bpy.props.StringProperty(
        name="Active",
        description="Active shape enum name",
        default="RECTANGLE",
    )

    rectangle: bpy.props.PointerProperty(type=Rectangle)
    box: bpy.props.PointerProperty(type=Box)
    triangle: bpy.props.PointerProperty(type=Triangle)
    prism: bpy.props.PointerProperty(type=Prism)
    circle: bpy.props.PointerProperty(type=Circle)
    cylinder: bpy.props.PointerProperty(type=Cylinder)
    sphere: bpy.props.PointerProperty(type=Sphere)
    corner: bpy.props.PointerProperty(type=Corner)
    ngon: bpy.props.PointerProperty(type=Ngon)
    nhedron: bpy.props.PointerProperty(type=Nhedron)

    @property
    def data(self):
        name = self.active.lower()
        pg = getattr(self, name, None)
        if pg is None:
            raise KeyError(
                f"Shape.active={self.active!r}: no sub-PG named {name!r}"
            )
        return pg

classes = (
    NgonPoint,
    Rectangle,
    Box,
    Triangle,
    Prism,
    Circle,
    Cylinder,
    Sphere,
    Corner,
    Ngon,
    Nhedron,
    Plane,
    BevelPrefType,
    BevelPref,
    BisectPref,
    Shape,
    Pref,
)
