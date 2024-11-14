from dataclasses import dataclass, field
import bpy
import bmesh

from mathutils import Vector, Matrix
from ...shaders import handle
from ...shaders.draw import DrawLine, DrawBMeshFaces
from ...utils import addon, scene, infobar, view3d
from ...bmeshutils import orientation, rectangle, facet, circle


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
    face: str = 'PLANAR'
    custom: Custom = field(default_factory=Custom)
    offset: float = 0.0


@dataclass
class Form:
    '''Dataclass for storing options'''
    increments: float = 0.0


@dataclass
class Config:
    '''Dataclass for storing options'''
    shape: str = 'RECTANGLE'
    form: str = field(default_factory=Form)
    align: Align = field(default_factory=Align)
    pick: str = 'SELECTED'
    extrude: bool = True


@dataclass
class Draw:
    '''Dataclass for storing options'''
    plane: tuple = (Vector(), Vector())
    direction: Vector = Vector((0, 1, 0))
    face: bmesh.types.BMFace = None
    verts: list = field(default_factory=list)


@dataclass
class Extrude:
    '''Dataclass for storing options'''
    plane: tuple = (Vector(), Vector())
    face: bmesh.types.BMFace = None
    faces: list = field(default_factory=list)
    verts: list = field(default_factory=list)
    value: float = 0.0


@dataclass
class CreatedData:
    '''Dataclass for storing'''
    obj: bpy.types.Object = None
    bm: bmesh.types.BMesh = None
    extrude: Extrude = field(default_factory=Extrude)
    draw: Draw = field(default_factory=Draw)
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
    store: Vector = Vector()
    co: Vector = Vector()


@dataclass
class DrawUI(handle.Common):
    '''Dataclass for the UI  drawing'''
    xaxis: handle.Line = field(default_factory=handle.Line)
    yaxis: handle.Line = field(default_factory=handle.Line)
    zaxis: handle.Line = field(default_factory=handle.Line)
    faces: handle.BMeshFaces = field(default_factory=handle.BMeshFaces)


class Rectangle(bpy.types.PropertyGroup):
    co: bpy.props.FloatVectorProperty(name="Rectangle", description="Rectangle coordinates", size=2, default=(0, 0), subtype='XYZ_LENGTH')


class Circle(bpy.types.PropertyGroup):
    radius: bpy.props.FloatProperty(name="Radius", description="Circle radius", default=0.0, subtype='DISTANCE')
    verts: bpy.props.IntProperty(name="Verts", description="Circle Verts", default=32, min=3, max=256)


class Plane(bpy.types.PropertyGroup):
    location: bpy.props.FloatVectorProperty(name="Location", description="Plane location", size=3, default=(0, 0, 0), subtype='XYZ')
    normal: bpy.props.FloatVectorProperty(name="Normal", description="Plane normal", size=3, default=(0, 0, 0), subtype='XYZ')


class Pref(bpy.types.PropertyGroup):
    extrusion: bpy.props.FloatProperty(name="Z", description="Z coordinates", default=0.0, subtype='DISTANCE')
    shape: bpy.props.StringProperty(name="Shape", description="Shape", default='RECTANGLE')

    offset: bpy.props.FloatProperty(name="Offset", description="Offset", default=0.0, subtype='DISTANCE')

    plane: bpy.props.PointerProperty(type=Plane)
    direction: bpy.props.FloatVectorProperty(name="Direction", description="Direction", default=(0, 1, 0), subtype='XYZ')


