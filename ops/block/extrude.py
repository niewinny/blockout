from mathutils import Vector

from ...utils import view3d
from ...utils.scene import ray_cast
from ...utils.types import DrawVert
from ...utilsbmesh import corner, facet
from . import ui as block_ui
from .data import ExtrudeEdge


def _corner_bevel_jump(op):
    """``True`` when CORNER + cutter mode skips the interactive extrude
    and routes straight to BEVEL (depth is fixed at 0.2 in invoke)."""
    return op.config.shape == "CORNER" and op.config.mode in {"CUT", "CARVE"}

def invoke(op, context, event):
    """Extrude the mesh"""

    op.state.phase = "EXTRUDE"
    op.state.volume = "3D"
    op.shape.volume = "3D"
    op.mouse.extrude = op.mouse.co

    region = context.region
    rv3d = context.region_data

    obj = op.data.obj
    bm = op.data.bm

    draw_faces = [bm.faces[index] for index in op.data.draw.faces]
    draw_face = draw_faces[0]
    plane = op.data.draw.matrix.plane
    normal = op.data.draw.matrix.normal
    direction = op.data.draw.matrix.direction
    rotations = (op.shape.corner.min, op.shape.corner.max)
    offset = op.config.align.offset

    shape = op.config.shape
    skip_modal_setup = _corner_bevel_jump(op)
    match shape:
        case "CORNER":
            op.data.extrude.value = 0.2
            extruded_faces_indexes, mid_edge_index = corner.extrude(
                bm, draw_faces, direction, normal, rotations, op.data.extrude.value
            )
            op.data.extrude.faces = extruded_faces_indexes
            op.data.extrude.edges = [
                ExtrudeEdge(index=mid_edge_index, position="MID")
            ]
            # Bottom offset is the cutter buffer — only meaningful in non-ADD
            # modes. Redo (mesh.py CORNER) reads ``pref.offset`` which is 0
            # in ADD mode, so gate the call here to match.
            if op.config.mode != "ADD":
                corner.offset(
                    bm, extruded_faces_indexes, direction, normal, rotations, offset
                )

            # Skip the snapshot when BEVEL will take over immediately —
            # the depth never changes again, so modal doesn't run.
            if not skip_modal_setup:
                # corner.extrude already places each new vert along its
                # own normal. Snapshot the dz=0 reference (= old_co) and
                # bake the per-vert direction so modal can play it back
                # without recomputing the partition every frame.
                n1, n2, avg, cos_half = corner.normals(direction, normal, rotations)
                top_faces = [bm.faces[fi] for fi in extruded_faces_indexes[-2:]]
                v_dirs = corner.vert_dirs(top_faces, n1, n2, avg, cos_half)
                initial_dz = op.data.extrude.value
                op.data.extrude.verts = [
                    DrawVert(
                        index=vi,
                        co=(bm.verts[vi].co - v_dirs[vi] * initial_dz).copy(),
                        direction=v_dirs[vi].copy(),
                    )
                    for vi in v_dirs
                ]

        case _:
            extruded_faces_indexes = facet.extrude(bm, draw_face, plane, 0.0)

            op.data.extrude.faces = extruded_faces_indexes
            op.data.draw.faces[0] = extruded_faces_indexes[0]
            extrude_face = bm.faces[op.data.extrude.faces[-1]]
            op.data.extrude.verts = [
                DrawVert(index=v.index, co=v.co.copy()) for v in extrude_face.verts
            ]
            draw_face = bm.faces[op.data.draw.faces[0]]
            op.data.draw.verts = [
                DrawVert(index=v.index, co=v.co.copy()) for v in draw_face.verts
            ]

            extrude_edges = [e.index for v in extrude_face.verts for e in v.link_edges]
            extrude_face_edges = [e.index for e in extrude_face.edges]
            extrude_edges = list(set(extrude_edges) - set(extrude_face_edges))

            op.data.extrude.edges = [
                ExtrudeEdge(index=e, position="MID") for e in extrude_edges
            ] + [ExtrudeEdge(index=e, position="END") for e in extrude_face_edges]

    op.update_bmesh(obj, bm, loop_triangles=True, destructive=True)

    # Wipe prior-phase handles; extrude will re-set zaxis below (unless
    # BEVEL is about to take over, which clears + sets its own UI).
    block_ui.clear_phase(op)
    if skip_modal_setup:
        return

    plane_world = (obj.matrix_world @ plane[0], obj.matrix_world.to_3x3() @ plane[1])
    line_origin = view3d.region_2d_to_plane_3d(
        region, rv3d, op.mouse.extrude, plane_world
    )
    op.data.extrude.origin = line_origin
    if shape == "CORNER":
        _, _, avg, _ = corner.normals(direction, normal, rotations)
        axis = obj.matrix_world.to_3x3() @ avg
    else:
        axis = plane_world[1]
    point1 = line_origin
    point2 = line_origin + axis
    op.ui.zaxis.callback.update_batch((point1, point2))

