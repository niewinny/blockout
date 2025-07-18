from dataclasses import dataclass, field
import math
import bpy

from mathutils import Vector

from ...shaders.draw import DrawPolyline
from ...shaders import handle
from ...utils import view3d, addon, infobar, modifier


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
    precision: float = 0.0


@dataclass
class Bevel:
    '''Dataclass for the modifier data'''
    obj: bpy.types.Object = None
    mod: bpy.types.Modifier = None
    new: bool = False
    initial_width: float = 0.0


@dataclass
class DrawUI:
    '''Dataclass for the UI drawing'''
    guide: handle.Polyline = field(default_factory=handle.Polyline)
    interface: handle.Interface = field(default_factory=handle.Interface)


class BevelOperatorBase(bpy.types.Operator):
    '''Base class for bevel operators with shared functionality'''
    bl_options = {'REGISTER', 'UNDO', 'BLOCKING', 'GRAB_CURSOR'}

    use_clamp_overlap: bpy.props.BoolProperty(name='Clamp Overlap', default=False)
    loop_slide: bpy.props.BoolProperty(name='Loop Slide', default=False)

    harden_normals: bpy.props.BoolProperty(name='Harden Normals', default=True)

    width_type: bpy.props.EnumProperty(
        name='Width Type',
        items=(
            ('OFFSET', 'Offset', 'Offset the bevel width'),
            ('WIDTH', 'Width', 'Set the bevel width'),
            ('PERCENT', 'Percent', 'Set the bevel width in percent'),
            ('DEPTH', 'Depth', 'Set the bevel depth'),
            ('ABSOLUTE', 'Absolute', 'Set the bevel width in absolute units')
        ),
        default='OFFSET'
    )
    width: bpy.props.FloatProperty(name='Offset', default=0.1, step=0.1, min=0, precision=3)
    segments: bpy.props.IntProperty(name='Segments', default=1, min=1, max=32)

    limit_method: bpy.props.EnumProperty(
        name='Limit Method',
        items=(
            ('NONE', 'None', 'No limit'),
            ('ANGLE', 'Angle', 'Limit by angle'),
            ('WEIGHT', 'Weight', 'Limit by weight'),
            ('VGROUP', 'Vertex Group', 'Limit by vertex group')
        ),
        default='ANGLE'
    )
    angle_limit: bpy.props.FloatProperty(name='Angle', default=0.523599, min=0, max=3.14159, precision=3)
    edge_weight: bpy.props.StringProperty(name='Edge Weight', default='bevel_weight_edge')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.mode: str = 'OFFSET'
        self.precision: bool = False
        self.snapping_ctrl: bool = False
        self.mouse: Mouse = Mouse()
        self.distance: Distance = Distance()
        self.ui: DrawUI = DrawUI()

        self.bevels: list = []

        self.saved_segments: int = 1
        self.saved_width: float = 0.0

    @classmethod
    def poll(cls, context):
        return context.area.type == 'VIEW_3D' and context.mode in {'EDIT_MESH', 'OBJECT'}

    def invoke(self, context, event):
        self._get_scene_properties(context)

        active_object = context.active_object if context.active_object and context.active_object.select_get() else None
        selected_objects = list(set(filter(None, context.selected_objects + [active_object])))
        self.mouse.median = sum([o.location for o in selected_objects], Vector()) / len(selected_objects) if selected_objects else Vector()

        self.mouse.co = self._get_intersect_point(context, event, self.mouse.median)
        self.mouse.init = self.mouse.co if self.mouse.co else self.mouse.median

        infobar.draw(context, event, self._infobar_hotkeys, blank=True)

        self._update_info(context)
        context.window.cursor_set('SCROLL_XY')
        self._setup_bevel(selected_objects, active_object)

        self._setup_drawing(context)
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):
        active_object = context.active_object if context.active_object and context.active_object.select_get() else None
        selected_objects = list(set(filter(None, context.selected_objects + [active_object])))

        self._update_bevel(selected_objects)
        self._set_scene_properties(context)

        return {'FINISHED'}

    def _bevel_properties(self):
        attributes = [
            "width",
            "harden_normals",
            "segments",
            "use_clamp_overlap",
            "loop_slide",
            "limit_method",
            "angle_limit",
            "edge_weight"
        ]
        return attributes

    def _get_bevel_properties(self, mod):
        attributes = self._bevel_properties()
        for attr in attributes:
            setattr(self, attr, getattr(mod, attr))

    def _set_bevel_properties(self, mod):
        attributes = self._bevel_properties()
        for attr in attributes:
            setattr(mod, attr, getattr(self, attr))

    def _update_bevel(self, selected_objects):
        for obj in selected_objects:
            mod = modifier.get(obj, 'BEVEL', -1)
            if not mod:
                mod = modifier.add(obj, "Bevel", 'BEVEL')
            self._set_bevel_properties(mod)

    def modal(self, context, event):
        if event.type == 'MOUSEMOVE':
            intersect_point = self._get_intersect_point(context, event, self.mouse.median)

            if intersect_point:
                self.mouse.co = intersect_point
                if self.mode == 'OFFSET':
                    self._set_width()
                elif self.mode == 'SEGMENTS':
                    self._set_segments(context, event)

                self._update_info(context)

            self._update_drawing(context)
            context.area.tag_redraw()

        elif event.type == 'LEFTMOUSE':
            self._set_scene_properties(context)
            self._end(context)
            return {'FINISHED'}

        elif event.type in {'RET', 'NUMPAD_ENTER', 'SPACE'} and event.value == 'PRESS':
            self._set_scene_properties(context)
            self._end(context)
            return {'FINISHED'}

        elif event.type in {'RIGHTMOUSE', 'ESC'} and event.value == 'PRESS':
            self._cancel()
            self._end(context)
            return {'CANCELLED'}

        elif event.type in {'LEFT_SHIFT', 'RIGHT_SHIFT'} and event.value == 'PRESS':
            self.precision = True
            self.distance.precision = self._calculate_distance()

        elif event.type in {'LEFT_SHIFT', 'RIGHT_SHIFT'} and event.value == 'RELEASE':
            self.precision = False

        elif event.type in {'LEFT_CTRL', 'RIGHT_CTRL'} and event.value == 'PRESS':
            self.snapping_ctrl = True

        elif event.type in {'LEFT_CTRL', 'RIGHT_CTRL'} and event.value == 'RELEASE':
            self.snapping_ctrl = False

        elif event.type == 'S' and event.value == 'PRESS':
            if not self.mode == 'SEGMENTS':
                self.mode = 'SEGMENTS'
                self.mouse.co = self._get_intersect_point(context, event, self.mouse.median)
                distance = self._calculate_distance()
                self.distance.length = distance - self.distance.delta
                self.mouse.saved = Vector((event.mouse_region_x, event.mouse_region_y))
                self.saved_segments = self.segments
                self._update_info(context)

        elif event.type == 'A' and event.value == 'PRESS':
            if not self.mode == 'OFFSET':
                self.mode = 'OFFSET'
                self.mouse.co = self._get_intersect_point(context, event, self.mouse.median)
                distance = self._calculate_distance()
                self.distance.delta = distance - self.distance.length

        elif event.type == 'N' and event.value == 'PRESS':
            self.harden_normals = not self.harden_normals
            for b in self.bevels:
                b.mod.harden_normals = self.harden_normals

        elif event.type == 'WHEELUPMOUSE' or event.type == 'NUMPAD_PLUS' or event.type == 'EQUAL':
            if event.value == 'PRESS':
                self.segments += 1
                for b in self.bevels:
                    b.mod.segments = self.segments
                self._update_info(context)
                self._update_drawing(context)

        elif event.type == 'WHEELDOWNMOUSE' or event.type == 'NUMPAD_MINUS' or event.type == 'MINUS':
            if event.value == 'PRESS':
                self.segments -= 1
                for b in self.bevels:
                    b.mod.segments = self.segments
                self._update_info(context)
                self._update_drawing(context)

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

    def _set_width(self):
        '''Set the offset based on the initial and current mouse position'''
        distance = self._calculate_distance()

        if self.precision:
            delta_distance = distance - self.distance.precision
            distance = self.distance.precision + (delta_distance * 0.1)

        distance += self.saved_width
        distance = distance if distance > self.distance.delta else self.distance.delta
        offset = distance - self.distance.delta

        # Apply snapping if Ctrl is held
        if self.snapping_ctrl:
            if self.precision:  # Both Shift and Ctrl held - snap to 0.01
                offset = round(offset / 0.01) * 0.01
            else:  # Only Ctrl held - snap to 0.1
                offset = round(offset / 0.1) * 0.1

        self.width = offset
        for b in self.bevels:
            b.mod.width = offset

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
            delta_segments = math.ceil(abs(distance) / 100)

            # Set segments directly based on distance
            new_segments = base_segments + delta_segments if distance > 0 else base_segments - delta_segments
            self.segments = max(1, new_segments)  # Ensure segments do not fall below 1

            for b in self.bevels:
                b.mod.segments = self.segments

    def _calculate_distance(self):
        '''Calculate the distance based on the initial and current mouse position'''
        intersect_point = self.mouse.co
        distance_fixed = 0.0
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

        info = f'Offset: {self.width:.3f}    Segments: {self.segments}'
        context.area.header_text_set(self._get_header_text() + '   ' + info)

    def _get_header_text(self):
        '''Get header text for operator type - to be overridden by subclasses'''
        return 'Bevel'

    def draw(self, _context):
        '''Draw the operator options'''
        layout = self.layout
        layout.use_property_split = True

        layout.prop(self, 'width')
        layout.prop(self, 'segments')

        layout.separator()

        header, body = layout.panel("geometry_panel", default_closed=True)
        header.label(text="Geometry")
        if body:
            col = body.column()
            col.prop(self, "use_clamp_overlap")
            col.prop(self, "loop_slide")

        header, body = layout.panel("shading_panel", default_closed=True)
        header.label(text="Shading")
        if body:
            col = body.column()
            col.prop(self, "harden_normals")

        layout.separator(factor=2)

    def _cancel(self):
        '''Cancel the operator'''

        for b in self.bevels:
            if b.new:
                modifier.remove(b.obj, b.mod)

    def _end(self, context):
        '''Cleanup and finish the operator'''

        infobar.remove(context)
        context.area.header_text_set(text=None)
        context.window.cursor_set('CROSSHAIR')

        self.ui.guide.remove()
        self.ui.interface.remove()

        context.area.tag_redraw()


    def _get_scene_properties(self, context):
        '''Override in subclasses to get from appropriate scene storage'''
        pass

    def _set_scene_properties(self, context):
        '''Override in subclasses to set to appropriate scene storage'''
        pass

    def _update_drawing(self, context):
        '''Update the drawing'''

        _theme = addon.pref().theme.ops.obj.bevel
        color = _theme.guide
        point = [(self.mouse.median, self.mouse.co)]
        self.ui.guide.callback.update_batch(point, color=color)

        width = self.width
        segments = self.segments
        mid_point = self.mouse.median + self.mouse.co / 2
        region = context.region
        rv3d = context.region_data
        point_2d = view3d.location_3d_to_region_2d(region, rv3d, mid_point)
        lines = [
            {"point": point_2d, "text_tuple": (f"Width: {width:.3f}", f"S: {segments}")}
        ]
        self.ui.interface.callback.update_batch(lines)

    def _setup_drawing(self, context, points=None):
        '''Setup the drawing'''

        _theme = addon.pref().theme.ops.obj.bevel
        color = _theme.guide

        points = points or [(Vector((0, 0, 0)), Vector((0, 0, 0)))]
        self.ui.guide.callback = DrawPolyline(points, width=1.2, color=color)
        self.ui.guide.handle = bpy.types.SpaceView3D.draw_handler_add(self.ui.guide.callback.draw, (context,), 'WINDOW', 'POST_VIEW')

        lines = []
        self.ui.interface.create(context, lines=lines)

    def _infobar_hotkeys(self, layout, _context, _event):
        '''Draw the infobar hotkeys'''

        row = layout.row(align=True)
        row.label(text='', icon='MOUSE_MOVE')
        row.label(text='Adjust Radius')
        row.separator(factor=6.0)
        row.label(text='', icon='MOUSE_LMB')
        row.label(text='Confirm')
        row.separator(factor=6.0)
        row.label(text='', icon='MOUSE_RMB')
        row.label(text='Cancel')
        row.separator(factor=6.0)
        row.label(text='', icon='EVENT_A')
        row.label(text='Offset')
        row.separator(factor=6.0)
        row.label(text='', icon='EVENT_S')
        row.label(text='Segments')


