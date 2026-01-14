"""Status bar (infobar) drawing utilities for modal operators.

Provides functions to display interactive help text and status information
in Blender's status bar during modal operations.
"""


def draw(context, event, func, blank=False):
    """Set the status bar header with modal operator controls.

    :param context: The Blender context.
    :type context: bpy.types.Context
    :param event: The current event (passed to custom function).
    :type event: bpy.types.Event
    :param func: Optional callback function(layout, context, event) for custom UI.
    :type func: Callable | None
    :param blank: If True, use minimal layout without default controls.
    :type blank: bool
    """
    def header(self, context):
        if blank:
            infobar_blank(self, context, event, func)
        else:
            infobar_main(self, context, event, func)

    context.workspace.status_text_set(header)


def remove(context):
    """Clear the status bar header.

    :param context: The Blender context.
    :type context: bpy.types.Context
    """
    context.workspace.status_text_set(None)


def infobar_blank(self, context, event, func):
    """Draw a minimal status bar with only custom content.

    :param self: The header UI element.
    :param context: The Blender context.
    :type context: bpy.types.Context
    :param event: The current event.
    :type event: bpy.types.Event
    :param func: Optional callback function for custom UI elements.
    :type func: Callable | None
    """
    layout = self.layout

    if func:
        func(layout, context, event)
    infobar_copiedlines(layout, context)


def infobar_main(self, context, event, func):
    """Draw the main status bar with standard modal controls.

    Displays: Move (adjust), LMB (confirm), MMB (rotate view), RMB (cancel).

    :param self: The header UI element.
    :param context: The Blender context.
    :type context: bpy.types.Context
    :param event: The current event.
    :type event: bpy.types.Event
    :param func: Optional callback function for additional UI elements.
    :type func: Callable | None
    """
    layout = self.layout
    row = self.layout.row(align=True)
    row.label(text="", icon="MOUSE_MOVE")
    row.label(text="Adjust")
    row.separator(factor=8.0)
    row.label(text="", icon="MOUSE_LMB")
    row.label(text="Confirm")
    row.separator(factor=8.0)
    row.label(text="", icon="MOUSE_MMB")
    row.label(text="Rotate View")
    row.separator(factor=8.0)
    row.label(text="", icon="MOUSE_RMB")
    row.label(text="Cancel")
    row.separator(factor=8.0)

    if func:
        func(layout, context, event)

    infobar_copiedlines(layout, context)


def infobar_copiedlines(layout, context):
    """Draw the right side of the status bar with stats and progress.

    :param layout: The UI layout to draw into.
    :type layout: bpy.types.UILayout
    :param context: The Blender context.
    :type context: bpy.types.Context
    """
    layout.separator_spacer()

    # Report Messages
    layout.template_reports_banner()

    layout.separator_spacer()

    row = layout.row()
    row.alignment = "RIGHT"

    # Stats & Info
    row.label(text=context.screen.statusbar_info(), translate=False)

    # Progress Bar
    row.template_running_jobs()
