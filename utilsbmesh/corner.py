import bmesh
from mathutils import Matrix, Vector
from . import bmeshface


def create(bm, plane):
    """Create a corner shape with two connected faces"""
    location, normal = plane

    # Create 6 vertices at the initial location
    v1 = bm.verts.new(location)
    v2 = bm.verts.new(location)
    v3 = bm.verts.new(location)
    v4 = bm.verts.new(location)
    v5 = bm.verts.new(location)
    v6 = bm.verts.new(location)

    bm.verts.ensure_lookup_table()
    bm.verts.index_update()

    # Create two connected faces
    face1 = bm.faces.new((v1, v2, v3, v4))
    face2 = bm.faces.new((v6, v5, v4, v3))

    face1.normal = normal
    face1.select_set(True)
    face2.select_set(True)
    bm.select_flush(True)

    bm.faces.ensure_lookup_table()
    bm.faces.index_update()

    return [face1.index, face2.index]


def set_xy(faces, plane, loc, direction, rotations, local_space=False, snap_value=0):
    """
    Configure the corner shape. The `loc` parameter is always provided.
    If `local_space` is True, `loc` is given in the plane's local coordinate system.
    If `local_space` is False, `loc` is given in global coordinate system and will be transformed.
    The corner parameter defines the normal of the second plane.
    """
    # Get the two faces from the faces list
    face1 = faces[0]
    face2 = faces[1]

    rot_min, rot_max = rotations

    # Unpack plane data
    location, normal = plane

    # Unpack face vertices
    v0, v1, v2, v3 = face1.verts
    v4, v5, _, _ = face2.verts  # v3b should be the same as v3

    # Build coordinate systems for the two planes
    # First plane: uses plane normal and direction
    x_axis = direction.normalized()
    y_axis = normal.cross(x_axis).normalized()

    # Create normal vectors based on rotations
    # Use the initial plane normal as the base
    normal_base = normal.copy()

    # Create rotation matrices around the direction vector for both min and max rotations
    rot_matrix_min = Matrix.Rotation(rot_min, 4, direction)
    rot_matrix_max = Matrix.Rotation(rot_max, 4, direction)

    # Rotate the base normal to get normals for both planes
    normal1 = rot_matrix_min @ normal_base  # First plane uses min rotation
    normal2 = rot_matrix_max @ normal_base  # Second plane uses max rotation

    # First plane coordinate system
    x_axis = direction.normalized()
    y_axis = normal1.cross(x_axis).normalized()

    # Build transformation matrices
    # First plane matrix
    rotation_matrix = Matrix((x_axis, y_axis, normal1)).transposed()
    matrix = rotation_matrix.to_4x4()
    matrix.translation = location
    matrix_inv = matrix.inverted_safe()

    # Second plane coordinate system
    x_axis2 = direction.normalized()  # Same direction for both planes
    y_axis2 = normal2.cross(x_axis2).normalized()

    # Second plane matrix
    rotation_matrix2 = Matrix((x_axis2, y_axis2, normal2)).transposed()
    matrix2 = rotation_matrix2.to_4x4()
    matrix2.translation = location

    # Calculate position in local space
    if local_space:
        x1, y1 = loc.x, loc.y
    else:
        mouse_local = matrix_inv @ loc
        x1, y1 = mouse_local.x, mouse_local.y

    # Apply snapping if a snap_value is provided
    if snap_value != 0:
        x1 = round(x1 / snap_value) * snap_value
        y1 = round(y1 / snap_value) * snap_value

    # Set up the corners with the symmetry line
    x0, y0 = 0, 0

    dx = x1 - x0
    dy = y1 - y0

    # normal2 and y_axis2 are now calculated once before entering the quadrant logic

    # Always keep the winding order the same, but move the correct corner
    if x1 >= 0 and y1 >= 0:  # Quadrant I: v0 is moving
        v0.co = matrix @ Vector((x1, y1, 0))
        v1.co = matrix @ Vector((-x1, y1, 0))
        v2.co = matrix @ Vector((-x1, y0, 0))
        v3.co = matrix @ Vector((x1, y0, 0))
        v4.co = v2.co - y_axis2 * dy
        v5.co = v3.co - y_axis2 * dy
    elif x1 < 0 and y1 >= 0:  # Quadrant II: v1 is moving
        v0.co = matrix @ Vector((-x1, y1, 0))
        v1.co = matrix @ Vector((x1, y1, 0))
        v2.co = matrix @ Vector((x1, y0, 0))
        v3.co = matrix @ Vector((-x1, y0, 0))
        v4.co = v2.co - y_axis2 * dy
        v5.co = v3.co - y_axis2 * dy
    elif x1 < 0 and y1 < 0:  # Quadrant III: v4 is moving
        v0.co = matrix @ Vector((-x1, -y1, 0))
        v1.co = matrix @ Vector((x1, -y1, 0))
        v2.co = matrix @ Vector((x1, y0, 0))
        v3.co = matrix @ Vector((-x1, y0, 0))
        v4.co = v2.co + y_axis2 * dy
        v5.co = v3.co + y_axis2 * dy
    else:  # Quadrant IV: v5 is moving
        v0.co = matrix @ Vector((x1, -y1, 0))
        v1.co = matrix @ Vector((-x1, -y1, 0))
        v2.co = matrix @ Vector((-x1, y0, 0))
        v3.co = matrix @ Vector((x1, y0, 0))
        v4.co = v2.co + y_axis2 * dy
        v5.co = v3.co + y_axis2 * dy

    # Compute the 3D point for return value
    point_local = Vector((x1, abs(y1), 0))
    point_3d = matrix @ point_local

    # Calculate dx, dy for return
    dx = x1 - x0
    dy = y1 - y0

    return (dx, dy), point_3d