class BOUT_OT_ModBevelPinned(BevelOperatorBase):
    '''Bevel operator for last pinned modifier'''
    bl_idname = "bout.mod_bevel_pinned"
    bl_label = "Bevel Pinned"
    bl_description = "Edit last pinned bevel modifier"

    def _get_header_text(self):
        return 'Bevel (Pinned)'
    
    def _get_scene_properties(self, context):
        '''Get scene properties for pinned operator'''
        scene_props = context.scene.bout.ops.obj.bevel.pinned
        self.segments = scene_props.segments
        self.harden_normals = scene_props.harden_normals
    
    def _set_scene_properties(self, context):
        '''Set scene properties for pinned operator'''
        scene_props = context.scene.bout.ops.obj.bevel.pinned
        scene_props.segments = self.segments
        scene_props.harden_normals = self.harden_normals

    def _setup_bevel(self, selected_objects, active_object):
        for obj in selected_objects:
            mod = modifier.get(obj, 'BEVEL', -1)
            if not mod or not mod.use_pin_to_last:
                new = True
                mod = modifier.add(obj, "Bevel", 'BEVEL')
                self.width = 0.0
                self._set_bevel_properties(mod)
                mod.use_pin_to_last = True
            else:
                self._get_bevel_properties(mod)
                new = False

            self.bevels.append(Bevel(obj=obj, mod=mod, new=new))
            if obj == active_object:
                self.saved_width = mod.width


