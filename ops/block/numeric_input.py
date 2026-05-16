"""Numeric input handling for block modal operators.

Handles keyboard numeric input during modal operations, allowing users
to type exact values instead of using mouse movement.
"""

import math

from mathutils import Vector

from ...utils import infobar
from ...utils.input import is_numeric_key, is_sign_key


def modal(op, context, event):
    """Handle numeric input events. Returns modal result or None to continue."""
    ni = op.data.numeric_input

    if is_numeric_key(event.type) and event.value == "PRESS":
        if op.state.phase == "EDIT":
            return {"RUNNING_MODAL"}

        if not ni.active:
            _start(op, context, event)

        ni.add_char(event.type)
        _apply(op, context, event)
        op._header(context)
        context.area.tag_redraw()
        return {"RUNNING_MODAL"}

    if is_sign_key(event.type) and event.value == "PRESS":
        if op.state.phase == "EDIT":
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

    # Numeric input is a sub-modal that overlays the current phase.
    # Accept: LMB press, SPACE, RET, NUMPAD_ENTER — apply the typed value.
    # Cancel: ESC, RMB — revert to the pre-typing value.
    # Either way, the outer modal phase does NOT advance. The event is
    # consumed (return RUNNING_MODAL) so the base modal doesn't process it.
    match (ni.active, event.type, event.value):
        case (True, "BACK_SPACE", "PRESS"):
            result = ni.backspace()
            if result == "apply":
                _apply(op, context, event)
            elif result == "revert":
                _revert(op, context, event)
            else:
                _stop_and_restore(op, context, event)
            op._header(context)
            context.area.tag_redraw()
            return {"RUNNING_MODAL"}

        case (True, "TAB", "PRESS"):
            if ni.buffer:
                _apply(op, context, event)
            indices = _get_editable_indices(op)
            if len(indices) <= 1:
                return {"RUNNING_MODAL"}
            try:
                pos = indices.index(ni.active_index)
            except ValueError:
                pos = -1
            ni.active_index = indices[(pos + 1) % len(indices)]
            ni.stored_value = _get_current_value(op)
            op._header(context)
            context.area.tag_redraw()
            return {"RUNNING_MODAL"}

        case (True, "ESC" | "RIGHTMOUSE", "PRESS"):
            _revert(op, context, event)
            _stop_and_restore(op, context, event)
            op._header(context)
            context.area.tag_redraw()
            return {"RUNNING_MODAL"}

        case (
            True,
            "RET" | "NUMPAD_ENTER" | "SPACE" | "LEFTMOUSE",
            "PRESS",
        ):
            if ni.buffer:
                _apply(op, context, event)
            ni.stop()
            infobar.draw(context, event, op._infobar, blank=True)
            op._header(context)
            context.area.tag_redraw()
            # LMB accept: suppress the trailing RELEASE of this click so
            # it doesn't re-advance the new phase we're about to enter.
            if event.type == "LEFTMOUSE":
                op._suppress_next_lmb_release = True
            # Numeric accept advances the outer phase — the accept gesture
            # commits the value AND moves to the next spine step.
            return op._force_advance(context, event)

        case (True, "LEFTMOUSE", "RELEASE"):
            # LMB release inside numeric does nothing — only press accepts.
            return {"RUNNING_MODAL"}

    return None


def _start(op, context, event):
    ni = op.data.numeric_input
    # Point `active_index` at the target slot FIRST (e.g. locked axis Y
    # → index 1) so `_get_current_value` reads that slot for stored_value.
    # Otherwise revert would restore the wrong component's baseline.
    idx = _get_initial_index(op)
    ni.active_index = idx
    ni.start(_get_current_value(op), idx)
    infobar.draw(context, event, op._infobar, blank=True)


def _stop_and_restore(op, context, event):
    ni = op.data.numeric_input
    ni.stop()
    infobar.draw(context, event, op._infobar, blank=True)


def _apply(op, context, event):
    ni = op.data.numeric_input
    value, error = ni.try_parse()
    if error or value is None:
        return

    if _is_int_value(op):
        value = max(1, min(32, int(value)))
    _set_current_value(op, value)
    _update_geometry(op, context, event)


def _revert(op, context, event):
    ni = op.data.numeric_input
    value = int(ni.stored_value) if _is_int_value(op) else ni.stored_value
    _set_current_value(op, value)
    _update_geometry(op, context, event)


