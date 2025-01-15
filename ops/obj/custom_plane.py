import bpy
import bmesh
from mathutils import Vector

from ...utils.scene import ray_cast
from ...utils import addon
from ...bmeshutils.orientation import direction_from_normal, face_bbox_center


class BOUT_OT_ObjSetCustomPlane(bpy.types.Operator):
    bl_idname = "bout.obj_set_custom_plane"
    bl_label = "Set Custom Plane"
    bl_description = "Set custom plane based on raycast hit location"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.object is not None and context.mode == 'OBJECT'

    def invoke(self, context, event):
        self.mouse_pos = (event.mouse_region_x, event.mouse_region_y)
        return self.execute(context)

    def find_closest_element(self, obj, hit_loc, face_idx, bm, threshold=0.1):
        matrix = obj.matrix_world
        inv_matrix = matrix.inverted()
        local_hit = inv_matrix @ hit_loc

        face = bm.faces[face_idx]

        # Check vertices first
        closest_vert = None
        min_vert_dist = float('inf')
        for vert in face.verts:
            dist = (vert.co - local_hit).length
            if dist < min_vert_dist:
                min_vert_dist = dist
                closest_vert = vert

        if min_vert_dist < threshold:
            return 'VERT', closest_vert

        # Check edges
        closest_edge = None
        min_edge_dist = float('inf')
        for edge in face.edges:
            # Calculate distance to edge
            edge_vec = edge.verts[1].co - edge.verts[0].co
            edge_len = edge_vec.length
            edge_dir = edge_vec / edge_len
            v1_to_hit = local_hit - edge.verts[0].co
            proj_len = v1_to_hit.dot(edge_dir)

            if 0 <= proj_len <= edge_len:
                proj_point = edge.verts[0].co + edge_dir * proj_len
                dist = (local_hit - proj_point).length
                if dist < min_edge_dist:
                    min_edge_dist = dist
                    closest_edge = edge

        if min_edge_dist < threshold:
            return 'EDGE', closest_edge

        return 'FACE', face

    def execute(self, context):
        if addon.pref().tools.block.align.mode == 'CUSTOM':
            addon.pref().tools.block.align.mode = 'FACE'
            self.report({'INFO'}, "Custom plane disabled")
            context.area.tag_redraw()
            return {'FINISHED'}

        # Get mouse position
        ray = ray_cast.visible(context, self.mouse_pos)

        if not ray.hit:
            self.report({'WARNING'}, "No object found under cursor")
            return {'CANCELLED'}

        obj = ray.obj
        matrix = obj.matrix_world
        hit_loc = ray.location
        face_idx = ray.index

        # Create bmesh from evaluated mesh
        depsgraph = context.evaluated_depsgraph_get()
        obj_eval = obj.evaluated_get(depsgraph)
        me_eval = obj_eval.to_mesh()
        bm = bmesh.new()
        bm.from_mesh(me_eval)
        obj_eval.to_mesh_clear()
        bm.verts.ensure_lookup_table()
        bm.edges.ensure_lookup_table()
        bm.faces.ensure_lookup_table()

        try:
            # Find closest element (vertex, edge, or face)
            element_type, element = self.find_closest_element(obj, hit_loc, face_idx, bm)

            # Initialize variables
            location = None
            normal = None
            direction = None

            if element_type == 'VERT':
                # Use the vertex
                vert = element
                location = matrix @ vert.co
                normal = matrix.to_3x3() @ vert.normal
                # Use direction_from_normal to compute direction
                direction = matrix.to_3x3() @ direction_from_normal(normal)
                addon.pref().tools.block.align.grid.size = 1

            elif element_type == 'EDGE':
                # Use the selected edge
                edge = element
                # Compute the midpoint of the edge
                location = (matrix @ edge.verts[0].co + matrix @ edge.verts[1].co) / 2.0

                # Compute normal as average of connected face normals
                sum_normal = Vector()
                faces_normals = [matrix.to_3x3() @ f.normal for f in edge.link_faces]
                sum_normal = sum(faces_normals, Vector())

                # Use direction from v1 to v2 as edge direction
                direction = matrix @ edge.verts[1].co - matrix @ edge.verts[0].co
                length = direction.length
                direction_y = sum_normal.cross(direction)

                normal = direction.cross(direction_y)
                addon.pref().tools.block.align.grid.size = length

            else:  # FACE
                # Use the face
                face = element
                normal = matrix.to_3x3() @ face.normal
                location = face_bbox_center(face, matrix)
                direction = matrix.to_3x3() @ face.calc_tangent_edge()
                length = direction.length + 0.1

                addon.pref().tools.block.align.grid.size = length

            normal.normalize()
            direction.normalize()

            # Set the custom plane's values
            custom = addon.pref().tools.block.align.custom
            custom.location = location
            custom.normal = normal
            custom.direction = direction

            addon.pref().tools.block.align.mode = 'CUSTOM'
            context.area.tag_redraw()

        finally:
            # Always free the bmesh
            bm.free()

        return {'FINISHED'}


classes = (
    BOUT_OT_ObjSetCustomPlane,
)
