import math
from mathutils import Matrix
from ...utils import addon, view3d
from ...utilsbmesh import ngon

def invoke(op, context):
    """Build the mesh data"""

    op.state.phase = "EDIT"
    op.edit_mode = "INIT"
    obj = op.data.obj
    bm = op.data.bm

    plane = op.data.draw.matrix.plane

    if plane is None:
        op.report({"ERROR"}, "Failed to detect drawing plane")
        return False

    op.update_bmesh(obj, bm, loop_triangles=True, destructive=True)
    ngon.history_reset(op)
    return True

def enter_from_converted(op, context):
    """Enter EDIT on a TAB-converted primitive face.

    edit_mode stays NONE (free hover) instead of invoke's INIT auto-grab, so a
    stray click can't immediately finalize.
    """
    obj = op.data.obj
    bm = op.data.bm
    bm.faces.ensure_lookup_table()

    # Winding depends on the drag quadrant; align it to the plane normal.
    plane_normal = op.data.draw.matrix.plane[1]
    op.data.draw.faces[0] = ngon.fix_winding_order(
        bm, op.data.draw.faces[0], plane_normal
    )

    # Primitive creators don't maintain the edge tables ngon.create does;
    # rebuild all three so edge hover + ngon.add_vert don't hit a stale table.
    bm.verts.ensure_lookup_table()
    bm.verts.index_update()
    bm.edges.ensure_lookup_table()
    bm.edges.index_update()
    bm.faces.ensure_lookup_table()
    bm.faces.index_update()

    # draw.verts is empty for primitives; rebuild it from the face.
    ngon.rebuild_vertex_list(op, bm, op.data.draw.faces[0], preserve_first=False)
    ngon.store(op)

    op.state.phase = "EDIT"
    op.edit_mode = "NONE"

    op.update_bmesh(obj, bm, loop_triangles=True, destructive=True)
    ngon.update_ui_after_change(op, bm, obj.matrix_world)
    ngon.history_reset(op)

