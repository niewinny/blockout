from dataclasses import dataclass, field
import bpy
import bmesh

from mathutils import Vector
from ...shaders import handle
from ...utils import addon, scene, infobar, view3d
from ...bmeshutils import orientation, rectangle


@dataclass
class Config:
    '''Dataclass for storing options'''
    shape: str = 'RECTANGLE'
    align: str = 'FACE'
    align_face: str = 'NORMAL'
    align_view: str = 'WORLD'


@dataclass
class CreatedData:
    '''Dataclass for storing'''
    obj: bpy.types.Object = None
    bm: bmesh.types.BMesh = None
    face: bmesh.types.BMFace = None
    direction: Vector = Vector((0, 1, 0))
    plane: tuple = (Vector(), Vector())
    is_local: bool = False


@dataclass
class Objects:
    '''Dataclass for storing'''
    active: bpy.types.Object = None
    selected: list = field(default_factory=list)


@dataclass
class Mouse:
    """Dataclass for tracking mouse positions."""
    init: Vector = Vector()
    co: Vector = Vector()


@dataclass
class DrawUI:
    '''Dataclass for the UI  drawing'''
    face: handle.Face = field(default_factory=handle.Face)


class DrawMesh(bpy.types.Operator):
    '''Draw a polygon mesh'''

    def __init__(self):
        self.ui = DrawUI()
        self.mouse = Mouse()
        self.ray = scene.ray_cast.Ray()
        self.data = CreatedData()
        self.config = Config()
        self.objects = Objects()

    def set_config(self, context):
        '''Set the options'''
        raise NotImplementedError("Subclasses must implement the set_options method")

    def invoke_data(self, context):
        '''Set the object data'''
        raise NotImplementedError("Subclasses must implement the set_object method")

    def update_bmesh(self, loop_triangles=False, destructive=False):
        '''Update the bmesh data'''
        raise NotImplementedError("Subclasses must implement the update_bmesh method")

    def invoke(self, context, event):
        self.config = self.set_config(context)
        mouse_region_prev_x, mouse_region_prev_y = view3d.get_mouse_region_prev(event)
        self.mouse.init = Vector((mouse_region_prev_x, mouse_region_prev_y))
        self.ray = scene.ray_cast.selected(context, self.mouse.init)

        self.objects.selected = context.selected_objects[:]
        self.objects.active = context.active_object

        self.invoke_data(context)

        created_mesh = self._build_mesh(context)
        if not created_mesh:
            self.report({'ERROR'}, 'Failed to create mesh data')
            return {'CANCELLED'}

        self.update_bmesh(loop_triangles=True, destructive=True)

        context.window.cursor_set('SCROLL_XY')
        self._header(context)
        infobar.draw(context, event, None)
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def modal(self, context, event):

        if event.type == 'MIDDLEMOUSE':
            return {'PASS_THROUGH'}

        if event.type == 'MOUSEMOVE':
            self.mouse.co = (event.mouse_region_x, event.mouse_region_y)
            self._draw_mesh(context)

        elif event.type in {'LEFTMOUSE', 'SPACE', 'RET', 'NUMPAD_ENTER'}:
            self._end(context)
            return {'FINISHED'}

        elif event.type in {'RIGHTMOUSE', 'ESC'}:
            self._end(context)
            return {'CANCELLED'}

        context.area.tag_redraw()
        return {'RUNNING_MODAL'}

    def _end(self, context):
        '''End the operator'''
        self.ui = None
        self.mouse = None
        self.ray = None
        self.data = None
        self.config = None
        self.objects = None

        context.window.cursor_set('CROSSHAIR')
        context.area.header_text_set(text=None)
        infobar.remove(context)

    def _heade_text(self):
        '''Set the header text'''
        raise NotImplementedError("Subclasses must implement the _header method")

    def _header(self, context):
        '''Set the header text'''
        text = self._header_text()
        context.area.header_text_set(text=text)

    def _build_mesh(self, context):
        '''Build the mesh data'''

        obj = self.data.obj

        align_view = self.config.align_view
        match align_view:
            case 'WORLD': depth = Vector((0, 0, 0))
            case 'OBJECT': depth = self.objects.active.location
            case 'CURSOR': depth = context.scene.cursor.location

        def get_view_direction(local=False):
            direction_world = orientation.direction_from_view(context)
            plane_world = orientation.plane_from_view(context, self.mouse.init, depth)

            if local:
                direction_local = orientation.direction_local(obj, direction_world)
                plane_local = orientation.plane_local(obj, plane_world)
                return direction_local, plane_local

            return direction_world, plane_world

        def get_face_direction(local=False):
            hit_obj = self.ray.obj
            hit_bm = bmesh.new()
            hit_bm.from_mesh(hit_obj.data)
            hit_bm.faces.ensure_lookup_table()
            hit_face = hit_bm.faces[self.ray.index]
            loc = self.ray.location

            align_face = self.config.align_face
            match align_face:
                case 'NORMAL': direction_local = orientation.direction_from_normal(hit_face.normal)
                case 'CLOSEST': direction_local = orientation.direction_from_closest_edge(hit_face, loc)
                case 'LONGEST': direction_local = orientation.direction_from_longest_edge(hit_face)

            plane_world = (self.ray.location, self.ray.normal)

            if local:
                plane_local = orientation.plane_local(obj, plane_world)
                return direction_local, plane_local

            direction_world = self.ray.obj.matrix_world.to_3x3() @ direction_local
            return direction_world, plane_world

        direction, plane = get_view_direction(self.data.is_local)

        if self.config.align == 'FACE':
            if self.ray.hit:
                direction, plane = get_face_direction(self.data.is_local)

        self.data.direction = direction
        self.data.plane = plane
        self.data.face = rectangle.create_rectangle(self.data.bm, self.data.plane)

        return True

    def _draw_mesh(self, context):
        obj = self.data.obj

        region = context.region
        re3d = context.region_data
        plane = self.data.plane
        direction = self.data.direction
        matrix_world = obj.matrix_world
        mouse_point_on_plane = view3d.region2d_to_plane3d(region, re3d, self.mouse.co, plane, matrix=matrix_world)

        if mouse_point_on_plane is None:
            return

        rectangle.expand_rectangle(self.data.face, plane, mouse_point_on_plane, direction)

        self.update_bmesh()


