import math

import bmesh
from mathutils import Vector

from ...utils import view3d


def modal(op, context, event):
    """Bisect the mesh"""
    region = context.region
    rv3d = context.region_data

    depth = rv3d.view_location

    if op.config.snap:
        precision = event.shift
        op.mouse.co = _snap(op, context, precision=precision)

    # Convert 2D mouse positions to 3D points
    point1 = view3d.region_2d_to_location_3d(
        region,
        rv3d,
        op.mouse.init,
        depth + rv3d.view_rotation @ Vector((0.0, 0.0, -1.0)),
    )
    point2 = view3d.region_2d_to_location_3d(
        region,
        rv3d,
        op.mouse.co,
        depth + rv3d.view_rotation @ Vector((0.0, 0.0, -1.0)),
    )

    # Update Line
    op.ui.bisect_line.callback.update_batch((point1, point2))
    # Update Polyline
    op.ui.bisect_polyline.callback.update_batch([(point1, point2)])

    obj = op.data.obj
    selected_objects = op.objects.selected

    objs = list(set(selected_objects + [obj]))
    bbox = _bbox_center(objs)
    center_point = view3d.location_3d_to_region_2d(region, rv3d, bbox)

    # Calculate line direction
    line_dir = (op.mouse.co - op.mouse.init).normalized()
    to_center = center_point - op.mouse.init

    # Cross product to determine which side center is on
    # In 2D, cross product > 0 means center is on left side of line
    cross_z = line_dir.x * to_center.y - line_dir.y * to_center.x

    # If center is on left side, make perpendicular vector point right
    # If center is on right side, make perpendicular vector point left
    flip = op.data.bisect.flip

    # Include flip in the direction logic - if flip is True, invert the behavior
    if (cross_z < 0) != flip:  # XOR logic: invert if flip is True
        tangent = (point2 - point1).normalized()
        perp_vector = Vector((-line_dir.y, line_dir.x))
    else:
        tangent = (point1 - point2).normalized()
        perp_vector = Vector((line_dir.y, -line_dir.x))

    perp_distance = 150

    dot3 = op.mouse.co + perp_vector * perp_distance
    dot4 = op.mouse.init + perp_vector * perp_distance
    points = [op.mouse.init, op.mouse.co, dot3, dot4]

    op.ui.bisect_gradient.callback.update_batch(points=points)

    location = (point1 + point2) / 2

    view_direction = view3d.region_2d_to_vector_3d(region, rv3d, op.mouse.init)
    normal = tangent.cross(view_direction).normalized()

    # Apply flip to the normal if needed
    if flip:
        normal = -normal

    op.data.bisect.plane = (location, normal)


def execute(op, context, obj, bm, bisect_data):
    """Bisect the mesh"""

    if op.pref.type == "EDIT_MESH":
        edited_objects = [
            obj for obj in context.objects_in_mode_unique_data if obj.type == "MESH"
        ]
        for obj in edited_objects:
            bm = bmesh.from_edit_mesh(obj.data)
            _bisect(obj, bm, bisect_data)
            bmesh.update_edit_mesh(obj.data)
    else:
        selected_objects = [
            obj for obj in context.selected_objects if obj.type == "MESH"
        ]
        for obj in selected_objects:
            bm = bmesh.new()
            bm.from_mesh(obj.data)
            _bisect(obj, bm, bisect_data)
            op.update_bmesh(obj, bm, loop_triangles=True, destructive=True)
            bm.to_mesh(obj.data)
            bm.free()

    return {"FINISHED"}


def _bisect(obj, bm, bisect_data):
    """Bisect the mesh"""

    plane_co_global = bisect_data[0]
    plane_no_global = bisect_data[1]
    flip = bisect_data[2]
    mode = bisect_data[3]

    # obj.update_from_editmode()
    plane_no = obj.matrix_world.transposed() @ plane_no_global
    plane_co = obj.matrix_world.inverted() @ plane_co_global

    geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
    geom = [g for g in geom if not g.hide]

    if flip:
        plane_no = -plane_no

    clear_outer = False
    if mode == "CUT":
        clear_outer = True

    # Perform bisect
    geom_cut = bmesh.ops.bisect_plane(
        bm,
        geom=geom,
        plane_co=plane_co,
        plane_no=plane_no,
        clear_outer=clear_outer,
        clear_inner=False,
        use_snap_center=False,
    )

    # Select the newly cut geometry
    for geom_elem in geom_cut["geom_cut"]:
        geom_elem.select = True

    if clear_outer:
        bmesh.ops.contextual_create(bm, geom=geom_cut["geom_cut"], mat_nr=0)


def _snap(op, context, precision=False):
    """Snap the mouse position to the nearest angle increment."""
    tool_settings = context.scene.tool_settings
    angle_increment = getattr(
        tool_settings, "snap_angle_increment_3d", math.radians(15)
    )
    if precision:
        angle_increment = getattr(
            tool_settings, "snap_angle_increment_3d_precision", math.radians(5)
        )

    delta = op.mouse.co - op.mouse.init
    angle = math.atan2(delta.y, delta.x)
    snapped_angle = round(angle / angle_increment) * angle_increment
    distance = delta.length
    direction = Vector((math.cos(snapped_angle), math.sin(snapped_angle)))
    snapped_mouse_pos = op.mouse.init + direction * distance
    return snapped_mouse_pos


def _bbox_center(objs):
    """Return the center of the combined bounding box of multiple objects in world space."""
    if not objs:
        return Vector((0, 0, 0))

    # Initialize bounds in world space
    world_min = Vector((float("inf"),) * 3)
    world_max = Vector((float("-inf"),) * 3)

    for obj in objs:
        # Get mesh bounds in world space
        matrix_world = obj.matrix_world

        # Handle object location/rotation/scale
        for v in obj.bound_box:
            world_vertex = matrix_world @ Vector(v)

            # Update bounds
            world_min.x = min(world_min.x, world_vertex.x)
            world_min.y = min(world_min.y, world_vertex.y)
            world_min.z = min(world_min.z, world_vertex.z)
            world_max.x = max(world_max.x, world_vertex.x)
            world_max.y = max(world_max.y, world_vertex.y)
            world_max.z = max(world_max.z, world_vertex.z)

    # Calculate center in world space
    if world_min.x != float("inf"):
        world_center = (world_min + world_max) * 0.5
        return world_center

    return Vector((0, 0, 0))
