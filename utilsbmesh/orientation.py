import math
from mathutils import Vector, Matrix, Euler
from ..utilsmath import geometry as geom
from ..utils import view3d


def direction_from_closest_edge(obj, face, loc):
    '''
    Get the direction from the closest edge

    :param obj: Object containing the face
    :param face: Face to find the closest edge for
    :param loc: Location to measure distance from
    :return: Direction vector along the closest edge
    '''
    matrix = obj.matrix_world
    edge = min(face.edges, key=lambda e: geom.distance_point_to_segment(loc, matrix @ e.verts[0].co, matrix @ e.verts[1].co))

    # get loop for the edge that is also in the face
    loop = next((loop for loop in edge.link_loops if loop.face == face), None)
    start_vert = loop.vert
    end_vert = loop.link_loop_next.vert
    direction = end_vert.co - start_vert.co

    tangent = edge.calc_tangent(loop)
    normal = direction.cross(tangent).normalized()

    return edge, direction, normal


def direction_from_normal(normal):
    '''
    Get the direction vector perpendicular to a normal

    :param normal: Normal vector
    :return: Direction vector perpendicular to the normal
    '''
    up_vector = Vector((0, 0, 1))
    if abs(normal.dot(up_vector)) > 0.9999:
        up_vector = Vector((0, 1, 0))

    direction = normal.cross(up_vector).normalized()

    return direction


def snap_plane(plane, snap_plane, direction, snap_value):
    '''
    Snap a point onto a plane and then onto a grid in that plane along the given direction
    and its perpendicular direction.

    :param plane: Tuple (origin, normal), defining the plane with point to snap
    :param snap_plane: Tuple (origin, normal), defining the target plane
    :param direction: Vector, a direction vector lying in the plane
    :param snap_value: Float, the grid spacing to snap to
    :return: Tuple (snapped_point, normal), the snapped point on the plane and the normal
    '''

    if plane[0] is None:
        return plane

    origin, normal = snap_plane
    point, _ = plane
    normal = normal.normalized()
    u = direction.normalized()
    v = normal.cross(u).normalized()

    # Project the point onto the plane
    vec = point - origin
    distance = vec.dot(normal)
    projected_point = point - distance * normal

    # Vector from plane origin to the projected point
    vec_in_plane = projected_point - origin

    # Coordinates in the plane along u and v
    s = vec_in_plane.dot(u)
    t = vec_in_plane.dot(v)

    # Snap s and t to the nearest multiple of snap_value
    s_snapped = round(s / snap_value) * snap_value
    t_snapped = round(t / snap_value) * snap_value

    # Reconstruct the snapped point
    snapped_point = origin + s_snapped * u + t_snapped * v

    return snapped_point, plane[1]


def point_on_axis(region, rv3d, plane, direction, point, distance):
    '''
    Get the closest point on the plane along the given axis within the given distance

    :param region: Region for 2D to 3D conversion
    :param rv3d: Region view 3D for 2D to 3D conversion
    :param plane: Tuple (origin, normal) defining the plane
    :param direction: Direction vector in the plane
    :param point: Point to project onto the axis
    :param distance: Maximum distance for snapping
    :return: Tuple (point, (snap_x, snap_y)) with the snapped point and snap status
    '''

    if not point:
        return None, (None, None)

    location, normal = plane
    x_axis = direction.normalized()
    z_axis = normal.normalized()
    y_axis = z_axis.cross(x_axis).normalized()

    vec = point - location
    proj_length = vec.dot(y_axis)
    proj_vec_y = proj_length * y_axis
    proj_vec_x = vec - proj_vec_y

    length_x = proj_vec_x.length
    length_y = proj_vec_y.length

    point_2d = view3d.location_3d_to_region_2d(region, rv3d, point)

    # First check center point
    if length_x <= 1 and length_y <= 1:
        # Verify in 2D space
        center_2d = view3d.location_3d_to_region_2d(region, rv3d, location)
        if center_2d and point_2d:
            if (center_2d - point_2d).length <= distance:
                return location, (True, True)

    # If center point didn't work, check individual axes
    if length_x <= 1:
        projected_point = location + proj_vec_y
        projected_2d = view3d.location_3d_to_region_2d(region, rv3d, projected_point)
        if projected_2d and point_2d:
            if (projected_2d - point_2d).length <= distance:
                return projected_point, (False, True)

    if length_y <= 1:
        projected_point = location + proj_vec_x
        projected_2d = view3d.location_3d_to_region_2d(region, rv3d, projected_point)
        if projected_2d and point_2d:
            if (projected_2d - point_2d).length <= distance:
                return projected_point, (True, False)

    # No valid snapping found
    return point, (False, False)


