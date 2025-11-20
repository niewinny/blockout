import bmesh


def bevel(bm, box_faces, bevel_offset=0.0, bevel_segments=5):
    extrude_faces = [bm.faces[index] for index in box_faces]
    bmesh.ops.recalc_face_normals(bm, faces=extrude_faces)

    if bevel_offset != 0.0:
        box_edges = [e for f in extrude_faces for e in f.edges]
        face = bm.faces[box_faces[0]]
        bevel_edges = set(box_edges) - set(face.edges)
        edges = list(bevel_edges)

        result = bmesh.ops.bevel(
            bm,
            geom=edges,
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
        bm.select_flush(True)

        bm.verts.ensure_lookup_table()
        bm.verts.index_update()
        bm.edges.ensure_lookup_table()
        bm.edges.index_update()
        bm.faces.ensure_lookup_table()
        bm.faces.index_update()
