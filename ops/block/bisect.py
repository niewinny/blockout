
import bpy
from mathutils import Vector
from ...utils import view3d
import bmesh


def modal(self, context, event):
    '''Bisect the mesh'''
    region = context.region
    rv3d = context.region_data

    depth = rv3d.view_location

    # Convert 2D mouse positions to 3D points
    point1 = view3d.region_2d_to_location_3d(region, rv3d, self.mouse.init, depth + rv3d.view_rotation @ Vector((0.0, 0.0, -1.0)))
    point2 = view3d.region_2d_to_location_3d(region, rv3d, self.mouse.co, depth + rv3d.view_rotation @ Vector((0.0, 0.0, -1.0)))

    # Update Line
    self.ui.bisect_line.callback.update_batch((point1, point2))
    # Update Polyline
    self.ui.bisect_polyline.callback.update_batch([(point1, point2)])

    # Update Gradient
    width, height = region.width, region.height
    center_point = Vector((width/2, height/2))

    # Calculate line direction
    line_dir = (self.mouse.co - self.mouse.init).normalized()
    to_center = center_point - self.mouse.init

    # Cross product to determine which side center is on
    # In 2D, cross product > 0 means center is on left side of line
    cross_z = line_dir.x * to_center.y - line_dir.y * to_center.x

    # If center is on left side, make perpendicular vector point right
    # If center is on right side, make perpendicular vector point left
    if cross_z < 0:
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

    _bisect(obj, bm, bisect_data)

    selected_objects = list(set(context.selected_objects) - {obj})

    for obj in selected_objects:
        if self.pref.type == 'EDIT_MESH':
            bm = bmesh.from_edit_mesh(obj.data)
        else:
            bm = bmesh.new()
            bm.from_mesh(obj.data)
        _bisect(obj, bm, bisect_data)

        if self.pref.type == 'EDIT_MESH':
            bmesh.update_edit_mesh(obj.data)
        else:
            bm.to_mesh(obj.data)
            bm.free()

    self.update_bmesh(obj, bm, loop_triangles=True, destructive=True)

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
