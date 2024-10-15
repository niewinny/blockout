from dataclasses import dataclass, field
import bpy
import bmesh
from mathutils import Vector

from ...shaders.draw import DrawPolyline
from ...shaders import handle
from ...utils import addon, view3d, scene, infobar
from ...bmeshutils import detection


@dataclass
class PlaneData:
    '''Dataclass for the plane data.'''
    co: Vector = None
    no: Vector = Vector((0, 0, 0))
    co_init: Vector = None
    no_init: Vector = None
    move_init: Vector = None
    orientation: str = 'EDGE'


@dataclass
class MeshData:
    '''Dataclass for the mesh data.'''
    bm: bmesh.types.BMesh = None
    geom: list = None
    stored_mesh_data: bpy.types.Mesh = None
    closest: detection.Closest = None


@dataclass
class DrawUI(handle.Common):
    '''Dataclass for the UI data.'''
    line: handle.Line = field(default_factory=handle.Line)
    guid: handle.Polyline = field(default_factory=handle.Polyline)


class BOUT_OT_LoopBisect(bpy.types.Operator):
    bl_idname = "bout.loop_bisect"
    bl_label = "Loop Bisect"
    bl_options = {'REGISTER', 'UNDO', 'BLOCKING', 'GRAB_CURSOR'}
    bl_description = "Create Loop Cut along a given edge across the mesh."

    move: bpy.props.FloatProperty(name="Move", description="Offset from selected edge center", default=0.0, step=1, precision=4, subtype='DISTANCE')
    plane_no: bpy.props.FloatVectorProperty(name="Normal", description="Move vector", default=(0, 0, 0), min=-1, max=1, subtype='XYZ')

    def __init__(self):
        self.state: str = 'DETECT'
        self.mesh_data = {}
        self.plane_data = PlaneData()
        self.ui = DrawUI()
        self.guid = None

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

        bpy.ops.mesh.select_all(action='DESELECT')

        for obj in selected_objects:
            if obj.type == 'MESH':
                obj.update_from_editmode()
                bm = bmesh.from_edit_mesh(obj.data)
                geom = [v for v in bm.verts if not v.hide] + \
                       [e for e in bm.edges if not e.hide] + \
                       [f for f in bm.faces if not f.hide]

                closest = detection.Closest(context, bm, mouse_pos)
                stored_mesh_data = obj.data.copy()

                self.mesh_data[obj] = MeshData(
                    bm=bm,
                    geom=geom,
                    stored_mesh_data=stored_mesh_data,
                    closest=closest
                )

        points = [(Vector((0, 0, 0)), Vector((0, 0, 0)))]

        _theme = addon.pref().theme.ops.mesh.loop_bisect
        color = _theme.line
        self.ui.line.callback = DrawPolyline(points, width=1.0, color=color)
        self.ui.line.handle = bpy.types.SpaceView3D.draw_handler_add(
            self.ui.line.callback.draw, (context,), 'WINDOW', 'POST_VIEW')
        color = _theme.guid
        self.ui.guid.callback = DrawPolyline(points, width=1.2, color=color)
        self.ui.guid.handle = bpy.types.SpaceView3D.draw_handler_add(
            self.ui.guid.callback.draw, (context,), 'WINDOW', 'POST_VIEW')

        infobar.draw(context, event, self._infobar_hotkeys_detect, blank=True)
        context.area.header_text_set(f'Cuts: {1}')
        context.window.cursor_set('SCROLL_XY')
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        if event.type == 'MOUSEMOVE':
            if self.state == 'DETECT':
                mouse_pos = Vector((event.mouse_region_x, event.mouse_region_y))
                scene.set_active_object(context, mouse_pos)

                edge, edit_object = self._detect_edge(context, event)

                if edge:
                    self.plane_data.co_init = (edge.verts[0].co + edge.verts[1].co) / 2
                    self.plane_data.no_init = (edge.verts[1].co - edge.verts[0].co).normalized()

                    self.guid = (
                        edit_object.matrix_world @ edge.verts[0].co,
                        edit_object.matrix_world @ edge.verts[1].co
                    )

                    self.plane_data.co = self.plane_data.co_init
                    if self.plane_data.orientation == 'EDGE':
                        self.plane_no = self.plane_data.no_init

                    self._update(context, edit_object, edge)
                else:
                    self.ui.line.callback.update_batch([])
            elif self.state == 'MOVE':
                edit_object = context.edit_object
                mesh_data = self.mesh_data.get(edit_object)
                plane_data = self.plane_data

                if not mesh_data:
                    # Handle case where mesh_data is missing
                    self.report({'WARNING'}, "Mesh data not found for the object.")
                    self._end(context)
                    return {'CANCELLED'}

                global_plane_co_init = edit_object.matrix_world @ plane_data.co_init
                plane_no = self.plane_no

                if self.plane_data.orientation == 'EDGE':
                    plane_no = (edit_object.matrix_world.to_3x3() @ self.plane_no).normalized()

                mouse_pos = Vector((event.mouse_region_x, event.mouse_region_y))
                region = context.region
                rv3d = context.region_data
                closest_point_on_line = view3d.region_2d_to_nearest_point_on_line_3d(
                    region, rv3d, mouse_pos, global_plane_co_init, plane_no)

                if closest_point_on_line:
                    local_closest_point = edit_object.matrix_world.inverted() @ closest_point_on_line

                    if plane_data.move_init is None:
                        plane_data.move_init = plane_data.co_init - local_closest_point

                    adjusted_closest_point = local_closest_point + plane_data.move_init
                    plane_data.co = adjusted_closest_point

                    self._calculate_offset_from_plane_co()
                    context.area.header_text_set(
                        f'Loop Slide: {self.move:.4f} along {self.plane_data.orientation.lower()}')

                self._restore_mesh(context)
                self.execute(context)

                self.ui.line.callback.update_batch([])
                self.ui.guid.callback.update_batch([self.guid])
        elif event.type == 'LEFTMOUSE':
            if event.value == 'PRESS':
                if self.state == 'MOVE':
                    self._end(context)
                    return {'FINISHED'}
                elif self.state == 'DETECT':
                    if self.mesh_data.get(context.edit_object).closest.edge:
                        self.state = 'MOVE'
                        infobar.draw(context, event, self._infobar_hotkeys_move, blank=True)
                    else:
                        self._end(context)
                        return {'CANCELLED'}
        elif event.type in {'X', 'Y', 'Z', 'E'} and event.value == 'PRESS' and self.state == 'MOVE':
            edit_object = context.edit_object

            if event.type == 'Z':
                if self.plane_data.orientation == 'GLOBAL_Z':
                    self.plane_data.orientation = 'LOCAL_Z'
                    self.plane_no = Vector((0, 0, 1))
                else:
                    self.plane_data.orientation = 'GLOBAL_Z'
                    self.plane_no = edit_object.matrix_world.to_3x3().inverted_safe() @ Vector((0, 0, 1))
            elif event.type == 'X':
                if self.plane_data.orientation == 'GLOBAL_X':
                    self.plane_data.orientation = 'LOCAL_X'
                    self.plane_no = Vector((1, 0, 0))
                else:
                    self.plane_data.orientation = 'GLOBAL_X'
                    self.plane_no = edit_object.matrix_world.to_3x3().inverted_safe() @ Vector((1, 0, 0))
            elif event.type == 'Y':
                if self.plane_data.orientation == 'GLOBAL_Y':
                    self.plane_data.orientation = 'LOCAL_Y'
                    self.plane_no = Vector((0, 1, 0))
                else:
                    self.plane_data.orientation = 'GLOBAL_Y'
                    self.plane_no = edit_object.matrix_world.to_3x3().inverted_safe() @ Vector((0, 1, 0))
            elif event.type == 'E':
                self.plane_data.orientation = 'EDGE'
                self.plane_no = self.plane_data.no_init

            context.area.header_text_set(f'Loop Slide: {self.move:.4f} along {self.plane_data.orientation.lower()}')
        if event.type in {'RIGHTMOUSE', 'ESC'} and event.value == 'PRESS':
            if self.state == 'MOVE':
                self._restore_mesh(context)
                self.move = 0.0
                self.plane_data.co = self.plane_data.co_init
                self.execute(context)
                self._end(context)
                return {'FINISHED'}
            elif self.state == 'DETECT':
                for obj in context.selected_objects:
                    bmesh.update_edit_mesh(obj.data)
                self._end(context)
                return {'CANCELLED'}
        return {'RUNNING_MODAL'}

    def _restore_mesh(self, context):
        '''Restore the mesh to the stored mesh data'''
        edit_object = context.edit_object
        mesh_data = self.mesh_data.get(edit_object)
        if not mesh_data:
            # Handle case where mesh_data is missing
            self.report({'WARNING'}, "Mesh data not found for the object.")
            return
        bm = mesh_data.bm
        stored_mesh_data = mesh_data.stored_mesh_data
        if stored_mesh_data:
            bm.clear()
            bm.from_mesh(stored_mesh_data)

    def _update(self, context, edit_object, edge):
        '''Update the bisect operation'''
        if edge:
            edge_points = self._traverse_edges(edge, edit_object)
            self._update_bisect_callback(edge_points)
            context.area.tag_redraw()

    def _traverse_edges(self, start_edge, edit_object):
        '''Traverse the edges to get the intersection points'''
        matrix_world = edit_object.matrix_world
        plane_co = matrix_world @ self.plane_data.co
        plane_no = matrix_world.to_3x3() @ self.plane_no
        visited_faces = set()
        intersection_points = []

        def traverse_single_direction(current_edge):
            '''Traverse the edges in a single direction'''
            prev_point = self._get_intersection_point(current_edge, plane_co, plane_no, matrix_world)
            if not prev_point:
                return []
            points = []
            while True:
                found_next_edge = False
                for face in current_edge.link_faces:
                    if face in visited_faces:
                        continue
                    visited_faces.add(face)
                    for edge in face.edges:
                        if edge != current_edge:
                            next_point = self._get_intersection_point(edge, plane_co, plane_no, matrix_world)
                            if next_point:
                                points.append((prev_point, next_point))
                                prev_point = next_point
                                current_edge = edge
                                found_next_edge = True
                                break
                    if found_next_edge:
                        break
                if not found_next_edge:
                    break
            return points

        # Traverse in the initial direction
        points_forward = traverse_single_direction(start_edge)
        intersection_points.extend(points_forward)

        # If the last edge does not bring us back to the starting edge, traverse again in the opposite direction
        if points_forward and points_forward[-1][1] != self._get_intersection_point(start_edge, plane_co, plane_no, matrix_world):
            points_backward = traverse_single_direction(start_edge)
            # Reverse the points collected and extend to the full list
            intersection_points.extend(reversed(points_backward))

        # If we still don't loop back, close the loop manually
        if intersection_points and intersection_points[-1][1] != intersection_points[0][0]:
            intersection_points.append((intersection_points[-1][1], intersection_points[0][0]))

        return intersection_points

    def _get_intersection_point(self, edge, plane_co, plane_no, matrix_world):
        '''Get the intersection point between the edge and the plane'''
        vert1 = matrix_world @ edge.verts[0].co
        vert2 = matrix_world @ edge.verts[1].co
        edge_vector = vert2 - vert1
        denom = plane_no.dot(edge_vector)
        if abs(denom) > 1e-6:
            t = (plane_co - vert1).dot(plane_no) / denom
            if 0 <= t <= 1:
                return vert1 + t * edge_vector
        return None

    def _update_bisect_callback(self, edge_points):
        '''Update the bisect callback'''
        if edge_points:
            color = addon.pref().theme.ops.mesh.loop_bisect.line
            flattened_points = [(start, end) for start, end in edge_points]
            self.ui.line.callback.update_batch(flattened_points, color=color)

    def _calculate_offset_from_plane_co(self):
        '''Calculate the offset from the plane co'''
        difference_vector = self.plane_data.co - self.plane_data.co_init
        projection_length = difference_vector.dot(self.plane_no)
        self.move = projection_length

    def _adjust_plane_co(self, plane_no):
        '''Adjust the plane co based on the move vector'''
        movement_vector = plane_no * self.move
        self.plane_data.co = self.plane_data.co_init + movement_vector

    def execute(self, context):
        if self.plane_data.co is None:
            return {'CANCELLED'}
        bpy.ops.mesh.select_all(action='DESELECT')
        edit_object = context.edit_object
        bm = bmesh.from_edit_mesh(edit_object.data)
        geom = [v for v in bm.verts if not v.hide] + \
               [e for e in bm.edges if not e.hide] + \
               [f for f in bm.faces if not f.hide]
        self._adjust_plane_co(self.plane_no)
        result = self._bisect(context, self.plane_data.co, self.plane_no, bm, geom)
        for edge in result['geom_cut']:
            if isinstance(edge, bmesh.types.BMEdge):
                edge.select = True
        bm.select_flush(True)
        bmesh.update_edit_mesh(edit_object.data)
        return {'FINISHED'}

    def _end(self, context):
        '''End the operator'''
        # Clean up stored mesh data
        for mesh_data in self.mesh_data.values():
            if mesh_data.stored_mesh_data:
                bpy.data.meshes.remove(mesh_data.stored_mesh_data)
        self.mesh_data.clear()
        self.guid = None
        infobar.remove(context)
        context.area.header_text_set(text=None)
        context.window.cursor_set('CROSSHAIR')

        self.ui.clear()

        context.area.tag_redraw()

    def _detect_edge(self, context, event):
        '''Detect the edge under the mouse cursor'''
        edit_object = context.edit_object
        mesh_data = self.mesh_data.get(edit_object)
        if not mesh_data:
            # Handle case where mesh_data is missing
            return None, None
        bm = mesh_data.bm
        mouse_pos = Vector((event.mouse_region_x, event.mouse_region_y))
        mesh_data.closest.detect(context, bm, mouse_pos)
        if mesh_data.closest.edge:
            edge_index = mesh_data.closest.edge.index
            edge = bm.edges[edge_index]
            return edge, edit_object
        return None, None

    def _bisect(self, context, plane_co, plane_no, bm, geom):
        '''Perform the bisect operation'''
        result = bmesh.ops.bisect_plane(
            bm,
            geom=geom,
            plane_co=plane_co,
            plane_no=plane_no,
            clear_outer=False,
            clear_inner=False
        )
        bmesh.update_edit_mesh(context.edit_object.data, destructive=True)
        return result

    def _infobar_hotkeys_detect(self, layout, _context, _event):
        '''Draw the infobar for the detect state'''
        row = layout.row()
        row.label(text='Select an edge to loop cut along it, hide the mesh to cut only chosen geometry.')

    def _infobar_hotkeys_move(self, layout, _context, _event):
        '''Draw the infobar for the move state'''
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

    def _axis_update(self, edge, edit_object):
        '''Update the axis for the edge'''
        _theme = addon.pref().theme.ops.mesh.loop_bisect

        axis_info = {
            'GLOBAL_X': {'axis': Vector((1, 0, 0)), 'color': _theme.axis_x},
            'GLOBAL_Y': {'axis': Vector((0, 1, 0)), 'color': _theme.axis_y},
            'GLOBAL_Z': {'axis': Vector((0, 0, 1)), 'color': _theme.axis_z},
            'LOCAL_X': {'axis': (edit_object.matrix_world.to_3x3() @ Vector((1, 0, 0))).normalized(), 'color': _theme.axis_x},
            'LOCAL_Y': {'axis': (edit_object.matrix_world.to_3x3() @ Vector((0, 1, 0))).normalized(), 'color': _theme.axis_y},
            'LOCAL_Z': {'axis': (edit_object.matrix_world.to_3x3() @ Vector((0, 0, 1))).normalized(), 'color': _theme.axis_z},
        }

        axis_data = axis_info.get(self.plane_data.orientation, None)

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

                    p1_rotated = rot_matrix @ (p1 - center) + center
                    p2_rotated = rot_matrix @ (p2 - center) + center

                    new_points.append((p1_rotated, p2_rotated))
                else:
                    new_points.append((p1, p2))
        else:
            new_points = []
            current_color = _theme.guid

        self.ui.guid.callback.update_batch(new_points, color=current_color)


class Theme(bpy.types.PropertyGroup):
    line: bpy.props.FloatVectorProperty(name="Loop Cut Line", description="Color of the line", size=4, subtype='COLOR', default=(1.0, 0.6, 0.0, 0.9), min=0.0, max=1.0)
    guid: bpy.props.FloatVectorProperty(name="Loop Cut guid", description="Color of the guid", size=4, subtype='COLOR', default=(1.0, 1.0, 0.3, 0.5), min=0.0, max=1.0)
    axis_x: bpy.props.FloatVectorProperty(name="Axis X", description="Color of the X axis", size=4, subtype='COLOR', default=(1.0, 0.2, 0.322, 1.0), min=0.0, max=1.0)
    axis_y: bpy.props.FloatVectorProperty(name="Axis Y", description="Color of the Y axis", size=4, subtype='COLOR', default=(0.545, 0.863, 0.0, 1.0), min=0.0, max=1.0)
    axis_z: bpy.props.FloatVectorProperty(name="Axis Z", description="Color of the Z axis", size=4, subtype='COLOR', default=(0.157, 0.565, 1.0, 1.0), min=0.0, max=1.0)


types_classes = (
    Theme,
)

classes = (
    BOUT_OT_LoopBisect,
)
