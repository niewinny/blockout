import bmesh
from mathutils import Vector
from ..bmath import geometry
from ..utils import view3d


def direction_from_longest_edge(face):
    '''Get the direction from the longest edge'''
    direction = face.calc_tangent_edge().normalized()

    return direction


def direction_from_closest_edge(face, loc):
    '''Get the direction from the closest edge'''
    edge = min(face.edges, key=lambda e: geometry.distance_point_to_segment(loc, e.verts[0].co, e.verts[1].co))

    # get loop for the edge that is also in the face
    loop = next((loop for loop in edge.link_loops if loop.face == face), None)
    direction = edge.calc_tangent(loop)

    return direction


def direction_from_active_edge(face, active_edge):
    '''Get the direction from the active edge'''

    loop = next((loop for loop in active_edge.link_loops if loop.face == face), None)
    direction = active_edge.calc_tangent(loop)
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


def plane_from_view(context, point, depth):
    '''Get the plane from the view'''

    region_data = context.space_data.region_3d

    # The view normal is the negative Z axis of the view rotation
    view_rotation = region_data.view_rotation
    view_normal_world = -view_rotation @ Vector((0.0, 0.0, 1.0))
    view_normal_world.normalize()

    region = context.region
    re3d = context.space_data.region_3d
    location_world = view3d.region_2d_to_location_3d(region, re3d, point, depth)

    plane_world = (location_world, view_normal_world)
    return plane_world


def plane_local(obj, plane):
    '''Get the plane from the view'''

    location_world, view_normal_world = plane

    obj_matrix_world = obj.matrix_world
    obj_matrix_world_inv = obj_matrix_world.inverted_safe()

    location_local = obj_matrix_world_inv @ location_world

    view_normal_local = view_normal_world @ obj_matrix_world_inv.transposed().to_3x3()
    view_normal_local.normalize()

    local_plane = (location_local, view_normal_local)

    return local_plane
