from mathutils import Matrix, Vector
import math
import bmesh

def create(bm, plane, verts_number):
    '''Create a circle face with specified number of vertices'''
    location, normal = plane

    # Build coordinate axes
    # We'll pick an arbitrary axis that is perpendicular to the normal
    if abs(normal.z) < 0.9999:
        x_axis = normal.cross(Vector((0, 0, 1))).normalized()
    else:
        x_axis = normal.cross(Vector((0, 1, 0))).normalized()

    y_axis = normal.cross(x_axis).normalized()

    # Build the transformation matrix
    rotation_matrix = Matrix((x_axis, y_axis, normal)).transposed()
    matrix = rotation_matrix.to_4x4()
    matrix.translation = location

    # Create circle with a small initial diameter
    result = bmesh.ops.create_circle(
        bm,
        cap_ends=True,
        radius=0.0,  # Small initial diameter
        segments=verts_number,
        matrix=matrix
    )

    bm.verts.ensure_lookup_table()
    bm.verts.index_update()

    bm.faces.ensure_lookup_table()
    bm.faces.index_update()

    vert = result['verts'][0]
    face = vert.link_faces[0]
    face.normal_update()
    face.select_set(True)
    bm.select_flush(True)

    return face.index


def set_xy(face, plane, loc=None, radius=None, local_space=False, snap_value=0):
    '''
    Expand the circle face. If `radius` is provided, it will be used directly.
    Otherwise, the `loc` parameter is used to compute the radius.
    '''
    # Unpack plane data
    location, normal = plane

    # Build coordinate axes
    if abs(normal.z) < 0.9999:
        x_axis = normal.cross(Vector((0, 0, 1))).normalized()
    else:
        x_axis = normal.cross(Vector((0, 1, 0))).normalized()

    y_axis = normal.cross(x_axis).normalized()

    # Build the transformation matrix
    rotation_matrix = Matrix((x_axis, y_axis, normal)).transposed()
    matrix = rotation_matrix.to_4x4()
    matrix.translation = location

    # Inverse matrix for coordinate transformation
    matrix_inv = matrix.inverted_safe()

    if radius is None:
        if loc is None:
            raise ValueError("Either 'radius' or 'loc' must be provided")

        if local_space:
            x1, y1 = loc.x, loc.y
        else:
            mouse_local = matrix_inv @ loc
            x1, y1 = mouse_local.x, mouse_local.y

        if snap_value != 0:
            x1 = round(x1 / snap_value) * snap_value
            y1 = round(y1 / snap_value) * snap_value

        # Compute the radius
        radius = math.hypot(x1, y1)
        point_local = Vector((x1, y1, 0))
    else:
        # Use radius directly
        point_local = Vector((radius, 0, 0))

    # Update the positions of the face's vertices
    verts = face.verts
    num_verts = len(verts)
    angle_step = (2 * math.pi) / num_verts

    for i, v in enumerate(verts):
        angle = i * angle_step
        x = radius * math.cos(angle)
        y = radius * math.sin(angle)
        v_local = Vector((x, y, 0))
        v.co = matrix @ v_local

    # Transform point_local to object local space
    point_3d = matrix @ point_local

    return radius, point_3d
