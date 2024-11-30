import math
import bmesh
from mathutils import Vector, geometry
from ..bmath import geometry as geom
from ..utils import view3d


def direction_from_longest_edge(face):
    '''Get the direction from the longest edge'''
    direction = face.calc_tangent_edge().normalized()

    return direction


def direction_from_closest_edge(obj, face, loc):
    '''Get the direction from the closest edge'''
    matrix = obj.matrix_world
    edge = min(face.edges, key=lambda e: geom.distance_point_to_segment(loc, matrix @ e.verts[0].co, matrix @ e.verts[1].co))

    # get loop for the edge that is also in the face
    loop = next((loop for loop in edge.link_loops if loop.face == face), None)
    direction = edge.calc_tangent(loop)

    return direction


def direction_from_normal(normal):
    '''Get the direction from the normal'''
    up_vector = Vector((0, 0, 1))
    if abs(normal.dot(up_vector)) > 0.9999:
        up_vector = Vector((0, 1, 0))

    direction = normal.cross(up_vector).normalized()

    return direction


def direction_from_view(context):
    '''Get the orientation from the view'''

    region_data = context.space_data.region_3d

    # The view direction is the negative Z axis of the view rotation
    view_rotation = region_data.view_rotation
    view_direction_global = -view_rotation @ Vector((1.0, 0.0, 0.0))
    view_direction_global.normalize()

    return view_direction_global


def direction_local(obj, direction):
    '''Get the orientation from the view'''

    view_direction_global = direction
    matrix_world_inverted = obj.matrix_world.inverted_safe()
    view_direction_local = view_direction_global @ matrix_world_inverted.transposed().to_3x3()
    view_direction_local.normalize()

    return view_direction_local


def plane_from_view(context, depth):
    '''Get the plane from the view'''

    region_data = context.space_data.region_3d

    # The view normal is the negative Z axis of the view rotation
    view_rotation = region_data.view_rotation
    view_normal_world = -view_rotation @ Vector((0.0, 0.0, 1.0))
    view_normal_world.normalize()

    plane_world = (depth, view_normal_world)
    return plane_world


def plane_local(obj, plane):
    '''Get the plane from the view'''

    location_world, view_normal_world = plane

    if location_world is None:
        return None

    obj_matrix_world = obj.matrix_world
    obj_matrix_world_inv = obj_matrix_world.inverted_safe()

    location_local = obj_matrix_world_inv @ location_world

    view_normal_local = view_normal_world @ obj_matrix_world_inv.transposed().to_3x3()
    view_normal_local.normalize()

    local_plane = (location_local, view_normal_local)

    return local_plane


def direction_from_custom(context, custom, mouse_co):
    '''Get the orientation from the custom plane and angle'''

    # Extract custom plane properties
    plane_co = custom.location.copy()
    plane_no = custom.normal.copy()
    angle_rad = custom.angle

    # Get the view ray from the mouse position
    region = context.region
    region_data = context.space_data.region_3d

    # Get the start and end points of the view ray
    view_origin = view3d.region_2d_to_origin_3d(region, region_data, mouse_co)
    view_direction = view3d.region_2d_to_vector_3d(region, region_data, mouse_co)
    view_end = view_origin + (view_direction * 1000.0)  # Extend the ray far enough

    # Compute the intersection of the view ray with the plane
    intersection_point = geometry.intersect_line_plane(view_origin, view_end, plane_co, plane_no)

    if intersection_point is None:
        # The ray is parallel to the plane or does not intersect
        return None, (None, None)  # Or handle this case appropriately

    to_origin = view_origin - plane_co
    side = plane_no.dot(to_origin)
    if side < 0:
        # Viewing from behind the plane; flip the normal
        plane_no.negate()

    arbitrary_vector = Vector((1, 0, 0))
    if abs(plane_no.dot(arbitrary_vector)) > 0.9999:
        arbitrary_vector = Vector((0, 1, 0))

    # Compute the local X and Y axes
    u = plane_no.cross(arbitrary_vector)
    u.normalize()
    v = plane_no.cross(u)
    v.normalize()

    # Compute the direction vector in the plane using the angle
    direction = math.cos(angle_rad) * u + math.sin(angle_rad) * v
    direction.normalize()

    # Return the direction vector, new location (intersection point), and adjusted normal
    return direction, (intersection_point, plane_no)


def offset_plane(context, obj, loc, plane, offset):
    '''offset a plane by a distance'''

    location, normal = plane
    location_offset = location + normal * offset

    plane_offset = (location_offset, normal)

    matrix = obj.matrix_world

    region = context.region
    re3d = context.region_data
    new_location = view3d.region2d_to_plane3d(region, re3d, loc, plane_offset, matrix=matrix)

    return new_location, normal


def snap_plane(plane, snap_plane, direction, snap_value):
    '''
    Snap a point onto a plane and then onto a grid in that plane along the given direction
    and its perpendicular direction.

    Parameters:
    - point: Vector, the point to be snapped.
    - plane: Tuple (origin, normal), defining the plane.
    - direction: Vector, a direction vector lying in the plane.
    - snap_value: Float, the grid spacing to snap to.

    Returns:
    - snapped_point: Vector, the snapped point on the plane.
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


def point_on_axis(plane, direction, point, distance):
    '''Get the closest point on the plane along the given axis within the given distance'''

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

    if length_x <= distance and length_y <= distance:
        axis = (True, True)
        closest_point = location
    elif length_x <= distance and (length_x <= length_y or length_y > distance):
        axis = (False, True)
        closest_point = location + proj_vec_y
    elif length_y <= distance and (length_y < length_x or length_x > distance):
        axis = (True, False)
        closest_point = location + proj_vec_x
    else:
        axis = (False, False)
        closest_point = point

    return closest_point, axis
