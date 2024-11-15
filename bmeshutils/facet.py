import bmesh


def extrude(bm, face, plane, dz):
    '''Extrude the face along the given direction by dz units'''

    # Normalize the direction vector
    _, normal = plane

    # Extrude the face region
    result = bmesh.ops.extrude_face_region(bm, geom=[face])

    # Collect the new geometry
    geom_extruded = result['geom']

    # Get the new vertices and faces
    new_verts = [ele for ele in geom_extruded if isinstance(ele, bmesh.types.BMVert)]
    new_faces = [ele for ele in geom_extruded if isinstance(ele, bmesh.types.BMFace)]

    # Move the new vertices along the direction vector by dz
    move_vector = -normal * dz
    for v in new_verts:
        v.co += move_vector

    # Recalculate normals for the new faces
    bmesh.ops.recalc_face_normals(bm, faces=new_faces)

    # Select the top face if needed
    extruded_face = None
    for f in new_faces:
        if all(v in new_verts for v in f.verts):
            extruded_face = f
            break

    # set of faces linked to new_verts
    connected_faces = []
    for v in new_verts:
        for f in v.link_faces:
            if f == extruded_face:
                continue
            if f in connected_faces:
                continue
            if f not in connected_faces:
                connected_faces.append(f)

    for f in connected_faces:
        f.select_set(True)

    for v in connected_faces[0].verts:
        for f in v.link_faces:
            if f not in connected_faces:
                if f != extruded_face:
                    draw_face = f

    connected_faces_indexes = [f.index for f in connected_faces]

    if extruded_face:
        extruded_face.select_set(True)

    return draw_face.index, extruded_face.index, connected_faces_indexes


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
