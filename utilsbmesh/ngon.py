import bmesh
from ..utils.types import DrawVert
from mathutils import Matrix, Vector


def create(bm, plane):
    """Create a ngon face"""

    location, normal = plane
    v1 = bm.verts.new(location)
    v2 = bm.verts.new(location)
    v3 = bm.verts.new(location)

    bm.edges.new((v1, v2))
    bm.edges.new((v2, v3))
    bm.edges.new((v3, v1))

    face = bm.faces.new((v1, v2, v3))
    face_index = face.index
    face.normal = normal
    face.select_set(True)

    bm.verts.ensure_lookup_table()
    bm.verts.index_update()
    bm.edges.ensure_lookup_table()
    bm.edges.index_update()
    bm.faces.ensure_lookup_table()
    bm.faces.index_update()

    bm.select_flush(True)

    return [face_index], [
        DrawVert(index=v1.index, co=v1.co),
        DrawVert(index=v2.index, co=v2.co),
        DrawVert(index=v3.index, co=v3.co),
    ]


def set_xy(
    bm,
    vert_index,
    plane,
    loc,
    direction,
    local_space=False,
    snap_value=0,
    symmetry=(False, False),
):
    """
    Move a single ngon vertex to the given xy location in the plane's local coordinate system.
    Updates vert.co and returns (dx, dy), point_3d.
    """

    vert = bm.verts[vert_index]

    symx, symy = symmetry

    # Unpack plane data
    location, normal = plane

    # Build consistent x and y axes for the plane's local coordinate system
    x_axis = direction.normalized()
    y_axis = normal.cross(x_axis).normalized()

    # Build the transformation matrix from plane local space to object local space
    rotation_matrix = Matrix((x_axis, y_axis, normal)).transposed()
    matrix = rotation_matrix.to_4x4()
    matrix.translation = location

    # Build the inverse matrix from object local space to plane local space
    matrix_inv = matrix.inverted_safe()

    # In plane local space, the initial point is at the origin
    if local_space:
        x1, y1 = loc.x, loc.y
    else:
        mouse_local = matrix_inv @ loc
        x1, y1 = mouse_local.x, mouse_local.y

    # Apply snapping if a snap_value is provided
    if snap_value != 0:
        x1 = round(x1 / snap_value) * snap_value
        y1 = round(y1 / snap_value) * snap_value

    x0 = -x1 if symy else 0
    y0 = -y1 if symx else 0

    dx = x1 - x0
    dy = y1 - y0

    # Update the vertex position in 3D
    point_local = Vector((x1, y1, 0))
    point_3d = matrix @ point_local
    vert.co = point_3d

    # Return dx, dy (2D location), and point_3d (3D point)
    if symx:
        dy = dy / 2
    if symy:
        dx = dx / 2

    return (dx, dy), point_3d


def add_vert(bm, index):
    """Add a vertex to the ngon"""

    edge = bm.edges[index]
    result = bmesh.ops.bisect_edges(bm, edges=[edge], cuts=1)

    bm.verts.ensure_lookup_table()
    bm.verts.index_update()
    bm.edges.ensure_lookup_table()
    bm.edges.index_update()
    bm.faces.ensure_lookup_table()
    bm.faces.index_update()

    verts = [v for v in result["geom_split"] if isinstance(v, bmesh.types.BMVert)]

    # Check if any vertices were created
    if not verts:
        # Fallback: split the edge manually
        v1, v2 = edge.verts
        midpoint = (v1.co + v2.co) / 2

        # Create new vertex at midpoint
        new_vert = bm.verts.new(midpoint)

        # Split the edge by creating two new edges and removing the old one
        bm.edges.new([v1, new_vert])
        bm.edges.new([new_vert, v2])

        # Update any faces that used the old edge
        for face in list(edge.link_faces):
            face_verts = list(face.verts)

            # Find where to insert the new vertex in the face
            for i, vert in enumerate(face_verts):
                next_vert = face_verts[(i + 1) % len(face_verts)]
                if (vert == v1 and next_vert == v2) or (vert == v2 and next_vert == v1):
                    # Insert new vertex between these two
                    if vert == v1:
                        face_verts.insert(i + 1, new_vert)
                    else:
                        face_verts.insert(i + 1, new_vert)
                    break

            # Remove old face and create new one
            bm.faces.remove(face)
            new_face = bm.faces.new(face_verts)
            new_face.select_set(True)

        # Remove the old edge
        bm.edges.remove(edge)

        # Update lookup tables
        bm.verts.ensure_lookup_table()
        bm.verts.index_update()
        bm.edges.ensure_lookup_table()
        bm.edges.index_update()
        bm.faces.ensure_lookup_table()
        bm.faces.index_update()

        verts = [new_vert]

    return verts


