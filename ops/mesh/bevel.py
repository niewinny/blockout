from dataclasses import dataclass, field
import math
import bpy
import bmesh

from mathutils import Vector, geometry

from ...shaders.draw import DrawPolyline
from ...shaders import handle
from ...utils import view3d, addon, infobar


@dataclass
class Mouse:
    '''Dataclass for the mouse data'''
    init: Vector = Vector()
    co: Vector = Vector()
    saved: Vector = Vector()
    median: Vector = Vector()


@dataclass
class Distance:
    '''Dataclass for the distance calculation'''
    length: float = 0.0
    delta: float = 0.0


@dataclass
class Selected:
    '''Dataclass for the selected vertices'''
    edges_indices: list = None
    verts_indices: list = None


@dataclass
class DrawUI:
    '''Dataclass for the UI drawing'''
    guide: handle.Polyline = field(default_factory=handle.Polyline)


class BOUT_OT_Bevel(bpy.types.Operator):
    bl_idname = "bout.bevel"
    bl_label = "Bevel"
    bl_options = {'REGISTER', 'UNDO', 'BLOCKING', 'GRAB_CURSOR'}
    bl_description = "Bevel the surface along the selected edge"

    offset: bpy.props.FloatProperty(name='Offset', default=0.1, step=0.1, min=0, precision=3)
    segments: bpy.props.IntProperty(name='Segments', default=1, min=1, max=50)
    expand: bpy.props.BoolProperty(name='Expand', default=True)
    solver: bpy.props.EnumProperty(name='Solver', items=[('EXACT', 'Exact', 'Exact'), ('FAST', 'Fast', 'Fast')], default='EXACT')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bm: bmesh.types.BMesh = None
        self.mesh: bpy.types.Mesh = None

        self.mode: str = 'OFFSET'

        self.selected: Selected = Selected()
        self.mouse: Mouse = Mouse()
        self.distance: Distance = Distance()
        self.ui: DrawUI = DrawUI()

        self.saved_segments: int = 1

    @classmethod
    def poll(cls, context):
        return context.area.type == 'VIEW_3D' and context.mode == 'EDIT_MESH'

    def invoke(self, context, event):

        obj = context.edit_object
        obj.update_from_editmode()
        self.bm = bmesh.from_edit_mesh(obj.data)

        selected_edges = [e for e in self.bm.edges if e.select]

        if not selected_edges:
            self.report({'WARNING'}, 'No Edge Selected.')
            return {'CANCELLED'}

        if not continuous_loop(selected_edges):
            self.report({'WARNING'}, 'Selected edges must form a continuous loop.')
            return {'CANCELLED'}

        _is_closed, end_verts = check_continuous_loop(selected_edges)
        ordered_edges = order_selected_edges(selected_edges, end_verts)
        ordered_verts = order_loop_vertices(ordered_edges, end_verts)

        self.selected = Selected(
            verts_indices=[v.index for v in ordered_verts],
            edges_indices=[e.index for e in ordered_edges]
        )

        self.mouse.median = self._calculate_mid_point(context, selected_edges)

        self.mouse.co = self._get_intersect_point(context, event, self.mouse.median)
        self.mouse.init = self.mouse.co if self.mouse.co else self.mouse.median

        self.mesh = obj.data.copy()

        for edge in selected_edges:
            edge.select = False

        infobar.draw(context, event, self._infobar_hotkeys, blank=True)

        self._update_info(context)
        context.window.cursor_set('SCROLL_XY')

        self._setup_drawing(context)
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def _calculate_mid_point(self, context, edges):
        '''Calculate the midpoint of the selected edges'''

        obj = context.edit_object
        matrix_world = obj.matrix_world

        points = [matrix_world @ v.co for e in edges for v in e.verts]
        return sum(points, Vector((0, 0, 0))) / len(points)

    def execute(self, context):

        bm = bmesh.from_edit_mesh(context.edit_object.data)
        self._update_geometry(context, bm)

        return {'FINISHED'}

    def modal(self, context, event):

        if event.type == 'MOUSEMOVE':
            intersect_point = self._get_intersect_point(context, event, self.mouse.median)

            if intersect_point:
                self.mouse.co = intersect_point
                if self.mode == 'OFFSET':
                    self._set_offset()
                elif self.mode == 'SEGMENTS':
                    self._set_segments(context, event)

                self._update_info(context)

            self._restore_original_mesh(context)
            self._update_geometry(context, self.bm)
            self._update_drawing()

        elif event.type == 'LEFTMOUSE':
            self._end(context)
            return {'FINISHED'}

        elif event.type in {'RIGHTMOUSE', 'ESC'} and event.value == 'PRESS':
            self._restore_original_mesh(context)
            self._end(context)
            return {'CANCELLED'}

        elif event.type == 'S' and event.value == 'PRESS':
            self.mode = 'SEGMENTS'
            self.mouse.co = self._get_intersect_point(context, event, self.mouse.median)
            distance = self._calculate_distance()
            self.distance.length = distance - self.distance.delta
            self.mouse.saved = Vector((event.mouse_region_x, event.mouse_region_y))
            self.saved_segments = self.segments
            self._update_info(context)

        elif event.type == 'A' and event.value == 'PRESS':
            self.mode = 'OFFSET'
            self.mouse.co = self._get_intersect_point(context, event, self.mouse.median)
            distance = self._calculate_distance()
            self.distance.delta = distance - self.distance.length

        elif event.type == 'E' and event.value == 'PRESS':
            self.expand = not self.expand
            self._restore_original_mesh(context)
            self._update_geometry(context, self.bm)
            self._update_info(context)

        elif event.type == 'Q' and event.value == 'PRESS':
            self.solver = 'EXACT' if self.solver == 'FAST' else 'FAST'
            self._restore_original_mesh(context)
            self._update_geometry(context, self.bm)
            self._update_info(context)

        elif event.type == 'WHEELUPMOUSE' or event.type == 'NUMPAD_PLUS' or event.type == 'EQUAL':
            if event.value == 'PRESS':
                self.segments += 1
                self._restore_original_mesh(context)
                self._update_geometry(context, self.bm)
                self._update_info(context)

        elif event.type == 'WHEELDOWNMOUSE' or event.type == 'NUMPAD_MINUS' or event.type == 'MINUS':
            if event.value == 'PRESS':
                self.segments -= 1
                self._restore_original_mesh(context)
                self._update_geometry(context, self.bm)
                self._update_info(context)

        return {'RUNNING_MODAL'}

    def _initialize_geometry(self, bm):
        '''Initialize the selected vertices and edges from the bmesh'''

        bm.verts.ensure_lookup_table()
        bm.edges.ensure_lookup_table()
        selected_verts = [bm.verts[i] for i in self.selected.verts_indices]
        selected_edges = [bm.edges[i] for i in self.selected.edges_indices]
        return selected_verts, selected_edges

    def _calculate_offsets(self, selected_verts, selected_edges):
        '''Calculate the offset vertices for the selected edges'''

        offset_verts = []
        for vert in selected_verts:
            linked_edges = [edge for edge in vert.link_edges if edge in selected_edges]
            points = [vert.co for edge in linked_edges]
            offset_verts.extend(points)
        return offset_verts

    def _calculate_tangents(self, selected_edges, verts_pairs):
        '''Calculate the tangents for the selected edges'''

        tangents_left, tangents_right = [], []
        for edge, pair in zip(selected_edges, verts_pairs):
            direction = (pair[0] - pair[1]).normalized()
            for face in edge.link_faces:

                tangent = direction.cross(face.normal).normalized()

                for v in face.verts:
                    if v.co == pair[0]:
                        firt_vert_index = v.index

                for loop in face.loops:
                    if loop.edge == edge:
                        loop_vert = loop.vert.index

                if firt_vert_index == loop_vert:
                    tangents_right.append(-tangent)
                else:
                    tangents_left.append(tangent)

        return tangents_left, tangents_right

    def _update_geometry(self, context, bm):
        '''Update the geometry based on the selected edges'''

        obj = context.edit_object
        selected_verts, selected_edges = self._initialize_geometry(bm)

        offset_verts = self._calculate_offsets(selected_verts, selected_edges)

        verts_pairs = [(offset_verts[i], offset_verts[i + 1]) for i in range(0, len(offset_verts), 2)]

        tangents_left, tangents_right = self._calculate_tangents(selected_edges, verts_pairs)

        normal_offset = 0.001
        offset_verts_pairs = []

        for pair, normal_left, normal_right in zip(verts_pairs, tangents_left, tangents_right):
            offset_pair = []
            for v in pair:
                v = v + normal_left * normal_offset
                v = v + normal_right * normal_offset

                offset_pair.append(v)

            offset_verts_pairs.append(offset_pair)

        if self.expand:
            expand_offset = max(obj.dimensions[i] * obj.scale[i] for i in range(3)) * 2
            first_vert = offset_verts_pairs[0][0] + (offset_verts_pairs[0][0] - offset_verts_pairs[0][1]).normalized() * expand_offset
            last_vert = offset_verts_pairs[-1][1] + (offset_verts_pairs[-1][1] - offset_verts_pairs[-1][0]).normalized() * expand_offset

            offset_verts_pairs[0][0] = first_vert
            offset_verts_pairs[-1][1] = last_vert

        offset_verts_pairs_left = []

        for pair, tangent in zip(offset_verts_pairs, tangents_left):
            offset_pair = []
            for v in pair:
                v = v - tangent * (self.offset + 0.01)
                offset_pair.append(v)
            offset_verts_pairs_left.append(offset_pair)

        offset_verts_pairs_right = []

        for pair, tangent in zip(offset_verts_pairs, tangents_right):
            offset_pair = []
            for v in pair:
                v = v - tangent * (self.offset + 0.01)
                offset_pair.append(v)
            offset_verts_pairs_right.append(offset_pair)

        def _pairs_to_loop_verts(offset_verts_pairs):
            '''Convert the offset vertices pairs to a loop of vertices'''

            offset_loop_verts = [offset_verts_pairs[0][0]]  # Start with the first point of the first pair

            for i in range(1, len(offset_verts_pairs)):
                prev_pair = offset_verts_pairs[i - 1]
                curr_pair = offset_verts_pairs[i]

                if prev_pair[1] == curr_pair[0]:
                    # Append the start of the next pair
                    offset_loop_verts.append(curr_pair[0])

                elif prev_pair[1] != curr_pair[0]:
                    # Calculate intersection when end of one pair does not match start of the next
                    intersection = geometry.intersect_line_line(prev_pair[0], prev_pair[1], curr_pair[0], curr_pair[1])
                    if intersection:
                        offset_loop_verts.append(intersection[0])

            # Always add the last point of the last pair
            offset_loop_verts.append(offset_verts_pairs[-1][1])

            return offset_loop_verts

        offset_loop_verts = _pairs_to_loop_verts(offset_verts_pairs)
        offset_loop_verts_left = _pairs_to_loop_verts(offset_verts_pairs_left)
        offset_loop_verts_right = _pairs_to_loop_verts(offset_verts_pairs_right)

        def _create_loop_geometry(bm, loop_points_co):
            '''Create the loop edges based on the loop vertices'''

            verts = []
            for v in loop_points_co:
                vert = bm.verts.new(v)
                verts.append(vert)
            edges = []
            for i in range(1, len(verts)):
                edge = bm.edges.new([verts[i - 1], verts[i]])
                edges.append(edge)

            return verts, edges

        loop_verts, main_loop = _create_loop_geometry(bm, offset_loop_verts)
        loop_verts_left, _ = _create_loop_geometry(bm, offset_loop_verts_left)
        loop_verts_right, _ = _create_loop_geometry(bm, offset_loop_verts_right)

        new_faces = []

        if not len(loop_verts) == len(loop_verts_left) == len(loop_verts_right):
            return

        for i in range(1, len(loop_verts)):
            left_face = bm.faces.new([loop_verts[i - 1], loop_verts[i], loop_verts_left[i], loop_verts_left[i - 1]])
            right_face = bm.faces.new([loop_verts[i], loop_verts[i - 1], loop_verts_right[i - 1], loop_verts_right[i]])

            left_face.select_set(True)
            right_face.select_set(True)

            new_faces.append(left_face)
            new_faces.append(right_face)

        if new_faces:
            self._shell_geometry(bm, new_faces, thickness=0.5)

        geom = bmesh.ops.bevel(bm, geom=main_loop, offset=self.offset, segments=self.segments, profile=0.5, affect='EDGES')

        for e in geom['verts']:
            e.select = True
        bm.select_flush(True)

        bm.normal_update()
        bmesh.update_edit_mesh(obj.data, loop_triangles=True, destructive=True)

        bpy.ops.mesh.intersect_boolean(operation='DIFFERENCE', use_swap=False, use_self=False, threshold=1e-06, solver=self.solver)

    def _shell_geometry(self, bm, faces, thickness):
        '''Create a shell geometry based on the selected faces'''

        shell = bmesh.ops.solidify(bm, geom=faces, thickness=thickness)

        # Move each new face's vertices along its normal
        for f in shell['geom']:
            if isinstance(f, bmesh.types.BMFace):
                normal = f.normal
                for vert in f.verts:
                    vert.select = True
                    vert.co += normal * thickness

    def _restore_original_mesh(self, context):
        '''Restore the original mesh data from a backup stored in self.mesh'''

        obj = context.edit_object

        bm = self.bm
        bm.clear()
        bm.from_mesh(self.mesh)
        bmesh.update_edit_mesh(obj.data, loop_triangles=True, destructive=True)

    def _set_offset(self):
        '''Set the offset based on the initial and current mouse position'''

        distance = self._calculate_distance()
        distance = distance if distance > self.distance.delta else self.distance.delta
        offset = distance - self.distance.delta
        self.offset = offset

    def _set_segments(self, context, event):
        '''Set the segments based on the initial and current mouse position'''

        region = context.region
        rv3d = context.region_data

        # Convert 3D mid_point to 2D
        mid_point_2d = view3d.location_3d_to_region_2d(region, rv3d, self.mouse.median)
        saved_mouse_pos = self.mouse.saved
        mouse = Vector((event.mouse_region_x, event.mouse_region_y))

        if mid_point_2d and saved_mouse_pos:
            ref_distance = (mid_point_2d - saved_mouse_pos).length
            current_distance = (mid_point_2d - mouse).length
            distance = current_distance - ref_distance

            # Set base segments and adjust based on distance
            base_segments = self.saved_segments
            delta_segments = math.ceil(abs(distance) / 20)

            # Set segments directly based on distance
            new_segments = base_segments + delta_segments if distance > 0 else base_segments - delta_segments
            self.segments = max(1, new_segments)  # Ensure segments do not fall below 1


    def _calculate_distance(self):
        '''Calculate the distance based on the initial and current mouse position'''
        intersect_point = self.mouse.co
        if intersect_point:
            delta_init = (self.mouse.median - self.mouse.init).length
            distance = (self.mouse.median - intersect_point).length
            distance_fixed = distance - delta_init

            return distance_fixed

    def _get_intersect_point(self, context, event, plane_co):
        '''Calculate the intersection point on the plane defined by the plane_co and plane_no'''

        mouse = Vector((event.mouse_region_x, event.mouse_region_y))

        region = context.region
        rv3d = context.region_data

        # Calculate the 3D mouse position on the plane defined by the plane_co and plane_no
        mouse_pos_3d = view3d.region_2d_to_location_3d(region, rv3d, mouse, plane_co)

        if mouse_pos_3d:
            return mouse_pos_3d

        return Vector((0, 0, 0))

    def _update_info(self, context):
        '''Update header with the current settings'''

        info = f'Offset: {self.offset:.3f}    Segments: {self.segments}    Expand: {self.expand}    Solver: {self.solver}'
        context.area.header_text_set('Bevel' + '   ' + info)

    def draw(self, _context):
        layout = self.layout
        layout.use_property_split = True

        layout.prop(self, 'offset')
        layout.prop(self, 'segments')
        layout.prop(self, 'expand')
        layout.prop(self, 'solver')

    def _end(self, context):
        '''Cleanup and finish the operator'''

        if self.mesh:
            bpy.data.meshes.remove(self.mesh)

        self.mesh = None
        self.bm = None

        infobar.remove(context)
        context.area.header_text_set(text=None)
        context.window.cursor_set('CROSSHAIR')

        self.ui.guide.remove()

        context.area.tag_redraw()

    def _update_drawing(self):
        '''Update the drawing'''

        _theme = addon.pref().theme.ops.mesh.bevel
        color = _theme.guide
        point = [(self.mouse.median, self.mouse.co)]
        self.ui.guide.callback.update_batch(point, color=color)

    def _setup_drawing(self, context, points=None):
        '''Setup the drawing'''

        _theme = addon.pref().theme.ops.mesh.bevel
        color = _theme.guide

        points = points or [(Vector((0, 0, 0)), Vector((0, 0, 0)))]
        self.ui.guide.callback = DrawPolyline(points, width=1.2, color=color)
        self.ui.guide.handle = bpy.types.SpaceView3D.draw_handler_add(self.ui.guide.callback.draw, (context,), 'WINDOW', 'POST_VIEW')

    def _infobar_hotkeys(self, layout, _context, _event):
        '''Draw the infobar hotkeys'''

        row = layout.row(align=True)
        row.label(text='', icon='MOUSE_MOVE')
        row.label(text='Adjust Radius')
        row.separator(factor=8.0)
        row.label(text='', icon='MOUSE_LMB')
        row.label(text='Confirm')
        row.separator(factor=8.0)
        row.label(text='', icon='MOUSE_RMB')
        row.label(text='Cancel')
        row.separator(factor=8.0)
        row.label(text='', icon='EVENT_A')
        row.label(text='Offset')
        row.separator(factor=8.0)
        row.label(text='', icon='EVENT_S')
        row.label(text='Segments')
        row.separator(factor=8.0)
        row.label(text='', icon='EVENT_E')
        row.label(text='Expand')
        row.separator(factor=8.0)
        row.label(text='', icon='EVENT_Q')
        row.label(text='Solver')


