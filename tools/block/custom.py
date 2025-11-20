import bpy
from bpy.app.handlers import persistent

from ...shaders.draw import DrawLine
from ...utils import addon
from ...utils.types import DrawMatrix
from ...utilsbmesh.orientation import get_vectors_from_align_rotation

draw_handlers = []
undo_post_handlers = []
redo_post_handlers = []


def add_draw_handlers(context):
    """Add draw handlers for the custom plane axes"""
    # Create DrawMatrix from the matrix property
    custom_matrix = DrawMatrix.from_property(context.scene.bout.align.matrix)
    highlight = context.scene.bout.axis.highlight

    location_world = custom_matrix.location
    direction_world = custom_matrix.direction
    normal_world = custom_matrix.normal

    point_x = location_world + direction_world
    direction_y = normal_world.cross(direction_world)
    point_y = location_world + direction_y

    color = addon.pref().theme.axis
    # Brighten colors when highlighted (multiply RGB by 1.5, set alpha to 1)
    value = 1.2
    x_color = (
        tuple(c * value if highlight.x else c for c in color.x[:3]) + (1,)
        if highlight.x
        else color.x
    )
    y_color = (
        tuple(c * value if highlight.y else c for c in color.y[:3]) + (1,)
        if highlight.y
        else color.y
    )

    x_axis = DrawLine(
        points=(location_world, point_x), width=1.6, color=x_color, depth=False
    )
    x_handler = bpy.types.SpaceView3D.draw_handler_add(
        x_axis.draw_tool, (context,), "WINDOW", "POST_VIEW"
    )
    y_axis = DrawLine(
        points=(location_world, point_y), width=1.6, color=y_color, depth=False
    )
    y_handler = bpy.types.SpaceView3D.draw_handler_add(
        y_axis.draw_tool, (context,), "WINDOW", "POST_VIEW"
    )

    draw_handlers.append((x_handler, "WINDOW"))
    draw_handlers.append((y_handler, "WINDOW"))

    # Redraw the area
    for area in bpy.context.window.screen.areas:
        if area.type == "VIEW_3D":
            area.tag_redraw()


def update_location(cls, context):
    location = context.scene.bout.align.location

    matrix = DrawMatrix.from_property(context.scene.bout.align.matrix)
    direction = matrix.direction
    normal = matrix.normal

    new_matrix = DrawMatrix.new()
    new_matrix.from_plane((location, normal), direction)
    context.scene.bout.align.matrix = new_matrix.to_property()

    redraw(cls, context)


def update_rotation(cls, context):
    rotation = context.scene.bout.align.rotation
    normal, direction = get_vectors_from_align_rotation(rotation)

    matrix = DrawMatrix.from_property(context.scene.bout.align.matrix)
    location = matrix.location

    new_matrix = DrawMatrix.new()
    new_matrix.from_plane((location, normal), direction)
    context.scene.bout.align.matrix = new_matrix.to_property()

    redraw(cls, context)


def clear_draw_handlers():
    """Remove all draw handlers"""
    try:
        for handler, region_type in draw_handlers:
            try:
                bpy.types.SpaceView3D.draw_handler_remove(handler, region_type)
            except (ValueError, ReferenceError):
                # Handler may have already been removed
                pass
        draw_handlers.clear()

        # Redraw the area, but only if we have a valid window
        if hasattr(bpy.context, "window") and bpy.context.window:
            for area in bpy.context.window.screen.areas:
                if area.type == "VIEW_3D":
                    area.tag_redraw()
    except AttributeError:
        # Context might not be available during certain undo operations
        pass


def update(context):
    """Update drawing handlers based on current conditions"""
    active_tool = context.workspace.tools.from_space_view3d_mode(
        context.mode, create=False
    )
    tool = active_tool and active_tool.idname in {
        "object.bout_block_obj",
        "object.bout_block_mesh",
    }

    clear_draw_handlers()

    if tool and context.scene.bout.align.mode == "CUSTOM":
        add_draw_handlers(context)


def redraw(_, context):
    """Redraw the custom plane axes"""
    update(context)

    # Redraw the area
    for area in bpy.context.window.screen.areas:
        if area.type == "VIEW_3D":
            area.tag_redraw()


def remove():
    """Remove draw handlers"""
    clear_draw_handlers()


def perform_deferred_update():
    """Safely execute the update when it's safe to do so"""
    # Only update if context is valid
    if hasattr(bpy, "context"):
        try:
            context = bpy.context

            # Access the property from scene data
            if not context.scene.bout.update:
                return False

            active_tool = context.workspace.tools.from_space_view3d_mode(
                context.mode, create=False
            )
            tool = active_tool and active_tool.idname in {
                "object.bout_block_obj",
                "object.bout_block_mesh",
            }

            # Clear handlers first
            clear_draw_handlers()

            # Only add handlers if needed
            if tool and context.scene.bout.align.mode == "CUSTOM":
                add_draw_handlers(context)

            # Reset flag
            context.scene.bout.update = False

        except ReferenceError:
            # Handle case where objects were deleted during undo
            clear_draw_handlers()
        except Exception as e:
            print(f"Blockout update error: {e}")
            clear_draw_handlers()

    # Return False to unregister the timer
    return False


@persistent
def undo(scene):
    """Handler for post-undo operations to ensure UI updates"""
    if hasattr(scene, "bout"):
        scene.bout.update = True
        bpy.app.timers.register(perform_deferred_update, first_interval=0.1)


def register_undo_post():
    """Register the undo_post handler"""
    if undo not in bpy.app.handlers.undo_post:
        bpy.app.handlers.undo_post.append(undo)
        undo_post_handlers.append(undo)


def unregister_undo_post():
    """Unregister the undo_post handler"""
    for handler in undo_post_handlers:
        if handler in bpy.app.handlers.undo_post:
            bpy.app.handlers.undo_post.remove(handler)
    undo_post_handlers.clear()


def register_redo_post():
    """Register the redo_post handler"""
    if undo not in bpy.app.handlers.redo_post:
        bpy.app.handlers.redo_post.append(undo)
        redo_post_handlers.append(undo)


def unregister_redo_post():
    """Unregister the redo_post handler"""
    for handler in redo_post_handlers:
        if handler in bpy.app.handlers.redo_post:
            bpy.app.handlers.redo_post.remove(handler)
    redo_post_handlers.clear()
