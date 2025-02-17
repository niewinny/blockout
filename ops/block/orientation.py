import bpy
import bmesh
from mathutils import Vector
from ...bmeshutils import orientation
from ...utils import view3d


def build(cls, context):
    '''Get the orientation for the drawing'''

    if cls.config.align.mode == 'CUSTOM':
        direction, plane = custom_orientation(cls, context)
    else:
        if cls.ray.hit:
            direction, plane = face_orientation(cls, context)
        else:
            direction, plane = world_orientation(cls, context)

    if cls.config.mode != 'ADD' and cls.config.type == 'EDITplaneMESH':
        bpy.ops.mesh.select_all(action='DESELECT')

    if cls.config.align.grid.enable:
        increments = cls.config.align.grid.spacing
        custom_plane = cls.config.align.custom.location, cls.config.align.custom.normal
        plane = orientation.snap_plane(plane, custom_plane, direction, increments)

    cls.data.draw.plane = plane
    cls.data.draw.direction = direction

    return direction, plane


def make_local(cls):
    '''Make the orientation local to the object'''

    plane = cls.data.draw.plane
    direction = cls.data.draw.direction

    obj = cls.data.obj
    direction = orientation.direction_local(obj, direction)
    plane = orientation.plane_local(obj, plane)

    cls.data.draw.plane = plane
    cls.data.draw.direction = direction


def face_orientation(cls, context):
    '''Get the orientation from the face'''

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


def custom_orientation(cls, context):
    '''Get the orientation from the custom plane'''

    custom_location = cls.config.align.custom.location
    custom_normal = cls.config.align.custom.normal
    custom_direction = cls.config.align.custom.direction

    custom_plane = (custom_location, custom_normal)

    # Get a point on the plane by projecting mouse.init onto the plane
    region = context.region
    rv3d = context.region_data

    location_world = view3d.region_2d_to_plane_3d(region, rv3d, cls.mouse.init, custom_plane)

    if location_world is None:
        return None, None

    location_world, detected_axis = orientation.point_on_axis(region, rv3d, custom_plane, custom_direction, location_world, distance=30)

    cls.data.draw.symmetry = detected_axis

    axis = context.scene.bout.axis
    axis.highlight.x, axis.highlight.y = detected_axis

    plane_world = (location_world, custom_normal)

    return custom_direction, plane_world


def world_orientation(cls, context):
    '''Get the world orientation'''

    # Get a point on the plane by projecting mouse.init onto the plane
    region = context.region
    rv3d = context.region_data

    orientations = [
        (Vector((1, 0, 0)),  Vector((0, 0, 0)), Vector((0, 0, 1))),  # First try: Z-up
        (Vector((0, 0, 1)),  Vector((0, 0, 0)), Vector((0, 1, 0))),  # Second try: Y-up
        (Vector((0, 0, 1)),  Vector((0, 0, 0)), Vector((1, 0, 0)))   # Third try: X-up
    ]

    for direction, location, normal in orientations:
        world_plane = (location, normal)
        location_world = view3d.region_2d_to_plane_3d(region, rv3d, cls.mouse.init, world_plane)
        if location_world is not None:
            world_direction = direction
            world_normal = normal
            break
    else:
        return None, None

    location_world, detected_axis = orientation.point_on_axis(region, rv3d, world_plane, world_direction, location_world, distance=30)

    cls.data.draw.symmetry = detected_axis

    axis = context.scene.bout.axis
    axis.highlight.x, axis.highlight.y = detected_axis

    plane_world = (location_world, world_normal)

    return world_direction, plane_world
