import bmesh


def set_copy(obj):
    obj.update_from_editmode()
    return obj.data.copy()


def get_copy(obj, bm, mesh_data=None):
    bm.clear()

    mesh = obj.data
    bm.normal_update()
    bmesh.update_edit_mesh(mesh, loop_triangles=True, destructive=True)
    bm.from_mesh(mesh_data)
    bmesh.update_edit_mesh(mesh, loop_triangles=True, destructive=True)

    bm.verts.ensure_lookup_table()
    bm.verts.index_update()
    bm.edges.ensure_lookup_table()
    bm.edges.index_update()
    bm.faces.ensure_lookup_table()
    bm.faces.index_update()
