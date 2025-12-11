import math

import bpy
from mathutils import Vector

from ....shaders.draw import DrawPolyline
from ....utils import addon, view3d


def calculate_distance(mouse_median, mouse_init, mouse_co):
    """Calculate the distance based on the initial and current mouse position"""
    intersect_point = mouse_co
    distance_fixed = 0.0
    if intersect_point:
        delta_init = (mouse_median - mouse_init).length
        distance = (mouse_median - intersect_point).length
        distance_fixed = distance - delta_init
    return distance_fixed


def get_intersect_point(context, event, plane_co):
    """Calculate the intersection point on the plane defined by the plane_co and plane_no"""
    mouse = Vector((event.mouse_region_x, event.mouse_region_y))
    region = context.region
    rv3d = context.region_data

    # Calculate the 3D mouse position on the plane defined by the plane_co and plane_no
    mouse_pos_3d = view3d.region_2d_to_location_3d(region, rv3d, mouse, plane_co)

    if mouse_pos_3d:
        return mouse_pos_3d

    return Vector((0, 0, 0))


def format_angle(angle_rad):
    """Format angle in degrees without trailing zeros"""
    angle_deg = math.degrees(angle_rad)
    # Format with 2 decimals then strip trailing zeros and decimal point
    return f"{angle_deg:.2f}".rstrip("0").rstrip(".")


def setup_drawing(context, ui, points=None):
    """Setup the drawing"""
    _theme = addon.pref().theme.ops.obj.bevel
    color = _theme.guide

    points = points or [(Vector((0, 0, 0)), Vector((0, 0, 0)))]
    ui.guide.callback = DrawPolyline(points, width=1.2, color=color)
    ui.guide.handle = bpy.types.SpaceView3D.draw_handler_add(
        ui.guide.callback.draw, (context,), "WINDOW", "POST_VIEW"
    )

    lines = []
    ui.interface.create(context, lines=lines)


def update_drawing(
    context,
    ui,
    mouse_median,
    mouse_co,
    width,
    segments,
    limit_method,
    angle_limit,
    modifier_count_text,
    numeric_input_active=False,
):
    """Update the drawing"""
    _theme = addon.pref().theme.ops.obj.bevel
    color = _theme.guide
    if numeric_input_active:
        ui.guide.callback.clear()
    else:
        point = [(mouse_median, mouse_co)]
        ui.guide.callback.update_batch(point, color=color)

    mid_point = (mouse_median + mouse_co) / 2
    region = context.region
    rv3d = context.region_data
    point_2d = view3d.location_3d_to_region_2d(region, rv3d, mid_point)

    # Build text tuple
    text_lines = [f"Width: {width:.3f}", f"S: {segments}"]

    # Add limit method if not none
    if limit_method != "NONE":
        if limit_method == "ANGLE":
            angle_formatted = format_angle(angle_limit)
            text_lines.append(f"L:{angle_formatted}")
        elif limit_method == "WEIGHT":
            text_lines.append("L:W")
        else:
            text_lines.append(f"L:{limit_method}")

    # Add modifier count if available
    if modifier_count_text:
        text_lines.append(modifier_count_text)

    lines = [{"point": point_2d, "text_tuple": tuple(text_lines)}]
    ui.interface.callback.update_batch(lines)


def set_segments_from_mouse(
    context, event, mouse_median, saved_mouse_pos, saved_segments
):
    """Set the segments based on the initial and current mouse position"""
    region = context.region
    rv3d = context.region_data

    # Convert 3D mid_point to 2D
    mid_point_2d = view3d.location_3d_to_region_2d(region, rv3d, mouse_median)
    mouse = Vector((event.mouse_region_x, event.mouse_region_y))

    if mid_point_2d and saved_mouse_pos:
        ref_distance = (mid_point_2d - saved_mouse_pos).length
        current_distance = (mid_point_2d - mouse).length
        distance = current_distance - ref_distance

        # Set base segments and adjust based on distance
        base_segments = saved_segments
        delta_segments = math.ceil(abs(distance) / 100)

        # Set segments directly based on distance
        new_segments = (
            base_segments + delta_segments
            if distance > 0
            else base_segments - delta_segments
        )
        return max(1, new_segments)  # Ensure segments do not fall below 1

    return saved_segments
