import bmesh


def extrude(bm, face, plane, dz,):
    """
    Manually extrude the face along the given direction by dz units, creating new geometry
    without using bmesh.ops.extrude_face_region.
    """
    # Get the normal from the plane and normalize it
    _, normal = plane
    normal = normal.normalized()

    face.normal_flip()

    # Get the original vertices of the face in order
    orig_verts = [v for v in face.verts]

    # Create new vertices by duplicating original vertices and moving them along the normal
    new_verts = []
    for v in orig_verts:
        new_co = v.co + normal * dz
        new_v = bm.verts.new(new_co)
        new_verts.append(new_v)

    # Create side faces between original and new vertices
    num_verts = len(orig_verts)
    side_faces = []
    for i in range(num_verts):
        v1 = orig_verts[i]
        v2 = orig_verts[(i + 1) % num_verts]
        v3 = new_verts[(i + 1) % num_verts]
        v4 = new_verts[i]
        # Correct vertex order to ensure normals point outward
        face_verts = [v1, v2, v3, v4]
        side_face = bm.faces.new(face_verts)
        side_face.select_set(True)
        side_faces.append(side_face)

    # Create the top face from the new vertices

    top_face_verts = new_verts
    top_face = bm.faces.new(top_face_verts)
    top_face.select_set(True)

    # Optionally flip the bottom face if needed
    face.normal_flip()

    # Recalculate normals
    bm.normal_update()
    bm.verts.ensure_lookup_table()
    bm.verts.index_update()
    bm.edges.ensure_lookup_table()
    bm.edges.index_update()
    bm.faces.ensure_lookup_table()
    bm.faces.index_update()

    # Return the indices of the new faces
    new_faces = [face.index] + [f.index for f in side_faces] + [top_face.index]
    return new_faces


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
