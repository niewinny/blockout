from dataclasses import dataclass, field
import bpy
import bmesh

from mathutils import Vector

from ...shaders import handle
from ...shaders.draw import DrawLine, DrawBMeshFaces, DrawPolyline
from ...utils import addon, scene, infobar, view3d
from ...bmeshutils import bmeshface, orientation, rectangle, facet, circle, box
from ...bmeshutils.mesh import set_copy


@dataclass
class Config:
    '''Dataclass for storing options'''
    shape: str = 'RECTANGLE'
    mode: str = 'CREATE'
    type: str = 'OBJECT'
    form: bpy.types.PropertyGroup = None
    align: bpy.types.PropertyGroup = None
    pick: str = 'SELECTED'


@dataclass
class Draw:
    '''Dataclass for storing options'''
    plane: tuple = (Vector(), Vector())
    direction: Vector = Vector((0, 1, 0))
    face: int = -1


@dataclass
class Bevel:
    '''Dataclass for storing options'''
    offset: float = 0.0
    delta: float = 0.0
    type: str = '2D'
    mode: str = 'OFFSET'
    verts: list = field(default_factory=list)  # v.co


@dataclass
class Extrude:
    '''Dataclass for storing options'''
    plane: tuple = (Vector(), Vector())
    origin: Vector = Vector()
    faces: list = field(default_factory=list)  # indexes
    verts: list = field(default_factory=list)  # v.co
    value: float = 0.0
    sign: int = -1


@dataclass
class Copy:
    '''Dataclass for storing options'''
    init: bpy.types.Mesh = None
    extrude: bpy.types.Mesh = None


@dataclass
class CreatedData:
    '''Dataclass for storing'''
    obj: bpy.types.Object = None
    volume: str = '2D'
    bm: bmesh.types.BMesh = None
    copy: Copy = field(default_factory=Copy)
    extrude: Extrude = field(default_factory=Extrude)
    bevel: Bevel = field(default_factory=Bevel)
    draw: Draw = field(default_factory=Draw)


@dataclass
class Objects:
    '''Dataclass for storing'''
    active: bpy.types.Object = None
    selected: list = field(default_factory=list)


@dataclass
class Mouse:
    """Dataclass for tracking mouse positions."""
    init: Vector = Vector()
    extrude: Vector = Vector()
    bevel: Vector = Vector()
    co: Vector = Vector()


@dataclass
class DrawUI(handle.Common):
    '''Dataclass for the UI  drawing'''
    xaxis: handle.Line = field(default_factory=handle.Line)
    yaxis: handle.Line = field(default_factory=handle.Line)
    zaxis: handle.Line = field(default_factory=handle.Line)
    faces: handle.BMeshFaces = field(default_factory=handle.BMeshFaces)
    guid: handle.Polyline = field(default_factory=handle.Polyline)


class Rectangle(bpy.types.PropertyGroup):
    '''PropertyGroup for storing rectangle data'''
    co: bpy.props.FloatVectorProperty(name="Rectangle", description="Rectangle coordinates", size=2, default=(0, 0), subtype='XYZ_LENGTH')


class Circle(bpy.types.PropertyGroup):
    '''PropertyGroup for storing circle data'''
    radius: bpy.props.FloatProperty(name="Radius", description="Circle radius", default=0.0, subtype='DISTANCE')
    verts: bpy.props.IntProperty(name="Verts", description="Circle Verts", default=32, min=3, max=256)


class Plane(bpy.types.PropertyGroup):
    '''PropertyGroup for storing plane data'''
    location: bpy.props.FloatVectorProperty(name="Location", description="Plane location", size=3, default=(0, 0, 0), subtype='XYZ')
    normal: bpy.props.FloatVectorProperty(name="Normal", description="Plane normal", size=3, default=(0, 0, 0), subtype='XYZ')


