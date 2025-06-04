import bmesh
from mathutils import Vector
from ...utilsbmesh import orientation
from ...utils import view3d
from ...utils.types import DrawMatrix


def _resolve_face_index(cls, hit_bm, hit_obj_eval, hit_data):
    '''Safely get face or return fallback orientation for instanced objects'''
    
    # Check if the face index is valid for this mesh (important for instanced objects)
    if cls.ray.index >= len(hit_bm.faces) or cls.ray.index < 0:
        # Face index is out of bounds - this can happen with instanced objects
        # Fall back to using the raycast normal directly
        direction_world = orientation.direction_from_normal(cls.ray.normal)
        plane_world = (cls.ray.location, cls.ray.normal)
        
        hit_bm.free()
        del hit_obj_eval
        del hit_data
        
        return None, direction_world, plane_world
    
    return hit_bm.faces[cls.ray.index], None, None


def build(cls, context, region, rv3d):
    '''Get the orientation for the drawing'''

    if context.scene.bout.align.mode == 'CUSTOM':
        direction, plane = custom_orientation(cls, context, region, rv3d)
    else:
        if cls.ray.hit:
            direction, plane = face_orientation(cls, context)
        else:
            direction, plane = world_orientation(cls, context, region, rv3d)

    cls.data.matrix.from_plane(plane, direction)


def make_local(cls):
    '''Make the orientation local to the object'''
    cls.data.matrix.to_local(cls.data.obj)


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
    
    hit_face, fallback_direction, fallback_plane = _resolve_face_index(cls, hit_bm, hit_obj_eval, hit_data)
    
    if hit_face is None:
        return fallback_direction, fallback_plane
    
    direction_local = orientation.direction_from_normal(hit_face.normal)
    direction_world = cls.ray.obj.matrix_world.to_3x3() @ direction_local
    plane_world = (cls.ray.location, cls.ray.normal)

    hit_bm.free()
    del hit_obj_eval
    del hit_data

    return direction_world, plane_world


def custom_orientation(cls, context, region, rv3d):
    '''Get the orientation from the custom plane'''

    # Create DrawMatrix from the matrix property
    custom_matrix = DrawMatrix.from_property(context.scene.bout.align.matrix)
    custom_location = custom_matrix.location
    custom_normal = custom_matrix.normal
    custom_direction = custom_matrix.direction

    custom_plane = (custom_location, custom_normal)

    location_world = view3d.region_2d_to_plane_3d(region, rv3d, cls.mouse.area, custom_plane)

    if location_world is None:
        return None, None

    location_world, detected_axis = orientation.point_on_axis(region, rv3d, custom_plane, custom_direction, location_world, distance=30)

    axis = context.scene.bout.axis
    axis.highlight.x, axis.highlight.y = detected_axis

    plane_world = (location_world, custom_normal)

    return custom_direction, plane_world


def world_orientation(cls, context, region, rv3d):
    '''Get the world orientation'''

    orientations = [
        (Vector((1, 0, 0)),  Vector((0, 0, 0)), Vector((0, 0, 1))),  # First try: Z-up
        (Vector((0, 0, 1)),  Vector((0, 0, 0)), Vector((0, 1, 0))),  # Second try: Y-up
        (Vector((0, 0, 1)),  Vector((0, 0, 0)), Vector((1, 0, 0)))   # Third try: X-up
    ]

    for direction, location, normal in orientations:
        world_plane = (location, normal)
        location_world = view3d.region_2d_to_plane_3d(region, rv3d, cls.mouse.area, world_plane)
        if location_world is not None:
            world_direction = direction
            world_normal = normal
            break
    else:
        return None, None

    location_world, detected_axis = orientation.point_on_axis(region, rv3d, world_plane, world_direction, location_world, distance=30)

    axis = context.scene.bout.axis
    axis.highlight.x, axis.highlight.y = detected_axis

    plane_world = (location_world, world_normal)

    return world_direction, plane_world
