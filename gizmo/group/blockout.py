import bpy
import bmesh
from mathutils import Matrix, Vector
from ..types import move, arrow


class BOUT_GGT_Blockout(bpy.types.GizmoGroup):
    bl_idname = 'BOUT_GGT_Blockout'
    bl_label = 'Blockout Gizmo'
    bl_space_type = 'VIEW_3D'
    bl_context_mode = 'EDIT_MESH'
    bl_region_type = 'WINDOW'
    bl_options = {'3D', 'EXCLUDE_MODAL'}

    extrude_gizmo: arrow.Draw = None
    bevel_gizmo: arrow.Draw = None

    @classmethod
    def poll(cls, context):
        active_tool = bpy.context.workspace.tools.from_space_view3d_mode(bpy.context.mode, create=False)
        blockout_tool = active_tool and active_tool.idname == 'bout.blockout'
        return context.space_data.show_gizmo_tool and context.edit_object and blockout_tool

    def setup(self, context):
        self.gizmos.clear()
        self.create_extrude_gizmo(context)
        self.create_bevel_gizmo(context)

    def refresh(self, context):
        self.update_extrude_gizmo(context)
        self.update_bevel_gizmo(context)

    def create_extrude_gizmo(self, context):
        '''Create the extrude gizmo.'''

        matrix = self.compute_extrude_gizmo_matrix(context)
        if matrix is not None:
            self.extrude_gizmo = arrow.Draw(self, matrix)
            self.extrude_gizmo.operator('mesh.extrude_manifold', {
                'MESH_OT_extrude_region': {
                    "use_dissolve_ortho_edges": True,
                },
                'TRANSFORM_OT_translate': {
                    "orient_type": 'NORMAL',
                    "constraint_axis": (False, False, True),
                    "release_confirm": True,
                },
            })

    def update_extrude_gizmo(self, context):
        '''Update the extrude gizmo.'''

        matrix = self.compute_extrude_gizmo_matrix(context)
        if matrix is not None:
            if self.extrude_gizmo:
                self.extrude_gizmo.gz.matrix_basis = matrix
            else:
                self.create_extrude_gizmo(context)
        else:
            if self.extrude_gizmo:
                self.gizmos.remove(self.extrude_gizmo.gz)
                self.extrude_gizmo = None

    def create_bevel_gizmo(self, context):
        '''Create the bevel gizmo.'''

        matrix = self.compute_bevel_gizmo_matrix(context)
        if matrix is not None:
            self.bevel_gizmo = arrow.Draw(self, matrix)
            self.bevel_gizmo.gz.draw_options = {'ORIGIN'}
            self.bevel_gizmo.gz.length = 0.0
            self.bevel_gizmo.gz.scale_basis = 0.2
            self.bevel_gizmo.gz.draw_style = 'CROSS'
            self.bevel_gizmo.operator('mesh.bevel', {
                'affect': 'EDGES',
                'offset_type': 'OFFSET',
                'segments': 1,
                'profile': 0.5,
                "release_confirm": True,
            })

    def update_bevel_gizmo(self, context):
        '''Update the bevel gizmo.'''

        matrix = self.compute_bevel_gizmo_matrix(context)
        if matrix is not None:
            if self.bevel_gizmo:
                self.bevel_gizmo.gz.matrix_basis = matrix
            else:
                self.create_bevel_gizmo(context)
        else:
            if self.bevel_gizmo:
                self.gizmos.remove(self.bevel_gizmo.gz)
                self.bevel_gizmo = None

    def compute_extrude_gizmo_matrix(self, context):
        '''Compute the matrix for the extrude gizmo.'''

        obj = context.edit_object
        me = obj.data
        bm = bmesh.from_edit_mesh(me)

        # Get selected faces
        selected_faces = [f for f in bm.faces if f.select]
        if not selected_faces:
            return None

        # Place gizmo on the last selected face
        active_face = bm.select_history.active
        if active_face and isinstance(active_face, bmesh.types.BMFace):
            last_selected_face = active_face
        else:
            last_selected_face = selected_faces[-1]
        face_center = last_selected_face.calc_center_median()

        # Compute the average normal of all selected faces
        avg_normal = Vector((0, 0, 0))
        for face in selected_faces:
            avg_normal += face.normal
        if avg_normal.length == 0:
            return None
        avg_normal.normalize()

        if context.scene.tool_settings.transform_pivot_point == 'ACTIVE_ELEMENT':
            active_face = bm.select_history.active
            if active_face and isinstance(active_face, bmesh.types.BMFace):
                avg_normal = active_face.normal

        # Create a rotation matrix directly from the average normal
        quat = avg_normal.to_track_quat('Z')  # Track the Z axis to the normal
        rotation_matrix = quat.to_matrix().to_4x4()

        # Extract location, rotation, and scale from the object's transformation matrix
        loc, rot, scale = obj.matrix_world.decompose()

        # Apply the object's scale to the translation part
        scaled_translation = loc + rot @ Vector(face_center) * scale

        # Reconstruct the transformation matrix without scaling the rotation
        rot_matrix = rot.to_matrix().to_4x4()
        world_matrix = Matrix.Translation(scaled_translation) @ rot_matrix @ rotation_matrix

        return world_matrix

    def compute_bevel_gizmo_matrix(self, context):
        '''Compute the matrix for the bevel gizmo.'''

        obj = context.edit_object
        me = obj.data
        bm = bmesh.from_edit_mesh(me)

        # Get selected edges
        selected_edges = [e for e in bm.edges if e.select]
        if not selected_edges:
            return None

        # Get the active edge or the last selected edge
        active_edge = bm.select_history.active
        if active_edge and isinstance(active_edge, bmesh.types.BMEdge):
            last_selected_edge = active_edge
        else:
            last_selected_edge = selected_edges[-1]

        edge_center = (last_selected_edge.verts[0].co + last_selected_edge.verts[1].co) / 2
        edge_direction = (last_selected_edge.verts[1].co - last_selected_edge.verts[0].co).normalized()

        # Compute the average normal of the linked faces of the last selected edge
        face_normals = [face.normal for face in last_selected_edge.link_faces]

        if face_normals:
            avg_normal = sum(face_normals, Vector()) / len(face_normals)
        else:
            avg_normal = Vector((0, 0, 0))

        if avg_normal.length == 0:
            avg_normal = Vector((0, 0, 1))

        avg_normal.normalize()

        # Create a matrix to align the gizmo with the edge direction and then rotate it based on the normals
        z_axis = avg_normal
        y_axis = edge_direction.cross(z_axis).normalized()
        x_axis = y_axis.cross(z_axis).normalized()

        rotation_matrix = Matrix((x_axis, y_axis, z_axis)).transposed().to_4x4()

        # Extract location, rotation, and scale from the object's transformation matrix
        loc, rot, scale = obj.matrix_world.decompose()

        # Apply the object's scale to the translation part
        scaled_translation = loc + rot @ Vector(edge_center) * scale

        # Reconstruct the transformation matrix without scaling the rotation
        rot_matrix = rot.to_matrix().to_4x4()
        world_matrix = Matrix.Translation(scaled_translation) @ rot_matrix @ rotation_matrix

        return world_matrix
