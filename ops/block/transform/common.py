"""Shared helpers for translate/rotate/scale sub-ops.

Covers plane-basis / origin accessors, block-vert lookup, pivot
calculation, UI clearing between phases, and guide-axis rendering. Some
helpers (``plane_basis_from_vectors``, ``pivot_from_verts``,
``safe_scale_factor``) are also consumed by ``operator._apply_pref_transforms``
and ``data.Pref._plane_basis`` for the F9 redo path, which runs outside
any modal context.
"""

from mathutils import Vector


def plane_basis_from_vectors(normal, direction):
    """(x, y, z) unit vectors of a draw plane in object-local space.

    Accepts raw normal/direction vectors — safe against degenerate inputs.
    """
    z = normal.normalized() if normal.length > 1e-9 else Vector((0.0, 0.0, 1.0))
    x = direction.normalized() if direction.length > 1e-9 else Vector((1.0, 0.0, 0.0))
    y = z.cross(x).normalized()
    if y.length < 1e-6:
        y = Vector((0.0, 1.0, 0.0))
    # Re-orthogonalize x against z.
    x = y.cross(z).normalized()
    return x, y, z


def plane_basis(op):
    """(x, y, z) unit vectors of the op's draw plane in object-local space.

    Reads the orthonormal basis directly off the draw matrix's 3x3 — the
    hitplane is built with ``DrawMatrix.from_plane`` which already
    orthonormalizes, so re-deriving from normal/direction would be wasted
    work. Sub-ops all reuse this single source of truth.
    """
    mat = op.data.draw.matrix.mat
    x = Vector((mat[0][0], mat[1][0], mat[2][0]))
    y = Vector((mat[0][1], mat[1][1], mat[2][1]))
    z = Vector((mat[0][2], mat[1][2], mat[2][2]))
    return x, y, z


def plane_origin_local(op):
    """Plane origin in object-local space (draw matrix translation)."""
    return op.data.draw.matrix.location


def plane_origin_world(op):
    """Plane origin in world space."""
    return op.data.obj.matrix_world @ op.data.draw.matrix.location


def render_axis_guides(op, anchor_world):
    """Draw colored xaxis/yaxis/zaxis lines through ``anchor_world``.

    Used by translate and scale. Reads ``transform.axis_lock`` /
    ``axis_lock_exclude`` (Blender convention: X alone = constrain TO,
    Shift+X = exclude). Constrain shows the single chosen axis;
    exclude shows the two free axes (defining the constrained plane).
    No lock: 2D always shows the plane X+Y as a visual reference (the
    plane is the constraint); 3D = max freedom = clears all three.
    Handles use the theme's axis colors.
    """
    lock = op.data.transform.axis_lock
    exclude = op.data.transform.axis_lock_exclude
    is_2d = not op.is_3d
    px, py, pz = plane_basis(op)
    rot3 = op.data.obj.matrix_world.to_3x3()

    basis_map = {"X": px, "Y": py, "Z": pz}
    handle_map = {"X": op.ui.xaxis, "Y": op.ui.yaxis, "Z": op.ui.zaxis}
    labels = ["X", "Y"] if is_2d else ["X", "Y", "Z"]

    if lock in labels:
        active = [a for a in labels if a != lock] if exclude else [lock]
    elif is_2d:
        active = labels
    else:
        active = []

    for label in ("X", "Y", "Z"):
        if label in active:
            big = (rot3 @ basis_map[label]) * 10000.0
            handle_map[label].callback.update_batch(
                (anchor_world - big, anchor_world + big)
            )
        else:
            handle_map[label].callback.clear()


def vert_indices(op):
    """Verts of the block's draw + extrude faces (always derived fresh).

    Also seeds from `draw.verts` so NGON/NHEDRON vertices are included
    even if the bmesh face got rebuilt during EDIT and the face-walk
    misses them.
    """
    bm = op.data.bm
    bm.faces.ensure_lookup_table()
    bm.verts.ensure_lookup_table()
    bm.verts.index_update()
    indices = set()
    n_faces = len(bm.faces)
    n_verts = len(bm.verts)
    face_indices = list(op.data.draw.faces) + list(op.data.extrude.faces)
    for fi in face_indices:
        if 0 <= fi < n_faces:
            for v in bm.faces[fi].verts:
                indices.add(v.index)
    for dv in op.data.draw.verts:
        idx = getattr(dv, "index", None)
        if isinstance(idx, int) and 0 <= idx < n_verts:
            indices.add(idx)
    return sorted(indices)


def pivot_local(op):
    """Fresh block centroid, resilient to post-rebuild stale indices.

    Walks draw+extrude face references directly so we never index into
    bm.verts with potentially outdated integers. Falls back to draw.verts
    (for NGON/NHEDRON) when the face walk yields nothing. Returns None
    when no coords are available (caller decides fallback).
    """
    bm = op.data.bm
    bm.faces.ensure_lookup_table()
    bm.verts.ensure_lookup_table()
    n_faces = len(bm.faces)
    n_verts = len(bm.verts)
    cos = []
    seen = set()
    face_indices = list(op.data.draw.faces) + list(op.data.extrude.faces)
    for fi in face_indices:
        if 0 <= fi < n_faces:
            for v in bm.faces[fi].verts:
                key = id(v)
                if key in seen:
                    continue
                seen.add(key)
                cos.append(v.co)
    if not cos:
        for dv in op.data.draw.verts:
            idx = getattr(dv, "index", None)
            if isinstance(idx, int) and 0 <= idx < n_verts:
                cos.append(bm.verts[idx].co)
    if not cos:
        return None
    return sum(cos, Vector()) / len(cos)


def pivot_from_verts(verts):
    """Centroid of the given bmesh verts, or None if empty."""
    if not verts:
        return None
    return sum((v.co for v in verts), Vector()) / len(verts)


SAFE_SCALE_EPS = 1e-6


def safe_scale_factor(factor):
    """Clamp zero components to 1.0 so the scale matrix stays invertible.

    `factor` is a 3-tuple or Vector. Used when re-applying pref.scale_factor
    from the F9 redo panel — a user-typed 0 would otherwise collapse the
    block to a plane.
    """
    return Vector(tuple(
        c if abs(c) >= SAFE_SCALE_EPS else 1.0
        for c in factor
    ))
