import bmesh


def set_copy(obj, all_copies):
    """
    Set the 'copy' of current mesh data.

    :param obj: A Blender object whose 'copy' attribute will be updated.
    :param all_copies: A list of bpy.types.Mesh copies.
    :return: A bpy.types.Mesh copy of 'obj.data'.
    """
    obj.update_from_editmode()
    copy = obj.data.copy()
    all_copies.append(copy)
    return copy


def get_copy(obj, bm, mesh_data=None):
    """
    Get the 'copy' of existing BMesh.

    :param obj: A Blender object whose mesh data is ultimately updated.
    :param bm:  A bmesh.BMesh which already holds some geometry,
                and into which 'mesh_data' will be appended.
    :param mesh_data: A bpy.types.Mesh (or mesh-like data) to merge. If None, do nothing.
    """
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


def merge_copy(obj, bm, mesh_data=None):
    """
    Merge geometry from 'mesh_data' into the existing BMesh 'bm' on 'obj',
    using 'bm.from_mesh(...)' multiple times rather than bmesh.ops.duplicate.

    :param obj: A Blender object whose mesh data is ultimately updated.
    :param bm:  A bmesh.BMesh which already holds some geometry,
                and into which 'mesh_data' will be appended.
    :param mesh_data: A bpy.types.Mesh (or mesh-like data) to merge. If None, do nothing.
    """
    if not mesh_data:
        return

    bm.from_mesh(mesh_data, face_normals=True, vertex_normals=True, use_shape_key=False, shape_key_index=0)

    bm.verts.ensure_lookup_table()
    bm.verts.index_update()
    bm.edges.ensure_lookup_table()
    bm.edges.index_update()
    bm.faces.ensure_lookup_table()
    bm.faces.index_update()


def remove_doubles(bm, verts_indicies):
    """
    Remove doubles from the BMesh 'bm' using the indices of the vertices to check.

    :param bm: A bmesh.BMesh.
    :param verts_indicies: A list of vertex indices to check for doubles.
    """

    verts = [bm.verts[i] for i in verts_indicies]
    bmesh.ops.remove_doubles(bm, verts=verts, dist=0.0001)
    bm.select_flush(True)
    bm.verts.ensure_lookup_table()
    bm.verts.index_update()
    bm.edges.ensure_lookup_table()
    bm.edges.index_update()
    bm.faces.ensure_lookup_table()
    bm.faces.index_update()

