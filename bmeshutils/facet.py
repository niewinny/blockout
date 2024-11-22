import bmesh


def extrude(bm, face, plane, dz):
    """
    Extrude the face along the given direction by dz units using bmesh.ops.extrude_face_region.
    Returns the indices of the faces in the following order:
    [index of the starting face (after extrusion), indices of side faces, index of the top face]
    """

    # Get the normal from the plane and normalize it
    _, normal = plane
    normal = normal.normalized()

    print('extrude face', face.index)

    face.normal_flip()
    # Perform the extrusion
    result = bmesh.ops.extrude_face_region(bm, geom=[face])

    # Move the new vertices along the normal by dz units
    new_geom = result['geom']
    new_verts = [elem for elem in new_geom if isinstance(elem, bmesh.types.BMVert)]
    for v in new_verts:
        v.co += normal * dz

    # Recalculate normals
    bm.normal_update()

    # Update indices and lookup tables
    bm.verts.ensure_lookup_table()
    bm.edges.ensure_lookup_table()
    bm.faces.ensure_lookup_table()
    bm.verts.index_update()
    bm.edges.index_update()
    bm.faces.index_update()

    # Identify the top face (the new face created at the extrusion end)
    new_faces = [elem for elem in new_geom if isinstance(elem, bmesh.types.BMFace)]
    if not new_faces:
        raise ValueError("No new faces created during extrusion.")
    top_face = new_faces[0]
    top_face.select_set(True)

    # Identify side faces connected to the top face
    side_faces = []
    for edge in top_face.edges:
        for linked_face in edge.link_faces:
            if linked_face != top_face and linked_face not in side_faces:
                linked_face.select_set(True)
                side_faces.append(linked_face)

    # Identify the bottom face (starting face)
    bot_face = None
    for side_face in side_faces:
        for edge in side_face.edges:
            for linked_face in edge.link_faces:
                if (linked_face != top_face and linked_face != side_face and
                    linked_face not in side_faces):
                    bot_face = linked_face
                    bot_face.select_set(True)
                    break
            if bot_face is not None:
                break
        if bot_face is not None:
            break
    if bot_face is None:
        raise ValueError("Bottom face not found after extrusion.")

    # Collect the indices in the desired order
    new_face_indices = [bot_face.index] + [f.index for f in side_faces] + [top_face.index]
    print('new faces', new_face_indices)

    return new_face_indices


def set_z(face, normal, dz, verts=None, snap_value=0):
    '''
    Set the vertices of the extrusion along the extrusion direction based on the mouse position,
    with an optional snap value for the extrusion distance.
    '''

    # Normalize the direction vector
    normal = normal.normalized()

    # Apply snapping if a snap_value is provided
    if snap_value != 0:
        dz = round(dz / snap_value) * snap_value

    if verts:
        for v, vert_co in zip(face.verts, verts):
            v.co = vert_co + normal * dz
    else:
        for v in face.verts:
            v.co = v.co + normal * dz

    return dz


def bevel(bm, face, bevel_offset=0.0, bevel_segments=1):
    '''Bevel the face region'''

    if bevel_offset != 0.0:
        rectangle_verts = [v for v in face.verts]

        result = bmesh.ops.bevel(bm, geom=rectangle_verts, offset=bevel_offset, profile=0.5, offset_type='OFFSET', affect='VERTICES', clamp_overlap=True, segments=bevel_segments)

        for v in result['verts']:
            v.select = True
        for e in result['edges']:
            e.select = True
        for f in result['faces']:
            f.select = True
        bm.select_flush(True)

        if result['verts']:
            face = result['verts'][0].link_faces[0]

        bm.verts.ensure_lookup_table()
        bm.verts.index_update()
        bm.edges.ensure_lookup_table()
        bm.edges.index_update()
        bm.faces.ensure_lookup_table()
        bm.faces.index_update()

    return face.index
