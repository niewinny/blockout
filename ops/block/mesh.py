import bpy
import bmesh

from .operator import Block
from .data import Config
from ...utils import addon, scene
from ...bmeshutils import bmeshface, rectangle, facet, box, circle, cylinder
from ...bmeshutils.mesh import set_copy, get_copy


class BOUT_OT_BlockMeshTool(Block):
    bl_idname = 'bout.block_mesh_tool'
    bl_label = 'Blockout Block'
    bl_options = {'REGISTER', 'UNDO', 'BLOCKING'}
    bl_description = "Tool for drawing a mesh"

    @classmethod
    def poll(cls, context):
        return context.area.type == 'VIEW_3D' and context.mode == 'EDIT_MESH'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True

        shape = self.pref.shape
        match shape:
            case 'RECTANGLE':
                col = layout.column(align=True)
                col.prop(self.shape.rectangle, 'co', text="Dimensions")
                layout.prop(self.pref, 'offset', text="Offset")
                col = layout.column(align=True)
                row = col.row(align=True)
                row.prop(self.pref.bevel, 'offset', text="Bevel")
                row.prop(self.pref.bevel, 'segments', text="")
            case 'BOX':
                col = layout.column(align=True)
                col.prop(self.shape.rectangle, 'co', text="Dimensions")
                col.prop(self.pref, 'extrusion', text="Z")
                layout.prop(self.pref, 'offset', text="Offset")
                row = layout.row(align=True)
                row.prop(self.pref.bevel, 'type', text="Bevel")
                row.prop(self.pref.bevel, 'offset', text="")
                row.prop(self.pref.bevel, 'segments', text="")
            case 'CIRCLE':
                layout.prop(self.shape.circle, 'radius', text="Radius")
                layout.prop(self.shape.circle, 'verts', text="Verts")
                layout.prop(self.pref, 'offset', text="Offset")
            case 'CYLINDER':
                layout.prop(self.shape.circle, 'radius', text="Radius")
                layout.prop(self.pref, 'extrusion', text="Dimensions Z")
                layout.prop(self.shape.circle, 'verts', text="Verts")
                layout.prop(self.pref, 'offset', text="Offset")

    def ray_cast(self, context):
        scene.set_active_object(context, self.mouse.init)
        if self.config.pick == 'SELECTED':
            ray = scene.ray_cast.edited(context, self.mouse.init)
        else:
            ray = scene.ray_cast.visible(context, self.mouse.init, modes={'EDIT', 'OBJECT'})
        return ray

    def _header_text(self):
        '''Set the header text'''
        pref = addon.pref().tools.block.mesh
        text = f"Shape: {pref.shape.capitalize()}"
        return text

    def set_config(self, context):
        config = Config()
        config.shape = addon.pref().tools.block.mesh.shape
        config.form = addon.pref().tools.block.form
        config.align = addon.pref().tools.block.align
        config.pick = addon.pref().tools.block.mesh.pick
        config.mode = addon.pref().tools.block.mesh.mode
        config.type = 'EDIT_MESH'
        return config

    def get_object(self, context, store_properties=True):
        obj = context.edit_object
        return obj

    def build_bmesh(self, obj):
        obj.update_from_editmode()
        bm = bmesh.from_edit_mesh(obj.data)
        return bm

    def update_bmesh(self, obj, bm, loop_triangles=False, destructive=False):
        mesh = obj.data
        bm.normal_update()
        bmesh.update_edit_mesh(mesh, loop_triangles=loop_triangles, destructive=destructive)

    def build_geometry(self, obj, bm):

        offset = self.pref.offset
        bevel_offset = self.pref.bevel.offset
        bevel_segments = self.pref.bevel.segments
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
                rectangle.set_xy(face, plane, self.shape.rectangle.co, direction, local_space=True, symmetry=symmetry_draw)
                facet.set_z(face, normal, offset)
                face_index = facet.bevel(bm, face, bevel_offset, bevel_segments=bevel_segments)
                face = bmeshface.from_index(bm, face_index)
                facet.remove_doubles(bm, face)
                self.update_bmesh(obj, bm, loop_triangles=True, destructive=True)
            case 'BOX':
                face_index = rectangle.create(bm, plane)
                face = bmeshface.from_index(bm, face_index)
                if symmetry_extrude:
                    offset = -extrusion
                fixed_extrusion = extrusion - offset
                rectangle.set_xy(face, plane, self.shape.rectangle.co, direction, local_space=True, symmetry=symmetry_draw)
                if self.pref.bevel.type == '3D':
                    facet.set_z(face, normal, offset)
                    box_faces_indexes = facet.extrude(bm, face, plane, fixed_extrusion)
                    box.bevel(bm, box_faces_indexes, bevel_offset, bevel_segments=bevel_segments)
                else:
                    face_index = facet.bevel(bm, face, bevel_offset, bevel_segments=bevel_segments)
                    face = bmeshface.from_index(bm, face_index)
                    facet.remove_doubles(bm, face)
                    if self.shape.volume == '3D':
                        facet.set_z(face, normal, offset)
                        extruded_faces = facet.extrude(bm, face, plane, fixed_extrusion)
                        self._recalculate_normals(bm, extruded_faces)
                self.update_bmesh(obj, bm, loop_triangles=True, destructive=True)
                self._boolean(self.pref.mode, obj, bm)
            case 'CIRCLE':
                face_index = circle.create(bm, plane, verts_number=self.shape.circle.verts)
                face = bmeshface.from_index(bm, face_index)
                circle.set_xy(face, plane, radius=self.shape.circle.radius, local_space=True)
                facet.set_z(face, normal, offset)
                self.update_bmesh(obj, bm, loop_triangles=True, destructive=True)
            case 'CYLINDER':
                face_index = circle.create(bm, plane, verts_number=self.shape.circle.verts)
                face = bmeshface.from_index(bm, face_index)
                circle.set_xy(face, plane, radius=self.shape.circle.radius, local_space=True)
                cylinder_faces_indexes = facet.extrude(bm, face, plane, extrusion)
                face = bmeshface.from_index(bm, cylinder_faces_indexes[0])
                self._recalculate_normals(bm, cylinder_faces_indexes)
                facet.set_z(face, normal, offset)
                cylinder.bevel(bm, cylinder_faces_indexes, bevel_offset, bevel_segments=bevel_segments)
                self.update_bmesh(obj, bm, loop_triangles=True, destructive=True)
                self._boolean(self.pref.mode, obj, bm)
            case _:
                raise ValueError(f"Unsupported shape: {self.pref.shape}")

        return face_index

    def _extrude_invoke(self, context, event):
        super()._extrude_invoke(context, event)
        if self.config.mode != 'CREATE':
            self.data.copy.draw = set_copy(self.data.obj)

    def _extrude_modal(self, context, event):
        if self.config.mode != 'CREATE':
            get_copy(self.data.obj, self.data.bm, self.data.copy.draw)
        super()._extrude_modal(context, event)

    def _boolean(self, mode, obj, bm):
        super()._boolean(mode, obj, bm)
        if mode != 'CREATE':
            if self.shape.volume == '3D':
                bpy.ops.mesh.intersect_boolean(operation='DIFFERENCE', use_swap=False, use_self=False, threshold=1e-06, solver='FAST')
                self.update_bmesh(obj, bm, loop_triangles=True, destructive=True)

    def _bevel(self):
        get_copy(self.data.obj, self.data.bm, self.data.copy.init)

        obj = self.data.obj
        bm = self.data.bm

        self.store_props()
        face_index = self.build_geometry(obj, bm)
        self.data.draw.face = face_index
        self.update_bmesh(obj, bm, loop_triangles=True, destructive=True)

    def _bevel_invoke(self, context, event):
        super()._bevel_invoke(context, event)
        self._bevel()

    def _bevel_modal(self, context, event):
        super()._bevel_modal(context, event)
        self._bevel()

    def _finish(self, context):
        super()._finish(context)
        if self.mode != 'BISECT':
            self.update_bmesh(self.data.obj, self.data.bm, loop_triangles=True, destructive=True)


classes = (
    BOUT_OT_BlockMeshTool,
)
