from dataclasses import dataclass

import bpy

from mathutils import Vector, Matrix
from ..view3d import region_2d_to_origin_3d, region_2d_to_vector_3d


def _prepare_ray_cast(position, region, rv3d):
    """Prepare for ray casting"""

    # Prepare for ray casting
    x, y = position
    origin = region_2d_to_origin_3d(region, rv3d, (x, y))
    direction = region_2d_to_vector_3d(region, rv3d, (x, y))

    return origin, direction


def _ray_cast(context, origin, direction, objects):
    """Cast a ray in the scene"""

    # Start ray casting
    depsgraph = context.view_layer.depsgraph
    scene = context.scene
    hit, location, normal, index, obj, matrix = scene.ray_cast(
        depsgraph, origin, direction
    )

    hidden = []

    # Hide objects that are not in the selection and not visible in the viewport
    while (
        obj
        and obj not in objects
        and (not obj.visible_in_viewport_get(context.space_data) or obj.visible_get())
    ):
        hidden.append(obj)
        obj.hide_viewport = True

        hit, location, normal, index, obj, matrix = scene.ray_cast(
            depsgraph, origin, direction
        )

    for h in hidden:
        h.hide_viewport = False

    ray = Ray(hit, location, normal, index, obj, matrix)
    return ray


def _setup_region(context, region=None, rv3d=None):
    if not region:
        region = context.region
    if not rv3d:
        rv3d = context.region_data
    return region, rv3d


def edited(context, position, region=None, rv3d=None):
    """Cast a ray in the scene to detect the selected objects"""

    region, rv3d = _setup_region(context, region, rv3d)
    origin, direction = _prepare_ray_cast(position, region=region, rv3d=rv3d)

    selection = {}
    obj = context.edit_object
    if obj and obj.type == "MESH":
        selection = {obj}

    ray = _ray_cast(context, origin, direction, selection)

    return ray


def selected(context, position, region=None, rv3d=None):
    """Cast a ray in the scene to detect the selected objects"""

    region, rv3d = _setup_region(context, region, rv3d)
    origin, direction = _prepare_ray_cast(position, region=region, rv3d=rv3d)

    types = {"MESH"}
    selection = {obj for obj in context.selected_objects if obj.type in types}

    ray = _ray_cast(context, origin, direction, selection)

    return ray


def visible(context, position, modes=("OBJECT"), region=None, rv3d=None):
    """Cast a ray in the scene to detect the visible objects"""

    region, rv3d = _setup_region(context, region, rv3d)
    origin, direction = _prepare_ray_cast(position, region=region, rv3d=rv3d)

    # Start ray casting
    types = {"MESH"}
    objects = {
        obj
        for obj in context.visible_objects
        if obj.type in types and obj.mode in modes
    }
    ray = _ray_cast(context, origin, direction, objects)
    return ray


@dataclass
class Ray:
    """Ray cast data"""

    hit: bool = False
    location: Vector = Vector()
    normal: Vector = Vector()
    index: int = -1
    obj: bpy.types.Object | None = None
    matrix: Matrix = Matrix()
