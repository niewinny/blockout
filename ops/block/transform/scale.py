"""Scale modify sub-op.

Scales about a pivot (shape centroid or selection median) in the draw
plane's local frame. Axis lock picks one plane axis; 2D free scales in
the plane; 3D free is uniform.
"""

from mathutils import Matrix, Vector

from ....utils import view3d
from .. import ui as block_ui
from . import common


def invoke(op, context, event):
    """Enter scale sub-op: snapshot mouse, pivot, and original coords."""
    block_ui.clear_phase(op)

    bm = op.data.bm
    bm.verts.ensure_lookup_table()

    sc = op.data.transform.scale
    sc.vert_indices = common.vert_indices(op)
    n_verts = len(bm.verts)
    sc.vert_indices = [i for i in sc.vert_indices if 0 <= i < n_verts]
    sc.orig_coords = [bm.verts[i].co.copy() for i in sc.vert_indices]
    pivot = common.pivot_local(op)
    sc.pivot = pivot if pivot is not None else Vector()
    sc.factor = Vector((1.0, 1.0, 1.0))
    sc.factor_stored = Vector((1.0, 1.0, 1.0))
    sc.mouse_invoke = op.mouse.co.copy()
    op.mouse.scale = op.mouse.co
    sc.precision = False

    op.data.transform.active = "SCALE"
    op.state.phase = "SCALE"


def _axis_components(op):
    """Returns (kx, ky, kz) — 1 on plane axes affected by the scale, else 0.

    Blender-style axis lock:
     - X/Y/Z alone → constrain TO that axis (only it scales).
     - Shift+X/Y/Z → exclude that axis (the others scale).
     - No lock → all available axes scale (2D: plane only; 3D: uniform).
    """
    lock = op.data.transform.axis_lock
    exclude = op.data.transform.axis_lock_exclude
    is_2d = op.state.volume == "2D"

    if lock not in {"X", "Y", "Z"}:
        return (1.0, 1.0, 0.0) if is_2d else (1.0, 1.0, 1.0)

    # Z-lock in 2D is rejected upstream, but guard anyway.
    if is_2d and lock == "Z":
        return (1.0, 1.0, 0.0)

    constrain = {"X": (1.0, 0.0, 0.0), "Y": (0.0, 1.0, 0.0), "Z": (0.0, 0.0, 1.0)}[lock]
    if not exclude:
        # Constrain TO: only the chosen axis scales. In 2D Z is unreachable
        # (filtered upstream), so this matches the plane.
        return constrain
    # Exclude: the chosen axis stays fixed, others scale. Drop Z in 2D.
    kx, ky, kz = (1.0 - constrain[0], 1.0 - constrain[1], 1.0 - constrain[2])
    if is_2d:
        kz = 0.0
    return (kx, ky, kz)


def _compute_factor(op, context):
    """Compute uniform scale factor from mouse distance ratio to pivot."""
    region = context.region
    rv3d = context.region_data
    obj = op.data.obj
    sc = op.data.transform.scale

    pivot_world = obj.matrix_world @ sc.pivot
    pivot_2d = view3d.location_3d_to_region_2d(region, rv3d, pivot_world, default=op.mouse.co)

    d0 = (op.mouse.scale - pivot_2d).length
    d1 = (op.mouse.co - pivot_2d).length
    if d0 < 1e-6:
        return 1.0
    return d1 / d0


def modal(op, context, event):
    """Update scale from mouse or numeric input."""
    sc = op.data.transform.scale
    ni = op.data.numeric_input

    if not ni.active:
        if event.shift != sc.precision:
            sc.factor_stored = sc.factor.copy()
            op.mouse.scale = op.mouse.co
            sc.precision = event.shift

        raw = _compute_factor(op, context)
        if event.shift:
            raw = 1.0 + (raw - 1.0) * 0.1

        kx, ky, kz = _axis_components(op)
        base = sc.factor_stored
        fx = base.x * raw if kx > 0.5 else base.x
        fy = base.y * raw if ky > 0.5 else base.y
        fz = base.z * raw if kz > 0.5 else base.z
        factor = Vector((fx, fy, fz))

        if op.config.snap:
            step = 0.01 if event.shift else 0.1
            factor = Vector((
                round(factor.x / step) * step,
                round(factor.y / step) * step,
                round(factor.z / step) * step,
            ))
        sc.factor = factor

    _apply(op)
    _ui(op, context)


