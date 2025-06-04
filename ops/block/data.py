import math
import bpy
import bmesh
from mathutils import Vector
from dataclasses import dataclass, field
from ...utils.types import DrawMatrix, DrawVert


@dataclass
class Config:
    '''Dataclass for storing options'''
    shape: str = 'RECTANGLE'
    mode: str = 'ADD'
    type: str = 'OBJECT'
    form: bpy.types.PropertyGroup = None
    align: bpy.types.PropertyGroup = None
    pick: str = 'SELECTED'


@dataclass
class Draw:
    '''Dataclass for storing options'''
    matrix: DrawMatrix = field(default_factory=DrawMatrix)
    faces: list = field(default_factory=list)  # f.index
    verts: list = field(default_factory=DrawVert)
    symmetry: tuple = (False, False)
    corner: Vector = Vector()


@dataclass
class BevelType:
    '''Dataclass for storing options'''
    enable: bool = False
    offset: float = 0.0
    offset_stored: float = 0.0
    segments: int = 0
    segments_stored: int = 0


@dataclass
class Bevel:
    '''Dataclass for storing options'''
    origin: Vector = Vector()
    round: BevelType = field(default_factory=BevelType)
    fill: BevelType = field(default_factory=BevelType)
    type: str = 'ROUND'
    mode: str = 'OFFSET'
    precision: bool = False


@dataclass
class Bisect:
    '''Dataclass for storing options'''
    plane: tuple = (Vector(), Vector())
    mode: str = 'CUT'
    flip: bool = False


@dataclass
class ExtrudeEdge:
    '''Dataclass for storing options'''
    index: int = -1
    position: str = 'MID'


@dataclass
class Extrude:
    '''Dataclass for storing options'''
    origin: Vector = Vector()
    verts: list = field(default_factory=DrawVert)
    edges: list = field(default_factory=ExtrudeEdge)
    faces: list = field(default_factory=list)  # f.index
    value: float = 0.0
    symmetry: bool = False


@dataclass
class Copy:
    '''Dataclass for storing options'''
    init: bpy.types.Mesh = None
    draw: bpy.types.Mesh = None
    boolean: bpy.types.Mesh = None
    all: list = field(default_factory=list)


@dataclass
class CreatedData:
    '''Dataclass for storing'''
    obj: bpy.types.Object = None
    bm: bmesh.types.BMesh = None
    copy: Copy = field(default_factory=Copy)
    extrude: Extrude = field(default_factory=Extrude)
    bevel: Bevel = field(default_factory=Bevel)
    bisect: Bisect = field(default_factory=Bisect)
    draw: Draw = field(default_factory=Draw)


@dataclass
class Objects:
    '''Dataclass for storing'''
    active: bpy.types.Object = None
    selected: list = field(default_factory=list)
    created: bpy.types.Object = None
    duplicated: list = field(default_factory=list)
    detected: str = ''


@dataclass
class Modifier:
    obj: bpy.types.Object = None
    mod: bpy.types.Modifier = None
    type: str = ''


@dataclass
class Modifiers:
    '''Dataclass for storing'''
    booleans: list = field(default_factory=list)
    bevels: list = field(default_factory=list)
    welds: list = field(default_factory=list)


@dataclass
class Mouse:
    """Dataclass for tracking mouse positions."""
    init: Vector = Vector()
    extrude: Vector = Vector()
    bevel: Vector = Vector()
    segment: Vector = Vector()
    co: Vector = Vector()


class Corner(bpy.types.PropertyGroup):
    '''PropertyGroup for storing corner data'''
    co: bpy.props.FloatVectorProperty(name="Corner", description="Corner coordinates", size=2, default=(0, 0), subtype='XYZ_LENGTH')
    min: bpy.props.FloatProperty(name="Rotation", description="Rotation", default=math.radians(0), subtype='ANGLE')
    max: bpy.props.FloatProperty(name="Rotation", description="Rotation", default=math.radians(0), subtype='ANGLE')


class Rectangle(bpy.types.PropertyGroup):
    '''PropertyGroup for storing rectangle data'''
    co: bpy.props.FloatVectorProperty(name="Rectangle", description="Rectangle coordinates", size=2, default=(0, 0), subtype='XYZ_LENGTH')


class Ngon(bpy.types.PropertyGroup):
    '''PropertyGroup for storing ngon data'''
    co: bpy.props.FloatVectorProperty(name="Ngon", description="Ngon coordinates", size=3, default=(0, 0, 0), subtype='XYZ_LENGTH')