class BOUT_OT_ModBevelSingle(BevelOperatorBase):
    '''Bevel operator for single unpinned modifier'''
    bl_idname = "bout.mod_bevel_single"
    bl_label = "Bevel Single"
    bl_description = "Edit single unpinned bevel modifier"

    current_index: bpy.props.IntProperty(default=0)
    unpinned_count: bpy.props.IntProperty(default=0)

    def _get_header_text(self):
        if self.unpinned_count > 0:
            return f'Bevel Single [{self.current_index + 1}/{self.unpinned_count}]'
        return 'Bevel Single (No unpinned modifiers)'
    
    def _get_scene_properties(self, context):
        '''Get scene properties for base operator'''
        scene_props = context.scene.bout.ops.obj.bevel.base
        self.segments = scene_props.segments
        self.harden_normals = scene_props.harden_normals
    
    def _set_scene_properties(self, context):
        '''Set scene properties for base operator'''
        scene_props = context.scene.bout.ops.obj.bevel.base
        scene_props.segments = self.segments
        scene_props.harden_normals = self.harden_normals

    def _setup_bevel(self, selected_objects, active_object):
        # Only work with active object for single mode
        if active_object and active_object.type == 'MESH':
            unpinned_bevels = [m for m in active_object.modifiers 
                             if m.type == 'BEVEL' and not m.use_pin_to_last]
            
            self.unpinned_count = len(unpinned_bevels)
            
            if unpinned_bevels:
                # Start with last unpinned
                self.current_index = len(unpinned_bevels) - 1
                mod = unpinned_bevels[self.current_index]
                self._get_bevel_properties(mod)
                self.bevels.append(Bevel(obj=active_object, mod=mod, new=False))
                self.saved_width = mod.width
            else:
                # No unpinned modifiers found - create new one
                mod = modifier.add(active_object, "Bevel", 'BEVEL')
                self.width = 0.0
                self._set_bevel_properties(mod)
                # Don't pin it - this is for unpinned modifiers
                self.bevels.append(Bevel(obj=active_object, mod=mod, new=True))
                self.saved_width = 0.0
                self.unpinned_count = 1
                self.current_index = 0

    def _navigate_modifier(self, direction):
        '''Navigate between unpinned modifiers'''
        if not self.bevels:
            return
            
        obj = self.bevels[0].obj
        unpinned_bevels = [m for m in obj.modifiers 
                         if m.type == 'BEVEL' and not m.use_pin_to_last]
        
        if not unpinned_bevels:
            return
            
        # Save current properties before switching
        current_mod = self.bevels[0].mod
        self._set_bevel_properties(current_mod)
        
        # Navigate
        if direction == 'NEXT':
            self.current_index = (self.current_index + 1) % len(unpinned_bevels)
        else:
            self.current_index = (self.current_index - 1) % len(unpinned_bevels)
        
        # Update to new modifier
        new_mod = unpinned_bevels[self.current_index]
        self._get_bevel_properties(new_mod)
        self.bevels[0] = Bevel(obj=obj, mod=new_mod, new=False)
        self.saved_width = new_mod.width

    def modal(self, context, event):
        # Handle navigation
        if event.type == 'TAB' and event.value == 'PRESS':
            if self.unpinned_count > 1:
                if event.shift:
                    self._navigate_modifier('PREVIOUS')
                else:
                    self._navigate_modifier('NEXT')
                self._update_info(context)
                self._update_drawing(context)
                return {'RUNNING_MODAL'}
        
        # Call parent modal
        return super().modal(context, event)

    def _infobar_hotkeys(self, layout, _context, _event):
        '''Draw the infobar hotkeys'''
        super()._infobar_hotkeys(layout, _context, _event)
        
        if self.unpinned_count > 1:
            row = layout.row(align=True)
            row.separator(factor=6.0)
            row.label(text='', icon='EVENT_TAB')
            row.label(text='Next/Previous')


