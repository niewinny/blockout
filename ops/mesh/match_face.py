from dataclasses import dataclass, field
import bpy
import bmesh

from mathutils import Vector

from ...shaders.draw import DrawFace
from ...shaders import handle
from ...utils import addon, scene, infobar


@dataclass
class DrawUI:
    '''Dataclass for the UI drawing'''
    face: handle.Face = field(default_factory=handle.Face)


class BOUT_OT_MatchFace(bpy.types.Operator):
    bl_idname = 'bout.match_face'
    bl_label = 'Edge Slide'
    bl_options = {'REGISTER', 'UNDO', 'BLOCKING'}
    bl_description = "Match the selected vertices to the face under the mouse cursor"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ui = DrawUI()
        self.ray = scene.ray_cast.Ray()

    @classmethod
    def poll(cls, context):
        return context.active_object and context.mode == 'EDIT_MESH'

    def invoke(self, context, event):

        if context.area.type == 'VIEW_3D':

            if context.active_object not in context.selected_objects:
                context.active_object.select_set(True)

            for obj in context.selected_objects:
                obj.update_from_editmode()

            self.ray.location, self.ray.normal, points = self.get_face_data(context, event)

            points = [Vector((0, 0, 0)), Vector((0, 1, 0)), Vector((1, 1, 0)), Vector((1, 0, 0))]
            color = addon.pref().theme.ops.mesh.match_face.face
            self.ui.face.callback = DrawFace(points, color=color)
            self.ui.face.handle = bpy.types.SpaceView3D.draw_handler_add(self.ui.face.callback.draw, (context,), 'WINDOW', 'POST_VIEW')

            context.window.cursor_set('SCROLL_XY')
            self._header(context)
            infobar.draw(context, event, None)
            context.window_manager.modal_handler_add(self)
            return {'RUNNING_MODAL'}
        else:
            self.report({'WARNING'}, 'View3D not found, cannot run operator')
            return {'CANCELLED'}

    def modal(self, context, event):

        if event.type == 'MIDDLEMOUSE':
            return {'PASS_THROUGH'}

        if event.type == 'MOUSEMOVE':
            _, _, points = self.get_face_data(context, event)
            self.ui.face.callback.update_batch(points)

        elif event.type in {'LEFTMOUSE', 'SPACE', 'RET', 'NUMPAD_ENTER'}:
            self._move_selection(context)
            self._end(context)
            return {'FINISHED'}

        elif event.type in {'RIGHTMOUSE', 'ESC'}:
            self._end(context)
            return {'CANCELLED'}

        context.area.tag_redraw()
        return {'RUNNING_MODAL'}

    def _end(self, context):
        '''End the operator'''
        context.window.cursor_set('CROSSHAIR')
        context.area.header_text_set(text=None)
        infobar.remove(context)
        bpy.types.SpaceView3D.draw_handler_remove(self.ui.face.handle, 'WINDOW')

    def _header(self, context):
        '''Set the header text'''
        context.area.header_text_set('Match Face')

    def _move_selection(self, context):
        '''Move the selected vertices'''

        for obj in context.selected_objects:

            normal = Vector(self.ray.normal)
            location = Vector(self.ray.location)

            # Transform normal and location to object's local space
            normal_local = obj.matrix_world.inverted().to_3x3() @ normal
            location_local = obj.matrix_world.inverted() @ location

            # Create BMesh from the active object's mesh
            bm = bmesh.from_edit_mesh(obj.data)
            selected_verts = [v for v in bm.verts if v.select]

            # Move selected vertices
            for v in selected_verts:
                to_target = location_local - v.co
                move_amount = to_target.project(normal_local)
                v.co += move_amount

            # Update normals

            selected_faces = [f for f in bm.faces if f.select]
            bmesh.ops.recalc_face_normals(bm, faces=selected_faces)

            # Update the mesh and free the BMesh
            bmesh.update_edit_mesh(obj.data, loop_triangles=True)

    def get_face_data(self, context, event):
        '''Get the face data from the raycast'''
        mouse_pos = Vector((event.mouse_region_x, event.mouse_region_y))
        self.ray = scene.ray_cast.visible(context, mouse_pos, modes=('OBJECT', 'EDIT'))
        verts = []

        if self.ray.hit:
            obj = self.ray.obj

            # Create a bmesh from the object's mesh data
            bm = bmesh.new()
            bm.from_mesh(obj.data)
            bm.faces.ensure_lookup_table()

            ngon = bm.faces[self.ray.index]

            # Get the vertices of the face
            verts = [obj.matrix_world @ vert.co for vert in ngon.verts]

            bm.free()

        return self.ray.location, self.ray.normal, verts


class Theme(bpy.types.PropertyGroup):
    face: bpy.props.FloatVectorProperty(name="Face", description="Face indicator color", default=(1.0, 0.6, 0.0, 0.3), subtype='COLOR', size=4, min=0.0, max=1.0)


types_classes = (
    Theme,
)

classes = (
    BOUT_OT_MatchFace,
)