def extrude(bm, faces, direction, base_normal, rotations, dz):
    """Extrude the corner shape by manually creating faces instead of using extrude_face_region.

    Args:
        bm: The BMesh object
        faces: List of BMFace objects to extrude
        direction: Direction vector for the rotation axis
        base_normal: Base normal vector (0 degrees rotation)
        rotations: Tuple of (min_rotation, max_rotation) in radians
        dz: Distance to extrude along the normals
    Returns:
        Tuple of (ordered_faces, mid_edge): List of face indices in the order [old_faces, mid_faces, new_faces] and mid edge index
    """
    # Initialize variables
    old_faces = []
    mid_faces = []
    new_faces = []
    mid_edge = None

    # Generate normals from base_normal and rotations
    rot_min, rot_max = rotations
    rot_matrix_min = Matrix.Rotation(rot_min, 4, direction)
    rot_matrix_max = Matrix.Rotation(rot_max, 4, direction)

    normal1 = rot_matrix_min @ base_normal
    normal2 = rot_matrix_max @ base_normal

    # Calculate average normal for the extrusion
    normal = (normal1 + normal2) / 2
    normal.normalize()

    # Ensure all lookup tables are updated
    bm.verts.ensure_lookup_table()
    bm.edges.ensure_lookup_table()
    bm.faces.ensure_lookup_table()

    for face in faces:
        face.normal_flip()

    old_faces = [f.index for f in faces]

    # Store old vertices and create new vertices (copied and offset)
    new_verts_map = {}  # Maps old vertex index to new vertex
    edge_map = {}  # Maps (v1_idx, v2_idx) pairs to new edge

    # First create all new vertices by copying and offsetting
    for face in faces:
        for v in face.verts:
            if v.index not in new_verts_map:
                # Create a new vertex at an offset position
                new_vert = bm.verts.new(v.co + normal * dz)
                new_verts_map[v.index] = new_vert

    # Update tables after creating new vertices
    bm.verts.ensure_lookup_table()
    bm.verts.index_update()

    # Find the shared edge between the two faces (if there are at least two faces)
    shared_edges = set()
    if len(faces) >= 2:
        # Get all edges from the first face
        face1_edges = set(faces[0].edges)
        # Find edges that are also in the second face
        for edge in faces[1].edges:
            if edge in face1_edges:
                shared_edges.add(edge)

    # Create side faces (mid faces) connecting old and new vertices, but skip shared edges
    for face in faces:
        # For each edge in the face
        for edge in face.edges:
            # Skip the edge if it's a shared edge (the middle edge)
            if edge in shared_edges:
                continue

            v1, v2 = edge.verts
            new_v1 = new_verts_map[v1.index]
            new_v2 = new_verts_map[v2.index]

            # Create a face connecting old and new vertices
            # Order is important for correct normal
            edge_key = tuple(sorted([v1.index, v2.index]))
            if edge_key not in edge_map:
                new_face = bm.faces.new([v1, v2, new_v2, new_v1])
                new_face.select = True
                mid_faces.append(new_face.index)
                edge_map[edge_key] = True

    # Create top faces (equivalent to the extruded faces)
    for face in faces:
        # Get vertices in the correct order
        old_verts = [v for v in face.verts]
        # Create new face with new vertices in the same order
        new_verts = [new_verts_map[v.index] for v in old_verts]
        # Reverse order for correct normal direction
        new_verts.reverse()

        new_face = bm.faces.new(new_verts)
        new_face.select = True
        new_faces.append(new_face.index)

    # Update all indices and ensure lookup tables
    bm.normal_update()
    bm.verts.ensure_lookup_table()
    bm.edges.ensure_lookup_table()
    bm.faces.ensure_lookup_table()
    bm.verts.index_update()
    bm.edges.index_update()
    bm.faces.index_update()

    # Find the mid edge (edge shared by both original faces)
    for e in faces[0].edges:
        if e in faces[1].edges:
            mid_edge = e.index
            break

    # Combine all faces in the order: old_faces + mid_faces + new_faces
    ordered_faces = old_faces + mid_faces + new_faces

    return ordered_faces, mid_edge