class BOUT_OT_ModBevelAll(BevelOperatorBase):
    '''Bevel operator for all unpinned modifiers'''
    bl_idname = "bout.mod_bevel_all"
    bl_label = "Bevel All"
    bl_description = "Edit all unpinned bevel modifiers"

    def _get_header_text(self):
        count = len(self.bevels)
        if count > 0:
            return f'Bevel All ({count} modifiers)'
        return 'Bevel All (No unpinned modifiers)'
    
    def _get_scene_properties(self, context):
        '''Get scene properties for base operator'''
        scene_props = context.scene.bout.ops.obj.bevel.base
        self.segments = scene_props.segments
        self.harden_normals = scene_props.harden_normals
    
    def _set_scene_properties(self, context):
        '''Set scene properties for base operator'''
        scene_props = context.scene.bout.ops.obj.bevel.base
        scene_props.segments = self.segments
        scene_props.harden_normals = self.harden_normals

    def _setup_bevel(self, selected_objects, active_object):
        for obj in selected_objects:
            unpinned_bevels = [m for m in obj.modifiers 
                             if m.type == 'BEVEL' and not m.use_pin_to_last]
            
            for mod in unpinned_bevels:
                # Store initial width for relative adjustment
                self.bevels.append(Bevel(obj=obj, mod=mod, new=False, 
                                       initial_width=mod.width))
        
        if self.bevels:
            # Use properties from first modifier as reference
            self._get_bevel_properties(self.bevels[0].mod)
            self.saved_width = 0.0  # Start from 0 for relative adjustment
        else:
            # No unpinned modifiers found - create new ones
            for obj in selected_objects:
                mod = modifier.add(obj, "Bevel", 'BEVEL')
                # Don't pin it - this is for unpinned modifiers
                self.bevels.append(Bevel(obj=obj, mod=mod, new=True, initial_width=0.0))
            
            if self.bevels:
                self.width = 0.0
                self._set_bevel_properties(self.bevels[0].mod)
                self.saved_width = 0.0

    def _set_width(self):
        '''Set the offset with relative adjustment for each modifier'''
        distance = self._calculate_distance()

        if self.precision:
            delta_distance = distance - self.distance.precision
            distance = self.distance.precision + (delta_distance * 0.1)

        # Calculate the adjustment amount
        adjustment = distance - self.distance.delta

        # Apply snapping if Ctrl is held
        if self.snapping_ctrl:
            if self.precision:  # Both Shift and Ctrl held - snap to 0.01
                adjustment = round(adjustment / 0.01) * 0.01
            else:  # Only Ctrl held - snap to 0.1
                adjustment = round(adjustment / 0.1) * 0.1

        # Apply relative changes to each modifier
        for bevel in self.bevels:
            new_width = bevel.initial_width + adjustment
            bevel.mod.width = max(0.0, new_width)
        
        # Update display width (show adjustment amount)
        self.width = adjustment


