import bpy
import bmesh

from mathutils import Vector

from ...shaders.draw import DrawPolyline
from ...utils import addon, view3d, scene, infobar
from ...utils.bmesh import Closest


class BOUT_OT_LoopBisect(bpy.types.Operator):
    bl_idname = "bout.loop_bisect"
    bl_label = "Loop Bisect"
    bl_options = {'REGISTER', 'UNDO', 'BLOCKING', 'GRAB_CURSOR'}
    bl_description = "Create Loop Cut along a given edge across the mesh."

    state: str = 'DETECT'
    orientation: str = 'EDGE'

    bms: dict = {}
    closests: dict = {}
    geoms: dict = {}
    stored_mesh_data: dict = {}
    guid: tuple = []

    edge: bmesh.types.BMEdge = None

    move_init: Vector = None
    move: bpy.props.FloatProperty(name="Move", description="Offset form selected edge center", default=0.0, step=1, precision=4, subtype='DISTANCE')

    plane_co: Vector
    plane_no: bpy.props.FloatVectorProperty(name="Normal", description="Move vector", default=(0, 0, 0), min=-1, max=1, subtype='XYZ')
    plane_co_init: Vector
    plane_no_init: Vector

    _callback_line: DrawPolyline
    _handle_line: int
    _callback_guid: DrawPolyline
    _handle_guid: int

    @classmethod
    def poll(cls, context):
        return context.mode == 'EDIT_MESH'

    def draw(self, _context):
        layout = self.layout
        layout.use_property_split = True

        col = layout.column()
        col.prop(self, 'move')
        col.prop(self, 'plane_no')

    def invoke(self, context, event):

        context.edit_object.select_set(True)
        selected_objects = context.selected_objects
        mouse_pos = Vector((event.mouse_region_x, event.mouse_region_y))

        self.bms = {}
        self.closests = {}

        bpy.ops.mesh.select_all(action='DESELECT')

        for obj in selected_objects:
            if obj.type == 'MESH':

                obj.update_from_editmode()
                # Operate on this object
                bm = bmesh.from_edit_mesh(obj.data)
                geom = [v for v in bm.verts if not v.hide] + [e for e in bm.edges if not e.hide] + [f for f in bm.faces if not f.hide]

                # Store bmesh and selections
                self.bms[obj] = bm
                self.geoms[obj] = geom
                self.closests[obj] = Closest(context, bm, mouse_pos)
                self.stored_mesh_data[obj] = obj.data.copy()

        points = [(Vector((0, 0, 0)), Vector((0, 0, 0)))]

        _theme = addon.pref().theme.ops.mesh.loop_bisect
        color = _theme.line
        self._callback_line = DrawPolyline(points, width=1.0, color=color)
        self._handle_line = bpy.types.SpaceView3D.draw_handler_add(self._callback_line.draw, (context,), 'WINDOW', 'POST_VIEW')
        color = _theme.guid
        self._callback_guid = DrawPolyline(points, width=1.2, color=color)
        self._handle_guid = bpy.types.SpaceView3D.draw_handler_add(self._callback_guid.draw, (context,), 'WINDOW', 'POST_VIEW')

        infobar.draw(context, event, self.infobar_hotkeys_detect, blank=True)
        context.area.header_text_set(f'Cuts: {1}')
        context.window.cursor_set('SCROLL_XY')
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def modal(self, context, event):

        if event.type == 'MOUSEMOVE':
            if self.state == 'DETECT':
                mouse_pos = Vector((event.mouse_region_x, event.mouse_region_y))
                scene.set_active_object(context, mouse_pos)

                edge, edit_object, _bm = self.detect_edge(context, event)
                if edge:

                    self.edge = edge
                    self.plane_co_init = (edge.verts[0].co + edge.verts[1].co) / 2
                    self.plane_no_init = (edge.verts[1].co - edge.verts[0].co).normalized()

                    self.guid = (edit_object.matrix_world @ edge.verts[0].co, edit_object.matrix_world @ edge.verts[1].co)

                    self.plane_co = self.plane_co_init
                    if self.orientation == 'EDGE':
                        self.plane_no = self.plane_no_init

                    self.update(context, edit_object, edge)

                else:
                    self.edge = None
                    self._callback_line.update_batch([])

            elif self.state == 'MOVE':

                edit_object = context.edit_object

                # Transform self.plane_co_init and self.plane_no to global space
                global_plane_co_init = edit_object.matrix_world @ self.plane_co_init

                plane_no = self.plane_no

                if self.orientation == 'EDGE':
                    plane_no = (edit_object.matrix_world.to_3x3() @ self.plane_no).normalized()

                # Now use these global vectors for calculating the closest point on the line
                mouse_pos = Vector((event.mouse_region_x, event.mouse_region_y))
                region = context.region
                rv3d = context.region_data
                closest_point_on_line = view3d.region_2d_to_nearest_point_on_line_3d(region, rv3d, mouse_pos, global_plane_co_init, plane_no)

                if closest_point_on_line:
                    # Convert the closest point back to local space before using it
                    local_closest_point = edit_object.matrix_world.inverted() @ closest_point_on_line

                    if self.move_init is None:
                        self.move_init = self.plane_co_init - local_closest_point

                    adjusted_closest_point = local_closest_point + self.move_init
                    self.plane_co = adjusted_closest_point

                    # Determine the direction to adjust the move
                    self.calculate_offset_from_plane_co()
                    context.area.header_text_set(f'Loop Slide: {self.move:.4f} along {self.orientation.lower()}')

                # Restore the previous mesh state
                self.restore_mesh(context)

                # Execute the bisect operation
                self.execute(context)

                self._callback_line.update_batch([])
                self._callback_guid.update_batch([self.guid])

        elif event.type == 'LEFTMOUSE':
            if event.value == 'PRESS':

                if self.state == 'MOVE':

                    self.end(context)
                    return {'FINISHED'}

                elif self.state == 'DETECT':
                    if self.edge:
                        self.state = 'MOVE'
                        infobar.draw(context, event, self.infobar_hotkeys_move, blank=True)

                    else:
                        self.end(context)
                        return {'CANCELLED'}

        elif event.type in {'X', 'Y', 'Z', 'E'} and event.value == 'PRESS' and self.state == 'MOVE':
            edit_object = context.edit_object

            if event.type == 'Z':
                if self.orientation == 'GLOBAL_Z':
                    self.orientation = 'LOCAL_Z'
                    self.plane_no = Vector((0, 0, 1))
                else:
                    self.orientation = 'GLOBAL_Z'
                    self.plane_no = edit_object.matrix_world.to_3x3().inverted_safe() @ Vector((0, 0, 1))

            elif event.type == 'X':
                if self.orientation == 'GLOBAL_X':
                    self.orientation = 'LOCAL_X'
                    self.plane_no = Vector((1, 0, 0))
                else:
                    self.orientation = 'GLOBAL_X'
                    self.plane_no = edit_object.matrix_world.to_3x3().inverted_safe() @ Vector((1, 0, 0))

            elif event.type == 'Y':
                if self.orientation == 'GLOBAL_Y':
                    self.orientation = 'LOCAL_Y'
                    self.plane_no = Vector((0, 1, 0))
                else:
                    self.orientation = 'GLOBAL_Y'
                    self.plane_no = edit_object.matrix_world.to_3x3().inverted_safe() @ Vector((0, 1, 0))

            elif event.type == 'E':
                self.orientation = 'EDGE'
                self.plane_no = self.plane_no_init

            context.area.header_text_set(f'Loop Slide: {self.move:.4f} along {self.orientation.lower()}')

        if event.type in {'RIGHTMOUSE', 'ESC'} and event.value == 'PRESS':

            if self.state == 'MOVE':

                self.restore_mesh(context)
                self.move = 0.0
                self.plane_co = self.plane_co_init
                self.execute(context)
                self.end(context)

                return {'FINISHED'}

            elif self.state == 'DETECT':

                selected_objects = context.selected_objects

                for obj in selected_objects:
                    bmesh.update_edit_mesh(obj.data)

                self.end(context)
                return {'CANCELLED'}

        return {'RUNNING_MODAL'}

    def restore_mesh(self, context):
        '''Restore the mesh to the state before the operation.'''
        edit_object = context.edit_object
        bm = self.bms[edit_object]
        stored_mesh_data = self.stored_mesh_data[edit_object]
        if stored_mesh_data:
            bm.clear()
            bm.from_mesh(stored_mesh_data)

    def update(self, context, edit_object, edge):
        '''Update the bisect operation based on the current state.'''

        if edge:
            edge_points = self.traverse_edges(edge, edit_object)
            self.update_bisect_callback(edge_points)
            context.area.tag_redraw()

    def traverse_edges(self, start_edge, edit_object):
        '''Traverse edges starting from a given edge, collecting intersection points with the plane.'''

        matrix_world = edit_object.matrix_world

        plane_co = matrix_world @ self.plane_co
        plane_no = matrix_world.to_3x3() @ self.plane_no

        visited_faces = set()
        intersection_points = []

        def traverse_single_direction(start_edge):
            '''Traverse edges in a single direction from the start edge.'''
            current_edge = start_edge
            prev_point = self.get_intersection_point(current_edge, plane_co, plane_no, matrix_world)

            if not prev_point:
                return []

            points = []
            initial_edge = current_edge

            while True:
                found_next_edge = False

                for face in current_edge.link_faces:
                    if face in visited_faces:
                        continue

                    visited_faces.add(face)

                    for edge in face.edges:
                        if edge != current_edge:
                            next_point = self.get_intersection_point(edge, plane_co, plane_no, matrix_world)
                            if next_point:
                                points.append((prev_point, next_point))
                                prev_point = next_point
                                current_edge = edge
                                found_next_edge = True
                                break  # Only follow one edge per face

                    if found_next_edge:
                        break

                # Stop if we've looped back to the initial edge or if no further edges were found
                if current_edge == initial_edge or not found_next_edge:
                    break

            return points

        # Traverse in the initial direction
        points_forward = traverse_single_direction(start_edge)
        intersection_points.extend(points_forward)

        # If the last edge does not bring us back to the starting edge, traverse again in the opposite direction
        if points_forward and points_forward[-1][1] != self.get_intersection_point(start_edge, plane_co, plane_no, matrix_world):
            points_backward = traverse_single_direction(start_edge)
            # Reverse the points collected and extend to the full list
            intersection_points.extend(reversed(points_backward))

        # If we still don't loop back, close the loop manually
        if intersection_points and intersection_points[-1][1] != intersection_points[0][0]:
            intersection_points.append((intersection_points[-1][1], intersection_points[0][0]))

        return intersection_points

    def get_intersection_point(self, edge, plane_co, plane_no, matrix_world):
        '''Calculate the intersection point of an edge with a plane.'''

        vert1 = matrix_world @ edge.verts[0].co
        vert2 = matrix_world @ edge.verts[1].co
        edge_vector = vert2 - vert1

        denom = plane_no.dot(edge_vector)
        if abs(denom) > 1e-6:  # Ensure the edge is not parallel to the plane
            t = (plane_co - vert1).dot(plane_no) / denom
            if 0 <= t <= 1:
                return vert1 + t * edge_vector

        return None

    def update_bisect_callback(self, edge_points):
        '''Update the drawing callback with new points.'''

        if edge_points:
            color = addon.pref().theme.ops.mesh.loop_bisect.line
            flattened_points = []
            for start, end in edge_points:
                flattened_points.append((start, end))
            self._callback_line.update_batch(flattened_points, color=color)

    def calculate_offset_from_plane_co(self):
        '''Calculate the move based on the current plane_co and the initial plane_co.'''

        difference_vector = self.plane_co - self.plane_co_init

        # The projection formula is: proj_v_on_u = (v . u / u . u) * u
        # But since plane_no should be a unit vector (normalized), u . u = 1, simplifying the formula
        projection_length = difference_vector.dot(self.plane_no)
        self.move = projection_length

    def adjust_plane_co(self, plane_no):
        '''Adjust the plane_co based on the move.'''

        movement_vector = plane_no * self.move
        self.plane_co = self.plane_co_init + movement_vector

    def execute(self, context):
        '''Execute the bisect operation.'''

        if self.plane_co is None:
            return {'CANCELLED'}

        bpy.ops.mesh.select_all(action='DESELECT')

        edit_object = context.edit_object
        bm = bmesh.from_edit_mesh(edit_object.data)
        geom = [v for v in bm.verts if not v.hide] + [e for e in bm.edges if not e.hide] + [f for f in bm.faces if not f.hide]

        self.adjust_plane_co(self.plane_no)
        result = self.bisect(context, self.plane_co, self.plane_no, bm, geom)

        for edge in result['geom_cut']:
            if isinstance(edge, bmesh.types.BMEdge):
                edge.select = True

        bm.select_flush(True)
        bmesh.update_edit_mesh(edit_object.data)

        return {'FINISHED'}

    def end(self, context):
        '''Clean up.'''

        self.bms.clear()
        self.geoms.clear()
        self.closests.clear()

        for data in self.stored_mesh_data.values():
            bpy.data.meshes.remove(data)
        self.stored_mesh_data.clear()

        self.edge = None
        self.guid = None

        infobar.remove(context)
        context.area.header_text_set(text=None)
        context.window.cursor_set('CROSSHAIR')
        bpy.types.SpaceView3D.draw_handler_remove(self._handle_line, 'WINDOW')
        bpy.types.SpaceView3D.draw_handler_remove(self._handle_guid, 'WINDOW')

        context.area.tag_redraw()

    def detect_edge(self, context, event):
        '''Detect the edge under the mouse cursor.'''

        edit_object = context.edit_object
        bm = self.bms[edit_object]

        mosue_pos = Vector((event.mouse_region_x, event.mouse_region_y))
        self.closests[edit_object].detect(context, bm, mosue_pos)
        if self.closests[edit_object].edge:
            edge_index = self.closests[edit_object].edge.index
            edge = bm.edges[edge_index]
            return edge, edit_object, bm

        return None, None, None

    def bisect(self, context, plane_co, plane_no, bm, geom):
        '''Cut the mesh using the bisect_plane.'''

        result = bmesh.ops.bisect_plane(
            bm,
            geom=geom,
            plane_co=plane_co,
            plane_no=plane_no,
            clear_outer=False,
            clear_inner=False
        )

        # Update the mesh
        bmesh.update_edit_mesh(context.edit_object.data, destructive=True)

        return result

    def infobar_hotkeys_detect(self, layout, _context, _event):
        '''Draw the infobar for the "DETECT" state.'''

        row = layout.row()
        row.label(text='Select an edge to loop cut along it, hide the mesh to cut ony chosen geometry.')

    def infobar_hotkeys_move(self, layout, _context, _event):
        '''Draw the infobar for the "MOVE" state.'''

        row = layout.row(align=True)
        row.label(text='', icon='MOUSE_MOVE')
        row.label(text='Adjust')
        row.separator(factor=8.0)
        row.label(text='', icon='MOUSE_LMB')
        row.label(text='Confirm')
        row.separator(factor=8.0)
        row.label(text='', icon='MOUSE_RMB')
        row.label(text='Cancel')
        row.separator(factor=8.0)
        row.label(text='', icon='EVENT_X')
        row.label(text='X Axis')
        row.separator(factor=8.0)
        row.label(text='', icon='EVENT_Y')
        row.label(text='Y Axis')
        row.separator(factor=8.0)
        row.label(text='', icon='EVENT_Z')
        row.label(text='Z Axis')
        row.separator(factor=8.0)
        row.label(text='', icon='EVENT_E')
        row.label(text='Edge Axis')

    def axis_update(self, edge, edit_object):
        _theme = addon.pref().theme.ops.mesh.loop_bisect

        # Define the axis vectors and their corresponding colors for each orientation
        axis_info = {
            'GLOBAL_X': {'axis': Vector((1, 0, 0)), 'color': _theme.axis_x},
            'GLOBAL_Y': {'axis': Vector((0, 1, 0)), 'color': _theme.axis_y},
            'GLOBAL_Z': {'axis': Vector((0, 0, 1)), 'color': _theme.axis_z},
            'LOCAL_X': {'axis': (edit_object.matrix_world.to_3x3() @ Vector((1, 0, 0))).normalized(), 'color': _theme.axis_x},
            'LOCAL_Y': {'axis': (edit_object.matrix_world.to_3x3() @ Vector((0, 1, 0))).normalized(), 'color': _theme.axis_y},
            'LOCAL_Z': {'axis': (edit_object.matrix_world.to_3x3() @ Vector((0, 0, 1))).normalized(), 'color': _theme.axis_z},
        }

        axis_data = axis_info.get(self.orientation, None)

        if axis_data:
            target_axis = axis_data['axis']
            current_color = axis_data['color']

            points = [edit_object.matrix_world @ edge.verts[0].co, edit_object.matrix_world @ edge.verts[1].co]
            new_points = []

            for p1, p2 in points:
                center = (p1 + p2) / 2
                edge_vector = p2 - p1

                if edge_vector.length > 0:
                    rotation_quaternion = edge_vector.rotation_difference(target_axis)
                    rot_matrix = rotation_quaternion.to_matrix().to_4x4()

                    # Translate points to origin, apply rotation, and translate back
                    p1_rotated = rot_matrix @ (p1 - center) + center
                    p2_rotated = rot_matrix @ (p2 - center) + center

                    new_points.append((p1_rotated, p2_rotated))
                else:
                    new_points.append((p1, p2))
        else:
            new_points = []
            current_color = theme.guid

        self._callback_guid.update_batch(new_points, color=current_color)


class theme(bpy.types.PropertyGroup):
    line: bpy.props.FloatVectorProperty(name="Loop Cut Line", description="Color of the line", size=4, subtype='COLOR', default=(1.0, 1.0, 0.3, 0.9), min=0.0, max=1.0)
    guid: bpy.props.FloatVectorProperty(name="Loop Cut guid", description="Color of the guid", size=4, subtype='COLOR', default=(1.0, 1.0, 0.3, 0.5), min=0.0, max=1.0)

    axis_x: bpy.props.FloatVectorProperty(name="Axis X", description="Color of the X axis", size=4, subtype='COLOR', default=(1.0, 0.2, 0.322, 1.0), min=0.0, max=1.0)
    axis_y: bpy.props.FloatVectorProperty(name="Axis Y", description="Color of the Y axis", size=4, subtype='COLOR', default=(0.545, 0.863, 0.0, 1.0), min=0.0, max=1.0)
    axis_z: bpy.props.FloatVectorProperty(name="Axis Z", description="Color of the Z axis", size=4, subtype='COLOR', default=(0.157, 0.565, 1.0, 1.0), min=0.0, max=1.0)


types_classes = (
    theme,
)
