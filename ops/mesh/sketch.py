import bpy
import bmesh

from ...src.sketch import Sketch, Config
from ...utils import addon, scene
from ...bmeshutils import bmeshface, rectangle, facet, box, circle
from ...bmeshutils.mesh import set_copy, get_copy


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
        config.mode = addon.pref().tools.sketch.mesh.mode
        config.type = 'MESH'

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

    def _extrude_invoke(self, context):
        super()._extrude_invoke(context)
        if self.config.mode != 'CREATE':
            self.data.copy.extrude = set_copy(self.data.obj)

    def _extrude_modal(self, context, event):
        if self.config.mode != 'CREATE':
            get_copy(self.data.obj, self.data.bm, self.data.copy.extrude)
        super()._extrude_modal(context, event)

    def _boolean(self, obj, bm):
        bpy.ops.mesh.intersect_boolean(operation='DIFFERENCE', use_swap=False, use_self=False, threshold=1e-06, solver='FAST')
        self.update_bmesh(obj, bm, loop_triangles=True, destructive=True)

    def build_geometry(self, obj, bm):

        offset = self.pref.offset
        bevel_offset = self.pref.bevel.offset
        bevel_segments = self.pref.bevel.segments
        location = self.pref.plane.location
        normal = self.pref.plane.normal
        plane = (location, normal)
        direction = self.pref.direction
        extrusion = self.pref.extrusion

        shape = self.pref.shape

        if self.pref.mode != 'CREATE':
            selected_verts = [v for v in bm.verts if v.select]
            for v in selected_verts:
                v.select = False
            bm.select_flush(False)

        match shape:
            case 'RECTANGLE':
                face_index = rectangle.create(bm, plane)
                face = bmeshface.from_index(bm, face_index)
                rectangle.set_xy(face, plane, self.shapes.rectangle.co, direction, local_space=True)
                facet.set_z(face, normal, offset)
                facet.bevel(bm, face, bevel_offset, bevel_segments=bevel_segments)
            case 'BOX':
                face_index = rectangle.create(bm, plane)
                face = bmeshface.from_index(bm, face_index)
                rectangle.set_xy(face, plane, self.shapes.rectangle.co, direction, local_space=True)
                if self.pref.bevel.type == '3D':
                    extrusion = extrusion + offset
                    box_faces_indexes = facet.extrude(bm, face, plane, extrusion)
                    facet.set_z(face, normal, offset)
                    box.bevel(bm, box_faces_indexes, bevel_offset, bevel_segments=bevel_segments)
                else:
                    face_index = facet.bevel(bm, face, bevel_offset, bevel_segments=bevel_segments)
                    face = bmeshface.from_index(bm, face_index)
                    if self.pref.volume == '3D':
                        extruded_faces = facet.extrude(bm, face, plane, extrusion)
                        self._recalculate_normals(bm, extruded_faces)
                        facet.set_z(face, normal, offset)
            case 'CIRCLE':
                face_index = circle.create(bm, plane, verts_number=self.shapes.circle.verts)
                face = bmeshface.from_index(bm, face_index)
                circle.set_xy(face, plane, radius=self.shapes.circle.radius, local_space=True)
                facet.set_z(face, normal, offset)
            case 'CYLINDER':
                face_index = circle.create(bm, plane, verts_number=self.shapes.circle.verts)
                face = bmeshface.from_index(bm, face_index)
                circle.set_xy(face, plane, radius=self.shapes.circle.radius, local_space=True)
                extruded_faces = facet.extrude(bm, face, plane, extrusion)
                face = bmeshface.from_index(bm, extruded_faces[0])
                self._recalculate_normals(bm, extruded_faces)
                facet.set_z(face, normal, offset)
            case _:
                raise ValueError(f"Unsupported shape: {self.pref.shape}")

    def _bevel_modal(self, context):
        super()._bevel_modal(context)
        get_copy(self.data.obj, self.data.bm, self.data.copy.init)

        obj = self.data.obj
        bm = self.data.bm

        self.store_props()
        self.build_geometry(obj, bm)
        self.update_bmesh(obj, bm, loop_triangles=True, destructive=True)


classes = (
    BOUT_OT_SketchMeshTool,
)