class BOUT_OT_DrawMeshTool(DrawMesh):
    bl_idname = 'bout.draw_mesh_tool'
    bl_label = 'Draw Polygon'
    bl_options = {'REGISTER', 'UNDO', 'BLOCKING'}
    bl_description = "Tool for drawing a mesh"

    @classmethod
    def poll(cls, context):
        return context.area.type == 'VIEW_3D' and context.mode == 'EDIT_MESH'

    def _header_text(self):
        '''Set the header text'''
        pref = addon.pref().tools.sketch
        text = f"Shape: {pref.shape.capitalize()}"

        return text

    def set_config(self, context):
        config = Config()
        config.shape = addon.pref().tools.sketch.shape
        config.align = addon.pref().tools.sketch.align
        config.align_face = addon.pref().tools.sketch.align_face
        config.align_view = addon.pref().tools.sketch.align_view

        return config

    def invoke_data(self, context):
        scene.set_active_object(context, self.mouse.init)
        obj = context.edit_object
        obj.update_from_editmode()
        self.data.is_local = True
        self.data.obj = obj
        self.data.bm = bmesh.from_edit_mesh(obj.data)

    def update_bmesh(self, loop_triangles=False, destructive=False):
        obj = self.data.obj
        mesh = obj.data
        bmesh.update_edit_mesh(mesh, loop_triangles=loop_triangles, destructive=destructive)


class Theme(bpy.types.PropertyGroup):
    face: bpy.props.FloatVectorProperty(name="Face", description="Face indicator color", default=(1.0, 0.6, 0.0, 0.3), subtype='COLOR', size=4, min=0.0, max=1.0)


types_classes = (
    Theme,
)


classes = (
    BOUT_OT_DrawMeshTool,
)
