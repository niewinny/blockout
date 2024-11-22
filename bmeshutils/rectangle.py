import bmesh
from mathutils import Matrix, Vector
from . import facet


def create(bm, plane):
    '''Create a rectangle face'''

    location, normal = plane
    v1 = bm.verts.new(location)
    v2 = bm.verts.new(location)
    v3 = bm.verts.new(location)
    v4 = bm.verts.new(location)

    bm.verts.ensure_lookup_table()
    bm.verts.index_update()

    face = bm.faces.new((v1, v2, v3, v4))
    face.normal = normal
    face.select_set(True)
    bm.select_flush(True)

    bm.faces.ensure_lookup_table()
    bm.faces.index_update()

    return face.index


def set_xy(face, plane, loc, direction, local_space=False, snap_value=0):
    '''
    Expand the rectangle face. The `loc` parameter is always provided.
    If `local_space` is True, `loc` is given in the plane's local coordinate system.
    If `local_space` is False, `loc` is given in global coordinate system and will be transformed.
    '''
    # Unpack plane data
    location, normal = plane

    # Unpack face vertices
    v1, v2, v3, v4 = face.verts

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
    x0, y0 = 0, 0

    if local_space:
        # Use loc directly as it is in local plane space
        x1, y1 = loc.x, loc.y
    else:
        # Transform loc from object local space to plane local space
        mouse_local = matrix_inv @ loc
        x1, y1 = mouse_local.x, mouse_local.y

    # Apply snapping if a snap_value is provided
    if snap_value != 0:
        x1 = round(x1 / snap_value) * snap_value
        y1 = round(y1 / snap_value) * snap_value

    dx = x1 - x0
    dy = y1 - y0

    # Determine the quadrant based on the signs of dx and dy
    quadrant_key = (dx >= 0, dy >= 0)

    # Map quadrants to vertex positions using a dictionary
    vertex_assignments = {
        (True, True): [  # Quadrant I (dx >= 0, dy >= 0)
            Vector((x0, y0, 0)),  # v1_local
            Vector((x1, y0, 0)),  # v2_local
            Vector((x1, y1, 0)),  # v3_local
            Vector((x0, y1, 0)),  # v4_local
        ],
        (False, True): [  # Quadrant II (dx < 0, dy >= 0)
            Vector((x1, y0, 0)),
            Vector((x0, y0, 0)),
            Vector((x0, y1, 0)),
            Vector((x1, y1, 0)),
        ],
        (False, False): [  # Quadrant III (dx < 0, dy < 0)
            Vector((x1, y1, 0)),
            Vector((x0, y1, 0)),
            Vector((x0, y0, 0)),
            Vector((x1, y0, 0)),
        ],
        (True, False): [  # Quadrant IV (dx >= 0, dy < 0)
            Vector((x0, y1, 0)),
            Vector((x1, y1, 0)),
            Vector((x1, y0, 0)),
            Vector((x0, y0, 0)),
        ],
    }

    # Get the local vertex positions based on the quadrant
    v_local = vertex_assignments.get(quadrant_key)

    # If the quadrant key is not found, default all vertices to the initial point
    if v_local is None:
        v_local = [Vector((x0, y0, 0))] * 4

    # Unpack the local vertex positions
    v1_local, v2_local, v3_local, v4_local = v_local

    # Transform local coordinates back to object local space and update vertex positions
    v1.co = matrix @ v1_local
    v2.co = matrix @ v2_local
    v3.co = matrix @ v3_local
    v4.co = matrix @ v4_local

    # Compute the 3D point corresponding to (x1, y1, 0) in plane local space
    point_local = Vector((x1, y1, 0))
    point_3d = matrix @ point_local

    # Return dx, dy (2D location), and point_3d (3D point)
    return (dx, dy), point_3d


def create_box(bm, plane, loc, direction, extrusion, local_space=False, snap_value=0):
    '''Set the box from face'''

    face_index = create(bm, plane)
    bm.faces.ensure_lookup_table()
    face = bm.faces[face_index]
    set_xy(face, plane, loc, direction, local_space=True)
    draw_face, _extrude_face, _extrude_faces = facet.extrude(bm, face, plane, extrusion)

    face = bm.faces[draw_face]
    extrude_face = bm.faces[_extrude_face]
    extrude_faces = [bm.faces[index] for index in _extrude_faces]

    box_faces = [face, extrude_face] + extrude_faces

    bmesh.ops.recalc_face_normals(bm, faces=box_faces)

    box_edges = [e for f in box_faces for e in f.edges]
    bevel_edges = set(box_edges) - set(face.edges)

    edges = list(bevel_edges)

    return face, edges
