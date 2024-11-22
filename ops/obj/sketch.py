import bpy
import bmesh

from ...src.sketch import Sketch, Config
from ...utils import addon, scene


class BOUT_OT_SketchObjTool(Sketch):
    bl_idname = 'bout.sketch_obj_tool'
    bl_label = 'Blockout Sketch'
    bl_options = {'REGISTER', 'UNDO', 'BLOCKING'}
    bl_description = "Tool for drawing a mesh"

    @classmethod
    def poll(cls, context):
        return context.area.type == 'VIEW_3D'

    def ray_cast(self, context):
        if self.config.pick == 'SELECTED':
            ray = scene.ray_cast.selected(context, self.mouse.init)
        else:
            ray = scene.ray_cast.visible(context, self.mouse.init, modes={'EDIT', 'OBJECT'})
        return ray

    def _header_text(self):
        '''Set the header text'''
        pref = addon.pref().tools.sketch.obj
        text = f"Shape: {pref.shape.capitalize()}"

        return text

    def set_config(self, context):
        config = Config()
        config.shape = addon.pref().tools.sketch.obj.shape
        config.form = addon.pref().tools.sketch.form
        config.align = addon.pref().tools.sketch.align
        config.pick = addon.pref().tools.sketch.obj.pick
        config.mode = addon.pref().tools.sketch.obj.mode
        config.type = 'OBJECT'

        return config

    def build_bmesh(self, context):

        new_mesh = bpy.data.meshes.new('BlockOut')
        new_obj = bpy.data.objects.new('BlockOut', new_mesh)
        if addon.pref().tools.sketch.obj.mode != 'CREATE':
            new_obj.display_type = 'WIRE'
        context.collection.objects.link(new_obj)

        bm = bmesh.new()
        return new_obj, bm

    def update_bmesh(self, obj, bm, loop_triangles=False, destructive=False):
        mesh = obj.data
        bm.to_mesh(mesh)

    def _boolean(self, obj, bm):
        pass


classes = (
    BOUT_OT_SketchObjTool,
)