class Shapes(bpy.types.PropertyGroup):
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
        raise NotImplementedError("Subclasses must implement the set_options method")

    def build_bmesh(self, context):
        '''Set the object data'''
        raise NotImplementedError("Subclasses must implement the set_object method")

    def update_bmesh(self, obj, bm, loop_triangles=False, destructive=False):
        '''Update the bmesh data'''
        raise NotImplementedError("Subclasses must implement the update_bmesh method")

    def ray_cast(self, context):
        '''Ray cast the scene'''
        raise NotImplementedError("Subclasses must implement the ray_cast method")

    def invoke(self, context, event):

        self._setup_drawing(context)

        self.config = self.set_config(context)
        mouse_region_prev_x, mouse_region_prev_y = view3d.get_mouse_region_prev(event)
        self.mouse.init = Vector((mouse_region_prev_x, mouse_region_prev_y))
        self.ray = self.ray_cast(context)

        self.objects.selected = context.selected_objects[:]
        self.objects.active = context.active_object

        self.data.obj, self.data.bm = self.build_bmesh(context)

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
            case 'BOX':
                col = layout.column(align=True)
                col.prop(self.shapes.rectangle, 'co', text="Dimensions")
                col.prop(self.pref, 'extrusion', text="Z")
            case 'CIRCLE':
                layout.prop(self.shapes.circle, 'radius', text="Radius")
                layout.prop(self.shapes.circle, 'verts', text="Verts")
            case 'CYLINDER':
                layout.prop(self.shapes.circle, 'radius', text="Radius")
                layout.prop(self.pref, 'extrusion', text="Dimensions Z")
                layout.prop(self.shapes.circle, 'verts', text="Verts")

        layout.prop(self.pref, 'offset', text="Offset")

    def _recalculate_normals(self, bm):
        selected_faces = [f for f in bm.faces if f.select]
        bmesh.ops.recalc_face_normals(bm, faces=selected_faces)

    def store_data(self):
        '''Finish the operator'''
        self.pref.plane.location = self.data.draw.plane[0]
        self.pref.plane.normal = self.data.draw.plane[1]
        self.pref.direction = self.data.draw.direction
        self.pref.offset = self.config.align.offset
        self.pref.extrusion = self.data.extrude.value
        self.pref.shape = self.config.shape

    def set_offset(self):
        '''Set the offset'''
        bm = self.data.bm
        obj = self.data.obj
        face = self.data.draw.face
        normal = self.data.draw.plane[1]
        offset = self.config.align.offset

        facet.set_z(face, normal, offset)
        self.update_bmesh(obj, bm, loop_triangles=True, destructive=True)

    def execute(self, context):
        offset = self.pref.offset
        location = self.pref.plane.location
        normal = self.pref.plane.normal
        plane = (location, normal)
        direction = self.pref.direction
        extrusion = self.pref.extrusion

        obj, bm = self.build_bmesh(context)

        shape = self.pref.shape
        match shape:
            case 'RECTANGLE':
                face = rectangle.create(bm, plane)
                rectangle.set_xy(face, plane, self.shapes.rectangle.co, direction, local_space=True)
            case 'BOX':
                face = rectangle.create(bm, plane)
                rectangle.set_xy(face, plane, self.shapes.rectangle.co, direction, local_space=True)
                facet.extrude(bm, face, plane, extrusion)
                self._recalculate_normals(bm)
            case 'CIRCLE':
                face = circle.create(bm, plane, verts_number=self.shapes.circle.verts)
                circle.set_xy(face, plane, radius=self.shapes.circle.radius, local_space=True)
            case 'CYLINDER':
                face = circle.create(bm, plane, verts_number=self.shapes.circle.verts)
                circle.set_xy(face, plane, radius=self.shapes.circle.radius, local_space=True)
                facet.extrude(bm, face, plane, extrusion)
                self._recalculate_normals(bm)
            case _:
                raise ValueError(f"Unsupported shape: {self.pref.shape}")

        facet.set_z(face, normal, offset)

        self.update_bmesh(obj, bm, loop_triangles=True, destructive=True)

        return {'FINISHED'}

    def modal(self, context, event):
        if event.type == 'MIDDLEMOUSE':
            return {'PASS_THROUGH'}

        if event.type == 'MOUSEMOVE':
            self.mouse.co = Vector((event.mouse_region_x, event.mouse_region_y))

            match self.mode:
                case 'DRAW':
                    self._draw_modal(context)
                case 'EXTRUDE':
                    self._extrude_modal(context)

            self._header(context)

        elif event.type in {'LEFTMOUSE', 'SPACE', 'RET', 'NUMPAD_ENTER'}:
            if event.value == 'RELEASE':
                shapes_to_extrude = {'BOX', 'CYLINDER'}
                if self.config.shape in shapes_to_extrude:
                    self.mode = 'EXTRUDE'
                    self.mouse.store = self.mouse.co
                    self._extrude_invoke()
                self.set_offset()
                if self.mode == 'EXTRUDE':
                    return {'RUNNING_MODAL'}

            if self.mode == 'EXTRUDE':
                self._recalculate_normals(self.data.bm)
                self.update_bmesh(self.data.obj, self.data.bm, loop_triangles=True, destructive=True)
            self.store_data()
            self._end(context)
            return {'FINISHED'}

        elif event.type in {'RIGHTMOUSE', 'ESC'}:
            self._end(context)
            return {'CANCELLED'}

        context.area.tag_redraw()
        return {'RUNNING_MODAL'}

    def _end(self, context):
        '''End the operator'''

        self.mouse = None
        self.ray = None
        self.data = None
        self.config = None
        self.objects = None

        self.ui.clear()

        context.window.cursor_set('CROSSHAIR')
        context.area.header_text_set(text=None)
        infobar.remove(context)

    def _heade_text(self):
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
        self.ui.faces.callback = DrawBMeshFaces(faces=[], color=(1.0, 0.6, 0.0, 0.7))
        self.ui.faces.handle = bpy.types.SpaceView3D.draw_handler_add(self.ui.faces.callback.draw, (context,), 'WINDOW', 'POST_VIEW')

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

        direction, plane = self._get_orientation(context)
        world_origin, world_normal = plane

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

        if self.data.is_local:
            direction = orientation.direction_local(obj, direction)
            plane = orientation.plane_local(obj, plane)

        if plane is None:
            self.report({'ERROR'}, 'Failed to detect drawing plane')
            return False

        self.data.draw.plane = plane
        self.data.draw.direction = direction

        shape = self.config.shape
        match shape:
            case 'RECTANGLE': self.data.draw.face = rectangle.create(self.data.bm, plane)
            case 'BOX': self.data.draw.face = rectangle.create(self.data.bm, plane)
            case 'CIRCLE': self.data.draw.face = circle.create(self.data.bm, plane, verts_number=self.shapes.circle.verts)
            case 'CYLINDER': self.data.draw.face = circle.create(self.data.bm, plane, verts_number=self.shapes.circle.verts)
        
        self.data.draw.face.hide_set(True)
        self.update_bmesh(self.data.obj, self.data.bm, loop_triangles=True, destructive=True)

        return True

    def _draw_modal(self, context):
        obj = self.data.obj

        region = context.region
        re3d = context.region_data
        plane = self.data.draw.plane
        direction = self.data.draw.direction
        matrix_world = obj.matrix_world

        mouse_point_on_plane = view3d.region_2d_to_plane_3d(region, re3d, self.mouse.co, plane, matrix=matrix_world)
        if mouse_point_on_plane is None:
            self.report({'WARNING'}, "Mouse was outside the drawing plane")
            return

        shape = self.config.shape
        if self.config.align.grid.enable:
            increments = self.config.align.grid.spacing
        else:
            increments = self.config.form.increments

        match shape:
            case 'RECTANGLE': self.shapes.rectangle.co, point = rectangle.set_xy(self.data.draw.face, plane, mouse_point_on_plane, direction, snap_value=increments)
            case 'BOX': self.shapes.rectangle.co, point = rectangle.set_xy(self.data.draw.face, plane, mouse_point_on_plane, direction, snap_value=increments)
            case 'CIRCLE': self.shapes.circle.radius, point = circle.set_xy(self.data.draw.face, plane, mouse_point_on_plane, snap_value=increments)
            case 'CYLINDER': self.shapes.circle.radius, point = circle.set_xy(self.data.draw.face, plane, mouse_point_on_plane, snap_value=increments)

        self.data.extrude.plane = (matrix_world @ point, matrix_world.to_3x3() @ direction)

        self.data.draw.verts = [v.co.copy() for v in self.data.draw.face.verts]
        self.update_bmesh(self.data.obj, self.data.bm)

        self.ui.faces.callback.update_batch([self.data.draw.face])

    def _extrude_invoke(self):
        '''Extrude the mesh'''

        face = self.data.draw.face
        face.normal_flip()
        plane = self.data.draw.plane

        # Get both the extruded face and all faces involved
        self.data.extrude.face, self.data.extrude.faces = facet.extrude(self.data.bm, face, plane, 0.0)
        self.data.extrude.verts = [v.co.copy() for v in self.data.extrude.face.verts]

        self.update_bmesh(self.data.obj, self.data.bm, loop_triangles=True, destructive=True)

        self.ui.xaxis.callback.clear()
        self.ui.yaxis.callback.clear()

    def _extrude_modal(self, context):
        '''Set the extrusion'''

        obj = self.data.obj
        matrix_world = obj.matrix_world
        face = self.data.extrude.face
        plane = self.data.draw.plane  # This plane is in object local space
        normal = -plane[1]  # Local space normal, negated
        verts = self.data.extrude.verts

        region = context.region
        rv3d = context.region_data

        # Transform plane to world space
        plane_location_world = matrix_world @ plane[0]
        plane_normal_world = matrix_world.to_3x3() @ plane[1]
        plane_normal_world.normalize()
        plane_world = (plane_location_world, plane_normal_world)

        # Transform normal to world space
        normal_world = matrix_world.to_3x3() @ normal
        normal_world.normalize()

        # Compute line_origin in world space
        line_origin = view3d.region_2d_to_plane_3d(region, rv3d, self.mouse.store, plane_world)

        # Use world space normal for line_direction
        line_direction = normal_world

        # Calculate extrusion using region_2d_to_line_3d
        _, extrude = view3d.region_2d_to_line_3d(region, rv3d, self.mouse.co, line_origin, line_direction)

        if extrude is None:
            # Handle the case where the line and ray are parallel
            self.pref.extrusion = 0.0
            self.data.extrude.value = 0.0
            return

        # Update the UI line visualization (if any)
        point1 = line_origin
        point2 = line_origin + line_direction
        self.ui.zaxis.callback.update_batch((point1, point2))

        # Update the mesh with the new extrusion value
        dz = facet.set_z(face, normal, extrude, verts, snap_value=self.config.form.increments)

        # Update the extrusion value
        self.pref.extrusion = dz
        self.data.extrude.value = dz

        # Update the bmesh
        self.update_bmesh(self.data.obj, self.data.bm, loop_triangles=True, destructive=True)


class BOUT_OT_SketchMeshTool(Sketch):
    bl_idname = 'bout.sketch_mesh_tool'
    bl_label = 'Blockout Sketch'
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
        config.form = addon.pref().tools.sketch.form
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
        bm.normal_update()
        bmesh.update_edit_mesh(mesh, loop_triangles=loop_triangles, destructive=True)


class Theme(bpy.types.PropertyGroup):
    face: bpy.props.FloatVectorProperty(name="Face", description="Face indicator color", default=(1.0, 0.6, 0.0, 0.3), subtype='COLOR', size=4, min=0.0, max=1.0)


types_classes = (
    Rectangle,
    Circle,
    Shapes,
    Plane,
    Pref,
    Theme,
)


classes = (
    BOUT_OT_SketchMeshTool,
)
