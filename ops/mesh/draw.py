from dataclasses import dataclass, field
import bpy
import bmesh

from mathutils import Vector
from ...shaders import handle
from ...utils import addon, scene, infobar, view3d
from ...bmeshutils import orientation, rectangle


@dataclass
class Custom:
    '''Dataclass for custom orientation'''
    location: Vector = Vector((0, 0, 0))
    normal: Vector = Vector((0, 0, 0))
    angle: float = 0.0


@dataclass
class Align:
    '''Dataclass for storing options'''
    mode: str = 'FACE'
    view: str = 'WORLD'
    face: str = 'NORMAL'
    custom: Custom = field(default_factory=Custom)
    offset: float = 0.0


@dataclass
class Config:
    '''Dataclass for storing options'''
    shape: str = 'RECTANGLE'
    align: Align = field(default_factory=Align)
    pick: str = 'SELECTED'


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


class Rectangle(bpy.types.PropertyGroup):
    co: bpy.props.FloatVectorProperty(name="Rectangle", description="Rectangle coordinates", size=2, default=(0, 0), subtype='XYZ_LENGTH')


class Plane(bpy.types.PropertyGroup):
    location: bpy.props.FloatVectorProperty(name="Location", description="Plane location", size=3, default=(0, 0, 0), subtype='XYZ')
    normal: bpy.props.FloatVectorProperty(name="Normal", description="Plane normal", size=3, default=(0, 0, 0), subtype='XYZ')


class Shape(bpy.types.PropertyGroup):
    rectangle: bpy.props.PointerProperty(type=Rectangle)

    offset: bpy.props.FloatProperty(name="Offset", description="Offset", default=0.0)

    obj_name: bpy.props.StringProperty(name="Object Name", description="Object name", default='BlockOut')
    face_index: bpy.props.IntProperty(name="Face Index", description="Face index", default=0)
    plane: bpy.props.PointerProperty(type=Plane)
    direction: bpy.props.FloatVectorProperty(name="Direction", description="Direction", default=(0, 1, 0), subtype='XYZ')


