def from_index(bm, index):
    bm.edges.ensure_lookup_table()
    edge = bm.edges[index]

    return edge
