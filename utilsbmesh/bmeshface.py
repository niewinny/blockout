def from_index(bm, index):
    bm.faces.ensure_lookup_table()
    face = bm.faces[index]

    return face
