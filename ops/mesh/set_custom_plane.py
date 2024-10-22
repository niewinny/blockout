import bpy
import bmesh
from mathutils import Vector
import math

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
        me = obj.data
        bm = bmesh.from_edit_mesh(me)

        addon.pref().tools.sketch.align.mode = 'CUSTOM'

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
            location = face.calc_center_median()
            normal = face.normal.copy()

            # Use direction_from_normal to compute direction
            direction = direction_from_normal(normal)

        # If not, check if exactly one edge is selected
        elif len(selected_edges) == 1:
            # Use the selected edge
            edge = selected_edges[0]
            # Compute the midpoint of the edge
            location = (edge.verts[0].co + edge.verts[1].co) / 2.0

            # Compute normal as average of connected face normals
            normal = Vector()
            for face in edge.link_faces:
                normal += face.normal
            if normal.length_squared > 0:
                normal.normalize()
            else:
                # If no linked faces, default normal
                normal = Vector((0, 0, 1))

            # Use direction_from_normal to compute direction
            direction = direction_from_normal(normal)

        # If not, check if exactly one vertex is selected
        elif len(selected_verts) == 1:
            # Use the selected vertex
            vert = selected_verts[0]
            location = vert.co.copy()
            normal = vert.normal.copy()

            # Use direction_from_normal to compute direction
            direction = direction_from_normal(normal)

        else:
            self.report({'ERROR'}, "Please select exactly one face, edge, or vertex")
            return {'CANCELLED'}

        # Transform location, normal, and direction to world coordinates
        location_world = obj.matrix_world @ location
        normal_world = obj.matrix_world.to_3x3() @ normal
        normal_world.normalize()
        direction_world = obj.matrix_world.to_3x3() @ direction
        direction_world.normalize()

        # Set the custom plane's values
        custom = addon.pref().tools.sketch.align.custom

        custom.location = location_world
        custom.normal = normal_world
        custom.direction = direction_world  # Store the direction vector directly

        self.report({'INFO'}, "Custom plane set based on selection")

        context.area.tag_redraw()
        return {'FINISHED'}


classes = (
    BOUT_OT_SetCustomPlane,
)