def new(bm, verts_list):
    """Create a ngon face"""

    verts = []
    for v in verts_list:
        vert = bm.verts.new(v.co)
        verts.append(vert)

    face = bm.faces.new(verts)
    face.select_set(True)

    bm.select_flush(True)

    return face


def fix_winding_order(bm, face_index, plane_normal):
    """Fix the winding order of a face to match the plane normal"""

    face = bm.faces[face_index]
    face_verts = list(face.verts)

    # Need at least 3 vertices to determine winding
    if len(face_verts) < 3:
        return face_index

    # Calculate current face normal based on first 3 vertices
    v0, v1, v2 = face_verts[0].co, face_verts[1].co, face_verts[2].co
    edge1 = v1 - v0
    edge2 = v2 - v0
    current_normal = edge1.cross(edge2).normalized()

    # Check if it matches plane normal
    if current_normal.dot(plane_normal) < 0:
        # Reverse the vertex order to fix the winding
        face_verts.reverse()
        bm.faces.remove(face)
        new_face = bm.faces.new(face_verts)
        new_face.select_set(True)
        bm.faces.ensure_lookup_table()
        return new_face.index

    return face_index


def dissolve_vert(bm, vert_index, face_index):
    """Dissolve a vertex from an n-gon face"""

    face = bm.faces[face_index]
    face_verts = list(face.verts)

    # Need at least 4 vertices to dissolve one (maintain triangle)
    if len(face_verts) <= 3:
        return None, face_index

    # Find the vertex to dissolve
    vert_to_remove = bm.verts[vert_index]
    if vert_to_remove not in face_verts:
        return None, face_index

    # Remove the vertex from the face
    face_verts.remove(vert_to_remove)

    # Delete the old face
    bm.faces.remove(face)

    # Create new face without the dissolved vertex
    new_face = bm.faces.new(face_verts)
    new_face.select_set(True)

    # Clean up the vertex if it has no more connections
    if len(vert_to_remove.link_faces) == 0:
        bm.verts.remove(vert_to_remove)

    # Update lookup tables
    bm.verts.ensure_lookup_table()
    bm.verts.index_update()
    bm.edges.ensure_lookup_table()
    bm.edges.index_update()
    bm.faces.ensure_lookup_table()
    bm.faces.index_update()

    return vert_to_remove, new_face.index


def store(self):
    """Store the ngon face to the active shape's ``points`` collection."""

    sd = self.shape.data
    if sd is None or not hasattr(sd, "points"):
        return
    sd.points.clear()
    if self.data.draw.faces:
        face = self.data.bm.faces[self.data.draw.faces[0]]
        for v in face.verts:
            ngon_item = sd.points.add()
            ngon_item.co = v.co


def rebuild_vertex_list(op, bm, face_index, preserve_first=True):
    """
    Rebuild the draw vertex list from the face, preserving the drawing vertex position.

    Args:
        bm: The BMesh object
        face_index: The face index to rebuild from
        preserve_first: If True, keep the first vertex as the first vertex if it still exists

    Returns:
        None (updates op.data.draw.verts in place)
    """
    face = bm.faces[face_index]

    # Store the current drawing vertex (first vertex) if we need to preserve it
    drawing_vert_index = None
    if preserve_first and len(op.data.draw.verts) > 0:
        drawing_vert_index = op.data.draw.verts[0].index

    # Build new vertex list
    new_draw_verts = []
    drawing_vert = None

    # First pass: find all vertices and identify the drawing vertex
    for v in face.verts:
        draw_vert = DrawVert(index=v.index, co=v.co.copy())
        if v.index == drawing_vert_index:
            drawing_vert = draw_vert
        else:
            new_draw_verts.append(draw_vert)

    # Reconstruct list with drawing vertex first (if it exists and we're preserving)
    if drawing_vert and preserve_first:
        op.data.draw.verts = [drawing_vert] + new_draw_verts
    else:
        # Just use face vertex order
        op.data.draw.verts = []
        for v in face.verts:
            op.data.draw.verts.append(DrawVert(index=v.index, co=v.co.copy()))


def update_ui_after_change(op, bm, matrix_world):
    """Update the UI/shader after vertex changes."""
    faces = [bm.faces[i] for i in op.data.draw.faces]
    points_global = []
    for p in op.data.draw.verts:
        point = bm.verts[p.index].co
        points_global.append(matrix_world @ point)

    op.ui.vert.callback.update_batch(points_global)
    if op.config.mode != "ADD":
        op.ui.faces.callback.update_batch(faces)