class DrawMesh(bpy.types.Operator):
    shape: bpy.props.PointerProperty(type=Shape)

    def __init__(self):
        self.ui = DrawUI()
        self.mouse = Mouse()
        self.data = CreatedData()
        self.config = Config()
        self.objects = Objects()

    def set_config(self, context):
        raise NotImplementedError("Subclasses must implement the set_options method")

    def build_bmesh(self, context):
        '''Set the object data'''
        raise NotImplementedError("Subclasses must implement the set_object method")

    def update_bmesh(self, loop_triangles=False, destructive=False):
        '''Update the bmesh data'''
        raise NotImplementedError("Subclasses must implement the update_bmesh method")
    
    def ray_cast(self, context):
        '''Ray cast the scene'''
        raise NotImplementedError("Subclasses must implement the ray_cast method")

    def invoke(self, context, event):

        self.config = self.set_config(context)
        mouse_region_prev_x, mouse_region_prev_y = view3d.get_mouse_region_prev(event)
        self.mouse.init = Vector((mouse_region_prev_x, mouse_region_prev_y))
        self.ray = self.ray_cast(context)

        self.objects.selected = context.selected_objects[:]
        self.objects.active = context.active_object

        self.data.obj, self.data.bm = self.build_bmesh(context)

        created_mesh = self._build_mesh(context)
        if not created_mesh:
            self.report({'ERROR'}, 'Failed to create mesh data')
            return {'CANCELLED'}

        self.update_bmesh(self.data.obj, self.data.bm, loop_triangles=True, destructive=True)

        context.window.cursor_set('SCROLL_XY')
        self._header(context)
        infobar.draw(context, event, None)
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}
    
    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.prop(self.shape.rectangle, 'co', text="Dimensions")
        layout.prop(self.shape, 'offset', text="Offset")

    def finish(self, context):
        '''Finish the operator'''
        self.shape.obj_name = self.data.obj.name
        self.shape.face_index = self.data.face.index
        self.shape.plane.location = self.data.plane[0]
        self.shape.plane.normal = self.data.plane[1]
        self.shape.direction = self.data.direction
        self.shape.offset = self.config.align.offset

    def execute(self, context):
        offset = self.shape.offset
        location = self.shape.plane.location
        normal = self.shape.plane.normal

        location = location + normal * offset
        plane = (location, normal)
        direction = self.shape.direction

        x, y = self.shape.rectangle.co
    
        obj, bm = self.build_bmesh(context)

        rectangle.create_rectangle(bm, plane)

        bm.faces.ensure_lookup_table()
        face = bm.faces[self.shape.face_index]

        rectangle.set_rectangle(face, plane, direction, x, y)

        self.update_bmesh(obj, bm, loop_triangles=True, destructive=True)

        return {'FINISHED'}

    def modal(self, context, event):

        if event.type == 'MIDDLEMOUSE':
            return {'PASS_THROUGH'}

        if event.type == 'MOUSEMOVE':
            self.mouse.co = (event.mouse_region_x, event.mouse_region_y)
            self._draw_mesh(context)
            self._header(context)

        elif event.type in {'LEFTMOUSE', 'SPACE', 'RET', 'NUMPAD_ENTER'}:
            self.finish(context)
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

        x_length, y_length = self.shape.rectangle.co
        dimentions = f' Dx:{x_length:.4f},  Dy:{y_length:.4f}'
    
        header = f'{text} {dimentions}'
        context.area.header_text_set(text=header)

    def _build_mesh(self, context):
        '''Build the mesh data'''

        obj = self.data.obj

        def get_view_orientation():
            align_view = self.config.align.view
            match align_view:
                case 'WORLD': depth = Vector((0, 0, 0))
                case 'OBJECT': depth = self.objects.active.location
                case 'CURSOR': depth = context.scene.cursor.location

            direction_world = orientation.direction_from_view(context)
            plane_world = orientation.plane_from_view(context, depth)

            return direction_world, plane_world

        def get_face_orientation():
            hit_obj = self.ray.obj
            hit_bm = bmesh.new()
            hit_bm.from_mesh(hit_obj.data)
            hit_bm.faces.ensure_lookup_table()
            hit_face = hit_bm.faces[self.ray.index]
            loc = self.ray.location

            align_face = self.config.align.face
            match align_face:
                case 'NORMAL': direction_local = orientation.direction_from_normal(hit_face.normal)
                case 'CLOSEST': direction_local = orientation.direction_from_closest_edge(hit_obj, hit_face, loc)
                case 'LONGEST': direction_local = orientation.direction_from_longest_edge(hit_face)
            
            direction_world = self.ray.obj.matrix_world.to_3x3() @ direction_local
            plane_world = (self.ray.location, self.ray.normal)

            hit_bm.free()

            return direction_world, plane_world
        
        def get_custom_orientation():
            location = self.config.align.custom.location
            normal = self.config.align.custom.normal
            axis = self.config.align.custom.angle

            custom = Custom(location, normal, axis)
            direction_world, plane_world = orientation.direction_from_custom(context, custom, self.mouse.init)

            return direction_world, plane_world

        if self.config.align.mode == 'FACE' and self.ray.hit:
            direction, plane = get_face_orientation()
        elif self.config.align.mode == 'CUSTOM':
            direction, plane = get_custom_orientation()
        else:
            direction, plane = get_view_orientation()

        def to_local(obj, plane, direction):
            plane_local = orientation.plane_local(obj, plane)
            direction_local = direction_local = orientation.direction_local(obj, direction)

            return direction_local, plane_local

        if self.data.is_local:
            direction, plane = to_local(obj, plane, direction)

        plane = orientation.offset_plane(context, obj, self.mouse.init, plane, self.config.align.offset)

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

        self.shape.rectangle.co = rectangle.expand_rectangle(self.data.face, plane, mouse_point_on_plane, direction)

        self.update_bmesh(self.data.obj, self.data.bm)


class BOUT_OT_DrawMeshTool(DrawMesh):
    bl_idname = 'bout.draw_mesh_tool'
    bl_label = 'Draw Mesh'
    bl_options = {'REGISTER', 'UNDO', 'BLOCKING'}
    bl_description = "Tool for drawing a mesh"

    @classmethod
    def poll(cls, context):
        return context.area.type == 'VIEW_3D' and context.mode == 'EDIT_MESH'
    
    def ray_cast(self, context):
        scene.set_active_object(context, self.mouse.init)
        if self.config.pick == 'SELECTED':
            ray = scene.ray_cast.edited(context, self.mouse.init)
        else:
            ray = scene.ray_cast.visible(context, self.mouse.init, modes={'EDIT', 'OBJECT'})
        return ray

    def _header_text(self):
        '''Set the header text'''
        pref = addon.pref().tools.sketch.mesh
        text = f"Shape: {pref.shape.capitalize()}"

        return text

    def set_config(self, context):
        config = Config()
        config.shape = addon.pref().tools.sketch.mesh.shape
        config.align = addon.pref().tools.sketch.align
        config.pick = addon.pref().tools.sketch.mesh.pick
        self.data.is_local = True

        return config

    def build_bmesh(self, context):
        obj = context.edit_object
        obj.update_from_editmode()
        bm = bmesh.from_edit_mesh(obj.data)

        return obj, bm

    def update_bmesh(self, obj, bm, loop_triangles=False, destructive=False):
        mesh = obj.data
        bmesh.update_edit_mesh(mesh, loop_triangles=loop_triangles, destructive=destructive)


class Theme(bpy.types.PropertyGroup):
    face: bpy.props.FloatVectorProperty(name="Face", description="Face indicator color", default=(1.0, 0.6, 0.0, 0.3), subtype='COLOR', size=4, min=0.0, max=1.0)


types_classes = (
    Rectangle,
    Plane,
    Shape,
    Theme,
)


classes = (
    BOUT_OT_DrawMeshTool,
)