def modal(op, context, event):
    obj = op.data.obj
    bm = op.data.bm

    region = context.region
    rv3d = context.region_data
    plane = op.data.draw.matrix.plane
    direction = op.data.draw.matrix.direction
    matrix_world = obj.matrix_world
    [bm.faces[i] for i in op.data.draw.faces]
    axis_snap = op.data.draw.axis_snap

    mouse = op.mouse.co

    increments = op.config.align.increments if op.config.snap else 0.0

    verts = [bm.verts[i.index] for i in op.data.draw.verts]

    mouse_point_on_plane = view3d.region_2d_to_plane_3d(
        region, rv3d, op.mouse.co, plane, matrix=matrix_world
    )
    if mouse_point_on_plane is None:
        op.report({"WARNING"}, "Mouse was outside the drawing plane")
        return

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

    mouse_local = matrix_inv @ mouse_point_on_plane
    x1, y1 = mouse_local.x, mouse_local.y

    # Apply snapping if a snap_value is provided
    if increments != 0:
        x1 = round(x1 / increments) * increments
        y1 = round(y1 / increments) * increments

    dx = x1
    dy = y1

    if op.edit_mode == "GET":
        if op.data.draw.faces:
            face = bm.faces[op.data.draw.faces[0]]

            for e in face.edges:
                mid_edge_co = (e.verts[0].co + e.verts[1].co) / 2
                # Transform from object local space to world space for projection
                mid_edge_co_world = matrix_world @ mid_edge_co
                reg = view3d.location_3d_to_region_2d(
                    region, rv3d, mid_edge_co_world, default=obj.location
                )
                if _is_near(region, mouse, reg):
                    op.edit_mode = "ADD_VERT"
                    op.edit_point = e.index
                    op.highlight_type = "EDGE"
                    break

            for v in face.verts:
                # Transform from object local space to world space for projection
                v_co_world = matrix_world @ v.co
                reg = view3d.location_3d_to_region_2d(
                    region, rv3d, v_co_world, default=obj.location
                )
                if _is_near(region, mouse, reg):
                    op.edit_mode = "MOVE"
                    op.edit_point = v.index
                    op.highlight_type = "VERTEX"
                    break

    if op.edit_mode == "GET":
        op.edit_mode = "END"

        return

    if op.edit_mode == "DELETE":
        # Check if we have more than 3 vertices and a valid highlight
        if (
            len(op.data.draw.verts) > 3
            and hasattr(op, "highlight_index")
            and op.highlight_index is not None
        ):
            match op.config.shape:
                case "NGON" | "NHEDRON":
                    # Dissolve the vertex
                    removed_vert, new_face_index = ngon.dissolve_vert(
                        bm, op.highlight_index, op.data.draw.faces[0]
                    )

                    if removed_vert:
                        # Compute preserve_first against the pre-rebuild list,
                        # then resync (reindex, winding, verts, mesh, shaders).
                        # Don't preserve first if it was the deleted vertex.
                        preserve_first = (
                            op.data.draw.verts[0].index != op.highlight_index
                        )
                        ngon.resync_after_topology_change(
                            op, bm, new_face_index, plane[1], preserve_first
                        )

                        # Clear the active highlight, then record the deletion.
                        op.ui.active.callback.update_batch([])
                        ngon.history_commit(op)
                    else:
                        op.report(
                            {"INFO"},
                            "Cannot delete vertex: minimum 3 vertices required",
                        )

        op.edit_mode = "NONE"
        return

    if op.edit_mode == "ADD_VERT":
        match op.config.shape:
            case "NGON":
                verts = ngon.add_vert(bm, op.edit_point)
            case "NHEDRON":
                verts = ngon.add_vert(bm, op.edit_point)

        # Safety check to ensure we have vertices
        if not verts:
            op.report({"ERROR"}, "Failed to add vertex to edge")
            return

        op.edit_point = verts[0].index

        # Rebuild the vertex list from the face to maintain consistency
        # The face may have been recreated with vertices in a different order
        ngon.rebuild_vertex_list(op, bm, op.data.draw.faces[0], preserve_first=True)

        # Record the insertion as its own undo step; the drag that follows
        # commits the new point's final position on release.
        ngon.history_commit(op)

        op.edit_mode = "MOVE"
        op.update_bmesh(obj, bm)

    if op.edit_mode == "INIT":
        # Safety check to ensure we have enough vertices
        if len(op.data.draw.verts) < 2:
            op.report({"ERROR"}, "Insufficient vertices for initialization")
            return

        op.edit_point = op.data.draw.verts[-2].index
        op.edit_mode = "MOVE"

    if op.edit_mode in {"MOVE"}:
        index = next(
            (
                idx
                for idx, vert in enumerate(op.data.draw.verts)
                if vert.index == op.edit_point
            ),
            None,
        )

        # Check if index is valid
        if index is None:
            op.edit_mode = "NONE"
            return

        match op.config.shape:
            case "NGON":
                op.data.draw.verts[index].region, point = ngon.set_xy(
                    bm,
                    op.edit_point,
                    plane,
                    mouse_point_on_plane,
                    direction,
                    snap_value=increments,
                    symmetry=axis_snap,
                )
                # Update the stored position
                op.data.draw.verts[index].co = bm.verts[op.edit_point].co.copy()
            case "NHEDRON":
                op.data.draw.verts[index].region, point = ngon.set_xy(
                    bm,
                    op.edit_point,
                    plane,
                    mouse_point_on_plane,
                    direction,
                    snap_value=increments,
                    symmetry=axis_snap,
                )
                # Update the stored position
                op.data.draw.verts[index].co = bm.verts[op.edit_point].co.copy()

        # After moving vertex, fix winding order if needed
        if op.data.draw.faces and len(op.data.draw.verts) >= 3:
            plane_normal = plane[1]
            new_face_index = ngon.fix_winding_order(
                bm, op.data.draw.faces[0], plane_normal
            )
            if new_face_index != op.data.draw.faces[0]:
                op.data.draw.faces[0] = new_face_index

        op.update_bmesh(obj, bm)
        ngon.store(op)

        match op.config.shape:
            case "NGON" | "NHEDRON":
                ngon.update_ui_after_change(op, bm, matrix_world)

                op.ui.active.callback.update_batch(
                    [matrix_world @ bm.verts[op.edit_point].co.copy()],
                    color=addon.pref().theme.ops.block.active,
                )

                point_x_2d = op.mouse.co.copy()
                point_x_2d.x += 20
                point_y_2d = op.mouse.co.copy()
                point_y_2d.x += 140
                lines = [
                    {"point": point_x_2d, "text_tuple": (f"X: {dx:.3f}",)},
                    {"point": point_y_2d, "text_tuple": (f"Y: {dy:.3f}",)},
                ]
                op.ui.interface.callback.update_batch(lines)

    if op.edit_mode == "NONE":
        op.ui.interface.callback.update_batch([])

        highlight = []
        op.highlight_type = None
        op.highlight_index = None

        if op.data.draw.faces:
            face = bm.faces[op.data.draw.faces[0]]

            for e in face.edges:
                mid_edge_co = (e.verts[0].co + e.verts[1].co) / 2
                # Transform from object local space to world space for projection
                mid_edge_co_world = matrix_world @ mid_edge_co
                reg = view3d.location_3d_to_region_2d(
                    region, rv3d, mid_edge_co_world, default=obj.location
                )
                if _is_near(region, mouse, reg):
                    highlight = [mid_edge_co_world]
                    op.highlight_type = "EDGE"
                    op.highlight_index = e.index
                    break

            for v in face.verts:
                # Transform from object local space to world space for projection
                v_co_world = matrix_world @ v.co
                reg = view3d.location_3d_to_region_2d(
                    region, rv3d, v_co_world, default=obj.location
                )
                if _is_near(region, mouse, reg):
                    highlight = [v_co_world]
                    op.highlight_type = "VERTEX"
                    op.highlight_index = v.index
                    break

            theme = addon.pref().theme.ops.block
            # Edge-midpoint hover is the "add vertex" hint (green); hovering an
            # existing vertex is the move target (yellow, the active color).
            color = theme.add if op.highlight_type == "EDGE" else theme.active
            op.ui.active.callback.update_batch(highlight, color=color)

def _is_near(region, point1, point2):
    """Check if point2 is within 'threshold' pixels of point1."""
    height = region.height
    width = region.width
    threshold = 0.02 * max(width, height)
    dist = math.hypot(point2[0] - point1[0], point2[1] - point1[1])
    return dist < threshold
