import bpy
import bmesh

from mathutils import Vector

from .data import CreatedData, Config, Objects, Mouse, Pref, Shape, Modifiers

from . import bevel, draw, extrude, ui, orientation, bisect

from ...utils import addon, scene, infobar, view3d
from ...bmeshutils import facet
from ...bmeshutils.mesh import set_copy


class Block(bpy.types.Operator):
    pref: bpy.props.PointerProperty(type=Pref)
    shape: bpy.props.PointerProperty(type=Shape)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ui = ui.DrawUI()
        self.ray = scene.ray_cast.Ray()
        self.mouse = Mouse()
        self.data = CreatedData()
        self.config = Config()
        self.objects = Objects()
        self.modifiers = Modifiers()
        self.mode = 'DRAW'

    def set_config(self, context):
        '''Set the options'''
        raise NotImplementedError("Subclasses must implement the set_options method")

    def get_tool_prpoerties(self):
        '''Get the tool properties'''
        self.data.bevel.round.segments = addon.pref().tools.block.form.segments
        self.data.bevel.fill.segments = addon.pref().tools.block.form.segments

    def get_object(self, context, store_properties=True):
        '''Set the object data'''
        raise NotImplementedError("Subclasses must implement the get_object method")

    def build_bmesh(self, obj):
        '''Set the object data'''
        raise NotImplementedError("Subclasses must implement the get_object method")

    def build_geometry(self, obj, bm):
        '''Build the geometry'''
        raise NotImplementedError("Subclasses must implement the build_geometry method")

    def update_bmesh(self, obj, bm, loop_triangles=False, destructive=False):
        '''Update the bmesh data'''
        raise NotImplementedError("Subclasses must implement the update_bmesh method")

    def ray_cast(self, context):
        '''Ray cast the scene'''
        raise NotImplementedError("Subclasses must implement the ray_cast method")

    def draw(self, context):
        '''Draw the operator'''
        layout = self.layout
        layout.use_property_split = True

        if self.pref.bisect.running:
            col = layout.column(align=True)
            col.prop(self.pref.bisect.plane, 'location', text="Location")
            col.prop(self.pref.bisect.plane, 'normal', text="Normal")
            layout.prop(self.pref.bisect, 'mode', text="Mode")
            layout.prop(self.pref.bisect, 'flip', text="Flip")
            return

        shape = self.pref.shape
        match shape:
            case 'RECTANGLE':
                col = layout.column(align=True)
                col.prop(self.shape.rectangle, 'co', text="Dimensions")
                layout.prop(self.pref, 'offset', text="Offset")
                col = layout.column(align=True)
                row = col.row(align=True)
                row.prop(self.pref.bevel, 'offset', text="Bevel")
                row.prop(self.pref.bevel, 'segments', text="")
            case 'BOX':
                col = layout.column(align=True)
                col.prop(self.shape.rectangle, 'co', text="Dimensions")
                col.prop(self.pref, 'extrusion', text="Z")
                layout.prop(self.pref, 'offset', text="Offset")
                col = layout.column(align=True, heading="Bevel")
                row = col.row(align=True)
                row.prop(self.pref.bevel.round, 'enable', text="Round", toggle=True)
                row.prop(self.pref.bevel.round, 'offset', text="")
                row.prop(self.pref.bevel.round, 'segments', text="")
                row = col.row(align=True)
                row.prop(self.pref.bevel.fill, 'enable', text="Fill", toggle=True)
                row.prop(self.pref.bevel.fill, 'offset', text="")
                row.prop(self.pref.bevel.fill, 'segments', text="")
            case 'CIRCLE':
                layout.prop(self.shape.circle, 'radius', text="Radius")
                layout.prop(self.shape.circle, 'verts', text="Verts")
                layout.prop(self.pref, 'offset', text="Offset")
            case 'CYLINDER':
                layout.prop(self.shape.circle, 'radius', text="Radius")
                layout.prop(self.pref, 'extrusion', text="Dimensions Z")
                layout.prop(self.shape.circle, 'verts', text="Verts")
                layout.prop(self.pref, 'offset', text="Offset")

    def _hide_transform_gizmo(self, context):
        self.pref.transform_gizmo = context.space_data.show_gizmo_context
        context.space_data.show_gizmo_context = False

    def _restore_transform_gizmo(self, context):
        context.space_data.show_gizmo_context = self.pref.transform_gizmo

    def _infobar(self, layout, context, event):
        '''Draw the infobar hotkeys'''
        ui.hotkeys(self, layout, context, event)

    def _recalculate_normals(self, bm, faces_indexes):
        '''Recalculate the normals'''
        faces = [bm.faces[index] for index in faces_indexes]
        bmesh.ops.recalc_face_normals(bm, faces=faces)

    def store_props(self):
        '''Finish the operator'''
        self.pref.bisect.plane.location = self.data.bisect.plane[0]
        self.pref.bisect.plane.normal = self.data.bisect.plane[1]
        self.pref.bisect.flip = self.data.bisect.flip
        self.pref.bisect.mode = self.data.bisect.mode
        self.pref.plane.location = self.data.draw.plane[0]
        self.pref.plane.normal = self.data.draw.plane[1]
        self.pref.direction = self.data.draw.direction
        self.pref.extrusion = self.data.extrude.value
        self.pref.symmetry_extrude = self.data.extrude.symmetry
        self.pref.symmetry_draw = self.data.draw.symmetry
        self.pref.shape = self.config.shape
        self.pref.mode = self.config.mode
        self.pref.bevel.round.enable = self.data.bevel.round.enable
        self.pref.bevel.round.offset = self.data.bevel.round.offset
        self.pref.bevel.round.segments = self.data.bevel.round.segments
        self.pref.bevel.fill.enable = self.data.bevel.fill.enable
        self.pref.bevel.fill.offset = self.data.bevel.fill.offset
        self.pref.bevel.fill.segments = self.data.bevel.fill.segments
        self.pref.detected = self.objects.detected
        if self.config.mode != 'ADD':
            self.pref.offset = self.config.align.offset
 
    def save_props(self):
        '''Store the properties'''
        addon.pref().tools.block.form.segments = self.pref.bevel.round.segments

    def set_offset(self):
        '''Set the offset'''
        bm = self.data.bm
        obj = self.data.obj
        face = self.data.bm.faces[self.data.draw.face]
        normal = self.data.draw.plane[1]
        offset = self.config.align.offset

        if self.config.mode != 'ADD':
            facet.set_z(face, normal, offset)

        self.update_bmesh(obj, bm, loop_triangles=True, destructive=True)

    def invoke(self, context, event):
        '''Start the operator'''

        self._hide_transform_gizmo(context)
        self.config = self.set_config(context)
        self.pref.type = self.config.type
        self.get_tool_prpoerties()

        mouse_region_prev_x, mouse_region_prev_y = view3d.get_mouse_region_prev(event)
        self.mouse.init = Vector((mouse_region_prev_x, mouse_region_prev_y))
        self.ray = self.ray_cast(context)

        self.objects.selected = [obj for obj in context.selected_objects if obj.type == 'MESH']
        self.objects.active = context.active_object if context.active_object and context.active_object.type == 'MESH' and context.active_object.select_get() else None
        self.objects.detected = self.ray.obj.name if self.ray.hit else ''

        if len(self.objects.selected) > 0:
            if not self.config.align.mode == 'CUSTOM' and not self.ray.hit:
                self.mode = 'BISECT'
                self.pref.bisect.running = True

        self.data.obj = self.get_object(context)
        if not self.data.obj:
            self.report({'ERROR'}, 'Failed to detect Drawing Plane: Set Custom orientation or pick Object')
            return {'CANCELLED'}
        self.data.bm = self.build_bmesh(self.data.obj)
        self.data.copy.init = set_copy(self.data.obj)

        orientation.build(self, context)

        ui.setup(self, context)

        if self.mode != 'BISECT':

            if not self.data.draw.plane:
                self.report({'ERROR'}, 'Failed to detect drawing plane')
                return {'CANCELLED'}

            draw.update_ui(self)
            orientation.make_local(self)

            if self.config.type == 'EDIT_MESH':
                bpy.ops.mesh.select_all(action='DESELECT')
            created_mesh = self._draw_invoke(context)
            if not created_mesh:
                self._end(context)
                return {'CANCELLED'}

        context.window.cursor_set('SCROLL_XY')
        self._header(context)
        infobar.draw(context, event, self._infobar, blank=True)
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):
        '''Execute the operator'''

        depsgraph = context.view_layer.depsgraph
        depsgraph.update()

        obj = self.get_object(context, store_properties=False)
        bm = self.build_bmesh(obj)

        if self.pref.bisect.running:
            bisect_data = (self.pref.bisect.plane.location, self.pref.bisect.plane.normal, self.pref.bisect.flip, self.pref.bisect.mode)
            bisect.execute(self, context, obj, bm, bisect_data)
        else:
            self.build_geometry(obj, bm)
        self.save_props()

        return {'FINISHED'}

    def modal(self, context, event):
        '''Run the operator modal'''

        if event.type == 'MIDDLEMOUSE':
            return {'PASS_THROUGH'}

        if event.type == 'MOUSEMOVE':
            self.mouse.co = Vector((event.mouse_region_x, event.mouse_region_y))

            match self.mode:
                case 'DRAW':
                    self._draw_modal(context, event)
                case 'EXTRUDE':
                    self._extrude_modal(context, event)
                case 'BEVEL':
                    self._bevel_modal(context, event)
                case 'BISECT':
                    bisect.modal(self, context, event)

            self._boolean(self.config.mode, self.data.obj, self.data.bm)

            self._header(context)

        elif event.type in {'LEFTMOUSE', 'SPACE', 'RET', 'NUMPAD_ENTER'}:

            match self.mode:
                case 'DRAW' | 'BEVEL':
                    if event.value == 'RELEASE':
                        if self.config.shape in {'BOX', 'CYLINDER'}:
                            self._extrude_invoke(context, event)
                            return {'RUNNING_MODAL'}
                        self.set_offset()

                case 'EXTRUDE':
                    if self.config.mode == 'ADD':
                        self._recalculate_normals(self.data.bm, self.data.extrude.faces)
                    self.update_bmesh(self.data.obj, self.data.bm, loop_triangles=True, destructive=True)
                case 'BISECT':
                    bisect_data = (self.data.bisect.plane[0], self.data.bisect.plane[1], self.data.bisect.flip, self.data.bisect.mode)
                    bisect.execute(self, context, self.data.obj, self.data.bm, bisect_data)

            self.store_props()
            self.save_props()
            self._finish(context)
            self._end(context)
            return {'FINISHED'}

        elif event.type == 'B':
            if event.value == 'PRESS':
                if self.config.shape in {'RECTANGLE', 'BOX', 'CYLINDER'}:
                    if self.config.shape == 'CYLINDER' and self.shape.volume == '2D':
                        return {'RUNNING_MODAL'}
                    self.data.bevel.mode = 'OFFSET'
                    if self.mode == 'BEVEL' and self.shape.volume == '3D':
                        self.data.bevel.type = 'ROUND' if self.data.bevel.type == 'FILL' else 'FILL'
                    self._bevel_invoke(context, event)
                    if self.config.mode != 'ADD':
                        self._boolean(self.config.mode, self.data.obj, self.data.bm)

        elif event.type == 'S':
            if event.value == 'PRESS':
                if self.mode == 'BEVEL':
                    self.data.bevel.mode = 'SEGMENTS'
                    self._bevel_invoke(context, event)
                    if self.config.mode != 'ADD':
                        self._boolean(self.config.mode, self.data.obj, self.data.bm)

        elif event.type == 'Z':
            if event.value == 'PRESS':
                self.data.extrude.symmetry = not self.data.extrude.symmetry

        elif event.type in {'RIGHTMOUSE', 'ESC'}:
            self._cancel(context)
            self._end(context)
            return {'CANCELLED'}

        context.area.tag_redraw()
        return {'RUNNING_MODAL'}

    def _finish(self, context):
        '''Finish the operator'''

    def _cancel(self, context):
        if self.objects.created:
            mesh = self.objects.created.data
            bpy.data.objects.remove(self.objects.created)
            bpy.data.meshes.remove(mesh)

    def _end(self, context):
        '''End the operator'''

        self._restore_transform_gizmo(context)

        for mesh_type in ('init', 'draw', 'boolean'):
            mesh = getattr(self.data.copy, mesh_type, None)
            if mesh:
                bpy.data.meshes.remove(mesh)

        self.mouse = None
        self.ray = None
        self.data = None
        self.config = None
        self.objects = None
        self.modifiers = None

        self.ui.clear()
        self.ui.clear_higlight()

        context.window.cursor_set('CROSSHAIR')
        context.area.header_text_set(text=None)
        infobar.remove(context)

    def _header_text(self):
        '''Set the header text'''
        raise NotImplementedError("Subclasses must implement the _header method")

    def _header(self, context):
        '''Set the header text'''

        if self.mode == 'BISECT':
            header = f'Bisec: mode:{self.data.bisect.mode}, flip:{self.data.bisect.flip}'
            context.area.header_text_set(text=header)
            return

        text = self._header_text()

        x_length, y_length = self.shape.rectangle.co
        z_length = self.data.extrude.value
        radius = self.shape.circle.radius
        dimentions = ''

        shape = self.config.shape
        if self.mode == 'BEVEL':
            text = 'Bevel'
            offset = self.data.bevel.round.offset if self.data.bevel.type == 'ROUND' else self.data.bevel.fill.offset
            segments = self.data.bevel.round.segments if self.data.bevel.type == 'ROUND' else self.data.bevel.fill.segments
            dimentions = f'Type:{self.data.bevel.type}, Offset:{offset:.4f}, Segments:{segments}'
        else:
            match shape:
                case 'RECTANGLE': dimentions = f' Dx:{x_length:.4f},  Dy:{y_length:.4f}'
                case 'CIRCLE': dimentions = f' Radius:{radius:.4f}'
                case 'BOX': dimentions = f' Dx:{x_length:.4f},  Dy:{y_length:.4f},  Dz:{z_length:.4f}'
                case 'CYLINDER': dimentions = f' Radius:{radius:.4f},  Dz:{z_length:.4f}'

        header = f'{text} {dimentions}'
        context.area.header_text_set(text=header)

    def _draw_invoke(self, context):
        result = draw.invoke(self, context)
        return result

    def _draw_modal(self, context, event):
        draw.modal(self, context, event)

    def _extrude_invoke(self, context, event):
        extrude.invoke(self, context, event)

    def _extrude_modal(self, context, event):
        extrude.modal(self, context, event)

    def _boolean(self, mode, obj, bm):
        '''Execute the boolean operation'''

    def _bevel_invoke(self, context, event):
        '''Bevel the mesh'''
        bevel.invoke(self, context, event)

    def _bevel_modal(self, context, event):
        '''Bevel the mesh'''
        bevel.modal(self, context, event)

    def _bisect_invoke(self, context, event):
        '''Bisect the mesh'''