class BevelPref(bpy.types.PropertyGroup):
    '''PropertyGroup for storing bevel data'''
    type: bpy.props.EnumProperty(name="Mode", description="Bevel Mode", items=[('3D', '3D', '3D'), ('2D', '2D', '2D')], default='3D')
    offset: bpy.props.FloatProperty(name="Offset", description="Bevel Offset", default=0.0, min=0.0, subtype='DISTANCE')
    segments: bpy.props.IntProperty(name="Segments", description="Bevel Segments", default=1, min=1, max=32)


class Pref(bpy.types.PropertyGroup):
    '''PropertyGroup for storing preferences'''
    extrusion: bpy.props.FloatProperty(name="Z", description="Z coordinates", default=0.0, subtype='DISTANCE')
    shape: bpy.props.StringProperty(name="Shape", description="Shape", default='RECTANGLE')
    mode: bpy.props.StringProperty(name="Mode", description="Mode", default='CREATE')

    offset: bpy.props.FloatProperty(name="Offset", description="Offset", default=0.0, subtype='DISTANCE')

    bevel: bpy.props.PointerProperty(type=BevelPref)

    plane: bpy.props.PointerProperty(type=Plane)
    direction: bpy.props.FloatVectorProperty(name="Direction", description="Direction", default=(0, 1, 0), subtype='XYZ')


class Shapes(bpy.types.PropertyGroup):
    volume: bpy.props.StringProperty(name="Volume", description="Volume", default='2D')
    rectangle: bpy.props.PointerProperty(type=Rectangle)
    circle: bpy.props.PointerProperty(type=Circle)