def modal(op, context, event):
    """Set the extrusion based on mouse or numeric input."""
    obj = op.data.obj
    bm = op.data.bm
    ni = op.data.numeric_input

    # Ensure lookup tables are valid after destructive updates
    bm.faces.ensure_lookup_table()
    bm.verts.ensure_lookup_table()

    is_corner = op.config.shape == "CORNER"
    if is_corner:
        # Mouse projects along the avg normal; the per-vert geometry
        # update reads each ``DrawVert.direction`` baked at invoke time.
        _, _, normal, _ = corner.normals(
            op.data.draw.matrix.direction,
            op.data.draw.matrix.normal,
            (op.shape.corner.min, op.shape.corner.max),
        )
    else:
        normal = op.data.draw.matrix.plane[1]

    region = context.region
    rv3d = context.region_data

    # Only calculate from mouse when not in numeric input mode
    if not ni.active:
        matrix_world = obj.matrix_world
        line_origin = op.data.extrude.origin
        line_direction = matrix_world.to_3x3() @ normal

        # Detect the view-parallel degenerate case explicitly. Near (but
        # not exactly) parallel, ``region_2d_to_line_3d`` still returns a
        # huge-magnitude value that skews wildly with tiny mouse motion,
        # so we lock the extrusion to 0 until the user rotates enough
        # out of alignment. ``0.999`` ≈ within 2.6° of parallel.
        view_dir = (rv3d.view_rotation @ Vector((0.0, 0.0, -1.0))).normalized()
        parallel = abs(line_direction.normalized().dot(view_dir)) > 0.999

        if parallel:
            op.data.extrude.value = 0.0
        else:
            _, extrude = view3d.region_2d_to_line_3d(
                region, rv3d, op.mouse.co, line_origin, line_direction
            )
            if extrude is not None:
                increments = op.config.align.increments if op.config.snap else 0.0
                if increments > 0:
                    extrude = round(extrude / increments) * increments
                op.data.extrude.value = extrude

    # Update geometry using current value
    dz = op.data.extrude.value
    increments = op.config.align.increments if op.config.snap else 0.0
    offset = op.config.align.offset if op.config.mode != "ADD" else 0.0

    if is_corner:
        if increments != 0:
            dz = round(dz / increments) * increments
        op.data.extrude.value = dz

        # Direct assignment per vert: ref + (its own baked direction) * dz.
        # face1-only verts get n1, face2-only get n2, shared mid-edge get
        # avg/cos_half — all decided at invoke time and stored on each
        # DrawVert.
        dz_effective = dz
        if offset and dz != 0.0:
            dz_effective = dz + (offset if dz >= 0 else -offset)
        for dv in op.data.extrude.verts:
            bm.verts[dv.index].co = dv.co + dv.direction * dz_effective

        face = bm.faces[op.data.extrude.faces[-1]]
    else:
        face = bm.faces[op.data.extrude.faces[-1]]
        verts = [v.co for v in op.data.extrude.verts]
        dz = facet.set_z(face, normal, dz, verts, snap_value=increments)
        op.data.extrude.value = dz  # Update with snapped value (user-facing)

        # For non-ADD (CUT/SLICE/etc.) extend the extrude face by `offset` in
        # the extrude direction so the final Z span equals |dz| + offset. The
        # draw face stays lifted by +offset (from set_offset) for z-buffer.
        if offset and dz != 0.0:
            dz_effective = dz + (offset if dz >= 0 else -offset)
            facet.set_z(face, normal, dz_effective, verts, snap_value=0.0)

        draw_face = bm.faces[op.data.extrude.faces[0]]
        draw_verts = [v.co for v in op.data.draw.verts]
        if op.data.extrude.symmetry:
            facet.set_z(draw_face, normal, -dz, draw_verts, snap_value=increments)
        else:
            facet.set_z(draw_face, normal, 0, draw_verts)

    bevel_verts = [obj.matrix_world @ v.co.copy() for v in face.verts]
    op.data.bevel.origin = sum(bevel_verts, Vector()) / len(bevel_verts)

    extrude_faces = [bm.faces[index] for index in op.data.extrude.faces]
    op._recalculate_normals(bm, op.data.extrude.faces)

    if op.config.mode != "ADD":
        op.ui.faces.callback.update_batch(extrude_faces)

    normal_global = obj.matrix_world.to_3x3() @ normal
    point_global = op.data.extrude.origin + normal_global * (dz / 2)
    _update_ui(op, region, rv3d, point_global, dz)

    op.update_bmesh(obj, bm, loop_triangles=True, destructive=True)

