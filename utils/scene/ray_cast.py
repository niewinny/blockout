"""Ray casting utilities for scene object detection.

Provides functions to cast rays from 2D viewport coordinates into 3D space
and detect intersections with mesh objects based on selection state or visibility.
"""

from dataclasses import dataclass, field

import bpy
from bpy.types import Context, Object, Region, RegionView3D, SpaceView3D
from mathutils import Matrix, Vector

from ..view3d import region_2d_to_origin_3d, region_2d_to_vector_3d


def _prepare_ray_cast(
    position: tuple[float, float], region: Region, rv3d: RegionView3D
) -> tuple[Vector, Vector]:
    """Convert 2D screen position to 3D ray origin and direction.

    :param position: The 2D position as (x, y) in region coordinates.
    :type position: tuple[float, float]
    :param region: The viewport region.
    :type region: bpy.types.Region
    :param rv3d: The region's 3D view data.
    :type rv3d: bpy.types.RegionView3D
    :return: Tuple of (origin, direction) vectors in world space.
    :rtype: tuple[mathutils.Vector, mathutils.Vector]
    """
    x, y = position
    origin = region_2d_to_origin_3d(region, rv3d, (x, y))
    direction = region_2d_to_vector_3d(region, rv3d, (x, y))
    return origin, direction


def _ray_cast(
    context: Context, origin: Vector, direction: Vector, objects: set[Object]
) -> "Ray":
    """Cast a ray and find intersection with specified objects.

    Temporarily hides non-target objects to find hits only on the specified set.

    :param context: The Blender context.
    :type context: bpy.types.Context
    :param origin: Ray origin in world space.
    :type origin: mathutils.Vector
    :param direction: Ray direction in world space.
    :type direction: mathutils.Vector
    :param objects: Set of objects to test for intersection.
    :type objects: set[bpy.types.Object]
    :return: Ray dataclass with hit information.
    :rtype: Ray
    """
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
    """Set up region and region data for ray casting.

    :param context: The Blender context.
    :type context: bpy.types.Context
    :param region: Optional region override.
    :type region: bpy.types.Region | None
    :param rv3d: Optional RegionView3D override.
    :type rv3d: bpy.types.RegionView3D | None
    :return: Tuple of (Region, RegionView3D).
    :rtype: tuple[bpy.types.Region, bpy.types.RegionView3D]
    :raises AssertionError: If region or rv3d cannot be determined.
    """
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
    """Cast a ray to detect hits on the currently edited mesh object.

    :param context: The Blender context.
    :type context: bpy.types.Context
    :param position: The 2D position as (x, y) in region coordinates.
    :type position: tuple[float, float]
    :param region: Optional region override (defaults to context.region).
    :type region: bpy.types.Region | None
    :param rv3d: Optional RegionView3D override (defaults to context.region_data).
    :type rv3d: bpy.types.RegionView3D | None
    :return: Ray dataclass with hit information for the edit object only.
    :rtype: Ray
    """
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
    """Cast a ray to detect hits on selected mesh objects.

    :param context: The Blender context.
    :type context: bpy.types.Context
    :param position: The 2D position as (x, y) in region coordinates.
    :type position: tuple[float, float]
    :param region: Optional region override (defaults to context.region).
    :type region: bpy.types.Region | None
    :param rv3d: Optional RegionView3D override (defaults to context.region_data).
    :type rv3d: bpy.types.RegionView3D | None
    :return: Ray dataclass with hit information for selected objects only.
    :rtype: Ray
    """
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
    """Cast a ray to detect hits on visible mesh objects in specified modes.

    :param context: The Blender context.
    :type context: bpy.types.Context
    :param position: The 2D position as (x, y) in region coordinates.
    :type position: tuple[float, float]
    :param modes: Tuple of object modes to include (e.g., "OBJECT", "EDIT").
    :type modes: tuple[str, ...]
    :param region: Optional region override (defaults to context.region).
    :type region: bpy.types.Region | None
    :param rv3d: Optional RegionView3D override (defaults to context.region_data).
    :type rv3d: bpy.types.RegionView3D | None
    :return: Ray dataclass with hit information for visible objects.
    :rtype: Ray
    """
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
    """Ray cast result data.

    :ivar hit: Whether the ray intersected an object.
    :vartype hit: bool
    :ivar location: World space hit location.
    :vartype location: mathutils.Vector
    :ivar normal: Surface normal at hit point.
    :vartype normal: mathutils.Vector
    :ivar index: Face index of the hit polygon.
    :vartype index: int
    :ivar obj: The hit object, or None if no hit.
    :vartype obj: bpy.types.Object | None
    :ivar matrix: World matrix of the hit object.
    :vartype matrix: mathutils.Matrix
    """

    hit: bool = False
    location: Vector = field(default_factory=Vector)
    normal: Vector = field(default_factory=Vector)
    index: int = -1
    obj: bpy.types.Object | None = None
    matrix: Matrix = field(default_factory=Matrix)
