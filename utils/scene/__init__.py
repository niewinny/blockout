import bpy
from . import ray_cast


def set_active_object(context, mouse_pos):
    '''Set the active object'''

    ray = ray_cast.selected(context, mouse_pos)
    if ray.hit:
        if ray.obj in context.selected_objects:
            if ray.obj.mode == "EDIT":
                bpy.context.view_layer.objects.active = ray.obj