class Sketch(bpy.types.Operator):
    pref: bpy.props.PointerProperty(type=Pref)
    shapes: bpy.props.PointerProperty(type=Shapes)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ui = DrawUI()
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
        self.pref.bevel.segments = addon.pref().tools.sketch.form.segments

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

    def invoke(self, context, event):
        '''Start the operator'''

        self.config = self.set_config(context)
        self.get_tool_prpoerties()

        mouse_region_prev_x, mouse_region_prev_y = view3d.get_mouse_region_prev(event)
        self.mouse.init = Vector((mouse_region_prev_x, mouse_region_prev_y))
        self.ray = self.ray_cast(context)

        self.data.obj, self.data.bm = self.build_bmesh(context)

        self.objects.selected = context.selected_objects[:]
        self.objects.active = context.active_object

        self.data.copy.init = set_copy(self.data.obj)
        self._setup_drawing(context)

        created_mesh = self._draw_invoke(context)
        if not created_mesh:
            return {'CANCELLED'}

        context.window.cursor_set('SCROLL_XY')
        self._header(context)
        infobar.draw(context, event, None)
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True

        shape = self.pref.shape
        match shape:
            case 'RECTANGLE':
                col = layout.column(align=True)
                col.prop(self.shapes.rectangle, 'co', text="Dimensions")
                layout.prop(self.pref, 'offset', text="Offset")
                col = layout.column(align=True)
                row = col.row(align=True)
                row.prop(self.pref.bevel, 'offset', text="Bevel")
                row.prop(self.pref.bevel, 'segments', text="")
            case 'BOX':
                col = layout.column(align=True)
                col.prop(self.shapes.rectangle, 'co', text="Dimensions")
                col.prop(self.pref, 'extrusion', text="Z")
                layout.prop(self.pref, 'offset', text="Offset")
                row = layout.row(align=True)
                row.prop(self.pref.bevel, 'type', text="Bevel")
                row.prop(self.pref.bevel, 'offset', text="")
                row.prop(self.pref.bevel, 'segments', text="")
            case 'CIRCLE':
                layout.prop(self.shapes.circle, 'radius', text="Radius")
                layout.prop(self.shapes.circle, 'verts', text="Verts")
                layout.prop(self.pref, 'offset', text="Offset")
            case 'CYLINDER':
                layout.prop(self.shapes.circle, 'radius', text="Radius")
                layout.prop(self.pref, 'extrusion', text="Dimensions Z")
                layout.prop(self.shapes.circle, 'verts', text="Verts")
                layout.prop(self.pref, 'offset', text="Offset")

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
        self.pref.shape = self.config.shape
        self.pref.mode = self.config.mode
        self.pref.bevel.offset = self.data.bevel.offset
        self.pref.bevel.type = self.data.bevel.type
        if self.config.mode != 'CREATE':
            self.pref.offset = self.config.align.offset

    def save_props(self):
        '''Store the properties'''
        addon.pref().tools.sketch.form.segments = self.pref.bevel.segments

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
                self._recalculate_normals(self.data.bm, self.data.extrude.faces)
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
                self._bevel_invoke()
                if self.config.mode != 'CREATE':
                    self._boolean_invoke(self.data.obj, self.data.bm)

        elif event.type == 'S':
            if event.value == 'PRESS':
                if self.mode == 'BEVEL':
                    self.data.bevel.mode = 'OFFSET' if self.data.bevel.mode == 'SEGMENTS' else 'SEGMENTS'
                    return {'RUNNING_MODAL'}

        elif event.type in {'RIGHTMOUSE', 'ESC'}:
            self._end(context)
            return {'CANCELLED'}

        context.area.tag_redraw()
        return {'RUNNING_MODAL'}

    def _end(self, context):
        '''End the operator'''

        if self.data.copy.init:
            bpy.data.meshes.remove(self.data.copy.init)
        if self.data.copy.extrude:
            bpy.data.meshes.remove(self.data.copy.extrude)

        self.mouse = None
        self.ray = None
        self.data = None
        self.config = None
        self.objects = None

        self.ui.clear()

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
        z_length = self.pref.extrusion
        radius = self.shapes.circle.radius

        shape = self.config.shape
        match shape:
            case 'RECTANGLE': dimentions = f' Dx:{x_length:.4f},  Dy:{y_length:.4f}'
            case 'CIRCLE': dimentions = f' Radius:{radius:.4f}'
            case 'BOX': dimentions = f' Dx:{x_length:.4f},  Dy:{y_length:.4f},  Dz:{z_length:.4f}'
            case 'CYLINDER': dimentions = f' Radius:{radius:.4f},  Dz:{z_length:.4f}'

        header = f'{text} {dimentions}'
        context.area.header_text_set(text=header)

    def _setup_drawing(self, context):

        color = addon.pref().theme.axis
        self.ui.zaxis.callback = DrawLine(points=(Vector((0, 0, 0)), Vector((0, 0, 0))), width=1.6, color=color.z, depth=False)
        self.ui.zaxis.handle = bpy.types.SpaceView3D.draw_handler_add(self.ui.zaxis.callback.draw, (context,), 'WINDOW', 'POST_VIEW')
        self.ui.xaxis.callback = DrawLine(points=(Vector((0, 0, 0)), Vector((0, 0, 0))), width=1.6, color=color.x, depth=False)
        self.ui.xaxis.handle = bpy.types.SpaceView3D.draw_handler_add(self.ui.xaxis.callback.draw, (context,), 'WINDOW', 'POST_VIEW')
        self.ui.yaxis.callback = DrawLine(points=(Vector((0, 0, 0)), Vector((0, 0, 0))), width=1.6, color=color.y, depth=False)
        self.ui.yaxis.handle = bpy.types.SpaceView3D.draw_handler_add(self.ui.yaxis.callback.draw, (context,), 'WINDOW', 'POST_VIEW')
        color = addon.pref().theme.src.sketch
        face_color = color.cut if self.config.mode == 'CUT' else color.slice
        obj = self.data.obj
        self.ui.faces.callback = DrawBMeshFaces(obj=obj, faces=[], color=face_color)
        self.ui.faces.handle = bpy.types.SpaceView3D.draw_handler_add(self.ui.faces.callback.draw, (context,), 'WINDOW', 'POST_VIEW')
        self.ui.guid.callback = DrawPolyline(points=[], width=1.6, color=color.guid)
        self.ui.guid.handle = bpy.types.SpaceView3D.draw_handler_add(self.ui.guid.callback.draw, (context,), 'WINDOW', 'POST_VIEW')

    def _get_orientation(self, context):
        def get_view_orientation():
            align_view = self.config.align.view
            match align_view:
                case 'WORLD': depth = Vector((0, 0, 0))
                case 'OBJECT': depth = self.objects.active.location
                case 'CURSOR': depth = context.scene.cursor.location

            direction_world = orientation.direction_from_view(context)
            plane_view = orientation.plane_from_view(context, depth)

            origin = view3d.region_2d_to_plane_3d(context.region, context.region_data, self.mouse.init, plane_view)
            plane_world = (origin, plane_view[1])

            return direction_world, plane_world

        def get_face_orientation():
            depsgraph = context.view_layer.depsgraph
            depsgraph.update()
            hit_obj = self.ray.obj

            # Get the evaluated data
            hit_obj_eval = hit_obj.evaluated_get(depsgraph)
            hit_data = hit_obj_eval.to_mesh(preserve_all_data_layers=True, depsgraph=depsgraph)

            hit_bm = bmesh.new()
            hit_bm.from_mesh(hit_data)
            hit_bm.faces.ensure_lookup_table()
            hit_face = hit_bm.faces[self.ray.index]
            loc = self.ray.location

            align_face = self.config.align.face
            match align_face:
                case 'PLANAR': direction_local = orientation.direction_from_normal(hit_face.normal)
                case 'CLOSEST': direction_local = orientation.direction_from_closest_edge(hit_obj, hit_face, loc)
                case 'LONGEST': direction_local = orientation.direction_from_longest_edge(hit_face)

            direction_world = self.ray.obj.matrix_world.to_3x3() @ direction_local
            plane_world = (self.ray.location, self.ray.normal)

            hit_bm.free()
            del hit_obj_eval
            del hit_data

            return direction_world, plane_world

        def get_custom_orientation():
            custom_location = self.config.align.custom.location
            custom_normal = self.config.align.custom.normal
            custom_direction = self.config.align.custom.direction

            custom_plane = (custom_location, custom_normal)
            location_world = view3d.region_2d_to_plane_3d(context.region, context.region_data, self.mouse.init, custom_plane)

            plane_world = (location_world, custom_normal)

            return custom_direction, plane_world

        if self.config.align.mode == 'FACE' and self.ray.hit:
            direction, plane = get_face_orientation()
        elif self.config.align.mode == 'CUSTOM':
            direction, plane = get_custom_orientation()
        else:
            direction, plane = get_view_orientation()

        return direction, plane

    def _draw_invoke(self, context):
        '''Build the mesh data'''

        obj = self.data.obj
        bm = self.data.bm

        direction, plane = self._get_orientation(context)
        world_origin, world_normal = plane

        if self.config.mode != 'CREATE':
            bpy.ops.mesh.select_all(action='DESELECT')

        if self.config.align.mode != 'CUSTOM':
            x_axis_point = world_origin + direction
            y_direction = world_normal.cross(direction).normalized()
            y_axis_point = world_origin + y_direction
            self.ui.xaxis.callback.update_batch((world_origin, x_axis_point))
            self.ui.yaxis.callback.update_batch((world_origin, y_axis_point))

        if self.config.align.grid.enable:
            increments = self.config.align.grid.spacing
            custom_plane = self.config.align.custom.location, self.config.align.custom.normal
            plane = orientation.snap_plane(plane, custom_plane, direction, increments)

        if self.config.type == 'MESH':
            direction = orientation.direction_local(obj, direction)
            plane = orientation.plane_local(obj, plane)

        if plane is None:
            self.report({'ERROR'}, 'Failed to detect drawing plane')
            return False

        self.data.draw.plane = plane
        self.data.draw.direction = direction

        shape = self.config.shape
        match shape:
            case 'RECTANGLE': self.data.draw.face = rectangle.create(bm, plane)
            case 'BOX': self.data.draw.face = rectangle.create(bm, plane)
            case 'CIRCLE': self.data.draw.face = circle.create(bm, plane, verts_number=self.shapes.circle.verts)
            case 'CYLINDER': self.data.draw.face = circle.create(bm, plane, verts_number=self.shapes.circle.verts)

        self.update_bmesh(obj, bm, loop_triangles=True, destructive=True)
        return True

    def _draw_modal(self, context, event):
        obj = self.data.obj
        bm = self.data.bm

        region = context.region
        rv3d = context.region_data
        plane = self.data.draw.plane
        direction = self.data.draw.direction
        matrix_world = obj.matrix_world
        face = bm.faces[self.data.draw.face]

        self.data.bevel.verts = [obj.matrix_world @ v.co.copy() for v in face.verts]

        mouse_point_on_plane = view3d.region_2d_to_plane_3d(region, rv3d, self.mouse.co, plane, matrix=matrix_world)
        if mouse_point_on_plane is None:
            self.report({'WARNING'}, "Mouse was outside the drawing plane")
            return

        shape = self.config.shape

        if self.config.align.grid.enable:
            increments = self.config.align.grid.spacing
        else:
            increments = self.config.form.increments if event.ctrl else 0.0

        match shape:
            case 'RECTANGLE': self.shapes.rectangle.co, point = rectangle.set_xy(face, plane, mouse_point_on_plane, direction, snap_value=increments)
            case 'BOX': self.shapes.rectangle.co, point = rectangle.set_xy(face, plane, mouse_point_on_plane, direction, snap_value=increments)
            case 'CIRCLE': self.shapes.circle.radius, point = circle.set_xy(face, plane, mouse_point_on_plane, snap_value=increments)
            case 'CYLINDER': self.shapes.circle.radius, point = circle.set_xy(face, plane, mouse_point_on_plane, snap_value=increments)

        self.update_bmesh(obj, bm)

        self.data.extrude.plane = (matrix_world @ point, matrix_world.to_3x3() @ direction)

        if self.config.mode != 'CREATE':
            self.ui.faces.callback.update_batch([face])

    def _extrude_invoke(self, context):
        '''Extrude the mesh'''

        self.mode = 'EXTRUDE'
        self.shapes.volume = '3D'
        self.mouse.extrude = self.mouse.co

        region = context.region
        rv3d = context.region_data

        obj = self.data.obj
        bm = self.data.bm

        draw_face = bm.faces[self.data.draw.face]
        plane = self.data.draw.plane

        extruded_faces = facet.extrude(bm, draw_face, plane, 0.0)
        self.data.extrude.faces = extruded_faces
        self.data.draw.face = extruded_faces[0]

        extrude_face = bm.faces[self.data.extrude.faces[-1]]
        self.data.extrude.verts = [v.co.copy() for v in extrude_face.verts]

        self.update_bmesh(obj, bm, loop_triangles=True, destructive=True)

        self.ui.xaxis.callback.clear()
        self.ui.yaxis.callback.clear()
        self.ui.guid.callback.clear()

        self.set_offset()

        plane_world = (obj.matrix_world @ plane[0], obj.matrix_world.to_3x3() @ plane[1])
        line_origin = view3d.region_2d_to_plane_3d(region, rv3d, self.mouse.extrude, plane_world)
        self.data.extrude.origin = line_origin
        point1 = line_origin
        point2 = line_origin + plane_world[1]
        self.ui.zaxis.callback.update_batch((point1, point2))

    def _extrude_modal(self, context, event):
        '''Set the extrusion'''

        obj = self.data.obj
        bm = self.data.bm
        matrix_world = obj.matrix_world

        face = bm.faces[self.data.extrude.faces[-1]]
        plane = self.data.draw.plane
        normal = plane[1]
        verts = self.data.extrude.verts

        region = context.region
        rv3d = context.region_data

        # Compute line_origin in world space
        line_origin = self.data.extrude.origin

        # Use world space normal for line_direction
        line_direction = matrix_world.to_3x3() @  normal

        # Calculate extrusion using region_2d_to_line_3d
        _, extrude = view3d.region_2d_to_line_3d(region, rv3d, self.mouse.co, line_origin, line_direction)

        if extrude is None:
            # Handle the case where the line and ray are parallel
            self.pref.extrusion = 0.0
            self.data.extrude.value = 0.0
            return

        # Update the mesh with the new extrusion value
        increments = self.config.form.increments if event.ctrl else 0.0
        dz = facet.set_z(face, normal, extrude, verts, snap_value=increments)

        # Update the extrusion value
        self.pref.extrusion = dz
        self.data.extrude.value = dz

        self.data.bevel.verts = [obj.matrix_world @ v.co.copy() for v in face.verts]

        extrude_faces = [bm.faces[index] for index in self.data.extrude.faces]

        if self.config.mode != 'CREATE':
            self.ui.faces.callback.update_batch(extrude_faces)

        self.update_bmesh(obj, bm, loop_triangles=True, destructive=True)

    def _boolean_invoke(self, obj, bm):
        '''Boolean operation'''
        raise NotImplementedError("Subclasses must implement the _boolean_invoke method")

    def _bevel_invoke(self):
        '''Bevel the mesh'''

        if self.data.bevel.mode != 'OFFSET':
            self.data.bevel.mode = 'OFFSET'
            return

        if self.mode == 'BEVEL':
            if self.shapes.volume == '3D':
                self.data.bevel.type = '3D' if self.data.bevel.type == '2D' else '2D'
            return

        volume = self.shapes.volume
        self.data.bevel.type = volume
        self.mouse.bevel = self.mouse.co
        self.ui.zaxis.callback.clear()

        self.mode = 'BEVEL'

    def _bevel_modal(self, context):
        '''Bevel the mesh'''
        region = context.region
        rv3d = context.region_data

        point = sum(self.data.bevel.verts, Vector()) / len(self.data.bevel.verts)
        point2d = view3d.location_3d_to_region_2d(region, rv3d, point)
        mouse_store_co_3d = view3d.region_2d_to_location_3d(region, rv3d, self.mouse.bevel, point)
        mouse_co_3d = view3d.region_2d_to_location_3d(region, rv3d, self.mouse.co, point)

        delta = (point - mouse_store_co_3d).length

        if self.data.bevel.mode == 'SEGMENTS':
            length = int((self.mouse.bevel - self.mouse.co).length)
            self.pref.bevel.segments = length
        else:
            if self.shapes.volume == '2D':
                self.data.bevel.offset = (point - mouse_co_3d).length - delta
                self.data.bevel.delta = self.data.bevel.offset
            else:
                self.data.bevel.offset = (point - mouse_co_3d).length - delta + self.data.bevel.delta
        self.ui.guid.callback.update_batch([(point, mouse_co_3d)])


class Theme(bpy.types.PropertyGroup):
    cut: bpy.props.FloatVectorProperty(name="Cut", description="Mesh indicator color", default=(0.5, 0.1, 0.1, 0.2), subtype='COLOR', size=4, min=0.0, max=1.0)
    slice: bpy.props.FloatVectorProperty(name="Slice", description="Mesh indicator color", default=(0.5, 0.1, 0.3, 0.2), subtype='COLOR', size=4, min=0.0, max=1.0)
    guid: bpy.props.FloatVectorProperty(name="Guid", description="Guid indicator color", default=(0.1, 0.1, 0.1, 0.8), subtype='COLOR', size=4, min=0.0, max=1.0)


types_classes = (
    Rectangle,
    Circle,
    Shapes,
    BevelPref,
    Plane,
    Pref,
    Theme,
)