class Theme(bpy.types.PropertyGroup):
    guide: bpy.props.FloatVectorProperty(name="Bevel Guid", description="Color of the guide line", size=4, subtype='COLOR', default=(0.0, 0.0, 0.0, 0.8), min=0.0, max=1.0)


class SceneBase(bpy.types.PropertyGroup):
    '''Base scene properties for bevel operators'''
    segments: bpy.props.IntProperty(name='Segments', default=5, min=1, max=32)
    harden_normals: bpy.props.BoolProperty(name='Harden Normals', default=False)


class ScenePinned(bpy.types.PropertyGroup):
    '''Scene properties for pinned bevel operator'''
    segments: bpy.props.IntProperty(name='Segments', default=1, min=1, max=32)
    harden_normals: bpy.props.BoolProperty(name='Harden Normals', default=True)


class Scene(bpy.types.PropertyGroup):
    '''Scene properties container for all bevel operators'''
    base: bpy.props.PointerProperty(type=SceneBase)
    pinned: bpy.props.PointerProperty(type=ScenePinned)


types_classes = (
    Theme,
    SceneBase,
    ScenePinned,
    Scene,
)


classes = (
    BOUT_OT_ModBevelPinned,
    BOUT_OT_ModBevelSingle,
    BOUT_OT_ModBevelAll,
)