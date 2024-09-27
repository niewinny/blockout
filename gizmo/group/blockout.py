from dataclasses import dataclass
import bpy
import bmesh
from mathutils import Matrix, Vector, Quaternion
from ..types import move, arrow


@dataclass
class Gizmo:
    '''Dataclass for the gizmo.'''
    extrude: arrow.Draw = None
    translate: move.Draw = None
    bevel: arrow.Draw = None


class BOUT_GGT_Blockout(bpy.types.GizmoGroup):
    bl_idname = 'BOUT_GGT_Blockout'
    bl_label = 'Blockout Gizmo'
    bl_space_type = 'VIEW_3D'
    bl_context_mode = 'EDIT_MESH'
    bl_region_type = 'WINDOW'
    bl_options = {'3D', 'PERSISTENT'}

    def __init__(self):
        self.gizmo = Gizmo()

    @classmethod
    def poll(cls, context):
        active_tool = context.workspace.tools.from_space_view3d_mode(context.mode, create=False)
        blockout_tool = active_tool and active_tool.idname == 'bout.blockout'
        return (context.space_data.show_gizmo_tool and
                context.edit_object and
                blockout_tool)

    def setup(self, context):
        '''Setup the gizmos.'''
        self.gizmos.clear()
        self.create_extrude_gizmo(context)
        self.create_bevel_gizmo(context)
        self.create_translate_gizmo(context)

    def refresh(self, context):
        '''Refresh the gizmos.'''
        modals = context.window.modal_operators
        if any(modal.bl_idname.startswith('MESH') for modal in modals):
            self.remove_gizmos()
            return
        self.update_extrude_gizmo(context)
        self.update_bevel_gizmo(context)
        self.update_translate_gizmo(context)

    def remove_gizmos(self):
        '''Remove all gizmos.'''
        if self.gizmo.extrude:
            self.gizmos.remove(self.gizmo.extrude.gz)
            self.gizmo.extrude = None
        if self.gizmo.bevel:
            self.gizmos.remove(self.gizmo.bevel.gz)
            self.gizmo.bevel = None
        if self.gizmo.translate:
            self.gizmos.remove(self.gizmo.translate.gz)
            self.gizmo.translate = None

    def create_translate_gizmo(self, context):
        matrix = self.compute_translate_gizmo_matrix(context)
        if matrix is not None:
            self.gizmo.translate = move.Draw(self, matrix, (1, 1, 0), 0.5, 0.2, hide_select=False)
            self.gizmo.translate.operator('transform.translate', {
                'release_confirm': True,
            })

    def update_translate_gizmo(self, context):
        '''Update the translate gizmo.'''
        matrix = self.compute_translate_gizmo_matrix(context)
        if matrix is not None:
            if self.gizmo.translate:
                self.gizmo.translate.gz.matrix_basis = matrix
            else:
                self.create_translate_gizmo(context)
        else:
            if self.gizmo.translate:
                self.gizmos.remove(self.gizmo.translate.gz)
                self.gizmo.translate = None

    def create_extrude_gizmo(self, context):
        '''Create the extrude gizmo.'''
        matrix = self.compute_extrude_gizmo_matrix(context)
        if matrix is not None:
            self.gizmo.extrude = arrow.Draw(self, matrix)
            self.gizmo.extrude.operator('mesh.extrude_manifold', {
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
            if self.gizmo.extrude:
                self.gizmo.extrude.gz.matrix_basis = matrix
            else:
                self.create_extrude_gizmo(context)
        else:
            if self.gizmo.extrude:
                self.gizmos.remove(self.gizmo.extrude.gz)
                self.gizmo.extrude = None

    def create_bevel_gizmo(self, context):
        '''Create the bevel gizmo.'''

        matrix = self.compute_bevel_gizmo_matrix(context)
        if matrix is not None:
            self.gizmo.bevel = arrow.Draw(self, matrix)
            self.gizmo.bevel.gz.draw_options = {'ORIGIN'}
            self.gizmo.bevel.gz.length = 0.0
            self.gizmo.bevel.gz.scale_basis = 0.2
            self.gizmo.bevel.gz.draw_style = 'CROSS'
            self.gizmo.bevel.operator('mesh.bevel', {
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
            if self.gizmo.bevel:
                self.gizmo.bevel.gz.matrix_basis = matrix
            else:
                self.create_bevel_gizmo(context)
        else:
            if self.gizmo.bevel:
                self.gizmos.remove(self.gizmo.bevel.gz)
                self.gizmo.bevel = None

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
        quat = avg_normal.to_track_quat('Z', 'Y')  # Adjusted to ensure correct orientation
        rotation_matrix = quat.to_matrix().to_4x4()

        # Extract location, rotation, and scale from the object's transformation matrix
        loc, rot, scale = obj.matrix_world.decompose()

        # Apply the object's scale to the translation part
        scaled_translation = loc + rot @ (face_center * scale)

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
        scaled_translation = loc + rot @ (edge_center * scale)

        # Reconstruct the transformation matrix without scaling the rotation
        rot_matrix = rot.to_matrix().to_4x4()
        world_matrix = Matrix.Translation(scaled_translation) @ rot_matrix @ rotation_matrix

        return world_matrix

    def compute_translate_gizmo_matrix(self, context):
        '''Compute the matrix for the translate gizmo based on the active vertex.'''
        obj = context.edit_object
        me = obj.data
        bm = bmesh.from_edit_mesh(me)

        # Get selected vertices
        selected_verts = [v for v in bm.verts if v.select]
        if not len(selected_verts) == 1:
            return None

        # Get the median of selected verts
        vert_co = sum((v.co for v in selected_verts), Vector()) / len(selected_verts)

        # Compute the world coordinates of the vertex
        world_co = obj.matrix_world @ vert_co

        # Determine the orientation based on normals if needed
        # For a translate gizmo, typically alignment is with global axes
        rotation_matrix = Matrix.Identity(4)

        # Create the transformation matrix
        world_matrix = Matrix.Translation(world_co) @ rotation_matrix

        return world_matrix