class Circle(bpy.types.PropertyGroup):
    '''PropertyGroup for storing circle data'''
    radius: bpy.props.FloatProperty(name="Radius", description="Circle radius", default=0.0, subtype='DISTANCE')
    verts: bpy.props.IntProperty(name="Verts", description="Circle Verts", default=32, min=3, max=256)


class Plane(bpy.types.PropertyGroup):
    '''PropertyGroup for storing plane data'''
    location: bpy.props.FloatVectorProperty(name="Location", description="Plane location", size=3, default=(0, 0, 0), subtype='XYZ')
    normal: bpy.props.FloatVectorProperty(name="Normal", description="Plane normal", size=3, default=(0, 0, 0), subtype='XYZ')


class Sphere(bpy.types.PropertyGroup):
    '''PropertyGroup for storing circle data'''
    radius: bpy.props.FloatProperty(name="Radius", description="Sphere radius", default=0.0, subtype='DISTANCE')
    subd: bpy.props.IntProperty(name="Subd", description="Sphere Subdivisions", default=3, min=1, max=32)


class BevelPrefType(bpy.types.PropertyGroup):
    enable: bpy.props.BoolProperty(name="Enable", description="Enable", default=False)
    offset: bpy.props.FloatProperty(name="Offset", description="Offset", default=0.0, subtype='DISTANCE')
    segments: bpy.props.IntProperty(name="Segments", description="Segments", default=1, min=1, max=32)


class BevelPref(bpy.types.PropertyGroup):
    '''PropertyGroup for storing bevel data'''
    round: bpy.props.PointerProperty(type=BevelPrefType)
    fill: bpy.props.PointerProperty(type=BevelPrefType)


class BisectPref(bpy.types.PropertyGroup):
    '''PropertyGroup for storing bisect data'''
    running: bpy.props.BoolProperty(name="Running", description="Running", default=False)
    mode: bpy.props.EnumProperty(name="Mode", description="Bisect Mode", items=[('CUT', 'Cut', 'Cut'), ('SPLIT', 'Split', 'Split')], default='CUT')
    flip: bpy.props.BoolProperty(name="Flip", description="Flip", default=False)
    plane: bpy.props.PointerProperty(type=Plane)


class Pref(bpy.types.PropertyGroup):
    '''PropertyGroup for storing preferences'''
    type: bpy.props.EnumProperty(name="Type", description="Type", items=[('OBJECT', 'Object', 'Object'), ('EDIT_MESH', 'Edit Mesh', 'Edit Mesh')], default='OBJECT')
    extrusion: bpy.props.FloatProperty(name="Z", description="Z coordinates", default=0.0, subtype='DISTANCE')
    symmetry_extrude: bpy.props.BoolProperty(name="Z", description="Symmetry Z", default=False)
    symmetry_draw_x: bpy.props.BoolProperty(name="X", description="Symmetry X", default=False)
    symmetry_draw_y: bpy.props.BoolProperty(name="Y", description="Symmetry Y", default=False)

    shape: bpy.props.StringProperty(name="Shape", description="Shape", default='RECTANGLE')
    mode: bpy.props.StringProperty(name="Mode", description="Mode", default='ADD')

    offset: bpy.props.FloatProperty(name="Offset", description="Offset", default=0.0, subtype='DISTANCE')

    bevel: bpy.props.PointerProperty(type=BevelPref)
    bisect: bpy.props.PointerProperty(type=BisectPref)

    plane: bpy.props.PointerProperty(type=Plane)
    direction: bpy.props.FloatVectorProperty(name="Direction", description="Direction", default=(0, 1, 0), subtype='XYZ')

    transform_gizmo: bpy.props.BoolProperty(name="Transform Gizmo", description="Transform Gizmo", default=False)

    detected: bpy.props.StringProperty(name="Detected", description="Detected", default='')

    ngon: bpy.props.CollectionProperty(type=Ngon)


class Shape(bpy.types.PropertyGroup):
    volume: bpy.props.StringProperty(name="Volume", description="Volume", default='2D')
    rectangle: bpy.props.PointerProperty(type=Rectangle)
    ngon: bpy.props.PointerProperty(type=Ngon)
    circle: bpy.props.PointerProperty(type=Circle)
    sphere: bpy.props.PointerProperty(type=Sphere)
    corner: bpy.props.PointerProperty(type=Corner)


classes = (
    Corner,
    Rectangle,
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
