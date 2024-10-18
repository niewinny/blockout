from dataclasses import dataclass, field
import bpy
import bmesh

from mathutils import Vector
from ...shaders import handle
from ...utils import addon, scene, infobar, view3d
from ...bmeshutils import orientation
from ...bmeshutils.rectangle import create_rectangle, expand_rectangle


@dataclass
class Config:
    '''Dataclass for storing options'''
    shape: str = 'RECTANGLE'
    align: str = 'NORMAL'


@dataclass
class CreatedData:
    '''Dataclass for storing'''
    bm: bmesh.types.BMesh = None
    face: bmesh.types.BMFace = None
    direction: Vector = Vector((0, 1, 0))
    plane: tuple = (Vector(), Vector())


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

    @classmethod
    def poll(cls, context):
        return context.area.type == 'VIEW_3D' and context.mode == 'EDIT_MESH'

    def set_config(self, context):
        raise NotImplementedError("Subclasses must implement the set_options method")

    def invoke(self, context, event):
        self.config = self.set_config(context)
        self.mouse.init = Vector((event.mouse_region_x, event.mouse_region_y))
        self.ray = scene.ray_cast.selected(context, self.mouse.init)

        scene.set_active_object(context, self.mouse.init)

        obj = context.edit_object
        self.data.bm = bmesh.from_edit_mesh(obj.data)

        created_mesh = self._build_mesh(context)
        if not created_mesh:
            self.report({'ERROR'}, 'Failed to create mesh data')
            return {'CANCELLED'}

        bmesh.update_edit_mesh(obj.data, loop_triangles=True, destructive=True)

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

        if not self.ray.hit:
            direction = orientation.direction_from_view(context)
            plane = orientation.plane_from_view(context, self.mouse.init, Vector((0, 0, 0)))

        else:
            hit_face = self.data.bm.faces[self.ray.index]
            loc = self.ray.location

            active_element = self.data.bm.select_history.active
            if isinstance(active_element, bmesh.types.BMEdge):
                active_edge = active_element
                if active_edge not in hit_face.edges:
                    self.report({'ERROR'}, 'Active Edge must be part of the hit face')
                    return False
            else:
                self.report({'ERROR'}, 'No Active Eddge Selected')
                return False

            align = self.config.align
            match align:
                case 'NORMAL': direction = orientation.direction_from_normal(hit_face.normal)
                case 'CLOSEST': direction = orientation.direction_from_closest_edge(hit_face, loc)
                case 'LONGEST': direction = orientation.direction_from_longest_edge(hit_face)
                case 'ACTIVE': direction = orientation.direction_from_active_edge(hit_face, active_edge)
            plane = orientation.plane_from_ray(self.ray)

        self.data.direction = direction
        self.data.plane = plane
        self.data.face = create_rectangle(self.data.bm, plane)

        return True

    def _draw_mesh(self, context):
        obj = context.edit_object

        region = context.region
        re3d = context.region_data
        plane = self.data.plane
        direction = self.data.direction
        matrix_world = obj.matrix_world
        mouse_point_on_plane = view3d.region2d_to_plane3d(region, re3d, self.mouse.co, plane, matrix=matrix_world)

        if mouse_point_on_plane is None:
            return

        expand_rectangle(self.data.face, plane, mouse_point_on_plane, direction)

        bmesh.update_edit_mesh(obj.data)


class BOUT_OT_DrawTool(DrawMesh):
    bl_idname = 'bout.draw_tool'
    bl_label = 'Draw Polygon'
    bl_options = {'REGISTER', 'UNDO', 'BLOCKING'}
    bl_description = "Tool for drawing a mesh"

    def _header_text(self):
        '''Set the header text'''
        pref = addon.pref().tools.sketch
        text = f"Shape: {pref.shape.capitalize()}"

        return text

    def set_config(self, context):
        config = Config()
        config.shape = addon.pref().tools.sketch.shape
        config.align = addon.pref().tools.sketch.align

        return config


class Theme(bpy.types.PropertyGroup):
    face: bpy.props.FloatVectorProperty(name="Face", description="Face indicator color", default=(1.0, 0.6, 0.0, 0.3), subtype='COLOR', size=4, min=0.0, max=1.0)


types_classes = (
    Theme,
)

classes = (
    BOUT_OT_DrawTool,
)
