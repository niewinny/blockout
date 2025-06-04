import bpy
import bmesh
from mathutils import Vector

from ...utils.scene import ray_cast
from ...utils import addon
from ...utilsbmesh.orientation import direction_from_normal, face_bbox_center, set_align_rotation_from_vectors
from ...utils.view3d import region_2d_to_origin_3d, region_2d_to_vector_3d
from ...utils.types import DrawMatrix


class BOUT_OT_ObjSetCustomPlane(bpy.types.Operator):
    bl_idname = "bout.obj_set_custom_plane"
    bl_label = "Set Custom Plane"
    bl_description = "Set custom plane based on raycast hit location"
    bl_options = {'REGISTER', 'UNDO'}

    mode: bpy.props.EnumProperty(
        name="Mode",
        description="Mode",
        items=[('SET', 'Set', 'Set'),
               ('MOVE', 'Move', 'Move'),
               ('ROTATE', 'Rotate', 'Rotate')],
        default='SET')

    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT'

    def invoke(self, context, event):
        self.mouse_pos = (event.mouse_region_x, event.mouse_region_y)
        return self.plane(context)

    def find_closest_element(self, obj, hit_loc, face_idx, bm, threshold=0.1):
        matrix = obj.matrix_world
        inv_matrix = matrix.inverted()
        local_hit = inv_matrix @ hit_loc

        # Check if the face index is valid for this mesh (important for instanced objects)
        if face_idx >= len(bm.faces) or face_idx < 0:
            self.report({'INFO'}, "Fallback: Geometry is not real")
            # Face index is out of bounds - this can happen with instanced objects
            # Fall back to finding the closest face to the hit location
            closest_face = None
            min_dist = float('inf')
            for face in bm.faces:
                face_center = face.calc_center_median()
                dist = (face_center - local_hit).length
                if dist < min_dist:
                    min_dist = dist
                    closest_face = face
            
            if closest_face is None:
                # If no faces found, return a fallback
                # Create a dummy face-like result
                return 'FACE', None

            face = closest_face
        else:
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
            
            # Skip zero-length edges (overlapping vertices)
            if edge_len < 1e-6:  # Use small epsilon for floating point comparison
                continue
            
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

    def plane(self, context):
        if self.mode == 'SET':
            if context.scene.bout.align.mode == 'CUSTOM':
                context.scene.bout.align.mode = 'FACE'
                self.report({'INFO'}, "Custom plane disabled")
                context.area.tag_redraw()
                return {'FINISHED'}

        old_matrix = DrawMatrix.from_property(context.scene.bout.align.matrix)
        old_location = old_matrix.location
        old_normal = old_matrix.normal
        old_direction = old_matrix.direction

        # Get mouse position
        ray = ray_cast.visible(context, self.mouse_pos)

        if not ray.hit:
            possible_normals = [
                Vector((1.0, 0.0, 0.0)),
                Vector((0.0, 1.0, 0.0)),
                Vector((0.0, 0.0, 1.0))
            ]
            hits = []
            origin = region_2d_to_origin_3d(context.region, context.region_data, self.mouse_pos)
            direction = region_2d_to_vector_3d(context.region, context.region_data, self.mouse_pos)

            for n in possible_normals:
                denom = direction.dot(n)
                if abs(denom) > 1e-6:  # Avoid division by zero
                    t = -origin.dot(n) / denom
                    if t > 0:  # Only consider intersections in front of the ray
                        hits.append((t, n))

            if hits:
                _, normal = min(hits, key=lambda x: x[0])
                location = Vector((0.0, 0.0, 0.0))
                direction = direction_from_normal(normal)
            else:
                self.report({'WARNING'}, "No object found under cursor, using default plane at (0,0,0)")
                location = Vector((0.0, 0.0, 0.0))
                normal = Vector((0.0, 0.0, 1.0))
                direction = direction_from_normal(normal)

            
            if self.mode == 'ROTATE':
                location = old_location
            if self.mode == 'MOVE':
                normal = old_normal
                direction = old_direction

            # Create a DrawMatrix from the plane data
            draw_matrix = DrawMatrix.new()
            # Set up the matrix from the plane data (location, normal) and direction
            draw_matrix.from_plane((location, normal), direction)
            # Convert to property format and update the matrix property
            context.scene.bout.align.matrix = draw_matrix.to_property()
            context.scene.bout.align.location = location
            context.scene.bout.align.rotation = set_align_rotation_from_vectors(normal, direction)

            context.scene.bout.align.mode = 'CUSTOM'
            context.area.tag_redraw()

            return {'FINISHED'}

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
                # Transform normal correctly using inverse transpose
                normal = (matrix.inverted().transposed()).to_3x3() @ vert.normal
                normal.normalize()
                # Use direction_from_normal to compute direction
                direction = matrix.to_3x3() @ direction_from_normal(vert.normal)

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
                direction_y = sum_normal.cross(direction)
                normal = direction.cross(direction_y)

            else:  # FACE
                # Use the face
                face = element
                if face is None:
                    # Fallback for instanced objects where we couldn't find a valid face
                    # Use the raycast hit data directly
                    location = hit_loc
                    normal = ray.normal
                    direction = direction_from_normal(normal)
                else:
                    normal = matrix.to_3x3() @ face.normal
                    location = face_bbox_center(face, matrix)
                    direction = matrix.to_3x3() @ face.calc_tangent_edge()


            normal.normalize()
            direction.normalize()

            if self.mode == 'ROTATE':
                location = old_location
            if self.mode == 'MOVE':
                normal = old_normal
                direction = old_direction

            # Create a DrawMatrix from the plane data
            draw_matrix = DrawMatrix.new()
            # Set up the matrix from the plane data (location, normal) and direction
            draw_matrix.from_plane((location, normal), direction)
            # Convert to property format and update the matrix property
            context.scene.bout.align.matrix = draw_matrix.to_property()
            context.scene.bout.align.location = location
            context.scene.bout.align.rotation = set_align_rotation_from_vectors(normal, direction)

            context.scene.bout.align.mode = 'CUSTOM'
            context.area.tag_redraw()

        finally:
            bm.free()
            del obj_eval

        return {'FINISHED'}


classes = (
    BOUT_OT_ObjSetCustomPlane,
)
