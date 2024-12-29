import bpy
from . tools.block import custom


def unregister_draw_handlers():
    '''Handler called after loading a file'''
    custom.remove()


def register():
    pass


def unregister():
    unregister_draw_handlers()
