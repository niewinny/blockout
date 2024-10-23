import bmesh
from mathutils import Matrix, Vector


def create(bm, plane):
    '''Create a rectangle face'''

    location, normal = plane
    v1 = bm.verts.new(location)
    v2 = bm.verts.new(location)
    v3 = bm.verts.new(location)
    v4 = bm.verts.new(location)
    face = bm.faces.new((v1, v2, v3, v4))
    face.normal = normal

    return face

def expand(face, plane, loc, direction, local_space=False):
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
    matrix_inv = matrix.inverted()

    # In plane local space, the initial point is at the origin
    x0, y0 = 0, 0

    if local_space:
        # Use loc directly as it is in local plane space
        x1, y1 = loc.x, loc.y
    else:
        # Transform loc from object local space to plane local space
        mouse_local = matrix_inv @ loc
        x1, y1 = mouse_local.x, mouse_local.y

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

    return dx, dy


def extrude(bm, face, plane, dz):
    '''Extrude the face along the given direction by dz units'''

    # Normalize the direction vector
    _, normal = plane

    # Extrude the face region
    result = bmesh.ops.extrude_face_region(bm, geom=[face])

    # Collect the new geometry
    geom_extruded = result['geom']

    # Get the new faces and vertices
    new_faces = [ele for ele in geom_extruded if isinstance(ele, bmesh.types.BMFace)]
    new_verts = [ele for ele in geom_extruded if isinstance(ele, bmesh.types.BMVert)]

    # Move the new vertices along the direction vector by dz
    move_vector = -normal * dz
    for v in new_verts:
        v.co += move_vector

    # Recalculate normals if necessary
    bmesh.ops.recalc_face_normals(bm, faces=new_faces)

    return new_faces[0]
