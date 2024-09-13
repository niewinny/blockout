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

    bm: bmesh.types.BMesh = None
    edge_index: int = -1
    face_index: int = -1
    closest: Closest
    stored_mesh_data: bpy.types.Mesh = None

    move: bpy.props.FloatProperty(name="Move", description="Offset from selected edge center", default=0.0, step=1, precision=4, subtype='DISTANCE')
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
        self.bm = bmesh.from_edit_mesh(obj.data)

        selected_edges = [e for e in self.bm.edges if e.select]

        if not selected_edges:
            return self.cancel_operator("No edge selected.")

        edge = selected_edges[0]
        self.edge_index = edge.index

        faces = edge.link_faces
        if len(faces) < 2:
            return self.cancel_operator("Selected edge has no linked face or more than two linked faces.")

        self.stored_mesh_data = obj.data.copy()

        # Initialize plane based on selected edge and face
        self.plane_co_init = (edge.verts[0].co + edge.verts[1].co) / 2
        self.plane_co = self.plane_co_init
        self.plane_no = faces[0].normal.normalized()

        # Initialize closest detection, infobar, etc.
        self.closest = Closest(context, self.bm, Vector((event.mouse_region_x, event.mouse_region_y)))

        infobar.draw(context, event, self.infobar_hotkeys, blank=True)
        context.area.header_text_set("Edge Expand")
        context.window.cursor_set('SCROLL_XY')
        context.window_manager.modal_handler_add(self)

        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        if event.type == 'MOUSEMOVE':
            self.handle_mouse_move(context, event)

        elif event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            self.end(context)
            return {'FINISHED'}

        elif event.type in {'RIGHTMOUSE', 'ESC'} and event.value == 'PRESS':
            self.end(context)
            return {'CANCELLED'}

        return {'RUNNING_MODAL'}

    def handle_mouse_move(self, context, event):
        mouse_pos = Vector((event.mouse_region_x, event.mouse_region_y))

        self.closest.detect(context, self.bm, mouse_pos)
        self.restore_mesh()

        if self.closest.face:
            self.bm.edges.ensure_lookup_table()
            edge_verts = self.bm.edges[self.edge_index].verts
            linked_faces = [face.index for vert in edge_verts for face in vert.link_faces]
            if self.closest.face.index in linked_faces:
                self.face_index = self.closest.face.index
                hit_loc = self.closest.face.hit_loc

                # Update the move distance and adjust plane_co accordingly
                self.move = (hit_loc - self.plane_co_init).dot(self.plane_no)
                self.update_plane_co()
                self.update_mesh(context)
                return

        self.face_index = -1
        bmesh.update_edit_mesh(context.edit_object.data)

    def update_plane_co(self):
        '''Update plane_co based on the current move value.'''
        self.plane_co = self.plane_co_init + self.plane_no * self.move

    def restore_mesh(self):
        '''Restore the mesh to its original state'''
        self.bm.clear()
        self.bm.from_mesh(self.stored_mesh_data)

    def get_intersections(self, face, hit_loc):
        '''Get the line segments for the new edge'''
        self.bm.edges.ensure_lookup_table()
        edge_verts = set(self.bm.edges[self.edge_index].verts)
        face_verts = set(face.verts)

        if edge_verts <= face_verts:
            return self.get_intersections_points(face.normal, hit_loc)
        if edge_verts & face_verts:
            vert = next(iter(edge_verts & face_verts))
            if len(self.bm.edges[self.edge_index].link_faces) == 2:
                avg_normal = sum((f.normal for f in self.bm.edges[self.edge_index].link_faces), Vector()).normalized()
                return self.get_intersections_points(avg_normal, vert.co)

        return None

    def get_intersections_points(self, normal, vec):
        '''Define the plane and calculate the intersection points'''
        self.plane_no = normal.cross(self.bm.edges[self.edge_index].verts[0].co - self.bm.edges[self.edge_index].verts[1].co).normalized()
        return self.calculate_intersection_points(vec, self.plane_no)

    def calculate_intersection_points(self, plane_co, plane_normal):
        '''Calculate the intersection points of the edges of the given face with the given plane'''
        intersections = []
        if self.face_index == -1:
            return intersections  # Return an empty list if no face is found

        face = self.bm.faces[self.face_index]
        for edge in face.edges:
            vert1, vert2 = edge.verts
            intersection = geometry.intersect_line_plane(vert1.co, vert2.co, plane_co, plane_normal)
            if intersection and 0 <= (intersection - vert1.co).dot((vert2.co - vert1.co).normalized()) <= (vert2.co - vert1.co).length:
                intersections.append((intersection, edge))
        return intersections

    def execute(self, context):
        '''Execute the operator'''
        obj = context.edit_object
        obj.update_from_editmode()
        self.bm = bmesh.from_edit_mesh(obj.data)

        self.update_mesh(context)
        return {'FINISHED'}

    def update_mesh(self, context):
        '''Run the operator'''
        if self.face_index == -1:
            return

        self.bm.edges.ensure_lookup_table()
        self.bm.faces.ensure_lookup_table()

        self.plane_no = self.bm.faces[self.face_index].normal.cross(self.bm.edges[self.edge_index].verts[0].co - self.bm.edges[self.edge_index].verts[1].co).normalized()
        self.plane_co = self.plane_co_init + self.plane_no * self.move

        intersections = self.get_intersections(self.bm.faces[self.face_index], self.plane_co)
        if not intersections:
            return

        new_verts = self.get_intersecting_vertices(intersections)
        if len(new_verts) < 2:
            return

        new_verts = self.remove_duplicates(new_verts)
        self.deselect_all_edges()
        self.connect_vertices_in_pairs(new_verts)

        bmesh.update_edit_mesh(context.edit_object.data)
        context.area.tag_redraw()

    def remove_duplicates(self, verts, threshold=0.0001):
        '''Remove duplicate vertices from a list of vertices'''
        return [v for i, v in enumerate(verts) if all((v.co - w.co).length >= threshold for w in verts[:i])]

    def get_intersecting_vertices(self, intersections):
        '''Get the vertices that intersect with the edges of the mesh'''
        return [self.subdivide_edge(edge, point) if isinstance(edge, bmesh.types.BMEdge) else edge for point, edge in intersections]

    def subdivide_edge(self, edge, intersect_point):
        '''Subdivide the edge at the intersection point'''
        result = bmesh.utils.edge_split(edge, edge.verts[0], 0.5)
        result[1].co = intersect_point
        return result[1]

    def connect_vertices_in_pairs(self, verts):
        '''Connect the vertices in pairs'''
        for v1, v2 in zip(verts[::2], verts[1::2]):
            if v1 != v2:
                result = bmesh.ops.connect_vert_pair(self.bm, verts=[v1, v2])
                if result is None or 'edges' not in result:
                    self.report({'ERROR'}, "Failed to connect vertices")
                else:
                    for edge in result['edges']:
                        edge.select = True
                    self.bm.select_flush_mode()

    def deselect_all_edges(self):
        '''Deselect all edges'''
        for edge in self.bm.edges:
            edge.select = False
        self.bm.select_flush_mode()

    def cancel_operator(self, message):
        '''Handle cancelling the operator with a message.'''
        self.report({'ERROR'}, message)
        return {'CANCELLED'}

    def end(self, context):
        '''End the operator and clean up.'''
        bpy.data.meshes.remove(self.stored_mesh_data)

        self.bm = None
        self.closest = None
        self.stored_mesh_data = None
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
