from dataclasses import dataclass, field
import bpy
import bmesh

from ..mesh.draw import DrawMesh, Config
from ...utils import addon


class BOUT_OT_DrawObjTool(DrawMesh):
    bl_idname = 'bout.draw_obj_tool'
    bl_label = 'Draw Polygon'
    bl_options = {'REGISTER', 'UNDO', 'BLOCKING'}
    bl_description = "Tool for drawing a mesh"

    @classmethod
    def poll(cls, context):
        return context.area.type == 'VIEW_3D'

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

        new_mesh = bpy.data.meshes.new('BlockOut')
        new_obj = bpy.data.objects.new('BlockOut', new_mesh)
        context.collection.objects.link(new_obj)

        self.data.obj = new_obj
        self.data.bm = bmesh.new()

    def update_bmesh(self, loop_triangles=False, destructive=False):
        obj = self.data.obj
        mesh = obj.data
        self.data.bm.to_mesh(mesh)


class Theme(bpy.types.PropertyGroup):
    face: bpy.props.FloatVectorProperty(name="Face", description="Face indicator color", default=(1.0, 0.6, 0.0, 0.3), subtype='COLOR', size=4, min=0.0, max=1.0)


types_classes = (
    Theme,
)

classes = (
    BOUT_OT_DrawObjTool,
)
