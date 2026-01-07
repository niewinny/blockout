from dataclasses import dataclass, field

import bpy
from bpy.types import Context, Object, Region, RegionView3D, SpaceView3D
from mathutils import Matrix, Vector

from ..view3d import region_2d_to_origin_3d, region_2d_to_vector_3d


def _prepare_ray_cast(
    position: tuple[float, float], region: Region, rv3d: RegionView3D
) -> tuple[Vector, Vector]:
    """Prepare for ray casting"""
    x, y = position
    origin = region_2d_to_origin_3d(region, rv3d, (x, y))
    direction = region_2d_to_vector_3d(region, rv3d, (x, y))
    return origin, direction


def _ray_cast(
    context: Context, origin: Vector, direction: Vector, objects: set[Object]
) -> "Ray":
    """Cast a ray in the scene"""
    depsgraph = context.evaluated_depsgraph_get()
    scene = context.scene
    if not scene:
        return Ray()

    hit, location, normal, index, obj, matrix = scene.ray_cast(
        depsgraph, origin, direction
    )

    hidden: list[Object] = []
    space = context.space_data
    if not isinstance(space, SpaceView3D):
        return Ray()

    # Hide objects that are not in the selection and not visible in the viewport
    while (
        obj
        and obj not in objects
        and (not obj.visible_in_viewport_get(space) or obj.visible_get())
    ):
        hidden.append(obj)
        obj.hide_viewport = True

        hit, location, normal, index, obj, matrix = scene.ray_cast(
            depsgraph, origin, direction
        )

    for h in hidden:
        h.hide_viewport = False

    return Ray(hit, location, normal, index, obj, matrix)


def _setup_region(
    context: Context, region: Region | None = None, rv3d: RegionView3D | None = None
) -> tuple[Region, RegionView3D]:
    if not region:
        region = context.region
    if not rv3d:
        rv3d = context.region_data
    assert region and rv3d, "Region and RegionView3D required"
    return region, rv3d


def edited(
    context: Context,
    position: tuple[float, float],
    region: Region | None = None,
    rv3d: RegionView3D | None = None,
) -> "Ray":
    """Cast a ray in the scene to detect the edited object"""
    region, rv3d = _setup_region(context, region, rv3d)
    origin, direction = _prepare_ray_cast(position, region, rv3d)

    selection: set[Object] = set()
    obj = context.edit_object
    if obj and obj.type == "MESH":
        selection = {obj}

    return _ray_cast(context, origin, direction, selection)


def selected(
    context: Context,
    position: tuple[float, float],
    region: Region | None = None,
    rv3d: RegionView3D | None = None,
) -> "Ray":
    """Cast a ray in the scene to detect the selected objects"""
    region, rv3d = _setup_region(context, region, rv3d)
    origin, direction = _prepare_ray_cast(position, region, rv3d)

    types = {"MESH"}
    selection = {obj for obj in context.selected_objects if obj.type in types}

    return _ray_cast(context, origin, direction, selection)


def visible(
    context: Context,
    position: tuple[float, float],
    modes: tuple[str, ...] = ("OBJECT",),
    region: Region | None = None,
    rv3d: RegionView3D | None = None,
) -> "Ray":
    """Cast a ray in the scene to detect the visible objects"""
    region, rv3d = _setup_region(context, region, rv3d)
    origin, direction = _prepare_ray_cast(position, region, rv3d)

    types = {"MESH"}
    objects = {
        obj
        for obj in context.visible_objects
        if obj.type in types and obj.mode in modes
    }
    return _ray_cast(context, origin, direction, objects)


@dataclass
class Ray:
    """Ray cast data"""

    hit: bool = False
    location: Vector = field(default_factory=Vector)
    normal: Vector = field(default_factory=Vector)
    index: int = -1
    obj: bpy.types.Object | None = None
    matrix: Matrix = field(default_factory=Matrix)