def offset(bm, faces_indexes, direction, base_normal, rotations, dz):
    """
    Offset each face along its corresponding normal by dz.
    Args:
        bm: The BMesh object
        faces_indexes: List of face indices to offset
        direction: Direction vector for the rotation axis
        base_normal: Base normal vector (0 degrees rotation)
        rotations: Tuple of (min_rotation, max_rotation) in radians
        dz: Distance to offset along the normals
    Returns:
        None
    """
    # Generate normals from base_normal and rotations
    rot_min, rot_max = rotations
    rot_matrix_min = Matrix.Rotation(rot_min, 4, direction)
    rot_matrix_max = Matrix.Rotation(rot_max, 4, direction)

    normal1 = rot_matrix_min @ base_normal
    normal2 = rot_matrix_max @ base_normal

    offset_faces_indexes = [faces_indexes[0], faces_indexes[1]]
    faces = [bmeshface.from_index(bm, index) for index in offset_faces_indexes]
    normals = [normal1, normal2]

    for face, normal in zip(faces, normals):
        for v in face.verts:
            v.co += normal * dz


def bevel(bm, edge, bevel_offset=0.0, bevel_segments=1):
    """Bevel the edges"""

    if bevel_offset != 0.0:
        result = bmesh.ops.bevel(
            bm,
            geom=[edge],
            offset=bevel_offset,
            profile=0.5,
            offset_type="OFFSET",
            affect="EDGES",
            clamp_overlap=True,
            segments=bevel_segments,
        )

        for v in result["verts"]:
            v.select = True
        for e in result["edges"]:
            e.select = True
        for f in result["faces"]:
            f.select = True

        # expand selection to all connected faces
        initial_faces = set(result["faces"])
        all_connected_faces = set(initial_faces)
        queue = list(initial_faces)

        while queue:
            f = queue.pop()
            for e in f.edges:
                for linked_face in e.link_faces:
                    if linked_face not in all_connected_faces:
                        all_connected_faces.add(linked_face)
                        queue.append(linked_face)

        for f in all_connected_faces:
            f.select = True
        bm.select_flush(True)

        bm.verts.ensure_lookup_table()
        bm.verts.index_update()
        bm.edges.ensure_lookup_table()
        bm.edges.index_update()
        bm.faces.ensure_lookup_table()
        bm.faces.index_update()

        return [v.index for v in result["verts"]]

    return []
