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
    vert = result['verts'][0]
    print(vert)
    face = vert.link_faces[0]
    face.normal_update()
    face.select_set(True)
    bm.select_flush(True)

    return face


def set_xy(face, plane, loc, direction, local_space=False, snap_value=0):
    '''
    Expand the circle face. The `loc` parameter is always provided.
    If `local_space` is True, `loc` is given in the plane's local coordinate system.
    If `local_space` is False, `loc` is given in global coordinate system and will be transformed.
    '''
    # Unpack plane data
    location, normal = plane

    # Build coordinate axes
    if abs(normal.z) < 0.9999:
        x_axis = normal.cross(Vector((0, 0, 1))).normalized()
    else:
        x_axis = normal.cross(Vector((0, 1, 0))).normalized()

    y_axis = normal.cross(x_axis).normalized()

    # Build the transformation matrix from plane local space to object local space
    rotation_matrix = Matrix((x_axis, y_axis, normal)).transposed()
    matrix = rotation_matrix.to_4x4()
    matrix.translation = location

    # Build the inverse matrix from object local space to plane local space
    matrix_inv = matrix.inverted_safe()

    # Origin in plane local space
    x0, y0 = 0, 0

    if local_space:
        # Use loc directly as it's in local plane space
        x1, y1 = loc.x, loc.y
    else:
        # Transform loc from object local space to plane local space
        mouse_local = matrix_inv @ loc
        x1, y1 = mouse_local.x, mouse_local.y

    # Apply snapping if snap_value is provided
    if snap_value != 0:
        x1 = round(x1 / snap_value) * snap_value
        y1 = round(y1 / snap_value) * snap_value

    # Compute the radius
    dx = x1 - x0
    dy = y1 - y0
    radius = math.hypot(dx, dy)

    # Update the positions of the face's vertices
    verts = face.verts
    num_verts = len(verts)
    angle_step = (2 * math.pi) / num_verts

    for i, v in enumerate(verts):
        angle = i * angle_step
        # Position in local space
        x = radius * math.cos(angle)
        y = radius * math.sin(angle)
        v_local = Vector((x, y, 0))
        # Transform to object local space
        v.co = matrix @ v_local

    # Compute the 3D point corresponding to the current mouse position
    point_local = Vector((x1, y1, 0))
    point_3d = matrix @ point_local

    # Return (dx, dy) as radius components and the 3D point
    return (dx, dy), point_3d
