from dataclasses import dataclass
import bpy
from .draw import DrawLine, DrawGradient, DrawPolyline, DrawPlane, DrawFace, DrawGrid, DrawBMeshFaces


@dataclass
class Handle:
    '''Common functions for the handle data'''
    handle: int = None

    def remove(self):
        '''Remove the draw handler'''
        if self.handle:
            bpy.types.SpaceView3D.draw_handler_remove(self.handle, 'WINDOW')


@dataclass
class Line(Handle):
    '''Dataclass for the handle data.'''
    callback: DrawLine = None


@dataclass
class Gradient(Handle):
    '''Dataclass for the gradient data.'''
    callback: DrawGradient = None


@dataclass
class Polyline(Handle):
    '''Dataclass for the polyline data.'''
    callback: DrawPolyline = None


@dataclass
class Plane(Handle):
    '''Dataclass for the plane data.'''
    callback: DrawPlane = None


@dataclass
class Face(Handle):
    '''Dataclass for the face data.'''
    callback: DrawFace = None


@dataclass
class Grid(Handle):
    '''Dataclass for the grid data.'''
    callback: DrawGrid = None


@dataclass
class BMeshFaces(Handle):
    '''Dataclass for the bmesh face data.'''
    callback: DrawBMeshFaces = None


@dataclass
class Common:
    '''Common functions for the handle data'''

    def clear(self):
        """Remove all draw handlers."""
        for handle in vars(self).values():
            handle.remove()
