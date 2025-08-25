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

    increments = self.config.align.increments if self.config.snap else 0.0

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
                # Transform from object local space to world space for projection
                mid_edge_co_world = matrix_world @ mid_edge_co
                reg = view3d.location_3d_to_region_2d(region, rv3d, mid_edge_co_world, default=obj.location)
                if _is_near(region, mouse, reg):
                    self.edit_mode = 'ADD_VERT'
                    self.edit_point = e.index
                    self.highlight_type = 'EDGE'
                    break

            for v in face.verts:
                # Transform from object local space to world space for projection
                v_co_world = matrix_world @ v.co
                reg = view3d.location_3d_to_region_2d(region, rv3d, v_co_world, default=obj.location)
                if _is_near(region, mouse, reg):
                    self.edit_mode = 'MOVE'
                    self.edit_point = v.index
                    self.highlight_type = 'VERTEX'
                    break

    if self.edit_mode == 'GET':
        self.edit_mode = 'END'

        return

    if self.edit_mode == 'DELETE':
        # Check if we have more than 3 vertices and a valid highlight
        if len(self.data.draw.verts) > 3 and hasattr(self, 'highlight_index') and self.highlight_index is not None:
            match self.config.shape:
                case 'NGON' | 'NHEDRON':
                    # Dissolve the vertex
                    removed_vert, new_face_index = ngon.dissolve_vert(bm, self.highlight_index, self.data.draw.faces[0])
                    
                    if removed_vert:
                        # Update face index
                        self.data.draw.faces[0] = new_face_index
                        
                        # Fix winding order after deletion
                        plane_normal = plane[1]
                        new_face_index = ngon.fix_winding_order(bm, new_face_index, plane_normal)
                        self.data.draw.faces[0] = new_face_index
                        
                        # Rebuild the draw verts list with correct indices from the face
                        # Don't preserve first if it was the deleted vertex
                        preserve_first = self.data.draw.verts[0].index != self.highlight_index
                        _rebuild_vertex_list(self, bm, new_face_index, preserve_first=preserve_first)
                        
                        self.update_bmesh(obj, bm)
                        ngon.store(self)
                        
                        # Update shader/UI with new vertex positions
                        _update_ui_after_change(self, bm, matrix_world)
                        
                        # Clear the active highlight
                        self.ui.active.callback.update_batch([])
                    else:
                        self.report({'INFO'}, 'Cannot delete vertex: minimum 3 vertices required')
        
        self.edit_mode = 'NONE'
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
        
        # Rebuild the vertex list from the face to maintain consistency
        # The face may have been recreated with vertices in a different order
        _rebuild_vertex_list(self, bm, self.data.draw.faces[0], preserve_first=True)

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
        
        # Check if index is valid
        if index is None:
            self.edit_mode = 'NONE'
            return
            
        match self.config.shape:
            case 'NGON': 
                self.data.draw.verts[index].region, point = ngon.set_xy(bm, self.edit_point, plane, mouse_point_on_plane, direction, snap_value=increments, symmetry=symmetry)
                # Update the stored position
                self.data.draw.verts[index].co = bm.verts[self.edit_point].co.copy()
            case 'NHEDRON': 
                self.data.draw.verts[index].region, point = ngon.set_xy(bm, self.edit_point, plane, mouse_point_on_plane, direction, snap_value=increments, symmetry=symmetry)
                # Update the stored position
                self.data.draw.verts[index].co = bm.verts[self.edit_point].co.copy()

        # After moving vertex, fix winding order if needed
        if self.data.draw.faces and len(self.data.draw.verts) >= 3:
            plane_normal = plane[1]
            new_face_index = ngon.fix_winding_order(bm, self.data.draw.faces[0], plane_normal)
            if new_face_index != self.data.draw.faces[0]:
                self.data.draw.faces[0] = new_face_index

        self.update_bmesh(obj, bm)
        ngon.store(self)

        match self.config.shape:
            case 'NGON' | 'NHEDRON':
                _update_ui_after_change(self, bm, matrix_world)

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
        self.highlight_type = None
        self.highlight_index = None
        
        if self.data.draw.faces:

            face = bm.faces[self.data.draw.faces[0]]

            for e in face.edges:
                mid_edge_co = (e.verts[0].co + e.verts[1].co) / 2
                # Transform from object local space to world space for projection
                mid_edge_co_world = matrix_world @ mid_edge_co
                reg = view3d.location_3d_to_region_2d(region, rv3d, mid_edge_co_world, default=obj.location)
                if _is_near(region, mouse, reg):
                    highlight = [mid_edge_co_world]
                    self.highlight_type = 'EDGE'
                    self.highlight_index = e.index
                    break

            for v in face.verts:
                # Transform from object local space to world space for projection
                v_co_world = matrix_world @ v.co
                reg = view3d.location_3d_to_region_2d(region, rv3d, v_co_world, default=obj.location)
                if _is_near(region, mouse, reg):
                    highlight = [v_co_world]
                    self.highlight_type = 'VERTEX'
                    self.highlight_index = v.index
                    break

            self.ui.active.callback.update_batch(highlight)

def _rebuild_vertex_list(self, bm, face_index, preserve_first=True):
    """
    Rebuild the draw vertex list from the face, preserving the drawing vertex position.
    
    Args:
        bm: The BMesh object
        face_index: The face index to rebuild from
        preserve_first: If True, keep the first vertex as the first vertex if it still exists
    
    Returns:
        None (updates self.data.draw.verts in place)
    """
    face = bm.faces[face_index]
    
    # Store the current drawing vertex (first vertex) if we need to preserve it
    drawing_vert_index = None
    if preserve_first and len(self.data.draw.verts) > 0:
        drawing_vert_index = self.data.draw.verts[0].index
    
    # Build new vertex list
    new_draw_verts = []
    drawing_vert = None
    
    # First pass: find all vertices and identify the drawing vertex
    for v in face.verts:
        draw_vert = DrawVert(index=v.index, co=v.co.copy())
        if v.index == drawing_vert_index:
            drawing_vert = draw_vert
        else:
            new_draw_verts.append(draw_vert)
    
    # Reconstruct list with drawing vertex first (if it exists and we're preserving)
    if drawing_vert and preserve_first:
        self.data.draw.verts = [drawing_vert] + new_draw_verts
    else:
        # Just use face vertex order
        self.data.draw.verts = []
        for v in face.verts:
            self.data.draw.verts.append(DrawVert(index=v.index, co=v.co.copy()))


def _update_ui_after_change(self, bm, matrix_world):
    """Update the UI/shader after vertex changes."""
    faces = [bm.faces[i] for i in self.data.draw.faces]
    points_global = []
    for p in self.data.draw.verts:
        point = bm.verts[p.index].co
        points_global.append(matrix_world @ point)
    
    self.ui.vert.callback.update_batch(points_global)
    if self.config.mode != 'ADD':
        self.ui.faces.callback.update_batch(faces)


def _is_near(region, point1, point2):
    """Check if point2 is within 'threshold' pixels of point1."""
    height = region.height
    width = region.width
    threshold = 0.02 * max(width, height)
    dist = math.hypot(point2[0] - point1[0], point2[1] - point1[1])
    return dist < threshold
