import bpy
import bmesh

from mathutils import Vector

from .data import CreatedData, Config, Objects, Mouse, Pref, Shapes

from . import bevel, draw, extrude, ui

from ...utils import addon, scene, infobar, view3d
from ...bmeshutils import facet
from ...bmeshutils.mesh import set_copy


class Block(bpy.types.Operator):
    pref: bpy.props.PointerProperty(type=Pref)
    shapes: bpy.props.PointerProperty(type=Shapes)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ui = ui.DrawUI()
        self.ray = scene.ray_cast.Ray()
        self.mouse = Mouse()
        self.data = CreatedData()
        self.config = Config()
        self.objects = Objects()
        self.mode = 'DRAW'

    def set_config(self, context):
        '''Set the options'''
        raise NotImplementedError("Subclasses must implement the set_options method")

    def get_tool_prpoerties(self):
        '''Get the tool properties'''
        self.pref.bevel.segments = addon.pref().tools.block.form.segments

    def build_bmesh(self, context):
        '''Set the object data'''
        raise NotImplementedError("Subclasses must implement the set_object method")

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

    def invoke(self, context, event):
        '''Start the operator'''

        self._hide_transform_gizmo(context)
        self.config = self.set_config(context)
        self.get_tool_prpoerties()

        mouse_region_prev_x, mouse_region_prev_y = view3d.get_mouse_region_prev(event)
        self.mouse.init = Vector((mouse_region_prev_x, mouse_region_prev_y))
        self.ray = self.ray_cast(context)

        if not self.config.align.mode == 'CUSTOM':
            if not self.ray.hit:
                self._end(context)
                bpy.ops.bout.mesh_line_cut_tool('INVOKE_DEFAULT', release_confirm=True)
                return {'CANCELLED'}

        self.data.obj, self.data.bm = self.build_bmesh(context)

        self.objects.selected = context.selected_objects[:]
        self.objects.active = context.active_object

        self.data.copy.init = set_copy(self.data.obj)
        self._setup_drawing(context)

        created_mesh = self._draw_invoke(context)
        if not created_mesh:
            self._end(context)
            return {'CANCELLED'}

        context.window.cursor_set('SCROLL_XY')
        self._header(context)
        infobar.draw(context, event, self._infobar, blank=True)
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

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

    def execute(self, context):
        obj, bm = self.build_bmesh(context)

        self.build_geometry(obj, bm)
        self.update_bmesh(obj, bm, loop_triangles=True, destructive=True)

        if self.pref.mode != 'CREATE':
            self._boolean_invoke(obj, bm)

        self.save_props()

        return {'FINISHED'}

    def modal(self, context, event):
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
                    self._bevel_modal(context)

            if self.config.mode != 'CREATE':
                self._boolean_invoke(self.data.obj, self.data.bm)

            self._header(context)

        elif event.type in {'LEFTMOUSE', 'SPACE', 'RET', 'NUMPAD_ENTER'}:
            if event.value == 'RELEASE':

                if self.config.shape in {'BOX', 'CYLINDER'}:
                    self._extrude_invoke(context)
                    return {'RUNNING_MODAL'}

                self.set_offset()

            if self.mode == 'EXTRUDE':
                if self.config.mode == 'CREATE':
                    self._recalculate_normals(self.data.bm, self.data.extrude.faces)
                self.update_bmesh(self.data.obj, self.data.bm, loop_triangles=True, destructive=True)

            self.store_props()
            self.save_props()
            self._end(context)
            return {'FINISHED'}

        elif event.type == 'B':
            if event.value == 'PRESS':
                if self.config.shape in {'RECTANGLE', 'BOX', 'CYLINDER'}:
                    if self.config.shape == 'CYLINDER' and self.shapes.volume == '2D':
                        return {'RUNNING_MODAL'}
                    self.data.bevel.mode = 'OFFSET'
                    if self.mode == 'BEVEL' and self.shapes.volume == '3D':
                        self.data.bevel.type = '2D' if self.data.bevel.type == '3D' else '3D'
                    self._bevel_invoke(context)
                    if self.config.mode != 'CREATE':
                        self._boolean_invoke(self.data.obj, self.data.bm)

        elif event.type == 'S':
            if event.value == 'PRESS':
                if self.mode == 'BEVEL':
                    self.data.bevel.mode = 'SEGMENTS'
                    self._bevel_invoke(context)
                    if self.config.mode != 'CREATE':
                        self._boolean_invoke(self.data.obj, self.data.bm)

        elif event.type == 'Z':
            if event.value == 'PRESS':
                self.data.extrude.symmetry = not self.data.extrude.symmetry

        elif event.type in {'RIGHTMOUSE', 'ESC'}:
            self._end(context)
            return {'CANCELLED'}

        context.area.tag_redraw()
        return {'RUNNING_MODAL'}

    def _end(self, context):
        '''End the operator'''

        self._restore_transform_gizmo(context)

        if self.data.copy.init:
            bpy.data.meshes.remove(self.data.copy.init)
        if self.data.copy.draw:
            bpy.data.meshes.remove(self.data.copy.draw)

        self.mouse = None
        self.ray = None
        self.data = None
        self.config = None
        self.objects = None

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

        x_length, y_length = self.shapes.rectangle.co
        z_length = self.data.extrude.value
        radius = self.shapes.circle.radius
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

    def _setup_drawing(self, context):

        color = addon.pref().theme.axis
        self.ui.zaxis.create(context, color=color.z)
        self.ui.xaxis.create(context, color=color.x)
        self.ui.yaxis.create(context, color=color.y)
        color = addon.pref().theme.src.block
        face_color = color.cut if self.config.mode == 'CUT' else color.slice
        obj = self.data.obj
        self.ui.faces.create(context, obj=obj, color=face_color)
        self.ui.guid.create(context, color=color.guid)

    def _draw_invoke(self, context):
        result = draw.invoke(self, context)
        return result

    def _draw_modal(self, context, event):
        draw.modal(self, context, event)

    def _extrude_invoke(self, context):
        extrude.invoke(self, context)

    def _extrude_modal(self, context, event):
        extrude.modal(self, context, event)

    def _boolean_invoke(self, obj, bm):
        '''Boolean operation'''
        raise NotImplementedError("Subclasses must implement the _boolean_invoke method")

    def _bevel_invoke(self, context):
        '''Bevel the mesh'''
        bevel.invoke(self, context)

    def _bevel_modal(self, context):
        '''Bevel the mesh'''
        bevel.modal(self, context)
