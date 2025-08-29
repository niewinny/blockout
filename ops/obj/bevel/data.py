from dataclasses import dataclass, field
import bpy
from mathutils import Vector
from ....shaders import handle


@dataclass
class Mouse:
    '''Dataclass for the mouse data'''
    init: Vector = Vector()
    co: Vector = Vector()
    saved: Vector = Vector()
    median: Vector = Vector()


@dataclass
class Distance:
    '''Dataclass for the distance calculation'''
    length: float = 0.0
    delta: float = 0.0
    precision: float = 0.0


@dataclass
class Bevel:
    '''Dataclass for the modifier data'''
    obj: bpy.types.Object = None
    mod: bpy.types.Modifier = None
    new: bool = False
    initial_width: float = 0.0


@dataclass
class DrawUI:
    '''Dataclass for the UI drawing'''
    guide: handle.Polyline = field(default_factory=handle.Polyline)
    interface: handle.Interface = field(default_factory=handle.Interface)