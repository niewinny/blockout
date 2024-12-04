import bpy
import bmesh
from mathutils import Vector
from ...bmeshutils import rectangle, circle, orientation
from ...utils import view3d


def invoke(self, context):
    '''Build the mesh data'''

    obj = self.data.obj
    bm = self.data.bm

    direction, plane = _get_orientation(self, context)
    world_origin, world_normal = plane

    if self.config.mode != 'CREATE':
        bpy.ops.mesh.select_all(action='DESELECT')

    if self.config.align.mode != 'CUSTOM':
        x_axis_point = world_origin + direction
        y_direction = world_normal.cross(direction).normalized()
        y_axis_point = world_origin + y_direction
        self.ui.xaxis.callback.update_batch((world_origin, x_axis_point))
        self.ui.yaxis.callback.update_batch((world_origin, y_axis_point))

    if self.config.align.grid.enable:
        increments = self.config.align.grid.spacing
        custom_plane = self.config.align.custom.location, self.config.align.custom.normal
        plane = orientation.snap_plane(plane, custom_plane, direction, increments)

    if self.config.type == 'MESH':
        direction = orientation.direction_local(obj, direction)
        plane = orientation.plane_local(obj, plane)

    if plane is None:
        self.report({'ERROR'}, 'Failed to detect drawing plane')
        return False

    self.data.draw.plane = plane
    self.data.draw.direction = direction

    shape = self.config.shape
    match shape:
        case 'RECTANGLE': self.data.draw.face = rectangle.create(bm, plane)
        case 'BOX': self.data.draw.face = rectangle.create(bm, plane)
        case 'CIRCLE': self.data.draw.face = circle.create(bm, plane, verts_number=self.shapes.circle.verts)
        case 'CYLINDER': self.data.draw.face = circle.create(bm, plane, verts_number=self.shapes.circle.verts)

    self.update_bmesh(obj, bm, loop_triangles=True, destructive=True)
    return True


def modal(self, context, event):
    obj = self.data.obj
    bm = self.data.bm

    region = context.region
    rv3d = context.region_data
    plane = self.data.draw.plane
    direction = self.data.draw.direction
    matrix_world = obj.matrix_world
    face = bm.faces[self.data.draw.face]

    bevel_verts = [obj.matrix_world @ v.co.copy() for v in face.verts]
    self.data.bevel.origin = sum(bevel_verts, Vector()) / len(bevel_verts)

    mouse_point_on_plane = view3d.region_2d_to_plane_3d(region, rv3d, self.mouse.co, plane, matrix=matrix_world)
    if mouse_point_on_plane is None:
        self.report({'WARNING'}, "Mouse was outside the drawing plane")
        return

    shape = self.config.shape

    if self.config.align.grid.enable:
        increments = self.config.align.grid.spacing
    else:
        increments = self.config.form.increments if event.ctrl else 0.0

    symmetry = self.data.draw.symmetry

    match shape:
        case 'RECTANGLE': self.shapes.rectangle.co, point = rectangle.set_xy(face, plane, mouse_point_on_plane, direction, snap_value=increments, symmetry=symmetry)
        case 'BOX': self.shapes.rectangle.co, point = rectangle.set_xy(face, plane, mouse_point_on_plane, direction, snap_value=increments, symmetry=symmetry)
        case 'CIRCLE': self.shapes.circle.radius, point = circle.set_xy(face, plane, mouse_point_on_plane, snap_value=increments)
        case 'CYLINDER': self.shapes.circle.radius, point = circle.set_xy(face, plane, mouse_point_on_plane, snap_value=increments)

    self.update_bmesh(obj, bm)

    self.data.extrude.plane = (matrix_world @ point, matrix_world.to_3x3() @ direction)

    if self.config.mode != 'CREATE':
        self.ui.faces.callback.update_batch([face])


def _get_orientation(cls, context):
    def get_view_orientation():
        align_view = cls.config.align.view
        match align_view:
            case 'WORLD': depth = Vector((0, 0, 0))
            case 'OBJECT': depth = cls.objects.active.location
            case 'CURSOR': depth = context.scene.cursor.location

        direction_world = orientation.direction_from_view(context)
        plane_view = orientation.plane_from_view(context, depth)

        origin = view3d.region_2d_to_plane_3d(context.region, context.region_data, cls.mouse.init, plane_view)
        plane_world = (origin, plane_view[1])

        return direction_world, plane_world

    def get_face_orientation():
        depsgraph = context.view_layer.depsgraph
        depsgraph.update()
        hit_obj = cls.ray.obj

        # Get the evaluated data
        hit_obj_eval = hit_obj.evaluated_get(depsgraph)
        hit_data = hit_obj_eval.to_mesh(preserve_all_data_layers=True, depsgraph=depsgraph)

        hit_bm = bmesh.new()
        hit_bm.from_mesh(hit_data)
        hit_bm.faces.ensure_lookup_table()
        hit_face = hit_bm.faces[cls.ray.index]
        loc = cls.ray.location

        align_face = cls.config.align.face
        match align_face:
            case 'PLANAR': direction_local = orientation.direction_from_normal(hit_face.normal)
            case 'EDGE': direction_local = orientation.direction_from_closest_edge(hit_obj, hit_face, loc)

        direction_world = cls.ray.obj.matrix_world.to_3x3() @ direction_local
        plane_world = (cls.ray.location, cls.ray.normal)

        hit_bm.free()
        del hit_obj_eval
        del hit_data

        return direction_world, plane_world

    def get_custom_orientation():
        custom_location = cls.config.align.custom.location
        custom_normal = cls.config.align.custom.normal
        custom_direction = cls.config.align.custom.direction

        custom_plane = (custom_location, custom_normal)

        # Get a point on the plane by projecting mouse.init onto the plane
        location_world = view3d.region_2d_to_plane_3d(context.region, context.region_data, cls.mouse.init, custom_plane)
        location_world, detected_axis = orientation.point_on_axis(custom_plane, custom_direction, location_world, distance=0.1)

        cls.data.draw.symmetry = detected_axis

        plane_world = (location_world, custom_normal)

        return custom_direction, plane_world

    if cls.config.align.mode == 'FACE' and cls.ray.hit:
        direction, plane = get_face_orientation()
    elif cls.config.align.mode == 'CUSTOM':
        direction, plane = get_custom_orientation()
    else:
        direction, plane = get_view_orientation()

    return direction, plane
