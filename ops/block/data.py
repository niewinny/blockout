import math
from dataclasses import dataclass, field

import bmesh
import bpy
from mathutils import Vector

from ...utils.input import NumericInput
from ...utils.types import DrawMatrix

@dataclass
class Config:
    """Dataclass for storing options"""

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
    """Runtime modal state.

    `phase` is the currently-active sub-state, one of:
      - CREATE stages: "DRAW", "EDIT", "EXTRUDE"
      - MODIFY detours: "BEVEL", "TRANSLATE", "ROTATE", "SCALE"
      - "BISECT" when the op runs in bisect mode (overrides the pipeline)

    `is_create` / `is_modify` / `is_bisect` classify the current phase.
    """

    phase: str = "DRAW"
    volume: str = "2D"
    spine_index: int = 0

    @property
    def is_create(self) -> bool:
        return self.phase in CREATE

    @property
    def is_modify(self) -> bool:
        return self.phase in MODIFY

    @property
    def is_bisect(self) -> bool:
        return self.phase == "BISECT"

# Per-shape pipeline of CREATE stages, ordered. Advance walks this list on
# LMB-release from DRAW/EDIT or LMB-press from EXTRUDE/MODIFY. Finalize when
# past the end. MODIFY is a user-triggered detour (via B/G/R/S), not a stage.
SPINE = {
    "RECTANGLE": [("DRAW", "2D")],
    "TRIANGLE": [("DRAW", "2D")],
    "CIRCLE": [("DRAW", "2D")],
    "NGON": [("DRAW", "2D"), ("EDIT", "2D")],
    "BOX": [("DRAW", "2D"), ("EXTRUDE", "3D")],
    "CYLINDER": [("DRAW", "2D"), ("EXTRUDE", "3D")],
    "PRISM": [("DRAW", "2D"), ("EXTRUDE", "3D")],
    "NHEDRON": [("DRAW", "2D"), ("EDIT", "2D"), ("EXTRUDE", "3D")],
    "CORNER": [("DRAW", "2D"), ("EXTRUDE", "3D")],
    "SPHERE": [("DRAW", "3D")],
}

@dataclass
class Draw:
    """Dataclass for storing options"""

    matrix: DrawMatrix = field(default_factory=DrawMatrix)
    faces: list = field(default_factory=list)  # f.index
    verts: list = field(default_factory=list)
    symmetry: tuple = (False, False)
    corner: Vector = field(default_factory=Vector)

@dataclass
class BevelType:
    """Dataclass for storing options"""

    enable: bool = False
    offset: float = 0.0
    offset_stored: float = 0.0
    segments: int = 0
    segments_stored: int = 0

@dataclass
class Bevel:
    """Dataclass for storing options"""

    origin: Vector = field(default_factory=Vector)
    round: BevelType = field(default_factory=BevelType)
    fill: BevelType = field(default_factory=BevelType)
    type: str = "ROUND"
    mode: str = "OFFSET"
    precision: bool = False

@dataclass
class Bisect:
    """Dataclass for storing options"""

    plane: tuple = field(default_factory=lambda: (Vector(), Vector()))
    mode: str = "CUT"
    flip: bool = False

@dataclass
class ExtrudeEdge:
    """Dataclass for storing options"""

    index: int = -1
    position: str = "MID"

@dataclass
class Extrude:
    """Dataclass for storing options"""

    origin: Vector = field(default_factory=Vector)
    verts: list = field(default_factory=list)  # list[DrawVert]
    edges: list = field(default_factory=list)  # list[ExtrudeEdge]
    faces: list = field(default_factory=list)  # f.index
    value: float = 0.0
    symmetry: bool = False

@dataclass
class Translate:
    """Per-session translate-modify state.

    mouse_invoke is the 2D mouse position at sub-op entry; anchor resets
    (on axis-lock change) rewind to it so the full mouse travel since
    invoke gets re-projected by the new rule, matching Blender.
    """

    delta: Vector = field(default_factory=Vector)
    delta_stored: Vector = field(default_factory=Vector)
    precision: bool = False
    mouse_invoke: Vector = field(default_factory=Vector)
    vert_indices: list = field(default_factory=list)
    orig_coords: list = field(default_factory=list)

@dataclass
class Rotate:
    """Per-session rotate-modify state."""

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
    """Per-session scale-modify state."""

    factor: Vector = field(default_factory=lambda: Vector((1.0, 1.0, 1.0)))
    factor_stored: Vector = field(default_factory=lambda: Vector((1.0, 1.0, 1.0)))
    pivot: Vector = field(default_factory=Vector)
    precision: bool = False
    mouse_invoke: Vector = field(default_factory=Vector)
    vert_indices: list = field(default_factory=list)
    orig_coords: list = field(default_factory=list)

@dataclass
class Transform:
    """Shared modify-layer state.

    axis_lock persists across G/R/S sub-op switches within a single MODIFY stage.
    axis_lock_exclude follows Blender's convention: False means constrain TO the
    chosen axis (pressed X alone); True means lock the chosen axis and move
    along the others (Shift+X). Rotate ignores axis_lock_exclude.

    The plane basis itself lives on Plane (origin/normal/direction) and is
    stable across modal frames — sub-ops read it via ``common.plane_basis``.
    """

    active: str = ""
    axis_lock: str = ""
    axis_lock_exclude: bool = False
    translate: Translate = field(default_factory=Translate)
    rotate: Rotate = field(default_factory=Rotate)
    scale: Scale = field(default_factory=Scale)