def _update_geometry(op, context, event):
    match op.state.phase:
        case "DRAW":
            op._draw_modal(context, event)
        case "EXTRUDE":
            op._extrude_modal(context, event)
        case "BEVEL":
            op._bevel_modal(context, event)
        case "TRANSLATE":
            op._translate_modal(context, event)
        case "ROTATE":
            op._rotate_modal(context, event)
        case "SCALE":
            op._scale_modal(context, event)


_AXIS_INDEX = {"X": 0, "Y": 1, "Z": 2}


def _get_editable_indices(op):
    """Vector-component indices currently editable via numeric input.

    Blender-style axis lock in TRANSLATE/SCALE:
     - No lock → all axes editable.
     - Axis alone (constrain TO) → only that axis is editable.
     - Shift+axis (exclude) → all axes except that one are editable.
    ROTATE is a single-angle input; the axis lock picks the rotation axis
    rather than gating input.
    """
    phase = op.state.phase
    if phase in {"TRANSLATE", "SCALE"}:
        all_idx = [0, 1] if not op.is_3d else [0, 1, 2]
        lock_idx = _AXIS_INDEX.get(op.data.transform.axis_lock)
        if lock_idx is None:
            return all_idx
        if op.data.transform.axis_lock_exclude:
            return [i for i in all_idx if i != lock_idx]
        return [lock_idx] if lock_idx in all_idx else all_idx

    match phase:
        case "DRAW":
            return list(op.shape.data.draw_editable_indices)
        case "EXTRUDE":
            return [0]
        case "BEVEL":
            return [0, 1]
        case "ROTATE":
            return [0]
    return []


def _get_num_editable_values(op):
    return len(_get_editable_indices(op))


def _get_initial_index(op):
    if op.state.phase == "BEVEL" and op.data.bevel.mode == "SEGMENTS":
        return 1
    indices = _get_editable_indices(op)
    return indices[0] if indices else 0


def _is_int_value(op):
    return (
        op.state.phase == "BEVEL"
        and op.data.numeric_input.active_index == 1
    )


def _get_current_value(op):
    idx = op.data.numeric_input.active_index
    name = op.state.phase

    if name == "DRAW":
        sd = op.shape.data
        match op.config.shape:
            case "RECTANGLE" | "BOX" | "CORNER":
                return sd.size[idx]
            case "TRIANGLE" | "PRISM":
                return sd.height if idx == 0 else sd.angle
            case "CIRCLE" | "CYLINDER" | "SPHERE":
                return sd.radius
            case _:
                return 0.0
    if name == "EXTRUDE":
        return op.data.extrude.value
    if name == "BEVEL":
        return _get_bevel_value(op, is_offset=(idx == 0))
    if name == "TRANSLATE":
        return op.data.transform.translate.delta[idx]
    if name == "ROTATE":
        return math.degrees(op.data.transform.rotate.angle)
    if name == "SCALE":
        return op.data.transform.scale.factor[idx]
    return 0.0


def _set_current_value(op, value):
    idx = op.data.numeric_input.active_index
    name = op.state.phase

    if name == "DRAW":
        sd = op.shape.data
        match op.config.shape:
            case "RECTANGLE" | "BOX" | "CORNER":
                sd.size[idx] = value
            case "TRIANGLE" | "PRISM":
                if idx == 0:
                    sd.height = value
                else:
                    sd.angle = value
            case "CIRCLE" | "CYLINDER" | "SPHERE":
                sd.radius = value
        return
    if name == "EXTRUDE":
        op.data.extrude.value = value
        return
    if name == "BEVEL":
        _set_bevel_value(op, value, is_offset=(idx == 0))
        return
    if name == "TRANSLATE":
        d = op.data.transform.translate.delta
        new = list(d)
        new[idx] = value
        op.data.transform.translate.delta = Vector(new)
        return
    if name == "ROTATE":
        op.data.transform.rotate.angle = math.radians(value)
        return
    if name == "SCALE":
        d = op.data.transform.scale.factor
        new = list(d)
        new[idx] = value
        op.data.transform.scale.factor = Vector(new)
        return


def _get_bevel_value(op, is_offset=True):
    bevel_data = (
        op.data.bevel.round if op.data.bevel.type == "ROUND" else op.data.bevel.fill
    )
    return bevel_data.offset if is_offset else bevel_data.segments


def _set_bevel_value(op, value, is_offset=True):
    bevel_data = (
        op.data.bevel.round if op.data.bevel.type == "ROUND" else op.data.bevel.fill
    )
    if is_offset:
        bevel_data.offset = value
    else:
        bevel_data.segments = int(value)
