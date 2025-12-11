"""Numeric input handling for bevel modal operators.

Handles keyboard numeric input during modal operations, allowing users
to type exact values instead of using mouse movement.
"""

from ....utils import infobar
from ....utils.input import is_numeric_key, is_sign_key


def modal(op, context, event):
    """Handle numeric input events. Returns modal result or None to continue."""
    ni = op.numeric_input

    # Numeric key pressed - start or continue numeric input
    if is_numeric_key(event.type) and event.value == "PRESS":
        if not ni.active:
            _start(op, context, event)

        ni.add_char(event.type)
        _apply(op, context)
        op._update_info(context)
        op._update_drawing(context)
        context.area.tag_redraw()
        return {"RUNNING_MODAL"}

    # Sign toggle (minus key)
    if is_sign_key(event.type) and event.value == "PRESS":
        if not ni.active:
            _start(op, context, event)
            ni.buffer = "-"
            _apply(op, context)
        else:
            ni.toggle_sign()
            _apply(op, context)

        op._update_info(context)
        op._update_drawing(context)
        context.area.tag_redraw()
        return {"RUNNING_MODAL"}

    # Handle numeric input mode events
    match (ni.active, event.type, event.value):
        case (True, "BACK_SPACE", "PRESS"):
            result = ni.backspace()
            if result == "apply":
                _apply(op, context)
            elif result == "revert":
                _revert(op, context)
            else:  # cancel
                _stop_and_restore(op, context, event)
            op._update_info(context)
            op._update_drawing(context)
            context.area.tag_redraw()
            return {"RUNNING_MODAL"}

        case (True, "TAB", "PRESS"):
            if ni.buffer:
                _apply(op, context)
            ni.cycle(_get_num_editable_values())
            ni.stored_value = _get_current_value(op)
            op._update_info(context)
            context.area.tag_redraw()
            return {"RUNNING_MODAL"}

        case (True, "ESC", "PRESS"):
            _revert(op, context)
            _stop_and_restore(op, context, event)
            op._update_info(context)
            op._update_drawing(context)
            context.area.tag_redraw()
            return {"RUNNING_MODAL"}

        case (True, "LEFTMOUSE", "PRESS"):
            # Apply and let LMB fall through to finish
            if ni.buffer:
                _apply(op, context)
            ni.stop()
            op._update_info(context)
            infobar.draw(context, event, op._infobar_hotkeys, blank=True)
            context.area.tag_redraw()
            # Don't return - let LMB fall through to normal handling

        case (True, "RET", "PRESS") | (True, "NUMPAD_ENTER", "PRESS"):
            if ni.buffer:
                _apply(op, context)
            ni.stop()
            # Don't return - let RETURN fall through to normal modal handling

    return None  # Continue to normal event handling


def _start(op, context, event):
    """Start numeric input mode."""
    ni = op.numeric_input
    ni.start(_get_current_value(op), _get_initial_index(op))
    infobar.draw(context, event, op._infobar_hotkeys, blank=True)


def _stop_and_restore(op, context, event):
    """Stop numeric input mode and restore UI state."""
    ni = op.numeric_input
    ni.stop()
    infobar.draw(context, event, op._infobar_hotkeys, blank=True)


def _apply(op, context):
    """Apply current buffer value and update modifiers."""
    ni = op.numeric_input
    value, error = ni.try_parse()
    if error or value is None:
        return

    if _is_int_value(op):
        # Validate and clamp integer values (segments: 1-32)
        value = max(1, min(32, int(value)))
    _set_current_value(op, value)


def _revert(op, context):
    """Revert to stored value."""
    ni = op.numeric_input
    value = int(ni.stored_value) if _is_int_value(op) else ni.stored_value
    _set_current_value(op, value)


def _get_num_editable_values():
    """Get number of editable values: offset and segments."""
    return 2


def _get_initial_index(op):
    """Get initial index when starting numeric input."""
    return 1 if op.mode == "SEGMENTS" else 0


def _is_int_value(op):
    """Check if current editable value is integer (segments)."""
    return op.numeric_input.active_index == 1


def _get_current_value(op):
    """Get current value being edited based on active index."""
    idx = op.numeric_input.active_index
    return op.segments if idx == 1 else op.width


def _set_current_value(op, value):
    """Set current value being edited and update all modifiers."""
    if not op.bevels:
        return

    idx = op.numeric_input.active_index

    if idx == 1:  # segments
        op.segments = max(1, min(32, int(value)))
        for b in op.bevels:
            b.mod.segments = op.segments
    else:  # offset
        op.width = max(0, value)
        for b in op.bevels:
            b.mod.width = op.width
