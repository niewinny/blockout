"""Numeric input handling for block modal operators.

Handles keyboard numeric input during modal operations, allowing users
to type exact values instead of using mouse movement.
"""

from mathutils import Vector

from ...utils import infobar
from ...utils.input import is_numeric_key, is_sign_key


def modal(op, context, event):
    """Handle numeric input events. Returns modal result or None to continue."""
    ni = op.data.numeric_input

    # Numeric key pressed - start or continue numeric input
    if is_numeric_key(event.type) and event.value == "PRESS":
        if op.mode == "EDIT":
            return {"RUNNING_MODAL"}

        if not ni.active:
            _start(op, context, event)

        ni.add_char(event.type)
        _apply(op, context, event)
        op._header(context)
        context.area.tag_redraw()
        return {"RUNNING_MODAL"}

    # Sign toggle (minus key)
    if is_sign_key(event.type) and event.value == "PRESS":
        if op.mode == "EDIT":
            return {"RUNNING_MODAL"}

        if not ni.active:
            _start(op, context, event)
            ni.buffer = "-"
        else:
            ni.toggle_sign()
            _apply(op, context, event)

        op._header(context)
        context.area.tag_redraw()
        return {"RUNNING_MODAL"}

    # Handle numeric input mode events
    match (ni.active, event.type, event.value):
        case (True, "BACK_SPACE", "PRESS"):
            result = ni.backspace()
            if result == "apply":
                _apply(op, context, event)
            elif result == "revert":
                _revert(op, context, event)
            else:  # cancel
                _stop_and_restore(op, context, event)
            op._header(context)
            context.area.tag_redraw()
            return {"RUNNING_MODAL"}

        case (True, "TAB", "PRESS"):
            if ni.buffer:
                _apply(op, context, event)
            ni.cycle(_get_num_editable_values(op))
            ni.stored_value = _get_current_value(op)
            op._header(context)
            context.area.tag_redraw()
            return {"RUNNING_MODAL"}

        case (True, "ESC", "PRESS"):
            _revert(op, context, event)
            _stop_and_restore(op, context, event)
            op._header(context)
            context.area.tag_redraw()
            return {"RUNNING_MODAL"}

        case (True, "RET" | "NUMPAD_ENTER", "PRESS"):
            if ni.buffer:
                _apply(op, context, event)
            op.mouse.co = Vector((event.mouse_region_x, event.mouse_region_y))
            op._header(context)
            context.area.tag_redraw()
            return {"RUNNING_MODAL"}

        case (True, "RET" | "NUMPAD_ENTER", "RELEASE"):
            ni.stop()
            # Fall through to normal handler

        case (True, "LEFTMOUSE", "PRESS"):
            # Only handle PRESS to avoid double-processing
            if ni.buffer:
                _apply(op, context, event)
            ni.stop()
            op.mouse.co = Vector((event.mouse_region_x, event.mouse_region_y))
            op._header(context)
            infobar.draw(context, event, op._infobar, blank=True)
            context.area.tag_redraw()
            # Don't return - let LMB fall through to normal handling

    return None  # Continue to normal event handling


def _start(op, context, event):
    """Start numeric input mode."""
    ni = op.data.numeric_input
    ni.start(_get_current_value(op), _get_initial_index(op))
    infobar.draw(context, event, op._infobar, blank=True)
    op.ui.guid.callback.clear()


def _stop_and_restore(op, context, event):
    """Stop numeric input mode and restore UI state."""
    ni = op.data.numeric_input
    ni.stop()
    infobar.draw(context, event, op._infobar, blank=True)
    # Note: UI guides will be restored on next geometry update


def _apply(op, context, event):
    """Apply current buffer value and update geometry."""
    ni = op.data.numeric_input
    value, error = ni.try_parse()
    if error or value is None:
        return

    if _is_int_value(op):
        # Validate and clamp integer values (bevel segments: 1-32)
        value = max(1, min(32, int(value)))
    _set_current_value(op, value)
    _update_geometry(op, context, event)


