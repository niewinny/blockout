import bpy
from dataclasses import dataclass, field
from mathutils import Vector
from ...utils.types import DrawMatrix


@dataclass
class Mouse:
    """Dataclass for tracking mouse positions."""
    area: Vector = Vector()
    window: Vector = Vector()


@dataclass
class CreatedData:
    '''Dataclass for storing'''
    matrix: DrawMatrix = field(default_factory=DrawMatrix)
    obj: bpy.types.Object = None
    selected_objects: list[bpy.types.Object] = field(default_factory=list)