def resync_after_topology_change(op, bm, face_index, plane_normal, preserve_first):
    """Shared tail after a face-rebuilding edit (delete / undo-redo restore).

    Reindex the bmesh, fix winding to the plane normal, rebuild the draw vert
    list, push the bmesh to the mesh, persist points, and refresh the shaders.
    Returns the (possibly new) face index after winding correction.
    """
    bm.verts.ensure_lookup_table()
    bm.verts.index_update()
    bm.edges.ensure_lookup_table()
    bm.edges.index_update()
    bm.faces.ensure_lookup_table()
    bm.faces.index_update()

    face_index = fix_winding_order(bm, face_index, plane_normal)
    op.data.draw.faces[0] = face_index

    rebuild_vertex_list(op, bm, face_index, preserve_first=preserve_first)

    op.update_bmesh(op.data.obj, bm)
    store(op)
    update_ui_after_change(op, bm, op.data.obj.matrix_world)
    return face_index


# ---------------------------------------------------------------------------
# In-modal undo/redo for NGON/NHEDRON point editing.
#
# A history state is an ordered snapshot of the editable face's vertex
# coordinates (object-local, plain tuples). Undo/redo rebuilds the face from a
# stored snapshot using the same delete-face + recreate-face pattern the rest of
# the edit code relies on. History lives on ``op.data.edit_history`` and is
# scoped to the EDIT phase of a single operator invocation.
# ---------------------------------------------------------------------------

_HISTORY_EPS = 1e-6


def _snapshot(op):
    """Ordered coords of the editable face's verts, as plain tuples."""
    bm = op.data.bm
    face = bm.faces[op.data.draw.faces[0]]
    return tuple(tuple(v.co) for v in face.verts)


def _coords_equal(a, b):
    """True when two snapshots match in length and per-component (epsilon)."""
    if len(a) != len(b):
        return False
    for pa, pb in zip(a, b):
        if (
            abs(pa[0] - pb[0]) > _HISTORY_EPS
            or abs(pa[1] - pb[1]) > _HISTORY_EPS
            or abs(pa[2] - pb[2]) > _HISTORY_EPS
        ):
            return False
    return True


def history_reset(op):
    """Seed the undo history with the current face as the baseline state."""
    eh = op.data.edit_history
    if not op.data.draw.faces:
        eh.states = []
        eh.index = -1
        return
    eh.states = [_snapshot(op)]
    eh.index = 0


def history_commit(op):
    """Record the current face state as a new undo step (no-op if unchanged)."""
    if not op.data.draw.faces:
        return
    eh = op.data.edit_history
    snap = _snapshot(op)
    if (
        eh.states
        and 0 <= eh.index < len(eh.states)
        and _coords_equal(eh.states[eh.index], snap)
    ):
        return
    # Drop any redo tail, then append the new state.
    del eh.states[eh.index + 1 :]
    eh.states.append(snap)
    if len(eh.states) > eh.max_depth:
        eh.states.pop(0)
    eh.index = len(eh.states) - 1


def undo(op, context):
    """Step back one history state and rebuild the face."""
    eh = op.data.edit_history
    if eh.index <= 0:
        op.report({"INFO"}, "Nothing to undo")
        return
    eh.index -= 1
    _restore(op, context, eh.states[eh.index])


def redo(op, context):
    """Step forward one history state and rebuild the face."""
    eh = op.data.edit_history
    if eh.index >= len(eh.states) - 1:
        op.report({"INFO"}, "Nothing to redo")
        return
    eh.index += 1
    _restore(op, context, eh.states[eh.index])


def _restore(op, context, coords):
    """Rebuild the editable face from a stored coordinate snapshot."""
    bm = op.data.bm

    # Tear down the current isolated face and its now-orphaned verts.
    if op.data.draw.faces:
        face = bm.faces[op.data.draw.faces[0]]
        old_verts = list(face.verts)
        bm.faces.remove(face)
        for v in old_verts:
            if not v.link_faces:
                bm.verts.remove(v)

    # Recreate the polygon from the snapshot, then reindex before reading index.
    new_verts = [bm.verts.new(Vector(c)) for c in coords]
    new_face = bm.faces.new(new_verts)
    new_face.select_set(True)

    bm.verts.ensure_lookup_table()
    bm.verts.index_update()
    bm.edges.ensure_lookup_table()
    bm.edges.index_update()
    bm.faces.ensure_lookup_table()
    bm.faces.index_update()

    op.data.draw.faces[0] = new_face.index
    plane_normal = op.data.draw.matrix.plane[1]
    resync_after_topology_change(
        op, bm, new_face.index, plane_normal, preserve_first=False
    )

    # Land back in idle hover; clear dangling interaction state.
    op.edit_mode = "NONE"
    op.highlight_type = None
    op.highlight_index = None
    op.edit_point = None
    op.ui.active.callback.update_batch([])
    op.ui.interface.callback.update_batch([])
