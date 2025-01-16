import bpy
import bmesh

from ..block.operator import Block
from ..block.data import Config
from ...utils import addon, scene

from ...bmeshutils import bmeshface, rectangle, facet, circle


class BOUT_OT_BlockObjTool(Block):
    bl_idname = 'bout.block_obj_tool'
    bl_label = 'Blockout Block'
    bl_options = {'REGISTER', 'UNDO', 'BLOCKING'}
    bl_description = "Tool for drawing a mesh"

    @classmethod
    def poll(cls, context):
        return context.area.type == 'VIEW_3D'

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True

        shape = self.pref.shape
        match shape:
            case 'RECTANGLE':
                col = layout.column(align=True)
                col.prop(self.shapes.rectangle, 'co', text="Dimensions")
                layout.prop(self.pref, 'offset', text="Offset")
            case 'BOX':
                col = layout.column(align=True)
                col.prop(self.shapes.rectangle, 'co', text="Dimensions")
                col.prop(self.pref, 'extrusion', text="Z")
                layout.prop(self.pref, 'offset', text="Offset")
            case 'CIRCLE':
                layout.prop(self.shapes.circle, 'radius', text="Radius")
                layout.prop(self.shapes.circle, 'verts', text="Verts")
                layout.prop(self.pref, 'offset', text="Offset")
            case 'CYLINDER':
                layout.prop(self.shapes.circle, 'radius', text="Radius")
                layout.prop(self.pref, 'extrusion', text="Dimensions Z")
                layout.prop(self.shapes.circle, 'verts', text="Verts")
                layout.prop(self.pref, 'offset', text="Offset")

    def ray_cast(self, context):
        if self.config.pick == 'SELECTED':
            ray = scene.ray_cast.selected(context, self.mouse.init)
        else:
            ray = scene.ray_cast.visible(context, self.mouse.init, modes={'EDIT', 'OBJECT'})
        return ray

    def _header_text(self):
        '''Set the header text'''
        pref = addon.pref().tools.block.obj
        text = f"Shape: {pref.shape.capitalize()}"

        return text

    def set_config(self, context):
        config = Config()
        config.shape = addon.pref().tools.block.obj.shape
        config.form = addon.pref().tools.block.form
        config.align = addon.pref().tools.block.align
        config.pick = addon.pref().tools.block.obj.pick
        config.mode = addon.pref().tools.block.obj.mode
        config.type = 'OBJECT'

        return config

    def build_bmesh(self, context):

        new_mesh = bpy.data.meshes.new('BlockOut')
        new_obj = bpy.data.objects.new('BlockOut', new_mesh)
        if addon.pref().tools.block.obj.mode != 'CREATE':
            new_obj.display_type = 'WIRE'
        context.collection.objects.link(new_obj)

        bm = bmesh.new()
        return new_obj, bm

    def build_geometry(self, obj, bm):

        offset = self.pref.offset
        location = self.pref.plane.location
        normal = self.pref.plane.normal
        plane = (location, normal)
        direction = self.pref.direction
        extrusion = self.pref.extrusion
        symmetry_extrude = self.pref.symmetry_extrude
        symmetry_draw = self.pref.symmetry_draw

        shape = self.pref.shape

        if self.pref.mode != 'CREATE':
            bpy.ops.mesh.select_all(action='DESELECT')

        match shape:
            case 'RECTANGLE':
                face_index = rectangle.create(bm, plane)
                face = bmeshface.from_index(bm, face_index)
                rectangle.set_xy(face, plane, self.shapes.rectangle.co, direction, local_space=True, symmetry=symmetry_draw)
                facet.set_z(face, normal, offset)
            case 'BOX':
                face_index = rectangle.create(bm, plane)
                face = bmeshface.from_index(bm, face_index)
                if symmetry_extrude:
                    offset = -extrusion
                rectangle.set_xy(face, plane, self.shapes.rectangle.co, direction, local_space=True, symmetry=symmetry_draw)
                facet.set_z(face, normal, offset)
                extruded_faces = facet.extrude(bm, face, plane, extrusion)
                self._recalculate_normals(bm, extruded_faces)
            case 'CIRCLE':
                face_index = circle.create(bm, plane, verts_number=self.shapes.circle.verts)
                face = bmeshface.from_index(bm, face_index)
                circle.set_xy(face, plane, radius=self.shapes.circle.radius, local_space=True)
                facet.set_z(face, normal, offset)
            case 'CYLINDER':
                face_index = circle.create(bm, plane, verts_number=self.shapes.circle.verts)
                face = bmeshface.from_index(bm, face_index)
                circle.set_xy(face, plane, radius=self.shapes.circle.radius, local_space=True)
                facet.set_z(face, normal, offset)
                cylinder_faces_indexes = facet.extrude(bm, face, plane, extrusion)
                face = bmeshface.from_index(bm, cylinder_faces_indexes[0])
                self._recalculate_normals(bm, cylinder_faces_indexes)
            case _:
                raise ValueError(f"Unsupported shape: {self.pref.shape}")

        return face_index

    def update_bmesh(self, obj, bm, loop_triangles=False, destructive=False):
        mesh = obj.data
        bm.to_mesh(mesh)

    def _boolean(self, obj, bm):
        pass


classes = (
    BOUT_OT_BlockObjTool,
)
