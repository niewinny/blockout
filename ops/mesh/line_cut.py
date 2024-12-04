import math
from dataclasses import dataclass, field

import bpy
import bmesh

from mathutils import Vector

from ...shaders import handle
from ...utils import view3d, addon, infobar


@dataclass
class Mouse:
    """Dataclass for tracking mouse positions."""
    init: Vector = Vector()
    co: Vector = Vector()


@dataclass
class DrawUI(handle.Common):
    """Dataclass for managing draw handlers."""
    line: handle.Line = field(default_factory=handle.Line)
    polyline: handle.Polyline = field(default_factory=handle.Polyline)
    gradient: handle.Gradient = field(default_factory=handle.Gradient)
    gradient_flip: handle.Gradient = field(default_factory=handle.Gradient)

    def __post_init__(self):
        self.clear_all()


class Bisect(bpy.types.Operator):
    """Operator to cut a mesh in Edit Mode."""

    mode: bpy.props.EnumProperty(name="Mode", description="Operation mode", items=[('CUT', 'Cut', 'Cut the mesh by removing one side'), ('SLICE', 'Slice', 'Slice the mesh without removing any side'), ('BISECT', 'Bisect', 'Bisect the mesh without duplication')], default='CUT')
    move: bpy.props.FloatProperty(name="Move", description="Offset from selected edge center", default=0.0, step=1, precision=4, subtype='DISTANCE')
    init_confirm: bpy.props.BoolProperty(name="Initial Confirm", description="Confirm on mouse press", default=False)
    release_confirm: bpy.props.BoolProperty(name="Release Confirm", description="Confirm on mouse release", default=True)
    flip: bpy.props.BoolProperty(name="Flip", description="Flip the cut direction", default=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.state = 'DRAW'
        self.mouse = Mouse()
        self.ui = DrawUI()
        self.draw_handlers = []

    @classmethod
    def poll(cls, context):
        return context.area.type == 'VIEW_3D' and context.mode == 'EDIT_MESH'

    def draw(self, context):
        """Draw the operator's UI in the tool panel."""
        layout = self.layout
        layout.use_property_split = True
        layout.prop(self, 'move')

    def invoke(self, context, event):
        """Initialize the operator."""

        self.mouse.init = Vector((event.mouse_region_x, event.mouse_region_y))
        if self.init_confirm:
            self.state = 'INIT'

        infobar.draw(context, event, self.infobar_hotkeys, blank=True)
        header_text = {'CUT': 'Mesh Cut', 'SLICE': 'Mesh Slice'}.get(self.mode, 'Mesh Cut')
        context.area.header_text_set(header_text)

        context.window.cursor_set('SCROLL_XY')
        self._setup_drawing(context)

        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        """Handle events during the operator's execution."""
        if self.state == 'INIT':
            if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
                self.mouse.init = Vector((event.mouse_region_x, event.mouse_region_y))
                self.state = 'DRAW'
            return {'RUNNING_MODAL'}

        if event.type == 'MOUSEMOVE':
            self._handle_mouse_move(context, event)
        elif event.type in {'F', 'X', 'B'} and event.value == 'PRESS':
            self._handle_key_press(context, event)
        elif event.type in {'LEFTMOUSE', 'RET', 'SPACE'}:
            if not (self.release_confirm and event.type == 'LEFTMOUSE' and event.value != 'RELEASE'):
                self.execute(context)
                self._end(context)
                return {'FINISHED'}
        elif event.type in {'RIGHTMOUSE', 'ESC'}:
            self._end(context)
            return {'CANCELLED'}

        return {'RUNNING_MODAL'}

    def _handle_mouse_move(self, context, event):
        """Update mouse position and redraw UI."""
        self.mouse.co = Vector((event.mouse_region_x, event.mouse_region_y))
        use_snap = context.scene.tool_settings.use_snap or event.ctrl
        if use_snap:
            precision = event.shift
            self.mouse.co = self._snap(context, precision=precision)
        self._update_drawing(context)
        context.area.tag_redraw()

    def _handle_key_press(self, context, event):
        """Handle key presses for flipping and mode switching."""
        if event.type == 'F':
            self.flip = not self.flip
            self._update_drawing(context)
            context.area.tag_redraw()
        elif event.type == 'X':
            self._toggle_mode('CUT' if self.mode == 'SLICE' else 'SLICE', context)
        elif event.type == 'B':
            self._toggle_mode('BISECT', context)

    def _toggle_mode(self, new_mode, context):
        """Toggle between different operation modes."""
        self.mode = new_mode
        visibility = {
            'CUT': {'gradient': True, 'gradient_flip': False},
            'SLICE': {'gradient': True, 'gradient_flip': True},
            'BISECT': {'gradient': False, 'gradient_flip': False}
        }
        self.ui.gradient.callback.visible = visibility[self.mode]['gradient']
        self.ui.gradient_flip.callback.visible = visibility[self.mode]['gradient_flip']
        context.area.header_text_set({
            'CUT': 'Mesh Cut',
            'SLICE': 'Mesh Slice',
            'BISECT': 'Mesh Bisect'
        }.get(self.mode, 'Mesh Cut'))
        self._update_drawing(context)
        context.area.tag_redraw()

    def _snap(self, context, precision=False):
        """Snap the mouse position to the nearest angle increment."""
        tool_settings = context.scene.tool_settings
        angle_increment = getattr(tool_settings, 'snap_angle_increment_3d', math.radians(15))
        if precision:
            angle_increment = getattr(tool_settings, 'snap_angle_increment_3d_precision', math.radians(5))

        delta = self.mouse.co - self.mouse.init
        angle = math.atan2(delta.y, delta.x)
        snapped_angle = round(angle / angle_increment) * angle_increment
        distance = delta.length
        direction = Vector((math.cos(snapped_angle), math.sin(snapped_angle)))
        snapped_mouse_pos = self.mouse.init + direction * distance
        return snapped_mouse_pos

    def _end(self, context):
        """Clean up after the operator finishes."""
        infobar.remove(context)
        context.area.header_text_set(text=None)
        context.window.cursor_set('CROSSHAIR')

        self.ui.clear()

        context.area.tag_redraw()

    def _setup_drawing(self, context):
        """Setup the drawing handlers based on the current mode."""
        color = addon.pref().theme.ops.mesh.line_cut

        self.ui.line.create(context, width=1.6, color=color.line if self.mode == 'CUT' else color.slice_line, depth=True)
        self.ui.polyline.create(context, width=1.6, color=color.line)
        self.ui.gradient.create(context)
        self.ui.gradient_flip.create(context)

    def _update_drawing(self, context):
        """Update the drawing elements based on the current mode and mouse position."""
        color = addon.pref().theme.ops.mesh.line_cut
        self._update_lines(context, color)

        # Update gradients based on mode
        if self.mode == 'CUT':
            self._update_gradient(perp_distance=150, gradient_color=color.gradient, flip=self.flip)
            self._reset_gradient(self.ui.gradient_flip.callback)
        elif self.mode == 'SLICE':
            self._update_gradient(perp_distance=75, gradient_color=color.slice_gradient)
            self._update_gradient(perp_distance=75, gradient_color=color.slice_gradient, flip=True, is_flip=True)
        elif self.mode == 'BISECT':
            self.ui.gradient.callback.visible = False
            self._reset_gradient(self.ui.gradient.callback)
            self._reset_gradient(self.ui.gradient_flip.callback)

    def _update_lines(self, context, color):
        """Update the line and polyline based on mouse positions."""
        region = context.region
        rv3d = context.region_data

        obj = context.edit_object
        obj.update_from_editmode()
        center_point = bbox_center(obj)
        largest_dim = get_largest_dimension(obj)

        # Convert 2D mouse positions to 3D points
        point1 = view3d.region_2d_to_location_3d(region, rv3d, self.mouse.init, center_point + largest_dim * rv3d.view_rotation @ Vector((0.0, 0.0, -1.0)))
        point2 = view3d.region_2d_to_location_3d(region, rv3d, self.mouse.co, center_point + largest_dim * rv3d.view_rotation @ Vector((0.0, 0.0, -1.0)))

        # Update Line
        line_color = color.line if self.mode == 'CUT' else color.slice_line if self.mode == 'SLICE' else color.bisect
        self.ui.line.callback.update_batch((point1, point2), color=line_color)

        # Update Polyline
        self.ui.polyline.callback.update_batch([(point1, point2)], color=line_color)

    def _update_gradient(self, perp_distance, gradient_color, flip=False, is_flip=False):
        """Update the gradient visualization based on direction and flip."""
        direction = (self.mouse.co - self.mouse.init).normalized()
        perp_vector = Vector((-direction.y, direction.x)) if flip else Vector((direction.y, -direction.x))

        point3 = self.mouse.co + perp_vector * perp_distance
        point4 = self.mouse.init + perp_vector * perp_distance
        points = [self.mouse.co, self.mouse.init, point4, point3] if flip else [self.mouse.init, self.mouse.co, point3, point4]

        colors = [gradient_color, gradient_color, (0.0, 0.0, 0.0, 0.0), (0.0, 0.0, 0.0, 0.0)]
        target_callback = self.ui.gradient_flip.callback if is_flip else self.ui.gradient.callback
        target_callback.update_batch(points=points, colors=colors)

    def _reset_gradient(self, gradient_callback):
        """Reset a gradient to a transparent state."""
        gradient_callback.update_batch(points=[(0, 0), (0, 0), (0, 0), (0, 0)], colors=[(0, 0, 0, 0)] * 4)

    def execute(self, context):
        """Execute the cutting operation."""
        region = context.region
        region_data = context.space_data.region_3d

        obj = context.edit_object
        obj.update_from_editmode()
        center_point = bbox_center(obj)

        # Convert mouse positions to 3D coordinates
        point1 = view3d.region_2d_to_location_3d(region, region_data, self.mouse.init, center_point)
        point2 = view3d.region_2d_to_location_3d(region, region_data, self.mouse.co, center_point)

        # Calculate plane normal based on mouse movement and view direction
        tangent = (point2 - point1).normalized()
        view_direction = view3d.region_2d_to_vector_3d(region, region_data, self.mouse.init)
        plane_no_global = tangent.cross(view_direction).normalized()

        # Iterate over selected mesh objects
        selected_meshes = [obj for obj in context.selected_objects if obj.type == 'MESH']
        for mesh_obj in selected_meshes:
            mesh_obj.update_from_editmode()
            plane_no_local = mesh_obj.matrix_world.transposed() @ plane_no_global
            move_vector = plane_no_local * self.move
            plane_co_local = (mesh_obj.matrix_world.inverted() @ point1) + move_vector

            if self.mode == 'CUT':
                self._bisect_mesh(mesh_obj, plane_co_local, plane_no_local, self.flip, clear_inner=True)
            elif self.mode == 'SLICE':
                self._slice_mesh(mesh_obj, plane_co_local, plane_no_local)
            elif self.mode == 'BISECT':
                self._bisect_mesh(mesh_obj, plane_co_local, plane_no_local, flip=False, clear_inner=False)

            bmesh.update_edit_mesh(mesh_obj.data, loop_triangles=True, destructive=True)

        return {'FINISHED'}

    def _slice_mesh(self, obj, plane_co, plane_no):
        """Slice the mesh with the given plane, retaining both sides."""
        bm = bmesh.from_edit_mesh(obj.data)
        geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
        geom = [g for g in geom if not g.hide]

        # Perform bisect without clearing any geometry
        result = bmesh.ops.bisect_plane(bm, geom=geom, plane_co=plane_co, plane_no=plane_no, clear_outer=False, clear_inner=False)

        # Update mesh without destruction to preserve both sides
        bmesh.update_edit_mesh(obj.data, loop_triangles=True, destructive=False)

        # Split along the bisect edges
        split_edges = [e for e in result['geom_cut'] if isinstance(e, bmesh.types.BMEdge)]
        if split_edges:
            bmesh.ops.split_edges(bm, edges=split_edges)
            bm.verts.ensure_lookup_table()
            bm.edges.ensure_lookup_table()
            bm.faces.ensure_lookup_table()

            # Fill open boundaries to form closed meshes
            fill_edges = [e for e in bm.edges if e.is_boundary]
            if fill_edges:
                bmesh.ops.edgeloop_fill(bm, edges=fill_edges)

            bm.select_flush(True)

    def _bisect_mesh(self, obj, plane_co, plane_no, flip, clear_inner):
        """Bisect the mesh with the given plane, optionally flipping and clearing inner geometry."""
        bm = bmesh.from_edit_mesh(obj.data)
        geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
        geom = [g for g in geom if not g.hide]

        if flip:
            plane_no = -plane_no

        # Perform bisect
        geom_cut = bmesh.ops.bisect_plane(bm, geom=geom, plane_co=plane_co, plane_no=plane_no, clear_outer=False, clear_inner=clear_inner)

        # Select the newly cut geometry
        for geom_elem in geom_cut['geom_cut']:
            geom_elem.select = True

        if clear_inner:
            bmesh.ops.contextual_create(bm, geom=geom_cut['geom_cut'], mat_nr=0)

        bm.select_flush(True)

    def infobar_hotkeys(self, layout, _context, _event):
        """Display hotkeys in the infobar."""
        row = layout.row(align=True)
        row.label(text='', icon='MOUSE_MOVE')
        row.label(text='Draw')
        row.separator(factor=12.0)
        row.label(text='', icon='MOUSE_LMB')
        row.label(text='Confirm')
        row.separator(factor=12.0)
        row.label(text='', icon='MOUSE_RMB')
        row.label(text='Cancel')
        row.separator(factor=12.0)
        row.label(text='', icon='EVENT_F')
        row.label(text='Flip Direction')
        row.separator(factor=12.0)
        row.label(text='', icon='EVENT_X')
        row.label(text='Change Mode')


class BOUT_OT_Cut2D(Bisect):
    """Operator to  bisect a mesh in Edit Mode."""
    bl_idname = "bout.mesh_line_cut"
    bl_label = "Mesh Line Cut"
    bl_description = "Cut, slice, or bisect the mesh"
    bl_options = {'REGISTER', 'UNDO', 'BLOCKING', 'GRAB_CURSOR'}


class BOUT_OT_Cut2D_TOOL(Bisect):
    """Tool variant of the CutLineOperator with predefined settings."""
    bl_idname = "bout.mesh_line_cut_tool"
    bl_label = "Mesh Line Cut Tool"
    bl_description = "Tool to bisect the mesh"
    bl_options = {'REGISTER', 'UNDO', 'BLOCKING', 'GRAB_CURSOR'}

    def invoke(self, context, event):
        """Initialize tool-specific settings before invoking the operator."""
        tool_prefs = addon.pref().tools.sketch
        self.mode = tool_prefs.mode
        return super().invoke(context, event)


def get_largest_dimension(obj):
    """Return the largest dimension of the object."""
    return max(obj.dimensions)


def bbox_center(obj):
    """Return the center of the bounding box of the object."""
    local_center = sum((Vector(b) for b in obj.bound_box), Vector()) * 0.125
    return obj.matrix_world @ local_center


class Theme(bpy.types.PropertyGroup):
    """Property group for operator theme colors."""
    guid: bpy.props.FloatVectorProperty(name="Cut Guide", description="Guide color", default=(0.0, 0.0, 0.0, 0.7), subtype='COLOR', size=4, min=0.0, max=1.0)
    line: bpy.props.FloatVectorProperty(name="Cut Line", description="Color of the cut line", default=(1.0, 0.0, 0.0, 0.8), subtype='COLOR', size=4, min=0.0, max=1.0)
    gradient: bpy.props.FloatVectorProperty(name="Cut Gradient", description="Color of the cut gradient", default=(1.0, 0.0, 0.0, 0.15), subtype='COLOR', size=4, min=0.0, max=1.0)
    slice_line: bpy.props.FloatVectorProperty(name="Slice Line", description="Color of the slice line", default=(1.0, 1.0, 0.0, 0.8), subtype='COLOR', size=4, min=0.0, max=1.0)
    slice_gradient: bpy.props.FloatVectorProperty(name="Slice Gradient", description="Color of the slice gradient", default=(1.0, 1.0, 0.0, 0.15), subtype='COLOR', size=4, min=0.0, max=1.0)
    bisect: bpy.props.FloatVectorProperty(name="Bisect", description="Color of the bisect line", default=(0.0, 0.88, 1.0, 0.8), subtype='COLOR', size=4, min=0.0, max=1.0)


types_classes = (
    Theme,
)


classes = (
    BOUT_OT_Cut2D,
    BOUT_OT_Cut2D_TOOL,
)
