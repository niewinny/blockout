"""Translate modify sub-op.

Operates in the draw plane's local frame: axis locks ``X``/``Y``/``Z``
align with plane direction / plane bitangent / plane normal. Blender
convention — ``X`` alone constrains TO that axis; ``Shift+X`` excludes
it (move on the other two). 2D always lies on the draw plane; 3D free
projects onto the view plane through the hitplane origin.
"""

from mathutils import Vector

from ....utils import view3d
from .. import ui as block_ui
from . import common


def invoke(op, context, event):
    """Enter translate sub-op: snapshot mouse and current vert positions.

    No per-sub-op pivot capture: translate uses the hitplane origin as
    the projection anchor (stable and always defined by the draw matrix).
    """
    block_ui.clear_phase(op)

    bm = op.data.bm
    bm.verts.ensure_lookup_table()

    tr = op.data.transform.translate
    tr.vert_indices = common.vert_indices(op)
    n_verts = len(bm.verts)
    tr.vert_indices = [i for i in tr.vert_indices if 0 <= i < n_verts]
    tr.orig_coords = [bm.verts[i].co.copy() for i in tr.vert_indices]
    tr.delta_stored = Vector()
    tr.delta = Vector()
    tr.mouse_invoke = op.mouse.co.copy()
    op.mouse.translate = op.mouse.co
    tr.precision = False

    op.data.transform.active = "TRANSLATE"
    op.state.phase = "TRANSLATE"


def _compute_delta(op, context):
    """Compute object-local delta from mouse motion.

    Matches the draw/extrude projection style — the mouse ray is
    intersected with the constraint surface, so motion feels direct:

     - 2D volume → always project onto the draw plane. An axis lock
       further constrains within the plane (keep/drop that component).
     - 3D, no lock → project onto the camera-facing plane through pivot.
     - 3D, X/Y/Z alone → slide along a world-space line (the plane axis
       through pivot). Uses ``region_2d_to_line_3d`` like extrude.
     - 3D, Shift+X/Y/Z → project onto the plane through pivot whose
       normal is the locked axis (the two free plane axes span it).
    """
    region = context.region
    rv3d = context.region_data
    obj = op.data.obj
    matrix_world = obj.matrix_world
    px, py, pz = common.plane_basis(op)

    origin_2d = op.mouse.translate
    current_2d = op.mouse.co

    lock = op.data.transform.axis_lock
    exclude = op.data.transform.axis_lock_exclude
    basis_map = {"X": px, "Y": py, "Z": pz}
    lock_axis = basis_map.get(lock)
    is_2d = not op.is_3d

    # ── 2D: translate strictly on the draw plane ────────────────────────
    if is_2d:
        plane = op.data.draw.matrix.plane
        p0 = view3d.region_2d_to_plane_3d(region, rv3d, origin_2d, plane, matrix=matrix_world)
        p1 = view3d.region_2d_to_plane_3d(region, rv3d, current_2d, plane, matrix=matrix_world)
        if p0 is None or p1 is None:
            return Vector()
        delta = p1 - p0
        delta -= pz * delta.dot(pz)
        if lock_axis is not None:
            projection = lock_axis * delta.dot(lock_axis)
            delta = (delta - projection) if exclude else projection
        return delta

    # ── 3D ──────────────────────────────────────────────────────────────
    # Work in object-local space throughout: helpers transform the mouse
    # ray via ``matrix=matrix_world``, so pivot/axis/result are all local.
    # This stays correct under non-identity object scale or rotation.
    pivot_local = common.plane_origin_local(op)

    if lock_axis is not None and not exclude:
        # G + axis: slide along the plane axis line through the pivot.
        _, d0 = view3d.region_2d_to_line_3d(
            region, rv3d, origin_2d, pivot_local, lock_axis, matrix=matrix_world
        )
        _, d1 = view3d.region_2d_to_line_3d(
            region, rv3d, current_2d, pivot_local, lock_axis, matrix=matrix_world
        )
        if d0 is None or d1 is None:
            return Vector()
        return lock_axis * (d1 - d0)

    if lock_axis is not None and exclude:
        # Shift + axis: project onto the plane through the pivot whose
        # normal is the locked axis (the two free axes span it).
        plane = (pivot_local, lock_axis)
        p0 = view3d.region_2d_to_plane_3d(
            region, rv3d, origin_2d, plane, matrix=matrix_world
        )
        p1 = view3d.region_2d_to_plane_3d(
            region, rv3d, current_2d, plane, matrix=matrix_world
        )
        if p0 is None or p1 is None:
            return Vector()
        delta = p1 - p0
        # Guard against numerical bleed onto the locked axis.
        delta -= lock_axis * delta.dot(lock_axis)
        return delta

    # Free 3D: camera-facing plane through pivot. Express the view normal
    # in object-local so the in-local projection stays consistent.
    view_normal_world = (rv3d.view_rotation @ Vector((0.0, 0.0, 1.0))).normalized()
    view_normal_local = (
        matrix_world.inverted().to_3x3() @ view_normal_world
    ).normalized()
    plane = (pivot_local, view_normal_local)
    p0 = view3d.region_2d_to_plane_3d(region, rv3d, origin_2d, plane, matrix=matrix_world)
    p1 = view3d.region_2d_to_plane_3d(region, rv3d, current_2d, plane, matrix=matrix_world)
    if p0 is None or p1 is None:
        return Vector()
    return p1 - p0


