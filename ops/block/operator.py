import bpy
import bmesh

from mathutils import Vector

from .data import CreatedData, Config, Objects, Mouse, Pref, Shape, Modifiers

from . import bevel, draw, extrude, ui, orientation

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
        self.data.bevel.segments = addon.pref().tools.block.form.segments

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
        '''Draw panel'''
        raise NotImplementedError("Subclasses must implement the ray_cast method")

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
        self.pref.plane.location = self.data.draw.plane[0]
        self.pref.plane.normal = self.data.draw.plane[1]
        self.pref.direction = self.data.draw.direction
        self.pref.extrusion = self.data.extrude.value
        self.pref.symmetry_extrude = self.data.extrude.symmetry
        self.pref.symmetry_draw = self.data.draw.symmetry
        self.pref.shape = self.config.shape
        self.pref.mode = self.config.mode
        self.pref.bevel.offset = self.data.bevel.offset
        self.pref.bevel.type = self.data.bevel.type
        self.pref.bevel.segments = self.data.bevel.segments
        self.pref.detected = self.objects.detected
        if self.config.mode != 'CREATE':
            self.pref.offset = self.config.align.offset

    def save_props(self):
        '''Store the properties'''
        addon.pref().tools.block.form.segments = self.pref.bevel.segments

    def set_offset(self):
        '''Set the offset'''
        bm = self.data.bm
        obj = self.data.obj
        face = self.data.bm.faces[self.data.draw.face]
        normal = self.data.draw.plane[1]
        offset = self.config.align.offset

        if self.config.mode != 'CREATE':
            facet.set_z(face, normal, offset)

        self.update_bmesh(obj, bm, loop_triangles=True, destructive=True)

    def invoke(self, context, event):
        '''Start the operator'''

        self._hide_transform_gizmo(context)
        self.config = self.set_config(context)
        self.get_tool_prpoerties()

        mouse_region_prev_x, mouse_region_prev_y = view3d.get_mouse_region_prev(event)
        self.mouse.init = Vector((mouse_region_prev_x, mouse_region_prev_y))
        self.ray = self.ray_cast(context)

        self.objects.selected = context.selected_objects[:]
        self.objects.active = context.active_object

        if not self.config.align.mode == 'CUSTOM' and not self.ray.hit:
            self.mode = 'BISECT'

        if self.mode != 'BISECT':
            self.data.obj = self.get_object(context)
            self.data.bm = self.build_bmesh(self.data.obj)
            self.data.copy.init = set_copy(self.data.obj)

            orientation.build(self, context)

            self._setup_ui(context)
            self._update_ui()

            orientation.make_local(self)

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
                    pass

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
                    if self.config.mode == 'CREATE':
                        self._recalculate_normals(self.data.bm, self.data.extrude.faces)
                    self.update_bmesh(self.data.obj, self.data.bm, loop_triangles=True, destructive=True)
                case 'BISECT':
                    pass

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
                        self.data.bevel.type = '2D' if self.data.bevel.type == '3D' else '3D'
                    self._bevel_invoke(context, event)
                    if self.config.mode != 'CREATE':
                        self._boolean(self.config.mode, self.data.obj, self.data.bm)

        elif event.type == 'S':
            if event.value == 'PRESS':
                if self.mode == 'BEVEL':
                    self.data.bevel.mode = 'SEGMENTS'
                    self._bevel_invoke(context, event)
                    if self.config.mode != 'CREATE':
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
        text = self._header_text()

        x_length, y_length = self.shape.rectangle.co
        z_length = self.data.extrude.value
        radius = self.shape.circle.radius
        dimentions = ''

        shape = self.config.shape
        if self.mode == 'BEVEL':
            text = 'Bevel'
            dimentions = f'Type:{self.data.bevel.type}, Offset:{self.data.bevel.offset:.4f},  Segments:{self.data.bevel.segments}'
        else:
            match shape:
                case 'RECTANGLE': dimentions = f' Dx:{x_length:.4f},  Dy:{y_length:.4f}'
                case 'CIRCLE': dimentions = f' Radius:{radius:.4f}'
                case 'BOX': dimentions = f' Dx:{x_length:.4f},  Dy:{y_length:.4f},  Dz:{z_length:.4f}'
                case 'CYLINDER': dimentions = f' Radius:{radius:.4f},  Dz:{z_length:.4f}'

        header = f'{text} {dimentions}'
        context.area.header_text_set(text=header)

    def _setup_ui(self, context):

        color = addon.pref().theme.axis
        self.ui.zaxis.create(context, color=color.z)
        self.ui.xaxis.create(context, color=color.x)
        self.ui.yaxis.create(context, color=color.y)
        color = addon.pref().theme.ops.block
        face_color = color.cut if self.config.mode == 'CUT' else color.slice
        obj = self.data.obj
        self.ui.faces.create(context, obj=obj, color=face_color)
        self.ui.guid.create(context, color=color.guid)

    def _update_ui(self):
        '''Update the drawing'''
        if self.config.align.mode != 'CUSTOM':
            plane = self.data.draw.plane
            direction = self.data.draw.direction
            world_origin, world_normal = plane
            x_axis_point = world_origin + direction
            y_direction = world_normal.cross(direction).normalized()
            y_axis_point = world_origin + y_direction
            self.ui.xaxis.callback.update_batch((world_origin, x_axis_point))
            self.ui.yaxis.callback.update_batch((world_origin, y_axis_point))

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