def continuous_loop(edges):
    '''Check if the selected edges form a continuous loop'''

    vertex_edge_map = {}

    # Map each vertex to its connected edges
    for edge in edges:
        for vert in edge.verts:
            if vert not in vertex_edge_map:
                vertex_edge_map[vert] = []
            vertex_edge_map[vert].append(edge)

    # Check connectivity via vertices
    for vert, connected_edges in vertex_edge_map.items():
        if len(connected_edges) != 2:
            # If any vertex connects to more or less than two edges, it's not a closed loop
            # For an open loop, exactly two vertices should connect to only one edge
            if len(connected_edges) == 1:
                continue
            return False

    # Optionally, check if you can traverse all edges starting from any edge
    visited_edges = set()
    stack = [edges[0]]

    while stack:
        current_edge = stack.pop()
        if current_edge in visited_edges:
            continue
        visited_edges.add(current_edge)

        # Get the vertices of the current edge and find the next edge to traverse
        for vert in current_edge.verts:
            for next_edge in vertex_edge_map[vert]:
                if next_edge != current_edge:
                    stack.append(next_edge)

    # If we visited all edges exactly once, it's a loop
    return len(visited_edges) == len(edges)


def order_loop_vertices(edges, end_verts):
    '''Order the vertices of the selected edges'''

    if not edges:
        return []

    # Start from an end vertex if available (open loop) or just pick the first vertex of the first edge (closed loop)
    if end_verts:
        current_vertex = end_verts[0]
    else:
        current_vertex = edges[0].verts[0]

    ordered_vertices = [current_vertex]
    visited_edges = set()

    while len(visited_edges) < len(edges):
        for edge in current_vertex.link_edges:
            if edge in edges and edge not in visited_edges:
                # Add the edge to the visited list
                visited_edges.add(edge)
                # Add the opposite vertex of the current edge to the ordered list
                next_vertex = edge.other_vert(current_vertex)
                ordered_vertices.append(next_vertex)
                # Move to the next vertex
                current_vertex = next_vertex
                break

    return ordered_vertices


