import bpy

from ...shaders.draw import DrawLine, DrawGrid
from ...utils import addon


draw_handlers = []
depsgraph_handler = None


def add_draw_handlers(context):
    '''Add draw handlers for the custom plane axes'''
    custom = addon.pref().tools.block.align.custom

    location_world = custom.location
    direction_world = custom.direction
    normal_world = custom.normal

    point_x = location_world + direction_world
    direction_y = normal_world.cross(direction_world)
    point_y = location_world + direction_y

    color = addon.pref().theme.axis
    x_axis = DrawLine(points=(location_world, point_x), width=1.6, color=color.x, depth=False)
    x_handler = bpy.types.SpaceView3D.draw_handler_add(x_axis.draw, (context,), 'WINDOW', 'POST_VIEW')
    y_axis = DrawLine(points=(location_world, point_y), width=1.6, color=color.y, depth=False)
    y_handler = bpy.types.SpaceView3D.draw_handler_add(y_axis.draw, (context,), 'WINDOW', 'POST_VIEW')

    draw_handlers.append((x_handler, 'WINDOW'))
    draw_handlers.append((y_handler, 'WINDOW'))

    grid_props = addon.pref().tools.block.align.grid
    if grid_props.enable:
        spacing = grid_props.spacing
        size = grid_props.size

        grid = DrawGrid(origin=location_world, normal=normal_world, direction=direction_world, spacing=spacing, size=size, color=(0.2, 0.2, 0.2, 0.5))
        grid_handler = bpy.types.SpaceView3D.draw_handler_add(grid.draw, (context,), 'WINDOW', 'POST_VIEW')
        draw_handlers.append((grid_handler, 'WINDOW'))

    # Redraw the area
    for area in bpy.context.window.screen.areas:
        if area.type == 'VIEW_3D':
            area.tag_redraw()


def clear_draw_handlers():
    '''Remove all draw handlers'''
    for handler, region_type in draw_handlers:
        bpy.types.SpaceView3D.draw_handler_remove(handler, region_type)
    draw_handlers.clear()

    # Redraw the area
    for area in bpy.context.window.screen.areas:
        if area.type == 'VIEW_3D':
            area.tag_redraw()


def update(context):
    '''Update drawing handlers based on current conditions'''
    active_tool = context.workspace.tools.from_space_view3d_mode(context.mode, create=False)
    tool = active_tool and active_tool.idname in {'bout.block_obj', 'bout.block'}

    clear_draw_handlers()

    if tool and addon.pref().tools.block.align.mode == 'CUSTOM':
        add_draw_handlers(context)


def redraw(cls, context):
    '''Redraw the custom plane axes'''
    update(context)
    
    # Redraw the area
    for area in bpy.context.window.screen.areas:
        if area.type == 'VIEW_3D':
            area.tag_redraw()
