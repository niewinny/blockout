"""Scene utilities for object selection and ray casting.

Provides functions for interacting with scene objects through ray casting.
"""

import bpy
from . import ray_cast


def set_active_object(context, mouse_pos):
    """Set the active object based on mouse position.

    Performs a ray cast at the mouse position and sets the hit object
    as active if it's selected and in edit mode.

    :param context: The Blender context.
    :type context: bpy.types.Context
    :param mouse_pos: The mouse position as (x, y) tuple.
    :type mouse_pos: tuple[float, float]
    """
    ray = ray_cast.selected(context, mouse_pos)
    if ray.hit:
        if ray.obj in context.selected_objects:
            if ray.obj.mode == "EDIT":
                bpy.context.view_layer.objects.active = ray.obj