def _revert(op, context, event):
    """Revert to stored value."""
    ni = op.data.numeric_input
    value = int(ni.stored_value) if _is_int_value(op) else ni.stored_value
    _set_current_value(op, value)
    _update_geometry(op, context, event)


def _update_geometry(op, context, event):
    """Update geometry after numeric input change."""
    match op.mode:
        case "DRAW":
            op._draw_modal(context, event)
        case "EXTRUDE":
            op._extrude_modal(context, event)
        case "BEVEL":
            op._bevel_modal(context, event)


def _get_num_editable_values(op):
    """Get number of editable values for current mode/shape."""
    match (op.mode, op.config.shape):
        case ("DRAW", "RECTANGLE" | "BOX" | "CORNER"):
            return 2
        case ("DRAW", "TRIANGLE" | "PRISM"):
            return 2
        case ("DRAW", "CIRCLE" | "CYLINDER" | "SPHERE"):
            return 1
        case ("EXTRUDE", _):
            return 1
        case ("BEVEL", _):
            return 2
        case _:
            return 0


def _get_initial_index(op):
    """Get initial index when starting numeric input."""
    if op.mode == "BEVEL" and op.data.bevel.mode == "SEGMENTS":
        return 1
    return 0


def _is_int_value(op):
    """Check if current editable value is integer."""
    return op.mode == "BEVEL" and op.data.numeric_input.active_index == 1


def _get_current_value(op):
    """Get current value being edited based on mode/shape/index."""
    idx = op.data.numeric_input.active_index

    match (op.mode, op.config.shape):
        case ("DRAW", "RECTANGLE" | "BOX"):
            return op.shape.rectangle.co[idx]
        case ("DRAW", "CORNER"):
            return op.shape.corner.co[idx]
        case ("DRAW", "TRIANGLE" | "PRISM"):
            return op.shape.triangle.height if idx == 0 else op.shape.triangle.angle
        case ("DRAW", "CIRCLE" | "CYLINDER"):
            return op.shape.circle.radius
        case ("DRAW", "SPHERE"):
            return op.shape.sphere.radius
        case ("EXTRUDE", _):
            return op.data.extrude.value
        case ("BEVEL", _):
            return _get_bevel_value(op, is_offset=(idx == 0))
        case _:
            return 0.0


def _set_current_value(op, value):
    """Set current value being edited based on mode/shape/index."""
    idx = op.data.numeric_input.active_index

    match (op.mode, op.config.shape):
        case ("DRAW", "RECTANGLE" | "BOX"):
            op.shape.rectangle.co[idx] = value
        case ("DRAW", "CORNER"):
            op.shape.corner.co[idx] = value
        case ("DRAW", "TRIANGLE" | "PRISM"):
            if idx == 0:
                op.shape.triangle.height = value
            else:
                op.shape.triangle.angle = value
        case ("DRAW", "CIRCLE" | "CYLINDER"):
            op.shape.circle.radius = value
        case ("DRAW", "SPHERE"):
            op.shape.sphere.radius = value
        case ("EXTRUDE", _):
            op.data.extrude.value = value
        case ("BEVEL", _):
            _set_bevel_value(op, value, is_offset=(idx == 0))


def _get_bevel_value(op, is_offset=True):
    """Get bevel offset or segments based on type."""
    bevel_data = (
        op.data.bevel.round if op.data.bevel.type == "ROUND" else op.data.bevel.fill
    )
    return bevel_data.offset if is_offset else bevel_data.segments


def _set_bevel_value(op, value, is_offset=True):
    """Set bevel offset or segments based on type."""
    bevel_data = (
        op.data.bevel.round if op.data.bevel.type == "ROUND" else op.data.bevel.fill
    )
    if is_offset:
        bevel_data.offset = value
    else:
        bevel_data.segments = int(value)
