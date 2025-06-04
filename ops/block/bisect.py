import math
from mathutils import Vector
from ...utils import view3d
import bmesh


def modal(self, context, event):
    '''Bisect the mesh'''
    region = context.region
    rv3d = context.region_data

    depth = rv3d.view_location

    if event.ctrl:
        precision = event.shift
        self.mouse.co = _snap(self, context, precision=precision)

    # Convert 2D mouse positions to 3D points
    point1 = view3d.region_2d_to_location_3d(region, rv3d, self.mouse.init, depth + rv3d.view_rotation @ Vector((0.0, 0.0, -1.0)))
    point2 = view3d.region_2d_to_location_3d(region, rv3d, self.mouse.co, depth + rv3d.view_rotation @ Vector((0.0, 0.0, -1.0)))

    # Update Line
    self.ui.bisect_line.callback.update_batch((point1, point2))
    # Update Polyline
    self.ui.bisect_polyline.callback.update_batch([(point1, point2)])

    obj = self.data.obj
    selected_objects = [obj for obj in context.selected_objects if obj.type == 'MESH']

    objs = list(set(selected_objects + [obj]))
    bbox = _bbox_center(objs)
    center_point = view3d.location_3d_to_region_2d(region, rv3d, bbox)

    # Calculate line direction
    line_dir = (self.mouse.co - self.mouse.init).normalized()
    to_center = center_point - self.mouse.init

    # Cross product to determine which side center is on
    # In 2D, cross product > 0 means center is on left side of line
    cross_z = line_dir.x * to_center.y - line_dir.y * to_center.x

    # If center is on left side, make perpendicular vector point right
    # If center is on right side, make perpendicular vector point left
    flip = self.data.bisect.flip

    # Include flip in the direction logic - if flip is True, invert the behavior
    if (cross_z < 0) != flip:  # XOR logic: invert if flip is True
        tangent = (point2 - point1).normalized()
        perp_vector = Vector((-line_dir.y, line_dir.x))
    else:
        tangent = (point1 - point2).normalized()
        perp_vector = Vector((line_dir.y, -line_dir.x))

    perp_distance = 150

    dot3 = self.mouse.co + perp_vector * perp_distance
    dot4 = self.mouse.init + perp_vector * perp_distance
    points = [self.mouse.init, self.mouse.co, dot3, dot4]

    self.ui.bisect_gradient.callback.update_batch(points=points)

    location = (point1 + point2) / 2

    view_direction = view3d.region_2d_to_vector_3d(region, rv3d, self.mouse.init)
    normal = tangent.cross(view_direction).normalized()

    self.data.bisect.plane = (location, normal)


def execute(self, context, obj, bm, bisect_data):
    '''Bisect the mesh'''

    if self.pref.type == 'EDIT_MESH' or obj.select_get():
        _bisect(obj, bm, bisect_data)
        self.update_bmesh(obj, bm, loop_triangles=True, destructive=True)

    selected_objects = [obj for obj in context.selected_objects if obj.type == 'MESH']
    selected_objects_without_obj = list(set(selected_objects) - {obj})
    for obj in selected_objects_without_obj:
        if self.pref.type == 'EDIT_MESH':
            bm = bmesh.from_edit_mesh(obj.data)
        else:
            bm = bmesh.new()
            bm.from_mesh(obj.data)
        _bisect(obj, bm, bisect_data)
        self.update_bmesh(obj, bm, loop_triangles=True, destructive=True)

        if self.pref.type == 'EDIT_MESH':
            bmesh.update_edit_mesh(obj.data)
        else:
            bm.to_mesh(obj.data)
            bm.free()

    return {'FINISHED'}


def _bisect(obj, bm, bisect_data):
    '''Bisect the mesh'''

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
    if mode == 'CUT':
        clear_outer = True

    # Perform bisect
    geom_cut = bmesh.ops.bisect_plane(bm, geom=geom, plane_co=plane_co, plane_no=plane_no, clear_outer=clear_outer, clear_inner=False, use_snap_center=False)

    # Select the newly cut geometry
    for geom_elem in geom_cut['geom_cut']:
        geom_elem.select = True

    if clear_outer:
        bmesh.ops.contextual_create(bm, geom=geom_cut['geom_cut'], mat_nr=0)


def _snap(self, context, precision=False):
    """Snap the mouse position to the nearest angle increment."""
    tool_settings = context.scene.tool_settings
    angle_increment = getattr(tool_settings, 'snap_angle_increment_3d', math.radians(15))
    if precision:
        angle_increment = getattr(tool_settings, 'snap_angle_increment_3d_precision', math.radians(5))

    delta = self.mouse.co - self.mouse.init
    angle = math.atan2(delta.y, delta.x)
    snapped_angle = round(angle / angle_increment) * angle_increment
    distance = delta.length
    direction = Vector((math.cos(snapped_angle), math.sin(snapped_angle)))
    snapped_mouse_pos = self.mouse.init + direction * distance
    return snapped_mouse_pos


def _bbox_center(objs):
    """Return the center of the combined bounding box of multiple objects in world space."""
    if not objs:
        return Vector((0, 0, 0))

    # Initialize bounds in world space
    world_min = Vector((float('inf'),) * 3)
    world_max = Vector((float('-inf'),) * 3)

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
    if world_min.x != float('inf'):
        world_center = (world_min + world_max) * 0.5
        return world_center

    return Vector((0, 0, 0))
