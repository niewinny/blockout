from dataclasses import dataclass

import bpy

from mathutils import Vector, Matrix
from ..view3d import region_2d_to_origin_3d, region_2d_to_vector_3d


def _prepare_ray_cast(context, position):
    '''Prepare for ray casting'''

    region = context.region
    rv3d = context.region_data

    # Prepare for ray casting
    x, y = position
    origin = Vector(region_2d_to_origin_3d(region, rv3d, (x, y)))
    direction = Vector(region_2d_to_vector_3d(region, rv3d, (x, y)))

    return origin, direction


def _ray_cast(context, origin, direction, objects):
    '''Cast a ray in the scene'''

    # Start ray casting
    depsgraph = context.view_layer.depsgraph
    hit, location, normal, index, obj, matrix = context.scene.ray_cast(depsgraph, origin, direction)

    hidden = []

    # Hide objects that are not in the selection and not visible in the viewport
    while obj and obj not in objects and (not obj.visible_in_viewport_get(context.space_data) or obj.visible_get()):
        hidden.append(obj)
        obj.hide_viewport = True

        hit, location, normal, index, obj, matrix = context.scene.ray_cast(depsgraph, origin, direction)

    for h in hidden:
        h.hide_viewport = False

    ray = Ray(hit, location, normal, index, obj, matrix)
    return ray

def edited(context, position):
    '''Cast a ray in the scene to detect the selected objects'''

    origin, direction = _prepare_ray_cast(context, position)

    selection = {}
    obj = context.edit_object
    if obj and obj.type == 'MESH':
        selection = {obj}

    ray = _ray_cast(context, origin, direction, selection)

    return ray


def selected(context, position):
    '''Cast a ray in the scene to detect the selected objects'''

    origin, direction = _prepare_ray_cast(context, position)

    types = {'MESH'}
    selection = {obj for obj in context.selected_objects if obj.type in types}

    ray = _ray_cast(context, origin, direction, selection)

    return ray


def visible(context, position, modes=('OBJECT')):
    '''Cast a ray in the scene to detect the visible objects'''

    origin, direction = _prepare_ray_cast(context, position)

    # Start ray casting
    types = {'MESH'}
    objects = {obj for obj in context.visible_objects if obj.type in types and obj.mode in modes}
    ray = _ray_cast(context, origin, direction, objects)
    return ray


@dataclass
class Ray:
    '''Ray cast data'''
    hit: bool = False
    location: Vector = Vector()
    normal: Vector = Vector()
    index: int = -1
    obj: bpy.types.Object = None
    matrix: Matrix = Matrix()