def check_continuous_loop(selected_edges):
    '''Check if the selected edges form a continuous loop'''

    edge_vertex_counts = {}
    for edge in selected_edges:
        for vert in edge.verts:
            if vert not in edge_vertex_counts:
                edge_vertex_counts[vert] = 1
            else:
                edge_vertex_counts[vert] += 1

    # Find end vertices (vertices with only one connected selected edge)
    end_verts = [vert for vert, count in edge_vertex_counts.items() if count == 1]

    # Valid continuous loop conditions: 0 end vertices (closed loop) or 2 end vertices (open loop)
    if len(end_verts) in [0, 2]:
        return True, end_verts
    else:
        return False, []


def order_selected_edges(selected_edges, end_verts):
    '''Order the selected edges based on the end vertices'''

    # Start with an edge that contains an end vertex or any edge if it's a closed loop
    start_edge = None
    if end_verts:
        for edge in selected_edges:
            if end_verts[0] in edge.verts:
                start_edge = edge
                break
    else:
        start_edge = selected_edges[0]

    ordered_edges = [start_edge]
    current_edge = start_edge
    while len(ordered_edges) < len(selected_edges):
        next_edge = None
        for vert in current_edge.verts:
            for edge in vert.link_edges:
                if edge in selected_edges and edge not in ordered_edges:
                    next_edge = edge
                    break
            if next_edge:
                break
        ordered_edges.append(next_edge)
        current_edge = next_edge

    return ordered_edges


class Theme(bpy.types.PropertyGroup):
    guide: bpy.props.FloatVectorProperty(name="Bevel Guid", description="Color of the guide line", size=4, subtype='COLOR', default=(0.0, 0.0, 0.0, 0.8), min=0.0, max=1.0)


types_classes = (
    Theme,
)


classes = (
    BOUT_OT_Bevel,
)
