"""Gizmo utilities for the 3D viewport."""


def refresh(self, context):
    """Force refresh of gizmos in all 3D viewports.

    Toggles gizmo visibility to trigger a redraw of all gizmos.

    :param self: The operator or gizmo instance (unused, for compatibility).
    :param context: The Blender context.
    :type context: bpy.types.Context
    """
    for area in context.screen.areas:
        if area.type == "VIEW_3D":
            space = area.spaces.active
            current_state = space.show_gizmo
            space.show_gizmo = not current_state  # Toggle to force gizmo refresh
            space.show_gizmo = current_state
