import bpy
import bmesh

from .operator import Block
from .data import Config, BevelMod
from . import bevel
from ...utils import addon, scene, infobar, modifier

from ...bmeshutils import bmeshface, rectangle, facet, circle


class BOUT_OT_BlockObjTool(Block):
    bl_idname = 'bout.block_obj_tool'
    bl_label = 'Blockout Block'
    bl_options = {'REGISTER', 'UNDO', 'BLOCKING'}
    bl_description = "Tool for drawing a mesh"
    

    @classmethod
    def poll(cls, context):
        return context.area.type == 'VIEW_3D'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.op = 'OBJECT'

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

    def build_bmesh(self, context, store_properties=True):

        new_mesh = bpy.data.meshes.new('BlockOut')
        new_obj = bpy.data.objects.new('BlockOut', new_mesh)
        if addon.pref().tools.block.obj.mode != 'CREATE':
            new_obj.display_type = 'WIRE'
        context.collection.objects.link(new_obj)
        new_obj.select_set(True)

        if store_properties:
            self.objects.created = new_obj

        bm = bmesh.new()
        return new_obj, bm

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
                rectangle.set_xy(face, plane, self.shapes.rectangle.co, direction, local_space=True, symmetry=symmetry_draw)
                facet.set_z(face, normal, offset)
                # self._add_bevel(obj, bevel_offset, bevel_segments)
            case 'BOX':
                face_index = rectangle.create(bm, plane)
                face = bmeshface.from_index(bm, face_index)
                if symmetry_extrude:
                    offset = -extrusion
                fixed_extrusion = extrusion - offset
                rectangle.set_xy(face, plane, self.shapes.rectangle.co, direction, local_space=True, symmetry=symmetry_draw)
                facet.set_z(face, normal, offset)
                extruded_faces = facet.extrude(bm, face, plane, fixed_extrusion)
                self._recalculate_normals(bm, extruded_faces)
                self._add_bevel(bm, obj, bevel_offset, bevel_segments, extruded_faces)
            case 'CIRCLE':
                face_index = circle.create(bm, plane, verts_number=self.shapes.circle.verts)
                face = bmeshface.from_index(bm, face_index)
                circle.set_xy(face, plane, radius=self.shapes.circle.radius, local_space=True)
                facet.set_z(face, normal, offset)
                # self._add_bevel(obj, bevel_offset, bevel_segments)
            case 'CYLINDER':
                face_index = circle.create(bm, plane, verts_number=self.shapes.circle.verts)
                face = bmeshface.from_index(bm, face_index)
                circle.set_xy(face, plane, radius=self.shapes.circle.radius, local_space=True)
                facet.set_z(face, normal, offset)
                cylinder_faces_indexes = facet.extrude(bm, face, plane, extrusion)
                face = bmeshface.from_index(bm, cylinder_faces_indexes[0])
                self._recalculate_normals(bm, cylinder_faces_indexes)
                # self._add_bevel(obj, bevel_offset, bevel_segments)
            case _:
                raise ValueError(f"Unsupported shape: {self.pref.shape}")

        return face_index

    def update_bmesh(self, obj, bm, loop_triangles=False, destructive=False):
        mesh = obj.data
        bm.to_mesh(mesh)

    def _extrude_invoke(self, context, event):
        super()._extrude_invoke(context, event)
        infobar.draw(context, event, self._infobar, blank=True)

    def _add_bevel(self, bm, obj, bevel_offset, bevel_segments, extruded_faces):
        if bevel_offset > 0.0:

            extruded_bot_edges = [e.index for e in bmeshface.from_index(bm, extruded_faces[0]).edges]
            extruded_top_edges = [e.index for e in bmeshface.from_index(bm, extruded_faces[-1]).edges]
            if self.pref.bevel.type == '2D':
                extruded_edges = [e.index for f_idx in extruded_faces[1:-1] for e in bmeshface.from_index(bm, f_idx).edges if e.index not in extruded_bot_edges and e.index not in extruded_top_edges]
            else:
                extruded_edges = [e.index for f_idx in extruded_faces[1:-1] for e in bmeshface.from_index(bm, f_idx).edges if e.index not in extruded_bot_edges]

            bevel.set_edge_weight(bm, extruded_edges)

            mod = modifier.add(obj, "Bevel", 'BEVEL')
            mod.width = bevel_offset
            mod.segments = bevel_segments
            mod.limit_method = 'WEIGHT'
            mod.edge_weight = "bout_bevel_weight_edge"

    def _bevel_invoke(self, context, event):
        super()._bevel_invoke(context, event)

        bm = self.data.bm

        set_position, del_position = ({'MID', 'END'}, {}) if self.data.bevel.type == '3D' else ({'MID'}, {'END'})
        set_edges_indexes = [e.index for e in self.data.extrude.edges if e.position in set_position]
        del_edges_indexes = [e.index for e in self.data.extrude.edges if e.position in del_position]
        bevel.set_edge_weight(bm, set_edges_indexes)
        bevel.clean_edge_weight(bm, del_edges_indexes)
        self.update_bmesh(self.data.obj, bm, loop_triangles=True, destructive=False)

        if not self.modifiers.bevels:
            mod = modifier.add(self.data.obj, "Bevel", 'BEVEL')
            mod.width = 0.0
            mod.segments = self.data.bevel.segments
            mod.use_pin_to_last = True
            mod.limit_method = 'WEIGHT'
            mod.edge_weight = "bout_bevel_weight_edge"
            self.modifiers.bevels.append(BevelMod(obj=self.data.obj, mod=mod))

        infobar.draw(context, event, self._infobar, blank=True)

    def _bevel_execute(self, context):
        super()._bevel_execute(context)
        if self.data.bevel.offset <= 0.0:
            for mod in self.modifiers.bevels:
                modifier.remove(mod.obj, mod.mod)

            bevel.del_edge_weight(self.data.bm)
            self.update_bmesh(self.data.obj, self.data.bm, loop_triangles=True, destructive=False)

    def _bevel_modal(self, context):
        super()._bevel_modal(context)
        if self.data.bevel.mode == 'OFFSET':
            offset = self.data.bevel.offset
            for mod in self.modifiers.bevels:
                mod.mod.width = offset

        if self.data.bevel.mode == 'SEGMENTS':
            segments = self.data.bevel.segments
            for mod in self.modifiers.bevels:
                mod.mod.segments = segments

    def _boolean(self, obj, bm):
        pass


classes = (
    BOUT_OT_BlockObjTool,
)
