"""Rotate modify sub-op.

Rotation axis is resolved in the draw plane's local frame:
 - 2D: always around the plane normal (Z).
 - 3D with axis lock X/Y/Z: around that plane axis.
 - 3D free (no lock): screen-space trackball (yaw about view-up,
   pitch about view-right), rotation applied about the shape centroid.
"""

import math

from mathutils import Matrix, Quaternion, Vector

from ....utils import view3d
from .. import ui as block_ui
from . import common


def _axis_local(op):
    """Rotation axis in object-local space, resolved against the draw plane."""
    lock = op.data.transform.axis_lock
    x, y, z = common.plane_basis(op)
    if op.state.volume == "2D":
        return z
    if lock == "X":
        return x
    if lock == "Y":
        return y
    if lock == "Z":
        return z
    return Vector()


def invoke(op, context, event):
    """Enter rotate sub-op: snapshot mouse, pivot, and original coords."""
    block_ui.clear_phase(op)

    bm = op.data.bm
    bm.verts.ensure_lookup_table()

    ro = op.data.transform.rotate
    ro.vert_indices = common.vert_indices(op)
    n_verts = len(bm.verts)
    ro.vert_indices = [i for i in ro.vert_indices if 0 <= i < n_verts]
    ro.orig_coords = [bm.verts[i].co.copy() for i in ro.vert_indices]
    pivot = common.pivot_local(op)
    ro.pivot = pivot if pivot is not None else Vector()
    ro.angle_stored = 0.0
    ro.angle = 0.0
    ro.axis_vec = _axis_local(op)
    ro.mouse_invoke = op.mouse.co.copy()
    op.mouse.rotate = op.mouse.co
    ro.precision = False

    op.data.transform.active = "ROTATE"
    op.state.phase = "ROTATE"


def _compute_angle(op, context):
    """Compute signed rotation angle from mouse motion.

    Axis-locked (and 2D) rotation measures the angle in the actual
    rotation plane: the mouse ray is intersected with the plane
    through the pivot whose normal is the rotation axis, and the
    signed angle between pivot→p0 and pivot→p1 is returned.
    3D free stays screen-space trackball.
    """
    region = context.region
    rv3d = context.region_data
    obj = op.data.obj
    ro = op.data.transform.rotate

    lock = op.data.transform.axis_lock
    trackball = op.state.volume == "3D" and lock not in {"X", "Y", "Z"}
    if trackball:
        view_up = (rv3d.view_rotation @ Vector((0.0, 1.0, 0.0))).normalized()
        view_right = (rv3d.view_rotation @ Vector((1.0, 0.0, 0.0))).normalized()
        dx = op.mouse.co.x - op.mouse.rotate.x
        dy = op.mouse.co.y - op.mouse.rotate.y
        sensitivity = 0.005
        q_world = Quaternion(view_up, dx * sensitivity) @ Quaternion(view_right, -dy * sensitivity)
        mw_rot = obj.matrix_world.to_quaternion()
        q_local = mw_rot.inverted() @ q_world @ mw_rot
        axis, angle = q_local.to_axis_angle()
        ro.axis_vec = axis.normalized() if axis.length > 1e-9 else Vector((0.0, 0.0, 1.0))
        return angle

    ro.axis_vec = _axis_local(op)

    matrix_world = obj.matrix_world
    pivot_world = matrix_world @ ro.pivot
    axis_world = (matrix_world.to_3x3() @ ro.axis_vec).normalized()
    if axis_world.length < 1e-9:
        return 0.0
    rot_plane = (pivot_world, axis_world)
    p0 = view3d.region_2d_to_plane_3d(region, rv3d, op.mouse.rotate, rot_plane)
    p1 = view3d.region_2d_to_plane_3d(region, rv3d, op.mouse.co, rot_plane)
    if p0 is None or p1 is None:
        # View grazes the rotation plane; no usable intersection this frame.
        return 0.0
    v0 = p0 - pivot_world
    v1 = p1 - pivot_world
    v0 -= axis_world * v0.dot(axis_world)
    v1 -= axis_world * v1.dot(axis_world)
    if v0.length < 1e-6 or v1.length < 1e-6:
        return 0.0
    cross = v0.cross(v1)
    sign = 1.0 if cross.dot(axis_world) >= 0.0 else -1.0
    cos_a = max(-1.0, min(1.0, v0.normalized().dot(v1.normalized())))
    return sign * math.acos(cos_a)


