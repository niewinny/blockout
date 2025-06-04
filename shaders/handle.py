from dataclasses import dataclass
import bpy
from .draw import DrawLine, DrawGradient, DrawPolyline, DrawPlane, DrawFace, DrawGrid, DrawBMeshFaces, DrawPoints
from .interface import InterfaceDraw


draw_handlers = []


@dataclass
class Handle:
    '''Common functions for the handle data'''
    handle: int = None

    def remove(self):
        '''Remove the draw handler'''
        if self.handle:
            bpy.types.SpaceView3D.draw_handler_remove(self.handle, 'WINDOW')
            if self.handle in draw_handlers:
                draw_handlers.remove(self.handle)


@dataclass
class Line(Handle):
    '''Dataclass for the handle data.'''
    callback: DrawLine = None

    def create(self, context, points=(), width=1.6, color=(0, 0, 0, 1), depth=False):
        '''Create a line draw handler.'''
        self.callback = DrawLine(points=points, width=width, color=color, depth=depth)
        self.handle = bpy.types.SpaceView3D.draw_handler_add(self.callback.draw, (context,), 'WINDOW', 'POST_VIEW')
        draw_handlers.append(self.handle)


@dataclass
class Gradient(Handle):
    '''Dataclass for the gradient data.'''
    callback: DrawGradient = None

    def create(self, context, points=(), colors=()):
        '''Create a gradient draw handler.'''
        self.callback = DrawGradient(points=points, colors=colors)
        self.handle = bpy.types.SpaceView3D.draw_handler_add(self.callback.draw, (context,), 'WINDOW', 'POST_PIXEL')
        draw_handlers.append(self.handle)


@dataclass
class Polyline(Handle):
    '''Dataclass for the polyline data.'''
    callback: DrawPolyline = None

    def create(self, context, points=(), width=1.6, color=(0, 0, 0, 1)):
        '''Create a polyline draw handler.'''
        self.callback = DrawPolyline(points=points, width=width, color=color)
        self.handle = bpy.types.SpaceView3D.draw_handler_add(self.callback.draw, (context,), 'WINDOW', 'POST_VIEW')
        draw_handlers.append(self.handle)


@dataclass
class Points(Handle):
    '''Dataclass for the points data.'''
    callback: DrawPoints = None

    def create(self, context, points=(), size=1.0, color=(0, 0, 0, 1)):
        '''Create a points draw handler.'''
        self.callback = DrawPoints(points=points, size=size, color=color)
        self.handle = bpy.types.SpaceView3D.draw_handler_add(self.callback.draw, (context,), 'WINDOW', 'POST_VIEW')
        draw_handlers.append(self.handle)


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

    def create(self, context, obj=None, faces=None, color=(0, 0, 0, 1)):
        '''Create a bmesh face draw handler.'''
        if faces is None:
            faces = []
        self.callback = DrawBMeshFaces(obj=obj, faces=faces, color=color)
        self.handle = bpy.types.SpaceView3D.draw_handler_add(self.callback.draw, (context,), 'WINDOW', 'POST_VIEW')
        draw_handlers.append(self.handle)


@dataclass
class Interface(Handle):
    """Dataclass for the interface data."""
    callback: InterfaceDraw = None

    def create(self, context, lines):
        """Create an interface draw handler.
        Args:
            context: The current context
            lines: List of dictionaries, each containing:
                  - "point": tuple (x, y) for position
                  - "text_tuple": tuple of strings for text
                  Example: [
                      {"point": (x1, y1), "text_tuple": ("text1", "text2")},
                      {"point": (x2, y2), "text_tuple": ("text3", "text4")}
                  ]
        """
        self.callback = InterfaceDraw(lines=lines)
        self.handle = bpy.types.SpaceView3D.draw_handler_add(self.callback.draw, (context,), 'WINDOW', 'POST_PIXEL')
        draw_handlers.append(self.handle)


@dataclass
class Common:
    '''Common functions for the handle data'''

    def clear(self):
        """Remove all draw handlers."""
        for handle in vars(self).values():
            handle.remove()

    def clear_all(self):
        """Remove all draw handlers."""
        for handle in draw_handlers:
            bpy.types.SpaceView3D.draw_handler_remove(handle, 'WINDOW')
        draw_handlers.clear()
