"""3D viewport coordinate conversion utilities.

Extends bpy_extras.view3d_utils with additional functions for
converting between 2D region coordinates and 3D world space,
including plane and line intersections.
"""

from bpy_extras.view3d_utils import (
    location_3d_to_region_2d,
    region_2d_to_location_3d,
    region_2d_to_origin_3d,
    region_2d_to_vector_3d,
)
from mathutils import geometry


def region_2d_to_plane_3d(region, re3d, point, plane, matrix=None):
    """
    Return the 3D point on a plane in world space from a 2D point in the region.

    :param region: The region.
    :type region: :class:`bpy.types.Region`
    :param re3d: The region's 3D view.
    :type re3d: :class:`bpy.types.RegionView3D`
    :param point: The 2D point.
    :type point: :class:`mathutils.Vector`
    :param plane: The plane in world space.
    :type plane: tuple of :class:`mathutils.Vector`
    :param matrix: (Optional) The matrix to apply to the plane.
    :type matrix: :class:`mathutils.Matrix`
    :return: The 3D point on the plane.
    :rtype: :class:`mathutils.Vector`
    """

    # Get mouse origin and direction in world space
    location, normal = plane

    mouse_origin_world = region_2d_to_origin_3d(region, re3d, point)
    mouse_direction_world = region_2d_to_vector_3d(region, re3d, point)

    mouse_origin = mouse_origin_world
    mouse_direction = mouse_direction_world

    if matrix:
        obj_matrix_world_inv = matrix.inverted_safe()

        # Transform them to object local space
        mouse_origin = obj_matrix_world_inv @ mouse_origin_world
        mouse_direction = obj_matrix_world_inv.to_3x3() @ mouse_direction_world

    # Intersect the mouse ray with the plane in object space
    mouse_point_on_plane = geometry.intersect_line_plane(
        mouse_origin, mouse_origin + mouse_direction, location, normal
    )

    return mouse_point_on_plane


def get_mouse_region_prev(event):
    """Get the previous mouse coordinates in region space.

    Calculates the previous mouse position in region coordinates by
    comparing current and previous global positions.

    :param event: The Blender event containing mouse position data.
    :type event: bpy.types.Event
    :return: Tuple of (x, y) coordinates in region space.
    :rtype: tuple[float, float]
    """
    mouse_x = event.mouse_x
    mouse_y = event.mouse_y

    mouse_prev_x = event.mouse_prev_press_x
    mouse_prev_y = event.mouse_prev_press_y

    mouse_region_x = event.mouse_region_x
    mouse_region_y = event.mouse_region_y

    global_diff_x = mouse_x - mouse_prev_x
    global_diff_y = mouse_y - mouse_prev_y

    mouse_region_prev_x = mouse_region_x - global_diff_x
    mouse_region_prev_y = mouse_region_y - global_diff_y

    return mouse_region_prev_x, mouse_region_prev_y


def region_2d_to_line_3d(region, rv3d, point, line_origin, line_direction, matrix=None):
    """Convert a 2D region point to the closest 3D point on a line.

    Calculates the signed distance from the line origin to the closest point.

    :param region: The region of the area.
    :type region: bpy.types.Region
    :param rv3d: The 3D region view.
    :type rv3d: bpy.types.RegionView3D
    :param point: The 2D point in the region.
    :type point: tuple[float, float]
    :param line_origin: The origin of the target line in 3D space.
    :type line_origin: mathutils.Vector
    :param line_direction: The direction vector of the target line.
    :type line_direction: mathutils.Vector
    :param matrix: Optional transformation matrix to apply to the line.
    :type matrix: mathutils.Matrix | None
    :return: Tuple of (closest point on line, signed distance), or (None, None) if parallel.
    :rtype: tuple[mathutils.Vector | None, float | None]
    """

    # Get the 3D ray from the 2D point
    ray_origin = region_2d_to_origin_3d(region, rv3d, point)
    ray_direction = region_2d_to_vector_3d(region, rv3d, point)

    if matrix:
        # Apply transformation to the line
        matrix_inv = matrix.inverted_safe()
        line_origin = matrix_inv @ line_origin
        line_direction = matrix_inv.to_3x3() @ line_direction

    # Compute the closest point between the ray and the line
    intersection = geometry.intersect_line_line(
        ray_origin,
        ray_origin + ray_direction,
        line_origin,
        line_origin + line_direction,
    )

    if intersection is not None:
        # intersection returns a tuple of points (point_on_ray, point_on_line)
        closest_point_on_line = intersection[1]

        # Compute the signed distance along the line direction
        # from line_origin to closest_point_on_line
        line_direction_normalized = line_direction.normalized()
        vector_from_origin = closest_point_on_line - line_origin
        distance = vector_from_origin.dot(line_direction_normalized)

        return closest_point_on_line, distance
    else:
        # Lines are parallel; return None or handle accordingly
        return None, None


__all__ = [
    "location_3d_to_region_2d",
    "region_2d_to_location_3d",
    "region_2d_to_origin_3d",
    "region_2d_to_vector_3d",
    "region_2d_to_plane_3d",
    "region_2d_to_line_3d",
    "get_mouse_region_prev",
]
