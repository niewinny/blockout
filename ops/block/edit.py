import math
import bmesh
from mathutils import Matrix, Vector
from ...utils import view3d
from ...utils.types import DrawVert
from ...utilsbmesh import ngon


def invoke(self, context):
    '''Build the mesh data'''

    self.mode = 'EDIT'
    self.edit_mode = 'INIT'
    obj = self.data.obj
    bm = self.data.bm

    plane = self.data.draw.matrix.plane

    if plane is None:
        self.report({'ERROR'}, 'Failed to detect drawing plane')
        return False

    self.update_bmesh(obj, bm, loop_triangles=True, destructive=True)
    return True



def modal(self, context, event):
    obj = self.data.obj
    bm = self.data.bm

    region = context.region
    rv3d = context.region_data
    plane = self.data.draw.matrix.plane
    direction = self.data.draw.matrix.direction
    matrix_world = obj.matrix_world
    faces = [bm.faces[i] for i in self.data.draw.faces]
    symmetry = self.data.draw.symmetry

    mouse = self.mouse.co

    increments = self.config.align.increments if event.ctrl else 0.0

    verts = [bm.verts[i.index] for i in self.data.draw.verts]

    mouse_point_on_plane = view3d.region_2d_to_plane_3d(region, rv3d, self.mouse.co, plane, matrix=matrix_world)
    if mouse_point_on_plane is None:
        self.report({'WARNING'}, "Mouse was outside the drawing plane")
        return

    # Unpack plane data
    location, normal = plane

    # Build consistent x and y axes for the plane's local coordinate system
    x_axis = direction.normalized()
    y_axis = normal.cross(x_axis).normalized()

    # Build the transformation matrix from plane local space to object local space
    rotation_matrix = Matrix((x_axis, y_axis, normal)).transposed()
    matrix = rotation_matrix.to_4x4()
    matrix.translation = location

    # Build the inverse matrix from object local space to plane local space
    matrix_inv = matrix.inverted_safe()

    mouse_local = matrix_inv @ mouse_point_on_plane
    x1, y1 = mouse_local.x, mouse_local.y

    # Apply snapping if a snap_value is provided
    if increments != 0:
        x1 = round(x1 / increments) * increments
        y1 = round(y1 / increments) * increments

    dx = x1
    dy = y1


    if self.edit_mode == 'GET':

        if self.data.draw.faces:
            face = bm.faces[self.data.draw.faces[0]]

            for e in face.edges:
                mid_edge_co = (e.verts[0].co + e.verts[1].co) / 2
                reg = view3d.location_3d_to_region_2d(region, rv3d, mid_edge_co, default=obj.location)
                if is_near(region, mouse, reg):
                    self.edit_mode = 'ADD_VERT'
                    self.edit_point = e.index
                    break

            for v in face.verts:
                reg = view3d.location_3d_to_region_2d(region, rv3d, v.co, default=obj.location)
                if is_near(region, mouse, reg):
                    self.edit_mode = 'MOVE'
                    self.edit_point = v.index
                    break

    if self.edit_mode == 'GET':
        self.edit_mode = 'END'

        return

    if self.edit_mode == 'ADD_VERT':

        match self.config.shape:
            case 'NGON': verts = ngon.add_vert(bm, self.edit_point)
            case 'NHEDRON': verts = ngon.add_vert(bm, self.edit_point)

        # Safety check to ensure we have vertices
        if not verts:
            self.report({'ERROR'}, 'Failed to add vertex to edge')
            return
        
        self.edit_point = verts[0].index
        self.data.draw.verts.append(DrawVert(index=verts[0].index, co=verts[0].co))

        self.edit_mode = 'MOVE'
        self.update_bmesh(obj, bm)

    if self.edit_mode == 'INIT':

        # Safety check to ensure we have enough vertices
        if len(self.data.draw.verts) < 2:
            self.report({'ERROR'}, 'Insufficient vertices for initialization')
            return
        
        self.edit_point = self.data.draw.verts[-2].index
        self.edit_mode = 'MOVE'

    if self.edit_mode in {'MOVE'}:

        index = next((idx for idx, vert in enumerate(self.data.draw.verts) if vert.index == self.edit_point), None)
        match self.config.shape:
            case 'NGON': self.data.draw.verts[index].region, point = ngon.set_xy(bm, self.edit_point, plane, mouse_point_on_plane, direction, snap_value=increments, symmetry=symmetry)
            case 'NHEDRON': self.data.draw.verts[index].region, point = ngon.set_xy(bm, self.edit_point, plane, mouse_point_on_plane, direction, snap_value=increments, symmetry=symmetry)

        self.update_bmesh(obj, bm)
        ngon.store(self)

        match self.config.shape:
            case 'NGON' | 'NHEDRON':
                faces = [bm.faces[i] for i in self.data.draw.faces]
                points_gloabal = []
                for p in self.data.draw.verts:
                    point = bm.verts[p.index].co
                    points_gloabal.append(matrix_world @ point)

                self.ui.vert.callback.update_batch(points_gloabal)
                if self.config.mode != 'ADD':
                    self.ui.faces.callback.update_batch(faces)

                self.ui.active.callback.update_batch([matrix_world @ bm.verts[self.edit_point].co.copy()])

                point_x_2d = self.mouse.co.copy()
                point_x_2d.x += 20
                point_y_2d = self.mouse.co.copy()
                point_y_2d.x += 140
                lines = [
                    {"point": point_x_2d, "text_tuple": (f"X: {dx:.3f}",)},
                    {"point": point_y_2d, "text_tuple": (f"Y: {dy:.3f}",)},
                ]
                self.ui.interface.callback.update_batch(lines)

    if self.edit_mode == 'NONE':
        self.ui.interface.callback.update_batch([])

        highlight = []
        if self.data.draw.faces:

            face = bm.faces[self.data.draw.faces[0]]

            for e in face.edges:
                mid_edge_co = (e.verts[0].co + e.verts[1].co) / 2
                reg = view3d.location_3d_to_region_2d(region, rv3d, mid_edge_co, default=obj.location)
                if is_near(region, mouse, reg):
                    highlight = [matrix_world  @ mid_edge_co]
                    break

            for v in face.verts:
                reg = view3d.location_3d_to_region_2d(region, rv3d, v.co, default=obj.location)
                if is_near(region, mouse, reg):
                    highlight = [matrix_world @ v.co.copy()]
                    break

            self.ui.active.callback.update_batch(highlight)

def is_near(region, point1, point2):
    """Check if point2 is within 'threshold' pixels of point1."""
    height = region.height
    width = region.width
    threshold = 0.02 * max(width, height)
    dist = math.hypot(point2[0] - point1[0], point2[1] - point1[1])
    return dist < threshold
