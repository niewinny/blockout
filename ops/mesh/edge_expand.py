import bpy
import bmesh
from mathutils import Vector, geometry
from ...utils import infobar
from ...utils.bmesh import Closest


class BOUT_OT_EdgeExpand(bpy.types.Operator):
    bl_idname = "bout.edge_expand"
    bl_label = "Edge Slide"
    bl_options = {'REGISTER', 'UNDO', 'BLOCKING', 'GRAB_CURSOR'}
    bl_description = "Slide a new edge parallel to a selected edge along a linked face"

    edge_index: int = -1
    face_index: int = -1
    closest: Closest = None
    stored_mesh_data: bpy.types.Mesh = None

    move: bpy.props.FloatProperty(
        name="Move",
        description="Offset from selected edge center",
        default=0.0,
        step=1,
        precision=4,
        subtype='DISTANCE'
    )
    plane_co_init: Vector = Vector((0, 0, 0))
    plane_co: Vector = Vector((0, 0, 0))
    plane_no: Vector = Vector((0, 0, 0))

    intersections: list = []

    @classmethod
    def poll(cls, context):
        return context.area.type == 'VIEW_3D' and context.mode == 'EDIT_MESH'

    def draw(self, _context):
        layout = self.layout
        layout.use_property_split = True
        layout.prop(self, 'move')

    def invoke(self, context, event):
        obj = context.edit_object
        obj.update_from_editmode()
        bm = bmesh.from_edit_mesh(obj.data)
        bm.faces.ensure_lookup_table()
        bm.edges.ensure_lookup_table()

        selected_edges = [e for e in bm.edges if e.select]

        if not selected_edges:
            return self.cancel_operator("No edge selected.")

        edge = selected_edges[0]
        self.edge_index = edge.index

        faces = edge.link_faces
        if len(faces) == 0:
            return self.cancel_operator("Selected edge has no linked faces.")
        elif len(faces) > 2:
            return self.cancel_operator("Selected edge has more than two linked faces.")

        self.stored_mesh_data = obj.data.copy()

        # Initialize plane based on selected edge and face
        self.plane_co_init = (edge.verts[0].co + edge.verts[1].co) / 2
        self.plane_co = self.plane_co_init.copy()
        self.plane_no = faces[0].normal.normalized()

        # Initialize Closest instance
        self.closest = Closest(context, bm, Vector((event.mouse_region_x, event.mouse_region_y)))

        infobar.draw(context, event, self.infobar_hotkeys, blank=True)
        context.area.header_text_set("Edge Expand")
        context.window.cursor_set('SCROLL_XY')
        context.window_manager.modal_handler_add(self)

        self.expand_edge(context)
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        if event.type == 'MOUSEMOVE':
            self.handle_mouse_move(context, event)

        elif event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            self.end(context)
            return {'FINISHED'}

        elif event.type in {'RIGHTMOUSE', 'ESC'} and event.value == 'PRESS':
            self.restore_mesh()
            self.end(context)
            return {'CANCELLED'}

        return {'RUNNING_MODAL'}

    def handle_mouse_move(self, context, event):
        mouse_pos = Vector((event.mouse_region_x, event.mouse_region_y))

        self.restore_mesh()
        obj = context.edit_object
        bm = bmesh.from_edit_mesh(obj.data)
        bm.faces.ensure_lookup_table()
        bm.edges.ensure_lookup_table()

        self.closest.detect(context, bm, mouse_pos)

        if self.closest.face:
            edge = bm.edges[self.edge_index]
            edge_verts = edge.verts
            linked_faces = set(face.index for vert in edge_verts for face in vert.link_faces)
            if self.closest.face.index in linked_faces:
                self.face_index = self.closest.face.index
                hit_loc = self.closest.face.hit_loc
                self.move = (hit_loc - self.plane_co_init).dot(self.plane_no)
                self.adjust_plane_co(self.move)
                self.expand_edge(context)

                return

        self.face_index = -1
        self.update_bmesh(context)

    def adjust_plane_co(self, move_distance):
        '''Adjust the plane_co based on the move distance.'''
        self.plane_co = self.plane_co_init + self.plane_no * move_distance

    def update_bmesh(self, context):
        '''Update the mesh with the new edge'''
        bmesh.update_edit_mesh(context.edit_object.data, loop_triangles=True, destructive=True)
        context.area.tag_redraw()

    def restore_mesh(self):
        '''Restore the mesh to its original state'''
        obj = bpy.context.edit_object
        bm = bmesh.from_edit_mesh(obj.data)
        bm.clear()
        bm.from_mesh(self.stored_mesh_data)
        bmesh.update_edit_mesh(obj.data)

    def get_intersections(self, face, hit_loc):
        '''Get the line segments for the new edge'''
        obj = bpy.context.edit_object
        bm = bmesh.from_edit_mesh(obj.data)
        bm.edges.ensure_lookup_table()
        edge = bm.edges[self.edge_index]
        edge_verts = set(edge.verts)
        face_verts = set(face.verts)

        if edge_verts <= face_verts:
            intersections = self.get_intersections_points(bm, face.normal, hit_loc)
            return intersections
        if edge_verts & face_verts:
            vert = next(iter(edge_verts & face_verts))
            if len(edge.link_faces) == 2:
                avg_normal = sum((f.normal for f in edge.link_faces), Vector()).normalized()
                intersections = self.get_intersections_points(bm, avg_normal, vert.co)
                return intersections

        return []

    def get_intersections_points(self, bm, normal, vec):
        '''Define the plane and calculate the intersection points'''
        edge = bm.edges[self.edge_index]
        edge_vector = edge.verts[1].co - edge.verts[0].co
        self.plane_no = normal.cross(edge_vector).normalized()
        return self.calculate_intersection_points(bm, vec, self.plane_no)

    def calculate_intersection_points(self, bm, plane_co, plane_normal):
        '''Calculate the intersection points of the edges of the given face with the given plane'''
        intersections = []
        if self.face_index == -1:
            return intersections  # Return an empty list if no face is found

        face = bm.faces[self.face_index]
        for edge in face.edges:
            vert1, vert2 = edge.verts
            intersection = geometry.intersect_line_plane(vert1.co, vert2.co, plane_co, plane_normal)
            if intersection:
                direction = vert2.co - vert1.co
                if direction.length == 0:
                    continue  # Avoid division by zero
                t = (intersection - vert1.co).dot(direction) / direction.dot(direction)
                if 0 <= t <= 1:
                    intersections.append((intersection, edge))
        return intersections

    def execute(self, context):
        '''Execute the operator'''
        self.expand_edge(context)
        return {'FINISHED'}

    def expand_edge(self, context):
        '''Run the operator'''
        if self.face_index == -1:
            return

        obj = context.edit_object
        bm = bmesh.from_edit_mesh(obj.data)
        bm.faces.ensure_lookup_table()
        bm.edges.ensure_lookup_table()

        edge = bm.edges[self.edge_index]
        if self.face_index >= len(bm.faces):
            return

        face = bm.faces[self.face_index]
        edge_vector = edge.verts[1].co - edge.verts[0].co
        self.plane_no = face.normal.cross(edge_vector).normalized()
        self.plane_co = self.plane_co_init + self.plane_no * self.move

        intersections = self.get_intersections(face, self.plane_co)
        if not intersections or len(intersections) < 2:
            return

        new_verts = self.get_intersecting_vertices(intersections)
        if len(new_verts) < 2:
            return

        new_verts = self.remove_duplicates(new_verts)
        self.deselect_all_edges(bm)
        self.connect_vertices_in_pairs(bm, new_verts)
        bmesh.update_edit_mesh(obj.data, loop_triangles=True, destructive=True)

        self.update_bmesh(context)

    def remove_duplicates(self, verts, threshold=0.0001):
        '''Remove duplicate vertices from a list of vertices'''
        unique_verts = []
        for v in verts:
            if all((v.co - u.co).length >= threshold for u in unique_verts):
                unique_verts.append(v)
        return unique_verts

    def get_intersecting_vertices(self, intersections):
        '''Get the vertices that intersect with the edges of the mesh'''
        verts = []
        for point, edge in intersections:
            vert = self.subdivide_edge(edge, point)
            if vert:
                verts.append(vert)
        return verts

    def subdivide_edge(self, edge, intersect_point):
        '''Subdivide the edge at the intersection point'''
        vert1, vert2 = edge.verts
        edge_vec = vert2.co - vert1.co
        length = edge_vec.length
        if length == 0:
            return None
        t = (intersect_point - vert1.co).dot(edge_vec) / (length ** 2)
        t = max(0.0, min(t, 1.0))  # Clamp t between 0 and 1
        result = bmesh.utils.edge_split(edge, vert1, t)
        result[1].co = intersect_point
        return result[1]

    def connect_vertices_in_pairs(self, bm, verts):
        '''Connect the vertices in pairs'''
        for v1, v2 in zip(verts[::2], verts[1::2]):
            if v1 != v2:
                result = bmesh.ops.connect_vert_pair(bm, verts=[v1, v2])
                if result is None or 'edges' not in result:
                    self.report({'ERROR'}, "Failed to connect vertices")
                else:
                    for edge in result['edges']:
                        edge.select = True
                    bm.select_flush_mode()

    def deselect_all_edges(self, bm):
        '''Deselect all edges'''
        for edge in bm.edges:
            edge.select = False
        bm.select_flush_mode()

    def cancel_operator(self, message):
        '''Handle cancelling the operator with a message.'''
        self.report({'ERROR'}, message)
        return {'CANCELLED'}

    def end(self, context):
        '''End the operator and clean up.'''
        if self.stored_mesh_data is not None:
            bpy.data.meshes.remove(self.stored_mesh_data)
            self.stored_mesh_data = None

        self.closest = None
        self.intersections = []

        infobar.remove(context)
        context.area.header_text_set(text=None)
        context.window.cursor_set('CROSSHAIR')
        context.area.tag_redraw()

    def infobar_hotkeys(self, layout, _context, _event):
        '''Draw the infobar hotkeys'''
        row = layout.row(align=True)
        row.label(text='', icon='MOUSE_MOVE')
        row.label(text='Adjust Radius')
        row.separator(factor=12.0)
        row.label(text='', icon='MOUSE_LMB')
        row.label(text='Confirm')
        row.separator(factor=12.0)
        row.label(text='', icon='MOUSE_RMB')
        row.label(text='Cancel')
        row.separator(factor=12.0)
