"""Cursor snapping helpers for the modal align-custom-plane operator.

Given a raycast hit on an evaluated mesh, pick the closest vertex/edge/face under
the cursor and derive a plane (location, normal, in-plane direction) plus the
world-space points used to highlight that element.

The element picking and plane math mirror the non-modal object-mode setter in
``ops/obj/custom_plane.py`` so both share the same behaviour.
"""

from mathutils import Vector

from ...utilsbmesh.orientation import (
    direction_from_normal,
    face_bbox_center,
)


def find_closest_element(context, obj, hit_loc, face_idx, bm):
    """Pick the vertex, edge, or face under the cursor on a raycast hit.

    Uses a viewport-distance dependent threshold so close geometry favours
    verts/edges while distant geometry favours faces.

    :param context: The Blender context.
    :param obj: The hit object (provides ``matrix_world``).
    :param hit_loc: World-space raycast hit location.
    :param face_idx: Face index reported by the raycast.
    :param bm: BMesh of the evaluated hit object (lookup tables ensured).
    :return: Tuple of (element_type, element) where element_type is one of
        ``"VERT"``, ``"EDGE"``, ``"FACE"``. ``element`` may be ``None`` when the
        face index is out of range and no fallback face exists.
    """
    matrix = obj.matrix_world
    inv_matrix = matrix.inverted()
    local_hit = inv_matrix @ hit_loc

    region_data = context.region_data
    if region_data and hasattr(region_data, "view_distance"):
        view_distance = region_data.view_distance
    else:
        view_location = (
            region_data.view_matrix.inverted().translation
            if region_data
            else Vector((0, 0, 10))
        )
        view_distance = (view_location - hit_loc).length

    # Clamp the distance factor so thresholds scale between near/far views.
    distance_factor = min(max(view_distance / 10.0, 0.2), 2.0)
    vert_threshold = 0.05 * distance_factor
    edge_threshold = 0.08 * distance_factor

    # Out-of-range face index (instanced/modified meshes): fall back to the
    # face whose center is nearest the hit point.
    if face_idx >= len(bm.faces) or face_idx < 0:
        closest_face = None
        min_dist = float("inf")
        for face in bm.faces:
            dist = (face.calc_center_median() - local_hit).length
            if dist < min_dist:
                min_dist = dist
                closest_face = face
        if closest_face is None:
            return "FACE", None
        face = closest_face
    else:
        face = bm.faces[face_idx]

    # Closest vertex on the face.
    closest_vert = None
    min_vert_dist = float("inf")
    for vert in face.verts:
        dist = (vert.co - local_hit).length
        if dist < min_vert_dist:
            min_vert_dist = dist
            closest_vert = vert

    # Closest edge on the face (within the segment).
    closest_edge = None
    min_edge_dist = float("inf")
    for edge in face.edges:
        edge_vec = edge.verts[1].co - edge.verts[0].co
        edge_len = edge_vec.length
        if edge_len < 1e-6:
            continue
        edge_dir = edge_vec / edge_len
        proj_len = (local_hit - edge.verts[0].co).dot(edge_dir)
        if 0 <= proj_len <= edge_len:
            proj_point = edge.verts[0].co + edge_dir * proj_len
            dist = (local_hit - proj_point).length
            if dist < min_edge_dist:
                min_edge_dist = dist
                closest_edge = edge

    # Priority by view distance: prefer verts/edges when close, faces when far.
    if view_distance < 5.0:
        if min_vert_dist < vert_threshold * 1.5:
            return "VERT", closest_vert
        if min_edge_dist < edge_threshold * 1.2:
            return "EDGE", closest_edge
    elif view_distance < 15.0:
        if min_vert_dist < vert_threshold:
            return "VERT", closest_vert
        if min_edge_dist < edge_threshold:
            return "EDGE", closest_edge
    else:
        if min_vert_dist < vert_threshold * 0.5:
            return "VERT", closest_vert
        if min_edge_dist < edge_threshold * 0.7:
            return "EDGE", closest_edge

    return "FACE", face


def element_plane(matrix, element_type, element, ray):
    """Derive a plane and highlight points from a picked mesh element.

    :param matrix: World matrix of the element's object.
    :param element_type: ``"VERT"``, ``"EDGE"`` or ``"FACE"``.
    :param element: The BMesh element (or ``None`` for the instanced fallback).
    :param ray: The raycast result (used for the ``None`` face fallback).
    :return: Tuple ``(location, normal, direction, hi_points)`` in world space.
        ``hi_points`` is the list of world coords to highlight the element.
    """
    inv_trans = matrix.inverted().transposed().to_3x3()

    if element_type == "VERT":
        vert = element
        location = matrix @ vert.co
        normal = inv_trans @ vert.normal
        normal.normalize()
        direction = matrix.to_3x3() @ direction_from_normal(vert.normal)
        hi_points = [location]

    elif element_type == "EDGE":
        edge = element
        v0 = matrix @ edge.verts[0].co
        v1 = matrix @ edge.verts[1].co
        location = (v0 + v1) / 2.0
        faces_normals = [inv_trans @ f.normal for f in edge.link_faces]
        sum_normal = sum(faces_normals, Vector())
        direction = v1 - v0
        direction_y = sum_normal.cross(direction)
        normal = direction.cross(direction_y)
        hi_points = [v0, v1]

    else:  # FACE
        face = element
        if face is None:
            # Instanced fallback: use the raw raycast hit data.
            location = ray.location.copy()
            normal = ray.normal.copy()
            direction = direction_from_normal(normal)
            hi_points = []
        else:
            normal = inv_trans @ face.normal
            location = face_bbox_center(face, matrix)
            direction = matrix.to_3x3() @ face.calc_tangent_edge()
            hi_points = [matrix @ loop.vert.co for loop in face.loops]

    normal.normalize()
    direction.normalize()
    return location, normal, direction, hi_points