def _apply(op):
    """Scale baseline coords about pivot in the plane's basis."""
    bm = op.data.bm
    bm.verts.ensure_lookup_table()
    sc = op.data.transform.scale
    px, py, pz = common.plane_basis(op)

    # Build a matrix that scales by factor components along (px, py, pz),
    # expressed in object-local space via a change-of-basis.
    basis = Matrix((
        (px.x, py.x, pz.x, 0.0),
        (px.y, py.y, pz.y, 0.0),
        (px.z, py.z, pz.z, 0.0),
        (0.0, 0.0, 0.0, 1.0),
    ))
    basis_inv = basis.inverted_safe()
    S = Matrix.Diagonal(Vector((sc.factor.x, sc.factor.y, sc.factor.z, 1.0)))
    local_scale = basis @ S @ basis_inv
    M = Matrix.Translation(sc.pivot) @ local_scale @ Matrix.Translation(-sc.pivot)

    n = len(bm.verts)
    for idx, orig in zip(sc.vert_indices, sc.orig_coords):
        if 0 <= idx < n:
            bm.verts[idx].co = M @ orig

    op.update_bmesh(op.data.obj, bm, loop_triangles=True, destructive=False)


def refresh(op, context):
    """Re-project the full mouse travel under the new scale-axis rule.

    Called on axis-lock toggle. Rewinds the anchor to the invoke-time
    mouse position and clears accumulated precision state, so scaling
    restarts cleanly on the new axis/plane — matching Blender's S
    behavior.
    """
    sc = op.data.transform.scale
    sc.factor_stored = Vector((1.0, 1.0, 1.0))
    op.mouse.scale = sc.mouse_invoke.copy()
    sc.precision = False
    raw = _compute_factor(op, context)
    kx, ky, kz = _axis_components(op)
    sc.factor = Vector((
        raw if kx > 0.5 else 1.0,
        raw if ky > 0.5 else 1.0,
        raw if kz > 0.5 else 1.0,
    ))
    _apply(op)
    _ui(op, context)


def _ui(op, context):
    region = context.region
    rv3d = context.region_data
    obj = op.data.obj
    matrix_world = obj.matrix_world
    sc = op.data.transform.scale

    bm = op.data.bm
    bm.verts.ensure_lookup_table()
    bm.faces.ensure_lookup_table()

    # Scale center stays at the shape centroid (``sc.pivot``) so geometry
    # scales about its own middle. The visible guide axes, however, render
    # through the hitplane origin for a stable, plane-anchored reference.
    pivot_world = matrix_world @ sc.pivot
    pivot_2d = view3d.location_3d_to_region_2d(region, rv3d, pivot_world, default=op.mouse.co)

    common.render_axis_guides(op, common.plane_origin_world(op))

    if op.config.mode != "ADD":
        face_indices = list(op.data.draw.faces) + list(op.data.extrude.faces)
        faces = [bm.faces[i] for i in face_indices if 0 <= i < len(bm.faces)]
        op.ui.faces.callback.update_batch(faces)

    if op.data.numeric_input.active:
        op.ui.interface.callback.clear()
    else:
        lock = op.data.transform.axis_lock
        exclude = op.data.transform.axis_lock_exclude
        is_2d = op.state.volume == "2D"
        all_axes = [(0, "X"), (1, "Y")] if is_2d else [(0, "X"), (1, "Y"), (2, "Z")]
        if lock in {"X", "Y", "Z"}:
            active = [(i, n) for i, n in all_axes if n != lock] if exclude else [(i, n) for i, n in all_axes if n == lock]
        else:
            active = all_axes
        text = tuple(f"S{n.lower()}:{sc.factor[i]:.3f}" for i, n in active)
        lines = [{"point": pivot_2d, "text_tuple": text}]
        op.ui.interface.callback.update_batch(lines)


def commit(op):
    """Persist final scale factor into pref (for redo panel)."""
    sc = op.data.transform.scale
    existing = Vector(op.pref.scale_factor)
    op.pref.scale_factor = (
        existing.x * sc.factor.x,
        existing.y * sc.factor.y,
        existing.z * sc.factor.z,
    )