def modal(op, context, event):
    """Update translation based on mouse or numeric input."""
    tr = op.data.transform.translate
    ni = op.data.numeric_input

    if not ni.active:
        if event.shift != tr.precision:
            tr.delta_stored = tr.delta.copy()
            op.mouse.translate = op.mouse.co
            tr.precision = event.shift

        delta = _compute_delta(op, context)
        adjustment = 0.1 if event.shift else 1.0
        delta = tr.delta_stored + delta * adjustment

        if op.config.snap:
            increments = op.config.align.increments
            if increments > 0:
                delta = Vector((
                    round(delta.x / increments) * increments,
                    round(delta.y / increments) * increments,
                    round(delta.z / increments) * increments,
                ))
        tr.delta = delta

    _apply(op)
    _ui(op, context)


def _apply(op):
    """Write baseline + delta into bmesh and push to mesh."""
    bm = op.data.bm
    bm.verts.ensure_lookup_table()
    tr = op.data.transform.translate
    n = len(bm.verts)

    for idx, orig in zip(tr.vert_indices, tr.orig_coords):
        if 0 <= idx < n:
            bm.verts[idx].co = orig + tr.delta

    op.update_bmesh(op.data.obj, bm, loop_triangles=True, destructive=False)


def refresh(op, context):
    """Re-project the full mouse travel under the new axis rule.

    Called on axis-lock toggle. Rewinds the anchor to the invoke-time
    mouse position and clears the stored (precision) delta, so the
    cutter snaps to the new constraint as if the user had pressed
    that axis from the start — matching Blender's G/R/S behavior.
    """
    tr = op.data.transform.translate
    tr.delta_stored = Vector()
    op.mouse.translate = tr.mouse_invoke.copy()
    tr.precision = False
    tr.delta = _compute_delta(op, context)
    _apply(op)
    _ui(op, context)


def _ui(op, context):
    """Update on-screen overlay for translate; refresh face/vert highlights."""
    region = context.region
    rv3d = context.region_data
    obj = op.data.obj
    matrix_world = obj.matrix_world
    tr = op.data.transform.translate

    bm = op.data.bm
    bm.verts.ensure_lookup_table()
    bm.faces.ensure_lookup_table()

    # Guide axes anchored at the hitplane origin (stable across the whole
    # modal). The text label rides the moving cutter for visual feedback.
    anchor_world = common.plane_origin_world(op)
    label_world = anchor_world + matrix_world.to_3x3() @ tr.delta
    label_2d = view3d.location_3d_to_region_2d(region, rv3d, label_world, default=op.mouse.co)

    common.render_axis_guides(op, anchor_world)

    # Refresh cutter-face highlight for non-ADD modes.
    if op.config.mode != "ADD":
        face_indices = list(op.data.draw.faces) + list(op.data.extrude.faces)
        faces = [bm.faces[i] for i in face_indices if 0 <= i < len(bm.faces)]
        op.ui.faces.callback.update_batch(faces)

    if op.data.numeric_input.active:
        op.ui.interface.callback.clear()
    else:
        lock = op.data.transform.axis_lock
        exclude = op.data.transform.axis_lock_exclude
        is_2d = not op.is_3d
        all_axes = [(0, "X"), (1, "Y")] if is_2d else [(0, "X"), (1, "Y"), (2, "Z")]
        if lock in {"X", "Y", "Z"}:
            active = [(i, n) for i, n in all_axes if n != lock] if exclude else [(i, n) for i, n in all_axes if n == lock]
        else:
            active = all_axes
        text = tuple(f"D{n.lower()}:{tr.delta[i]:.3f}" for i, n in active)
        lines = [{"point": label_2d, "text_tuple": text}]
        op.ui.interface.callback.update_batch(lines)


def commit(op):
    """Fold the delta into the live draw matrix and pref.plane.origin.

    `DrawMatrix.location` is a read-only property; we write through the
    underlying 4x4 matrix's translation component. pref.plane.origin
    drives F9 rebuilds; the draw-matrix update prevents `store_props`
    from overwriting pref on the next rebuild.
    """
    tr = op.data.transform.translate
    mat = op.data.draw.matrix.mat
    mat.translation = mat.translation + tr.delta
    op.pref.plane.origin = tuple(Vector(op.pref.plane.origin) + tr.delta)