def _update_ui(op, region, rv3d, point_global, dz):
    """Update extrude UI elements."""

    point_2d = view3d.location_3d_to_region_2d(region, rv3d, point_global)
    lines = [
        {"point": point_2d, "text_tuple": (f"Z: {dz:.3f}",)},
    ]
    op.ui.interface.callback.update_batch(lines)

def uniform(op, context):
    """Finish 2D shapes by extruding them based on raycasting"""

    obj = op.data.obj
    bm = op.data.bm

    # Get the 2D face
    face_index = op.data.draw.faces[0]
    face = bm.faces[face_index]

    # Get face normal and plane
    plane = op.data.draw.matrix.plane
    normal = plane[1].normalized()

    # Transform normal to world space (use rotation part of matrix only)
    world_normal = (obj.matrix_world.to_3x3() @ normal).normalized()

    # Transform vertices to world space
    world_verts = [obj.matrix_world @ v.co for v in face.verts]

    # Calculate center of the face in world space
    face_center = sum(world_verts, Vector()) / len(world_verts)

    # Perform raycasts from opposite side to each vertex
    hit_distances = []
    ray_direction = -world_normal

    for vert_world in world_verts:
        # Start ray from far away in the opposite direction
        ray_origin = vert_world - ray_direction * 100000.0

        # Cast ray toward the vertex using proper object filtering
        ray = ray_cast._ray_cast(
            context, ray_origin, ray_direction, op.objects.selected
        )

        if ray.hit:
            distance = (ray.location - vert_world).length
            hit_distances.append(distance)

    # Calculate median distance for object bounds
    if hit_distances:
        hit_distances.sort()
        median_distance = hit_distances[len(hit_distances) // 2]
    else:
        # Default distance if no hits
        median_distance = 1.0

    # Cast rays from face center AND each vertex to find maximum extrusion distance
    extrusion_candidates = []

    # Cast from face center
    ray_origin = face_center - world_normal * (median_distance + 10.0)
    ray = ray_cast._ray_cast(context, ray_origin, world_normal, op.objects.selected)

    if ray.hit:
        distance = (ray.location - face_center).length
        extrusion_candidates.append(distance)

    # Cast from each vertex
    for vert_world in world_verts:
        ray_origin = vert_world - world_normal * (median_distance + 10.0)
        ray = ray_cast._ray_cast(
            context, ray_origin, world_normal, op.objects.selected
        )

        if ray.hit:
            distance = (ray.location - vert_world).length
            extrusion_candidates.append(distance)

    # Cast from middle of each edge and quarter points
    for edge in face.edges:
        edge_verts_world = [obj.matrix_world @ v.co for v in edge.verts]
        edge_mid = (edge_verts_world[0] + edge_verts_world[1]) / 2.0

        # Cast from edge middle
        ray_origin = edge_mid - world_normal * (median_distance + 10.0)
        ray = ray_cast._ray_cast(
            context, ray_origin, world_normal, op.objects.selected
        )

        if ray.hit:
            distance = (ray.location - edge_mid).length
            extrusion_candidates.append(distance)

        # Cast from midpoint between edge middle and first vertex
        quarter_point_1 = (edge_mid + edge_verts_world[0]) / 2.0
        ray_origin = quarter_point_1 - world_normal * (median_distance + 10.0)
        ray = ray_cast._ray_cast(
            context, ray_origin, world_normal, op.objects.selected
        )

        if ray.hit:
            distance = (ray.location - quarter_point_1).length
            extrusion_candidates.append(distance)

        # Cast from midpoint between edge middle and second vertex
        quarter_point_2 = (edge_mid + edge_verts_world[1]) / 2.0
        ray_origin = quarter_point_2 - world_normal * (median_distance + 10.0)
        ray = ray_cast._ray_cast(
            context, ray_origin, world_normal, op.objects.selected
        )

        if ray.hit:
            distance = (ray.location - quarter_point_2).length
            extrusion_candidates.append(distance)

    # Cast from midpoints between face center and each vertex
    for vert_world in world_verts:
        mid_point = (face_center + vert_world) / 2.0

        ray_origin = mid_point - world_normal * (median_distance + 10.0)
        ray = ray_cast._ray_cast(
            context, ray_origin, world_normal, op.objects.selected
        )

        if ray.hit:
            distance = (ray.location - mid_point).length
            extrusion_candidates.append(distance)

    # Pick the maximum extrusion value. ``depth`` is the target object's
    # dimension along the cut direction (stored into pref.extrusion).
    # ``extrusion_value`` adds ``offset`` on BOTH sides so the cut portion
    # equals ``depth`` exactly with z-fighting buffer hanging past each
    # target surface. Matches ``mesh.build_geometry``'s 2D-cutter logic.
    offset = getattr(op.config.align, "offset", 0.1)
    if extrusion_candidates:
        depth = max(extrusion_candidates)
    else:
        depth = 0.1
    extrusion_value = depth + 2.0 * offset

    # Perform the extrusion
    if extrusion_value > 0:
        # Store current face selection state
        was_selected = face.select

        # Lift the 2D face by +offset (z-fighting buffer) so the extrude
        # direction produces total Z span of depth + offset.
        facet.set_z(face, normal, offset)

        # Extrude the face by the effective magnitude (includes offset).
        extruded_faces = facet.extrude(bm, face, plane, -extrusion_value)

        # Update shape volume to 3D
        op.shape.volume = "3D"
        op.state.volume = "3D"

        # Update extrude data. Store the user-intended depth (without the
        # offset extension) in pref so F9 rebuild via build_geometry
        # applies the offset extension consistently.
        op.data.extrude.value = -depth
        op.data.extrude.faces = extruded_faces

        op.pref.extrusion = -depth

        # Restore selection if needed
        if was_selected:
            for face_idx in extruded_faces:
                bm.faces[face_idx].select_set(True)

        # Update the mesh
        op.update_bmesh(obj, bm, loop_triangles=True, destructive=True)