@dataclass
class Copy:
    """Dataclass for storing options"""

    init: bpy.types.Mesh = None
    draw: bpy.types.Mesh = None
    boolean: bpy.types.Mesh = None
    all: list = field(default_factory=list)

@dataclass
class CreatedData:
    """Dataclass for storing all operation data"""

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
    """Dataclass for storing object references"""

    active: bpy.types.Object = None
    selected: list = field(default_factory=list)
    created: bpy.types.Object = None
    duplicated: list = field(default_factory=list)
    detected: str = ""

@dataclass
class Modifier:
    """Dataclass for storing modifier references"""

    obj: bpy.types.Object = None
    mod: bpy.types.Modifier = None
    type: str = ""

@dataclass
class Modifiers:
    """Dataclass for storing multiple modifier references"""

    booleans: list = field(default_factory=list)
    bevels: list = field(default_factory=list)
    welds: list = field(default_factory=list)

@dataclass
class Mouse:
    """Dataclass for tracking mouse positions."""

    init: Vector = field(default_factory=Vector)
    extrude: Vector = field(default_factory=Vector)
    bevel: Vector = field(default_factory=Vector)
    segment: Vector = field(default_factory=Vector)
    translate: Vector = field(default_factory=Vector)
    rotate: Vector = field(default_factory=Vector)
    scale: Vector = field(default_factory=Vector)
    co: Vector = field(default_factory=Vector)

class Corner(bpy.types.PropertyGroup):
    """PropertyGroup for storing corner data"""

    co: bpy.props.FloatVectorProperty(
        name="Corner",
        description="Corner coordinates",
        size=2,
        default=(0, 0),
        subtype="XYZ_LENGTH",
    )
    min: bpy.props.FloatProperty(
        name="Rotation",
        description="Rotation",
        default=math.radians(0),
        subtype="ANGLE",
    )
    max: bpy.props.FloatProperty(
        name="Rotation",
        description="Rotation",
        default=math.radians(0),
        subtype="ANGLE",
    )

class Rectangle(bpy.types.PropertyGroup):
    """PropertyGroup for storing rectangle data"""

    co: bpy.props.FloatVectorProperty(
        name="Rectangle",
        description="Rectangle coordinates",
        size=2,
        default=(0, 0),
        subtype="XYZ_LENGTH",
    )

class Triangle(bpy.types.PropertyGroup):
    """PropertyGroup for storing triangle data"""

    flip: bpy.props.BoolProperty(name="Flip", description="Flip", default=False)
    symmetry: bpy.props.BoolProperty(name="H", description="Symmetry", default=True)
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

class Ngon(bpy.types.PropertyGroup):
    """PropertyGroup for storing ngon data"""

    co: bpy.props.FloatVectorProperty(
        name="Ngon",
        description="Ngon coordinates",
        size=3,
        default=(0, 0, 0),
        subtype="XYZ_LENGTH",
    )

class Circle(bpy.types.PropertyGroup):
    """PropertyGroup for storing circle data"""

    radius: bpy.props.FloatProperty(
        name="Radius", description="Circle radius", default=0.0, subtype="DISTANCE"
    )
    verts: bpy.props.IntProperty(
        name="Verts", description="Circle Verts", default=32, min=3, max=256
    )

class Plane(bpy.types.PropertyGroup):
    """PropertyGroup for storing plane data"""

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

class Sphere(bpy.types.PropertyGroup):
    """PropertyGroup for storing circle data"""

    radius: bpy.props.FloatProperty(
        name="Radius", description="Sphere radius", default=0.0, subtype="DISTANCE"
    )
    subd: bpy.props.IntProperty(
        name="Subd", description="Sphere Subdivisions", default=3, min=1, max=32
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
    """PropertyGroup for storing bevel data"""

    round: bpy.props.PointerProperty(type=BevelPrefType)
    fill: bpy.props.PointerProperty(type=BevelPrefType)

class BisectPref(bpy.types.PropertyGroup):
    """PropertyGroup for storing bisect data"""

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
    """PropertyGroup for storing preferences"""

    type: bpy.props.EnumProperty(
        name="Type",
        description="Type",
        items=[("OBJECT", "Object", "Object"), ("EDIT_MESH", "Edit Mesh", "Edit Mesh")],
        default="OBJECT",
    )
    extrusion: bpy.props.FloatProperty(
        name="Z", description="Z coordinates", default=0.0, subtype="DISTANCE"
    )
    symmetry_extrude: bpy.props.BoolProperty(
        name="Z", description="Symmetry Z", default=False
    )
    symmetry_draw_x: bpy.props.BoolProperty(
        name="X", description="Symmetry X", default=False
    )
    symmetry_draw_y: bpy.props.BoolProperty(
        name="Y", description="Symmetry Y", default=False
    )

    shape: bpy.props.StringProperty(
        name="Shape", description="Shape", default="RECTANGLE"
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

    ngon: bpy.props.CollectionProperty(type=Ngon)

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
    volume: bpy.props.StringProperty(name="Volume", description="Volume", default="2D")
    rectangle: bpy.props.PointerProperty(type=Rectangle)
    triangle: bpy.props.PointerProperty(type=Triangle)
    ngon: bpy.props.PointerProperty(type=Ngon)
    circle: bpy.props.PointerProperty(type=Circle)
    sphere: bpy.props.PointerProperty(type=Sphere)
    corner: bpy.props.PointerProperty(type=Corner)

classes = (
    Corner,
    Rectangle,
    Triangle,
    Ngon,
    Circle,
    Plane,
    Sphere,
    BevelPrefType,
    BevelPref,
    BisectPref,
    Shape,
    Pref,
)
