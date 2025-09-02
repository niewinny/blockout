import bpy
import bmesh
import mathutils

from .operator import Block
from .data import Config, Modifier
from . import bevel, boolean, weld, draw, extrude
from ...utils import addon, scene, infobar, modifier, collection

from ...utilsbmesh import bmeshface, rectangle, facet, circle, sphere, corner, ngon


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
        ray = scene.ray_cast.selected(context, self.mouse.init)
        return ray

    def _header_text(self):
        '''Set the header text'''
        pref = addon.pref().tools.block
        text = f"Shape: {pref.shape.capitalize()}"

        return text

    def set_config(self, context):
        '''Set the config dataclass'''
        config = Config()
        config.shape = addon.pref().tools.block.shape
        config.form = addon.pref().tools.block.form
        config.align = addon.pref().tools.block.align
        config.mode = addon.pref().tools.block.mode
        config.type = 'OBJECT'
        config.snap = context.scene.tool_settings.use_snap
        return config

    def _invoke(self, context, event):
        '''Invoke the operator'''
        if self.mode == 'BISECT':
            return
        self.objects.created = self.data.obj
        if self.mode == 'DRAW' and self.config.mode == 'SLICE':
            self.objects.duplicated = self._duplicate_objects(context)

    def get_object(self, context):
        if self.mode == 'BISECT':
            active_obj = context.active_object if context.active_object and context.active_object.type == 'MESH' else None
            selected_objects = [obj for obj in context.selected_objects if obj.type == 'MESH']

            if active_obj:
                return active_obj

            if len(selected_objects) > 1:
                active_obj = selected_objects[0] if selected_objects else None
                return active_obj

        new_mesh = bpy.data.meshes.new('BlockOut')
        new_obj = bpy.data.objects.new('BlockOut', new_mesh)

        mode = addon.pref().tools.block.mode
        if mode not in ('ADD', 'BISECT'):
            new_obj.display_type = 'WIRE'
            new_obj.hide_render = True
            # Link to Cutters collection instead of active collection
            cutters_collection = collection.get_or_create_cutters_collection()
            cutters_collection.objects.link(new_obj)
        else:
            context.collection.objects.link(new_obj)

        return new_obj

    def build_bmesh(self, obj):
        bm = bmesh.new()
        if self.mode == 'BISECT':
            mesh = obj.data
            bm.from_mesh(mesh)

        return bm

    def build_geometry(self, obj, bm):

        mode = self.pref.mode
        offset = self.pref.offset
        bevel_round_enable = self.pref.bevel.round.enable
        bevel_round_offset = self.pref.bevel.round.offset
        bevel_round_segments = self.pref.bevel.round.segments
        bevel_round = (bevel_round_enable, bevel_round_offset, bevel_round_segments)
        bevel_fill_enable = self.pref.bevel.fill.enable
        bevel_fill_offset = self.pref.bevel.fill.offset
        bevel_fill_segments = self.pref.bevel.fill.segments
        bevel_fill = (bevel_fill_enable, bevel_fill_offset, bevel_fill_segments)
        location = self.pref.plane.location
        normal = self.pref.plane.normal
        plane = (location, normal)
        direction = self.pref.direction
        extrusion = self.pref.extrusion
        symmetry_extrude = self.pref.symmetry_extrude
        symmetry_draw = (self.pref.symmetry_draw_x, self.pref.symmetry_draw_y)
        detected_obj = bpy.data.objects[self.pref.detected] if self.pref.detected else None

        shape = self.pref.shape

        match shape:
            case 'RECTANGLE':
                faces_indexes = rectangle.create(bm, plane)
                face = bmeshface.from_index(bm, faces_indexes[0])
                rectangle.set_xy(face, plane, self.shape.rectangle.co, direction, local_space=True, symmetry=symmetry_draw)
                facet.set_z(face, normal, offset)
                if mode == 'ADD':
                    bevel.mod.verts(obj, bevel_round)
                    self.update_bmesh(obj, bm, loop_triangles=True, destructive=True)
                else:
                    extruded_faces = facet.extrude(bm, face, plane, extrusion)
                    self._recalculate_normals(bm, extruded_faces)
                    bevel.mod.faces(bm, obj, bevel_round, bevel_fill, extruded_faces)
                    self.update_bmesh(obj, bm, loop_triangles=True, destructive=True)
                    self._add_boolean(obj, detected_obj, extruded_faces[0])
            case 'BOX':
                faces_indexes = rectangle.create(bm, plane)
                face = bmeshface.from_index(bm, faces_indexes[0])
                rectangle.set_xy(face, plane, self.shape.rectangle.co, direction, local_space=True, symmetry=symmetry_draw)
                facet.set_z(face, normal, offset)
                extruded_faces = facet.extrude(bm, face, plane, extrusion)
                self._recalculate_normals(bm, extruded_faces)
                if symmetry_extrude:
                    facet.set_z(bmeshface.from_index(bm, extruded_faces[0]), normal, -extrusion)
                bevel.mod.faces(bm, obj, bevel_round, bevel_fill, extruded_faces)
                self.update_bmesh(obj, bm, loop_triangles=True, destructive=True)
                self._add_boolean(obj, detected_obj, extruded_faces[0])
            case 'CIRCLE':
                faces_indexes = circle.create(bm, plane, verts_number=self.shape.circle.verts)
                face = bmeshface.from_index(bm, faces_indexes[0])
                circle.set_xy(face, plane, None, direction, radius=self.shape.circle.radius, local_space=True)
                facet.set_z(face, normal, offset)
                if mode == 'ADD':
                    bevel.mod.verts(obj, bevel_round)
                    self.update_bmesh(obj, bm, loop_triangles=True, destructive=True)
                else:
                    extruded_faces = facet.extrude(bm, face, plane, extrusion)
                    self._recalculate_normals(bm, extruded_faces)
                    bevel.mod.faces(bm, obj, bevel_round, bevel_fill, extruded_faces)
                    self.update_bmesh(obj, bm, loop_triangles=True, destructive=True)
                    self._add_boolean(obj, detected_obj, extruded_faces[0])
            case 'CYLINDER':
                faces_indexes = circle.create(bm, plane, verts_number=self.shape.circle.verts)
                face = bmeshface.from_index(bm, faces_indexes[0])
                circle.set_xy(face, plane, None, direction, radius=self.shape.circle.radius, local_space=True)
                facet.set_z(face, normal, offset)
                extruded_faces = facet.extrude(bm, face, plane, extrusion)
                self._recalculate_normals(bm, extruded_faces)
                if symmetry_extrude:
                    facet.set_z(bmeshface.from_index(bm, extruded_faces[0]), normal, -extrusion)
                bevel.mod.faces(bm, obj, bevel_round, bevel_fill, extruded_faces)
                self.update_bmesh(obj, bm, loop_triangles=True, destructive=True)
                self._add_boolean(obj, detected_obj, extruded_faces[0])
            case 'SPHERE':
                sphere.create(bm, plane, direction, radius=self.shape.sphere.radius, subd=self.shape.sphere.subd)
                self.update_bmesh(obj, bm, loop_triangles=True, destructive=True)
                self._add_boolean(obj, detected_obj, extruded_faces[0])
            case 'CORNER':
                faces_indexes = corner.create(bm, plane)
                faces = [bmeshface.from_index(bm, index) for index in faces_indexes]
                corner.set_xy(faces, plane, self.shape.corner.co, direction, (self.shape.corner.min, self.shape.corner.max), local_space=True)
                rotations = (self.shape.corner.min, self.shape.corner.max)
                extruded_face_indexes, edge_index = corner.extrude(bm, faces, direction, normal, rotations, extrusion)
                corner.offset(bm, extruded_face_indexes, direction, normal, rotations, offset)
                bevel.mod.edges(bm, obj, [edge_index], bevel_round)
                self.update_bmesh(obj, bm, loop_triangles=True, destructive=True)
                self._add_boolean(obj, detected_obj, extruded_face_indexes[0])
            case 'NGON':
                face = ngon.new(bm, self.pref.ngon)
                facet.set_z(face, normal, offset)
                if mode == 'ADD':
                    bevel.mod.verts(obj, bevel_round)
                    self.update_bmesh(obj, bm, loop_triangles=True, destructive=True)
                else:
                    extruded_faces = facet.extrude(bm, face, plane, extrusion)
                    self._recalculate_normals(bm, extruded_faces)
                    bevel.mod.faces(bm, obj, bevel_round, bevel_fill, extruded_faces)
                    self.update_bmesh(obj, bm, loop_triangles=True, destructive=True)
                    self._add_boolean(obj, detected_obj, extruded_faces[0])
            case 'NHEDRON':
                face = ngon.new(bm, self.pref.ngon)
                facet.set_z(face, normal, offset)
                extruded_faces = facet.extrude(bm, face, plane, extrusion)
                self._recalculate_normals(bm, extruded_faces)
                bevel.mod.faces(bm, obj, bevel_round, bevel_fill, extruded_faces)
                self.update_bmesh(obj, bm, loop_triangles=True, destructive=True)
                self._add_boolean(obj, detected_obj, extruded_faces[0])
            case _:
                raise ValueError(f"Unsupported shape: {self.pref.shape}")

        self._set_origin(obj)

        if self.pref.reveal:
            self._reveal_objects(bpy.context, obj)

    def update_bmesh(self, obj, bm, loop_triangles=False, destructive=False):
        mesh = obj.data
        bm.to_mesh(mesh)

    def _draw_invoke(self, context, event):
        mesh = draw.invoke(self, context)
        self._boolean(self.config.mode, self.data.obj)
        infobar.draw(context, event, self._infobar, blank=True)
        return mesh

    def _extrude_invoke(self, context, event):
        super()._extrude_invoke(context, event)
        self._boolean(self.config.mode, self.data.obj)
        infobar.draw(context, event, self._infobar, blank=True)

    def _bevel_invoke(self, context, event):
        super()._bevel_invoke(context, event)
        bm = self.data.bm

        angle, affect = 'ANGLE', 'VERTICES'

        if self.shape.volume == '3D':
            set_round_edges_indexes = [e.index for e in self.data.extrude.edges if e.position == 'MID']
            set_fill_edges_indexes = [e.index for e in self.data.extrude.edges if e.position == 'END']

            bevel.set_edge_weight(bm, set_round_edges_indexes, type='ROUND')
            bevel.set_edge_weight(bm, set_fill_edges_indexes, type='FILL')

            angle, affect = 'WEIGHT', 'EDGES'

        if not self.modifiers.bevels:
            mod, type = bevel.add_modifier(self.data.obj, 0.0, self.data.bevel.round.segments, type='ROUND', limit_method=angle, affect=affect)
            self.modifiers.bevels.append(Modifier(obj=self.data.obj, mod=mod, type=type))
            mod, type = weld.add_modifier(self.data.obj, type='ROUND')
            self.modifiers.welds.append(Modifier(obj=self.data.obj, mod=mod, type=type))
            mod, type = bevel.add_modifier(self.data.obj, 0.0, self.data.bevel.fill.segments, type='FILL')
            self.modifiers.bevels.append(Modifier(obj=self.data.obj, mod=mod, type=type))
            mod, type = weld.add_modifier(self.data.obj, type='FILL')
            self.modifiers.welds.append(Modifier(obj=self.data.obj, mod=mod, type=type))
        else:
            for m in self.modifiers.bevels:
                if m.type == 'FILL':
                    m.mod.segments = self.data.bevel.fill.segments

        self._boolean(self.pref.mode, self.data.obj)
        self.update_bmesh(self.data.obj, bm, loop_triangles=True, destructive=False)
        infobar.draw(context, event, self._infobar, blank=True)

    def _bevel_cleanup(self, context):
        if not self.modifiers.bevels:
            return

        for m in self.modifiers.bevels[:]:
            if m.type == 'ROUND' and self.data.bevel.round.offset <= 0.0:
                modifier.remove(m.obj, m.mod)
                self.modifiers.bevels.remove(m)
            elif m.type == 'FILL' and self.data.bevel.fill.offset <= 0.0:
                modifier.remove(m.obj, m.mod)
                self.modifiers.bevels.remove(m)

        for m in self.modifiers.welds[:]:
            if m.type == 'ROUND' and self.data.bevel.round.offset <= 0.0:
                modifier.remove(m.obj, m.mod)
                self.modifiers.welds.remove(m)
            elif m.type == 'FILL' and self.data.bevel.fill.offset <= 0.0:
                modifier.remove(m.obj, m.mod)
                self.modifiers.welds.remove(m)

        if not any(mod.type == 'ROUND' for mod in self.modifiers.bevels):
            bevel.del_edge_weight(self.data.bm, type='ROUND')
            self.pref.bevel.round.enable = False

        if not any(mod.type == 'FILL' for mod in self.modifiers.bevels):
            bevel.del_edge_weight(self.data.bm, type='FILL')
            self.pref.bevel.fill.enable = False

        self.update_bmesh(self.data.obj, self.data.bm, loop_triangles=True, destructive=False)

    def _bevel_modal(self, context, event):
        super()._bevel_modal(context, event)
        if self.data.bevel.mode == 'OFFSET':
            if self.data.bevel.type == 'ROUND':
                offset = self.data.bevel.round.offset
                for mod in self.modifiers.bevels:
                    if mod.type == 'ROUND':
                        mod.mod.width = offset
            else:
                offset = self.data.bevel.fill.offset
                for mod in self.modifiers.bevels:
                    if mod.type == 'FILL':
                        mod.mod.width = offset

        if self.data.bevel.mode == 'SEGMENTS':
            if self.data.bevel.type == 'ROUND':
                segments = self.data.bevel.round.segments
                for mod in self.modifiers.bevels:
                    if mod.type == 'ROUND':
                        mod.mod.segments = segments
            else:
                segments = self.data.bevel.fill.segments
                for mod in self.modifiers.bevels:
                    if mod.type == 'FILL':
                        mod.mod.segments = segments

        created_obj = self.objects.created
        bm = bmesh.new()

        depsgraph = bpy.context.evaluated_depsgraph_get()
        obj_eval = created_obj.evaluated_get(depsgraph)
        bm.from_mesh(obj_eval.data)

        faces = [f for f in bm.faces]
        self.ui.faces.callback.update_batch(faces)

        bm.free()

    def _duplicate_objects(self, context):
        """Duplicate objects"""
        # Deselect all objects
        objs_to_duplicate = []
        duplicated = []

        for obj in self.objects.selected:
            objs_to_duplicate.append(obj)

        for o in objs_to_duplicate:
            new_obj = o.copy()
            new_obj.data = o.data.copy()
            context.collection.objects.link(new_obj)
            duplicated.append(new_obj)
            self._set_parent(new_obj, o)

        return duplicated

    def _add_boolean(self, obj, detected_obj, face_index):
        if self.pref.mode != 'ADD':
            if self.shape.volume == '3D':
                context = bpy.context
                selected_objs = [o for o in context.selected_objects if o.type == 'MESH']

                if self.pref.mode == 'CARVE':
                    self._add_carve_obj(bpy.context, obj, face_index, self.pref.offset, self.pref.plane.normal)

                if self.pref.mode == 'SLICE':
                    _selected = selected_objs[:]
                    _selected_set = set(_selected + [detected_obj])
                    selected = list(_selected_set)

                    created_objs = []
                    for o in selected:
                        new_obj = o.copy()
                        new_obj.data = o.data.copy()
                        context.collection.objects.link(new_obj)
                        created_objs.append(new_obj)
                    self._create_boolean_modifiers(obj, None, created_objs, 'INTERSECT')

                self._create_boolean_modifiers(obj, detected_obj, selected_objs, self.pref.mode)
                self._set_parent(obj, detected_obj)

                # Move cutter object to Cutters collection before hiding
                collection.move_to_cutters_collection(obj)
                obj.hide_set(True)
                obj.data.shade_smooth()

    def _boolean(self, mode, obj):
        if mode != 'ADD':
            if self.shape.volume == '3D':

                if not self.modifiers.booleans:
                    selected = self.objects.selected[:]
                    detected = bpy.data.objects[self.objects.detected]

                    self._create_boolean_modifiers(obj, detected, selected, mode, append=True)
                    self._set_parent(obj, detected)

                    if self.config.mode == 'SLICE':
                        duplicated_objs = self.objects.duplicated[:]
                        self._create_boolean_modifiers(obj, None, duplicated_objs, 'INTERSECT', append=True)


    def _create_boolean_modifiers(self, obj, bool_obj, selected_objs, mode, append=False):
        '''Create the boolean modifiers'''
        _selected = selected_objs
        if bool_obj:
            _selected_set = set(_selected + [bool_obj])
        else:
            _selected_set = set(_selected)
        selected = list(_selected_set)
        for sel_obj in selected:
            match mode:
                case 'UNION': operation = 'UNION'
                case 'CUT': operation = 'DIFFERENCE'
                case 'INTERSECT': operation = 'INTERSECT'
                case _: operation = 'DIFFERENCE'
            mod = boolean.add_modifier(sel_obj, obj, operation)
            if append:
                self.modifiers.booleans.append(Modifier(obj=sel_obj, mod=mod))


    def _add_carve_obj(self, context, obj, face_index, offset, normal):

        new_obj = obj.copy()
        new_obj.data = obj.data.copy()
        new_obj.display_type = 'TEXTURED'
        new_obj.hide_render = False
        context.collection.objects.link(new_obj)

        bm = bmesh.new()
        bm.from_mesh(new_obj.data)
        bm.faces.ensure_lookup_table()
        face = bm.faces[face_index]
        for v in face.verts:
            v.co -= normal * offset
        bm.to_mesh(new_obj.data)
        bm.free()

    def _reveal_objects(self, context, obj):
        '''Reveal the created objects'''
        bpy.ops.object.select_all(action='DESELECT')
        obj.hide_set(False)
        obj.select_set(True)
        context.view_layer.objects.active = obj


    def _finish(self, context):
        super()._finish(context)

        if self.mode != 'BISECT':

            if self.config.mode != 'ADD':
                if self.shape.volume == '2D':
                    extrude.uniform(self, context)
                    if self.data.bevel.round.enable and self.data.extrude.faces:
                        bevel.uniform(self, self.data.bm, self.data.obj, self.data.extrude.faces)
                        self.update_bmesh(self.data.obj, self.data.bm, loop_triangles=True, destructive=False)
                    self._boolean(self.config.mode, self.data.obj)

            if self.config.mode == 'CARVE':
                self._add_carve_obj(context, self.data.obj, self.data.extrude.faces[0], self.config.align.offset, self.data.draw.matrix.normal)

            self._bevel_cleanup(context)
            if self.config.mode != 'ADD':
                # Ensure cutter object is in Cutters collection
                collection.move_to_cutters_collection(self.data.obj)
                self.data.obj.hide_set(True)
                self.data.obj.data.shade_smooth()

            self._set_origin(self.data.obj)

            if self.pref.reveal:
                self._reveal_objects(context, self.data.obj)

    def _set_origin(self, obj):
        bbox_corners = [mathutils.Vector(corner) for corner in obj.bound_box]
        bbox_center = sum(bbox_corners, mathutils.Vector()) / 8

        # Create rotation matrix where Z faces normal and X faces direction
        normal = self.pref.plane.normal.normalized()
        direction = self.pref.direction.normalized()

        # Ensure direction is perpendicular to normal (for X axis)
        x_axis = direction - direction.dot(normal) * normal
        x_axis.normalize()

        # Y axis is the cross product of Z and X (right-handed system)
        y_axis = normal.cross(x_axis)
        y_axis.normalize()

        # Create rotation matrix from these axes
        rot_matrix = mathutils.Matrix()
        rot_matrix.col[0][:3] = x_axis
        rot_matrix.col[1][:3] = y_axis
        rot_matrix.col[2][:3] = normal
        rot_matrix.col[3][:3] = (0, 0, 0)
        rot_matrix.col[3][3] = 1.0

        # Store original world matrix
        original_matrix = obj.matrix_world.copy()

        # Create translation to center
        translation_to_center = mathutils.Matrix.Translation(-bbox_center)

        # Create inverse rotation matrix
        rot_matrix_inverse = rot_matrix.inverted()

        # Apply translation then rotation to mesh vertices
        obj.data.transform(translation_to_center)
        obj.data.transform(rot_matrix_inverse)

        # Update object matrix to compensate - keep visual appearance unchanged
        # First set position to bbox center
        obj.matrix_world = mathutils.Matrix.Translation(original_matrix @ bbox_center)
        # Then apply the rotation
        obj.matrix_world @= rot_matrix

    def _set_parent(self, child_obj, parent_obj):
        parent_world = parent_obj.matrix_world.copy()
        child_obj.parent = parent_obj
        child_obj.matrix_parent_inverse = parent_world.inverted()

    def _cancel(self, context):
        if self.objects.created:
            mesh = self.objects.created.data
            bpy.data.objects.remove(self.objects.created)
            bpy.data.meshes.remove(mesh)
        boolean.clear_modifiers(self.modifiers)

        for obj in self.objects.duplicated:
            mesh_data = obj.data
            bpy.data.objects.remove(obj, do_unlink=True)
            if mesh_data and mesh_data.users == 0:
                bpy.data.meshes.remove(mesh_data)


classes = (
    BOUT_OT_BlockObjTool,
)
