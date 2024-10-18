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
    loop = next((l for l in edge.link_loops if l.face == face), None)
    direction = edge.calc_tangent(loop)

    return direction


def direction_from_active_edge(face, active_edge):
    '''Get the direction from the active edge'''

    loop = next((l for l in active_edge.link_loops if l.face == face), None)
    direction = active_edge.calc_tangent(loop)
    return direction


def direction_from_normal(normal):
    '''Get the direction from the normal'''
    up_vector = Vector((0, 0, 1))
    if abs(normal.dot(up_vector)) > 0.9999:
        up_vector = Vector((0, 1, 0))

    direction = normal.cross(up_vector).normalized()

    return direction


def plane_from_ray(ray):
    '''Get the plane from the ray hit'''

    obj_matrix_world = ray.obj.matrix_world
    obj_matrix_world_inv = obj_matrix_world.inverted_safe()

    # Transform location and normal to object local space
    location = obj_matrix_world_inv @ ray.location

    # Correct normal transformation
    normal = ray.normal @ obj_matrix_world_inv.transposed().to_3x3()
    normal.normalize()

    plane = (location, normal)

    return plane


def direction_from_view(context):
    '''Get the orientation from the view'''

    region_data = context.space_data.region_3d


    # The view direction is the negative Z axis of the view rotation
    view_rotation = region_data.view_rotation
    view_direction = -view_rotation @ Vector((1.0, 0.0, 0.0))
    view_direction.normalize()

    return view_direction


def plane_from_view(context, point, depth):
    '''Get the plane from the view'''

    region_data = context.space_data.region_3d

    # The view normal is the negative Z axis of the view rotation
    view_rotation = region_data.view_rotation
    view_normal = -view_rotation @ Vector((0.0, 0.0, 1.0))
    view_normal.normalize()

    region = context.region
    re3d = context.space_data.region_3d
    location = view3d.region_2d_to_location_3d(region, re3d, point, depth)

    plane = (location, view_normal)

    return plane
