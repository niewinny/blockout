import bpy
import bmesh

import mathutils
from .operator import Block
from .data import Config, Modifier
from . import bevel, boolean
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

    def get_object(self, context, store_properties=True):
        if self.mode == 'BISECT':
            obj = context.active_object
            return obj

        new_mesh = bpy.data.meshes.new('BlockOut')
        new_obj = bpy.data.objects.new('BlockOut', new_mesh)
        if addon.pref().tools.block.obj.mode != 'CREATE':
            new_obj.display_type = 'WIRE'
        context.collection.objects.link(new_obj)
        # new_obj.select_set(True)

        if store_properties:
            self.objects.created = new_obj

        return new_obj

    def build_bmesh(self, obj):
        bm = bmesh.new()
        if self.mode == 'BISECT':
            mesh = obj.data
            bm.from_mesh(mesh)

        return bm

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
        mode = self.pref.mode
        active_obj = bpy.context.active_object
        detected_obj = self._get_detected_obj(self.pref.detected, active_obj)

        shape = self.pref.shape

        match shape:
            case 'RECTANGLE':
                face_index = rectangle.create(bm, plane)
                face = bmeshface.from_index(bm, face_index)
                rectangle.set_xy(face, plane, self.shape.rectangle.co, direction, local_space=True, symmetry=symmetry_draw)
                facet.set_z(face, normal, offset)
                self.update_bmesh(obj, bm, loop_triangles=True, destructive=True)
                # self._add_bevel(obj, bevel_offset, bevel_segments)
            case 'BOX':
                face_index = rectangle.create(bm, plane)
                face = bmeshface.from_index(bm, face_index)
                if symmetry_extrude:
                    offset = -extrusion
                fixed_extrusion = extrusion - offset
                rectangle.set_xy(face, plane, self.shape.rectangle.co, direction, local_space=True, symmetry=symmetry_draw)
                facet.set_z(face, normal, offset)
                extruded_faces = facet.extrude(bm, face, plane, fixed_extrusion)
                self._recalculate_normals(bm, extruded_faces)
                self._add_bevel(bm, obj, bevel_offset, bevel_segments, extruded_faces)
                self.update_bmesh(obj, bm, loop_triangles=True, destructive=True)
                self._add_boolean(obj, detected_obj, active_obj)
            case 'CIRCLE':
                face_index = circle.create(bm, plane, verts_number=self.shape.circle.verts)
                face = bmeshface.from_index(bm, face_index)
                circle.set_xy(face, plane, radius=self.shape.circle.radius, local_space=True)
                facet.set_z(face, normal, offset)
                self.update_bmesh(obj, bm, loop_triangles=True, destructive=True)
                # self._add_bevel(obj, bevel_offset, bevel_segments)
            case 'CYLINDER':
                face_index = circle.create(bm, plane, verts_number=self.shape.circle.verts)
                face = bmeshface.from_index(bm, face_index)
                circle.set_xy(face, plane, radius=self.shape.circle.radius, local_space=True)
                facet.set_z(face, normal, offset)
                cylinder_faces_indexes = facet.extrude(bm, face, plane, extrusion)
                face = bmeshface.from_index(bm, cylinder_faces_indexes[0])
                self._recalculate_normals(bm, cylinder_faces_indexes)
                self.update_bmesh(obj, bm, loop_triangles=True, destructive=True)
                self._add_boolean(obj, detected_obj, active_obj)
                # self._add_bevel(obj, bevel_offset, bevel_segments)
            case _:
                raise ValueError(f"Unsupported shape: {self.pref.shape}")

        self._set_origin(obj, plane, self.pref.direction)
        self._set_parent(mode, obj, detected_obj)

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
            bevel.add_modifier(obj, bevel_offset, bevel_segments)

    def _bevel_invoke(self, context, event):
        super()._bevel_invoke(context, event)
        bm = self.data.bm

        set_position, del_position = ({'MID', 'END'}, {}) if self.data.bevel.type == '3D' else ({'MID'}, {'END'})
        set_edges_indexes = [e.index for e in self.data.extrude.edges if e.position in set_position]
        del_edges_indexes = [e.index for e in self.data.extrude.edges if e.position in del_position]
        bevel.set_edge_weight(bm, set_edges_indexes)
        bevel.clean_edge_weight(bm, del_edges_indexes)

        if not self.modifiers.bevels:
            mod = bevel.add_modifier(self.data.obj, 0.0, self.data.bevel.segments)
            self.modifiers.bevels.append(Modifier(obj=self.data.obj, mod=mod))

        self.update_bmesh(self.data.obj, bm, loop_triangles=True, destructive=False)
        infobar.draw(context, event, self._infobar, blank=True)

    def _bevel_cleanup(self, context):
        if self.data.bevel.offset <= 0.0:
            if not self.modifiers.bevels:
                return

            for mod in self.modifiers.bevels:
                modifier.remove(mod.obj, mod.mod)

            bevel.del_edge_weight(self.data.bm)
            self.update_bmesh(self.data.obj, self.data.bm, loop_triangles=True, destructive=False)

    def _bevel_modal(self, context, event):
        super()._bevel_modal(context, event)
        if self.data.bevel.mode == 'OFFSET':
            offset = self.data.bevel.offset
            for mod in self.modifiers.bevels:
                mod.mod.width = offset

        if self.data.bevel.mode == 'SEGMENTS':
            segments = self.data.bevel.segments
            for mod in self.modifiers.bevels:
                mod.mod.segments = segments

    def _add_boolean(self, obj, detected_obj, active_obj):
        if self.pref.mode != 'CREATE':
            if self.shape.volume == '3D':
                bool_obj = detected_obj
                _selected = bpy.context.selected_objects[:]
                _selected_set = set(_selected + [bool_obj])
                # _selected_set.remove(obj)
                selected = list(_selected_set)
                for sel_obj in selected:
                    boolean.add_modifier(sel_obj, obj)
                obj.hide_set(True)
                obj.data.shade_smooth()

    def _boolean(self, mode, obj, bm):
        if mode != 'CREATE':
            if self.shape.volume == '3D':
                if not self.modifiers.booleans:
                    bool_obj = self._get_detected_obj(self.objects.detected, self.objects.active)
                    if not bool_obj:
                        return

                    _selected = self.objects.selected[:]
                    _selected_set = set(_selected + [bool_obj])
                    selected = list(_selected_set)
                    for sel_obj in selected:
                        mod = boolean.add_modifier(sel_obj, obj)
                        self.modifiers.booleans.append(Modifier(obj=sel_obj, mod=mod))

    def _finish(self, context):
        super()._finish(context)

        if self.mode != 'BISECT':
            self._bevel_cleanup(context)
            if self.config.mode != 'CREATE':
                self.data.obj.hide_set(True)
                self.data.obj.data.shade_smooth()

            self._set_origin(self.data.obj, self.data.draw.plane, self.data.draw.direction)
            detected_obj = self._get_detected_obj(self.pref.detected, self.objects.active)
            self._set_parent(self.config.mode, self.data.obj, detected_obj)

    def _set_origin(self, obj, plane, direction):
        _, normal = plane

        x_axis = direction.normalized()
        z_axis = normal.normalized()
        y_axis = z_axis.cross(x_axis).normalized()

        rot_mat = mathutils.Matrix((
            (x_axis.x, y_axis.x, z_axis.x),
            (x_axis.y, y_axis.y, z_axis.y),
            (x_axis.z, y_axis.z, z_axis.z),
        )).to_4x4()

        old_matrix = obj.matrix_world.copy()
        bbox_center = sum((old_matrix @ mathutils.Vector(corner) for corner in obj.bound_box), mathutils.Vector()) / 8
        new_loc = mathutils.Matrix.Translation(bbox_center)
        new_matrix = new_loc @ rot_mat

        diff = new_matrix.inverted() @ old_matrix
        obj.data.transform(diff)
        obj.matrix_world = new_matrix

    def _get_detected_obj(self, detected_obj, active_obj):
        if detected_obj == '':
            return active_obj
        return bpy.data.objects[detected_obj]

    def _set_parent(self, mode, obj, detected_obj):
        if mode != 'CREATE' and detected_obj is not None:
            parent_world = detected_obj.matrix_world.copy()
            obj.parent = detected_obj
            obj.matrix_parent_inverse = parent_world.inverted()

    def _cancel(self, context):
        super()._cancel(context)
        boolean.clear_modifiers(self.modifiers)


classes = (
    BOUT_OT_BlockObjTool,
)