def face_bbox_center(face, matrix):
    """
    Compute the axis-aligned bounding box center for a face

    :param face: Face to compute the bounding box for
    :param matrix: Matrix to transform from local to world space
    :return: Center of the face's bounding box in world space
    """

    # 1. Convert normal and direction to world space if not already
    normal_world = (matrix.to_3x3() @ face.normal).normalized()
    location_world = matrix @ face.calc_center_median()
    direction_world = (matrix.to_3x3() @ face.calc_tangent_edge()).normalized()

    x_axis = direction_world.normalized()
    y_axis = normal_world.cross(x_axis).normalized()

    # 2. Gather the face's vertices in world space
    verts_local = [v.co for v in face.verts]
    verts_world = [matrix @ v for v in verts_local]

    # 3. Project each vertex into (x_axis, y_axis) space, with origin = location_world
    coords_2d = []
    for p in verts_world:
        rel = p - location_world
        px = rel.dot(x_axis)
        py = rel.dot(y_axis)
        coords_2d.append((px, py))

    # 4. Compute the axis-aligned bounding box in that 2D system
    min_x = min(px for px, py in coords_2d)
    max_x = max(px for px, py in coords_2d)
    min_y = min(py for px, py in coords_2d)
    max_y = max(py for px, py in coords_2d)

    # 5. The bounding-box center in 2D coords
    center_2d = (
        0.5 * (min_x + max_x),
        0.5 * (min_y + max_y),
    )

    # 6. Convert that center back into 3D world space
    bbox_center_world = (
        location_world +
        center_2d[0] * x_axis +
        center_2d[1] * y_axis
    )

    return bbox_center_world


def set_align_rotation_from_vectors(normal, direction):
    """
    Set context.scene.bout.align.rotation from normal and direction vectors.

    :param normal: Normal vector of the plane
    :param direction: Direction vector along the plane (should be perpendicular to normal)
    :return: Euler rotation angles in radians [x, y, z]
    """

    normal = normal.normalized()
    direction = direction.normalized()

    # Handle exact axis-aligned cases for precision
    x_pos = Vector((1, 0, 0))
    x_neg = Vector((-1, 0, 0))
    y_pos = Vector((0, 1, 0))
    y_neg = Vector((0, -1, 0))
    z_pos = Vector((0, 0, 1))
    z_neg = Vector((0, 0, -1))

    axis_threshold = 0.999

    # This now handles ALL cases, including axis-aligned ones
    z_axis = normal
    x_axis = direction
    y_axis = z_axis.cross(x_axis).normalized()
    x_axis = y_axis.cross(z_axis).normalized()

    rotation_matrix = Matrix((x_axis, y_axis, z_axis)).transposed().to_3x3()
    euler = rotation_matrix.to_euler('XYZ')
    rotation_radians = [angle for angle in euler]

    # Snap angles close to 90° increments to exact values
    half_pi = math.pi/2
    for i, angle in enumerate(rotation_radians):
        if abs(angle % half_pi) < 0.01 or abs(angle % half_pi - half_pi) < 0.01:
            rotation_radians[i] = round(angle / half_pi) * half_pi

    return rotation_radians


def get_vectors_from_align_rotation(rotation):
    """
    Convert rotation angles (in radians) back to normal and direction vectors.
    This is the inverse function of set_align_rotation_from_vectors.

    :param rotation: Euler angles in radians [x, y, z]
    :return: Tuple with (normal, direction) vectors
    """

    # Convert Euler angles to a rotation matrix
    rot_euler = Euler(rotation, 'XYZ')
    rotation_matrix = rot_euler.to_matrix()

    # Extract columns from rotation matrix
    # In a rotation matrix, columns represent the transformed basis vectors
    # Column 0 (X axis) = direction vector
    # Column 2 (Z axis) = normal vector
    direction = Vector((rotation_matrix[0][0], rotation_matrix[1][0], rotation_matrix[2][0]))
    normal = Vector((rotation_matrix[0][2], rotation_matrix[1][2], rotation_matrix[2][2]))

    # Ensure vectors are normalized
    normal = normal.normalized()
    direction = direction.normalized()

    return normal, direction
