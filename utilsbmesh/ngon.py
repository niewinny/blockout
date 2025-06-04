import bmesh
from ..utils.types import DrawVert
from mathutils import Matrix, Vector


def create(bm, plane):
    '''Create a ngon face'''

    location, normal = plane
    v1 = bm.verts.new(location)
    v2 = bm.verts.new(location)
    v3 = bm.verts.new(location)

    edge1 = bm.edges.new((v1, v2))
    edge2 = bm.edges.new((v2, v3))
    edge3 = bm.edges.new((v3, v1))

    face = bm.faces.new((v1, v2, v3))
    face_index = face.index
    face.normal = normal
    face.select_set(True)

    bm.verts.ensure_lookup_table()
    bm.verts.index_update()
    bm.edges.ensure_lookup_table()
    bm.edges.index_update()
    bm.faces.ensure_lookup_table()
    bm.faces.index_update()

    bm.select_flush(True)

    return [face_index], [DrawVert(index=v1.index, co=v1.co), DrawVert(index=v2.index, co=v2.co), DrawVert(index=v3.index, co=v3.co)]


def set_xy(bm, vert_index, plane, loc, direction, local_space=False, snap_value=0, symmetry=(False, False)):
    '''
    Move a single ngon vertex to the given xy location in the plane's local coordinate system.
    Updates vert.co and returns (dx, dy), point_3d.
    '''

    vert = bm.verts[vert_index]

    symx, symy = symmetry

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

    # In plane local space, the initial point is at the origin
    if local_space:
        x1, y1 = loc.x, loc.y
    else:
        mouse_local = matrix_inv @ loc
        x1, y1 = mouse_local.x, mouse_local.y

    # Apply snapping if a snap_value is provided
    if snap_value != 0:
        x1 = round(x1 / snap_value) * snap_value
        y1 = round(y1 / snap_value) * snap_value

    x0 = -x1 if symy else 0
    y0 = -y1 if symx else 0

    dx = x1 - x0
    dy = y1 - y0

    # Update the vertex position in 3D
    point_local = Vector((x1, y1, 0))
    point_3d = matrix @ point_local
    vert.co = point_3d

    # Return dx, dy (2D location), and point_3d (3D point)
    if symx:
        dy = dy / 2
    if symy:
        dx = dx / 2

    return (dx, dy), point_3d


def add_vert(bm, index):
    '''Add a vertex to the ngon'''

    edge = bm.edges[index]
    result = bmesh.ops.bisect_edges(bm, edges=[edge], cuts=1)

    bm.verts.ensure_lookup_table()
    bm.verts.index_update()
    bm.edges.ensure_lookup_table()
    bm.edges.index_update()
    bm.faces.ensure_lookup_table()
    bm.faces.index_update()

    verts = [v for v in result['geom_split'] if isinstance(v, bmesh.types.BMVert)]

    return verts


def new(bm, verts_list):
    '''Create a ngon face'''

    verts = []
    for v in verts_list:
        vert = bm.verts.new(v.co)
        verts.append(vert)

    face = bm.faces.new(verts)
    face.select_set(True)

    bm.select_flush(True)

    return face


def store(self):
    '''Store the ngon face'''

    self.pref.ngon.clear()
    if self.data.draw.faces:
        face = self.data.bm.faces[self.data.draw.faces[0]]
        for v in face.verts:
            ngon_item = self.pref.ngon.add()
            ngon_item.co = v.co