def modal(op, context, event):
    """Update rotation from mouse or numeric input."""
    ro = op.data.transform.rotate
    ni = op.data.numeric_input

    if not ni.active:
        if event.shift != ro.precision:
            ro.angle_stored = ro.angle
            op.mouse.rotate = op.mouse.co
            ro.precision = event.shift

        angle = _compute_angle(op, context)
        adjustment = 0.1 if event.shift else 1.0
        angle = ro.angle_stored + angle * adjustment

        if op.config.snap:
            step = math.radians(1.0) if event.shift else math.radians(15.0)
            angle = round(angle / step) * step
        ro.angle = angle

    _apply(op)
    _ui(op, context)


def _apply(op):
    """Build rotation matrix and re-apply from cached baseline."""
    bm = op.data.bm
    bm.verts.ensure_lookup_table()
    ro = op.data.transform.rotate

    axis = ro.axis_vec
    if axis.length < 1e-9:
        axis = Vector((0.0, 0.0, 1.0))
    M = (
        Matrix.Translation(ro.pivot)
        @ Matrix.Rotation(ro.angle, 4, axis)
        @ Matrix.Translation(-ro.pivot)
    )
    n = len(bm.verts)
    for idx, orig in zip(ro.vert_indices, ro.orig_coords):
        if 0 <= idx < n:
            bm.verts[idx].co = M @ orig

    op.update_bmesh(op.data.obj, bm, loop_triangles=True, destructive=False)


def refresh(op, context):
    """Re-project the full mouse travel under the new rotation axis.

    Called on axis-lock toggle. Rewinds the anchor to the invoke-time
    mouse position and clears accumulated precision state, so the
    geometry snaps to the new axis as if it had been pressed from the
    start — matching Blender's R behavior.
    """
    ro = op.data.transform.rotate
    ro.axis_vec = _axis_local(op)
    if ro.axis_vec.length < 1e-9:
        ro.axis_vec = Vector((0.0, 0.0, 1.0))
    ro.angle_stored = 0.0
    op.mouse.rotate = ro.mouse_invoke.copy()
    ro.precision = False
    ro.angle = _compute_angle(op, context)
    _apply(op)
    _ui(op, context)


def _ui(op, context):
    region = context.region
    rv3d = context.region_data
    obj = op.data.obj
    matrix_world = obj.matrix_world
    ro = op.data.transform.rotate

    bm = op.data.bm
    bm.verts.ensure_lookup_table()
    bm.faces.ensure_lookup_table()

    pivot_world = matrix_world @ ro.pivot
    pivot_2d = view3d.location_3d_to_region_2d(region, rv3d, pivot_world, default=op.mouse.co)

    # Rotation axis line through the pivot, in the matching theme color.
    # 2D always rotates about plane Z. 3D axis-locked draws that axis.
    # 3D free (trackball) → no axis line (no single rotation axis).
    lock = op.data.transform.axis_lock
    is_2d = op.state.volume == "2D"
    if is_2d:
        active = "Z"
    elif lock in {"X", "Y", "Z"}:
        active = lock
    else:
        active = None
    handle_map = {"X": op.ui.xaxis, "Y": op.ui.yaxis, "Z": op.ui.zaxis}
    for label, handle in handle_map.items():
        if label == active:
            big = (matrix_world.to_3x3() @ ro.axis_vec) * 10000.0
            handle.callback.update_batch((pivot_world - big, pivot_world + big))
        else:
            handle.callback.clear()

    if op.config.mode != "ADD":
        face_indices = list(op.data.draw.faces) + list(op.data.extrude.faces)
        faces = [bm.faces[i] for i in face_indices if 0 <= i < len(bm.faces)]
        op.ui.faces.callback.update_batch(faces)

    if op.data.numeric_input.active:
        op.ui.interface.callback.clear()
    else:
        deg = math.degrees(ro.angle)
        axis_label = lock if lock else ("Z" if op.state.volume == "2D" else "Free")
        text = (f"Rotate {axis_label}", f"{deg:.2f}°")
        lines = [{"point": pivot_2d, "text_tuple": text}]
        op.ui.interface.callback.update_batch(lines)


def commit(op):
    """Fold current rotation into the per-axis pref angles.

    2D always rotates about plane Z. 3D axis-locked rotates about the
    corresponding plane axis. 3D free (trackball) is folded into plane Z
    as a fallback since no single axis captures it.
    """
    ro = op.data.transform.rotate
    lock = op.data.transform.axis_lock
    if op.state.volume == "2D":
        axis = "Z"
    elif lock in {"X", "Y", "Z"}:
        axis = lock
    else:
        axis = "Z"
    if axis == "X":
        op.pref.rotate_x += ro.angle
    elif axis == "Y":
        op.pref.rotate_y += ro.angle
    else:
        op.pref.rotate_z += ro.angle
