import bpy

from mathutils import Matrix, Vector, geometry
from mathutils.geometry import intersect_line_plane, intersect_line_line
from bpy_extras.view3d_utils import region_2d_to_origin_3d, region_2d_to_vector_3d, location_3d_to_region_2d, region_2d_to_location_3d


def location2d_to_origin3d(x, y, clamp=None):
    '''Get the 3D origin of the mouse cursor'''
    return region_2d_to_origin_3d(bpy.context.region, bpy.context.region_data, (x, y), clamp=clamp)


def location2d_to_vector3d(x, y):
    '''Get the 3D vector of the mouse cursor'''
    return region_2d_to_vector_3d(bpy.context.region, bpy.context.region_data, (x, y))


def location2d_to_intersect3d(x, y, location, normal, origin=None):
    '''Get the 3D location of the mouse cursor intersecting a plane'''
    if not origin:
        origin = location2d_to_origin3d(x, y)
    return intersect_line_plane(origin, origin + location2d_to_vector3d(x, y), location, normal)


def location3d_to_location2d(location, region=None, region_data=None, region_3d=None, persp_matrix_invert=False):
    '''Get the 2D location of a 3D point'''
    if region_3d or persp_matrix_invert:
        region_3d = region_3d or bpy.context.space_data.region_3d

        if not region_3d.is_perspective:
            location = region_3d.view_matrix.inverted() @ Vector(location)

    return location_3d_to_region_2d(region, region_data, location)


def location2d_to_location3d(x, y, location, region_3d=None, persp_matrix_invert=False):
    '''Get the 3D location of a 2D point'''
    if region_3d or persp_matrix_invert:
        region_3d = region_3d or bpy.context.space_data.region_3d

        if not region_3d.is_perspective:
            location = region_3d.view_matrix.inverted() @ Vector(location)

    return region_2d_to_location_3d(bpy.context.region, bpy.context.region_data, (x, y), location)


def track_matrix(normal=Vector(), location=None, matrix=Matrix(), up='Z', align='Y'):
    '''
    Return a matrix that tracks the given normal.

    :arg normal: The normal to track.
    :type normal: :class:`mathutils.Vector`
    :arg location: The location of the matrix.
    :type location: :class:`mathutils.Vector`
    :arg matrix: The matrix to track.
    :type matrix: :class:`mathutils.Matrix`
    :arg up: The up axis.
    :type up: str
    :arg align: The align axis.
    :type align: str
    :return: The tracked matrix.
    :rtype: :class:`mathutils.Matrix`
    '''

    track_mat = (matrix.copy().to_3x3().inverted() @ normal).to_track_quat(up, align).to_matrix().to_4x4()
    track_mat.translation = location if location else matrix.translation

    return track_mat


def locations_3d_to_region_2d(region, rv3d, coords_3d, *, default=None):
    '''
    Return the *region* relative 2d locations of a list of 3d positions.

    :arg region: region of the 3D viewport, typically bpy.context.region.
    :type region: :class:`bpy.types.Region`
    :arg rv3d: 3D region data, typically bpy.context.space_data.region_3d.
    :type rv3d: :class:`bpy.types.RegionView3D`
    :arg coords_3d: List of 3d world-space locations.
    :type coords_3d: list of 3d vectors
    :arg default: Return this value if a ``coord``
       is behind the origin of a perspective view.
    :return: List of 2d locations
    :rtype: list of :class:`mathutils.Vector` or ``default`` argument.
    '''

    results = []
    width_half = region.width / 2.0
    height_half = region.height / 2.0

    for coord in coords_3d:
        prj = rv3d.perspective_matrix @ Vector((coord[0], coord[1], coord[2], 1.0))
        if prj.w > 0.0:
            results.append(Vector((
                width_half + width_half * (prj.x / prj.w),
                height_half + height_half * (prj.y / prj.w),
            )))
        else:
            results.append(default)

    return results


def region_2d_to_nearest_point_on_line_3d(region, rv3d, point, vector, normal):
    '''
    Return the nearest point on a line in 3D space to a 2D point in the region.

    :param region: The region.
    :type region: :class:`bpy.types.Region`
    :param rv3d: The region's 3D view.
    :type rv3d: :class:`bpy.types.RegionView3D`
    :param point: The 2D point.
    :type point: :class:`mathutils.Vector`
    :param vector: The line's vector.
    :type vector: :class:`mathutils.Vector`
    :param normal: The line's normal.
    :type normal: :class:`mathutils.Vector`
    :return: The nearest point on the line.
    :rtype: :class:`mathutils.Vector`
    '''

    view_origin = region_2d_to_origin_3d(region, rv3d, point)
    view_vector = region_2d_to_vector_3d(region, rv3d, point)

    line_start = view_origin
    line_end = view_origin + view_vector
    vector_line = [vector, vector + normal]
    closest_points = intersect_line_line(vector_line[0], vector_line[1], line_start, line_end)

    if closest_points is not None:
        closest_point = closest_points[0]
        return closest_point

    return None


def region2d_to_plane3d(region, re3d, point, plane, matrix=None):
    # Get mouse origin and direction in world space
    location, normal = plane

    mouse_origin_world = region_2d_to_origin_3d(
        region, re3d, point)
    mouse_direction_world = region_2d_to_vector_3d(
        region, re3d, point)

    mouse_origin = mouse_origin_world
    mouse_direction = mouse_direction_world

    if matrix:
        obj_matrix_world_inv = matrix.inverted_safe()

        # Transform them to object local space
        mouse_origin = obj_matrix_world_inv @ mouse_origin_world
        mouse_direction = obj_matrix_world_inv.to_3x3() @ mouse_direction_world

    # Intersect the mouse ray with the plane in object space
    mouse_point_on_plane = geometry.intersect_line_plane(
        mouse_origin, mouse_origin + mouse_direction, location, normal)

    return mouse_point_on_plane


def get_mouse_region_prev(event):
    '''Get the previous mouse coordinates in region space'''

    mouse_x = event.mouse_x
    mouse_y = event.mouse_y

    mouse_prev_x = event.mouse_prev_x
    mouse_prev_y = event.mouse_prev_y

    mouse_region_x = event.mouse_region_x
    mouse_region_y = event.mouse_region_y

    global_diff_x = mouse_x - mouse_prev_x
    global_diff_y = mouse_y - mouse_prev_y

    mouse_region_prev_x = mouse_region_x - global_diff_x
    mouse_region_prev_y = mouse_region_y - global_diff_y

    return mouse_region_prev_x, mouse_region_prev_y
