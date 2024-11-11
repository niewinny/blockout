import bpy
import bmesh
from mathutils import Vector

from ...bmeshutils.orientation import direction_from_normal
from ...utils import addon


class BOUT_OT_SetCustomPlane(bpy.types.Operator):
    bl_idname = "bout.set_custom_plane"
    bl_label = "Set Custom Plane"
    bl_description = "Set custom plane based on selected vertex, edge, or face"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return (context.object is not None and context.object.type == 'MESH' and context.mode == 'EDIT_MESH')

    def execute(self, context):
        # Get the active object and its bmesh
        obj = context.active_object
        matrix = obj.matrix_world
        me = obj.data
        bm = bmesh.from_edit_mesh(me)

        if addon.pref().tools.sketch.align.mode == 'CUSTOM':
            addon.pref().tools.sketch.align.mode = 'FACE'
            self.report({'INFO'}, "Custom plane disabled")
            context.area.tag_redraw()
            return {'FINISHED'}

        # Ensure lookup tables are up to date
        bm.verts.ensure_lookup_table()
        bm.edges.ensure_lookup_table()
        bm.faces.ensure_lookup_table()

        # Get selected elements
        selected_verts = [v for v in bm.verts if v.select]
        selected_edges = [e for e in bm.edges if e.select]
        selected_faces = [f for f in bm.faces if f.select]

        # Initialize variables
        location = None
        normal = None
        direction = None  # Direction vector

        # Start by checking if exactly one face is selected
        if len(selected_faces) == 1:
            # Use the selected face
            face = selected_faces[0]
            location = matrix @ face.calc_center_median()
            normal = matrix.to_3x3() @ face.normal.copy()
            direction = matrix.to_3x3() @ face.calc_tangent_edge()

        # If not, check if exactly one edge is selected
        elif len(selected_edges) == 1:
            # Use the selected edge
            edge = selected_edges[0]
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

        # If not, check if exactly one vertex is selected
        elif len(selected_verts) == 1:
            # Use the selected vertex
            vert = selected_verts[0]
            location = matrix @ vert.co.copy()
            normal = matrix.to_3x3() @ vert.normal.copy()

            # Use direction_from_normal to compute direction
            direction = matrix.to_3x3() @ direction_from_normal(normal)

        else:
            self.report({'ERROR'}, "Please select exactly one face, edge, or vertex")
            return {'CANCELLED'}

        normal.normalize()
        direction.normalize()

        # Set the custom plane's values
        custom = addon.pref().tools.sketch.align.custom

        custom.location = location
        custom.normal = normal
        custom.direction = direction

        addon.pref().tools.sketch.align.mode = 'CUSTOM'
        self.report({'INFO'}, "Custom plane set based on selection")

        context.area.tag_redraw()
        return {'FINISHED'}


classes = (
    BOUT_OT_SetCustomPlane,
)
