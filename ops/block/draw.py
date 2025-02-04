from mathutils import Vector
from ...bmeshutils import rectangle, circle
from ...utils import view3d
from .import orientation


def invoke(self, context):
    '''Build the mesh data'''

    obj = self.data.obj
    bm = self.data.bm

    plane = self.data.draw.plane

    if plane is None:
        self.report({'ERROR'}, 'Failed to detect drawing plane')
        return False

    shape = self.config.shape
    match shape:
        case 'RECTANGLE': self.data.draw.face = rectangle.create(bm, plane)
        case 'BOX': self.data.draw.face = rectangle.create(bm, plane)
        case 'CIRCLE': self.data.draw.face = circle.create(bm, plane, verts_number=self.shape.circle.verts)
        case 'CYLINDER': self.data.draw.face = circle.create(bm, plane, verts_number=self.shape.circle.verts)

    self.update_bmesh(obj, bm, loop_triangles=True, destructive=True)
    return True


def modal(self, context, event):
    obj = self.data.obj
    bm = self.data.bm

    region = context.region
    rv3d = context.region_data
    plane = self.data.draw.plane
    direction = self.data.draw.direction
    matrix_world = obj.matrix_world
    face = bm.faces[self.data.draw.face]

    bevel_verts = [obj.matrix_world @ v.co.copy() for v in face.verts]
    self.data.bevel.origin = sum(bevel_verts, Vector()) / len(bevel_verts)

    mouse_point_on_plane = view3d.region_2d_to_plane_3d(region, rv3d, self.mouse.co, plane, matrix=matrix_world)
    if mouse_point_on_plane is None:
        self.report({'WARNING'}, "Mouse was outside the drawing plane")
        return

    shape = self.config.shape

    if self.config.align.grid.enable:
        increments = self.config.align.grid.spacing
    else:
        increments = self.config.align.increments if event.ctrl else 0.0

    symmetry = self.data.draw.symmetry

    match shape:
        case 'RECTANGLE': self.shape.rectangle.co, point = rectangle.set_xy(face, plane, mouse_point_on_plane, direction, snap_value=increments, symmetry=symmetry)
        case 'BOX': self.shape.rectangle.co, point = rectangle.set_xy(face, plane, mouse_point_on_plane, direction, snap_value=increments, symmetry=symmetry)
        case 'CIRCLE': self.shape.circle.radius, point = circle.set_xy(face, plane, mouse_point_on_plane, snap_value=increments)
        case 'CYLINDER': self.shape.circle.radius, point = circle.set_xy(face, plane, mouse_point_on_plane, snap_value=increments)

    self.update_bmesh(obj, bm)

    self.data.extrude.plane = (matrix_world @ point, matrix_world.to_3x3() @ direction)

    if self.config.mode != 'CREATE':
        self.ui.faces.callback.update_batch([face])
