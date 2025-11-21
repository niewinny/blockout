import bmesh
import bpy

from ...utils import addon, scene
from ...utilsbmesh import (
    bmeshedge,
    bmeshface,
    circle,
    corner,
    cylinder,
    facet,
    ngon,
    rectangle,
    sphere,
    triangle,
)
from ...utilsbmesh.mesh import get_copy, remove_doubles, set_copy
from . import draw, extrude
from .data import Config
from .operator import Block


class BOUT_OT_BlockMeshTool(Block):
    bl_idname = "object.bout_block_mesh_tool"
    bl_label = "Blockout Block"
    bl_options = {"REGISTER", "UNDO", "BLOCKING"}
    bl_description = "Tool for drawing a mesh"

    @classmethod
    def poll(cls, context):
        return context.area.type == "VIEW_3D" and context.mode == "EDIT_MESH"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def ray_cast(self, context):
        scene.set_active_object(context, self.mouse.init)
        ray = scene.ray_cast.edited(context, self.mouse.init)
        return ray

    def _header_text(self):
        """Set the header text"""
        pref = addon.pref().tools.block
        text = f"Shape: {pref.shape.capitalize()}"
        return text

    def set_config(self, context):
        """Set the config dataclass"""
        config = Config()
        config.shape = addon.pref().tools.block.shape
        config.form = addon.pref().tools.block.form
        config.align = addon.pref().tools.block.align
        config.mode = addon.pref().tools.block.mode
        config.type = "EDIT_MESH"
        config.snap = context.scene.tool_settings.use_snap
        return config

    def _invoke(self, context, event):
        """Invoke the operator"""
        self.data.copy.init = set_copy(self.data.obj, self.data.copy.all)

    def get_object(self, context):
        obj = context.edit_object
        return obj

    def build_bmesh(self, obj):
        obj.update_from_editmode()
        bm = bmesh.from_edit_mesh(obj.data)
        return bm

    def update_bmesh(self, obj, bm, loop_triangles=True, destructive=True):
        mesh = obj.data
        bm.normal_update()
        bmesh.update_edit_mesh(
            mesh, loop_triangles=loop_triangles, destructive=destructive
        )

    def build_geometry(self, obj, bm, ui=False):
        mode = self.pref.mode
        offset = self.pref.offset
        bevel_round_offset = self.pref.bevel.round.offset
        bevel_round_segments = self.pref.bevel.round.segments
        bevel_fill_offset = self.pref.bevel.fill.offset
        bevel_fill_segments = self.pref.bevel.fill.segments
        location = self.pref.plane.location
        normal = self.pref.plane.normal
        plane = (location, normal)
        direction = self.pref.direction
        extrusion = self.pref.extrusion
        symmetry_extrude = self.pref.symmetry_extrude
        symmetry_draw = (self.pref.symmetry_draw_x, self.pref.symmetry_draw_y)

        shape = self.pref.shape

        if mode != "ADD":
            bpy.ops.mesh.select_all(action="DESELECT")

        match shape:
            case "RECTANGLE":
                faces_indexes = rectangle.create(bm, plane)
                face = bmeshface.from_index(bm, faces_indexes[0])
                rectangle.set_xy(
                    face,
                    plane,
                    self.shape.rectangle.co,
                    direction,
                    local_space=True,
                    symmetry=symmetry_draw,
                )
                facet.set_z(face, normal, offset)
                if self.pref.bevel.round.enable:
                    face_index = facet.bevel_verts(
                        bm,
                        face,
                        bevel_round_offset,
                        bevel_segments=bevel_round_segments,
                    )
                    face = bmeshface.from_index(bm, face_index)
                    facet.remove_doubles(bm, face)
                if mode != "ADD":
                    extruded_faces = facet.extrude(bm, face, plane, extrusion)
                self.update_bmesh(obj, bm, loop_triangles=True, destructive=True)
                if mode != "ADD":
                    self._boolean(self.pref.mode, obj, bm, ui)
            case "BOX":
                faces_indexes = rectangle.create(bm, plane)
                face = bmeshface.from_index(bm, faces_indexes[0])
                rectangle.set_xy(
                    face,
                    plane,
                    self.shape.rectangle.co,
                    direction,
                    local_space=True,
                    symmetry=symmetry_draw,
                )
                if self.pref.bevel.round.enable:
                    face_index = facet.bevel_verts(
                        bm,
                        face,
                        bevel_round_offset,
                        bevel_segments=bevel_round_segments,
                    )
                    face = bmeshface.from_index(bm, face_index)
                    facet.remove_doubles(bm, face)
                facet.set_z(face, normal, offset)
                extruded_faces = facet.extrude(bm, face, plane, extrusion)
                self._recalculate_normals(bm, extruded_faces)
                if symmetry_extrude:
                    facet.set_z(
                        bmeshface.from_index(bm, extruded_faces[0]), normal, -extrusion
                    )
                if self.pref.bevel.fill.enable:
                    face_index = extruded_faces[-1]
                    face = bmeshface.from_index(bm, face_index)
                    edges = face.edges
                    verts_indicies = facet.bevel_edges(
                        bm, edges, bevel_fill_offset, bevel_segments=bevel_fill_segments
                    )
                    remove_doubles(bm, verts_indicies)
                self.update_bmesh(obj, bm, loop_triangles=True, destructive=True)
                self._boolean(self.pref.mode, obj, bm, ui)
            case "CIRCLE":
                faces_indexes = circle.create(
                    bm, plane, verts_number=self.shape.circle.verts
                )
                face = bmeshface.from_index(bm, faces_indexes[0])
                circle.set_xy(
                    face,
                    plane,
                    None,
                    direction,
                    radius=self.shape.circle.radius,
                    local_space=True,
                )
                facet.set_z(face, normal, offset)
                if mode != "ADD":
                    cylinder_faces_indexes = facet.extrude(bm, face, plane, extrusion)
                    self._recalculate_normals(bm, cylinder_faces_indexes)
                self.update_bmesh(obj, bm, loop_triangles=True, destructive=True)
                if mode != "ADD":
                    self._boolean(self.pref.mode, obj, bm, ui)
            case "CYLINDER":
                faces_indexes = circle.create(
                    bm, plane, verts_number=self.shape.circle.verts
                )
                face = bmeshface.from_index(bm, faces_indexes[0])
                circle.set_xy(
                    face,
                    plane,
                    None,
                    direction,
                    radius=self.shape.circle.radius,
                    local_space=True,
                )
                facet.set_z(face, normal, offset)
                cylinder_faces_indexes = facet.extrude(bm, face, plane, extrusion)
                self._recalculate_normals(bm, cylinder_faces_indexes)
                if symmetry_extrude:
                    facet.set_z(
                        bmeshface.from_index(bm, cylinder_faces_indexes[0]),
                        normal,
                        -extrusion,
                    )
                if self.pref.bevel.fill.enable:
                    cylinder.bevel(
                        bm,
                        cylinder_faces_indexes,
                        bevel_fill_offset,
                        bevel_segments=bevel_fill_segments,
                    )
                self.update_bmesh(obj, bm, loop_triangles=True, destructive=True)
                self._boolean(self.pref.mode, obj, bm, ui)
            case "SPHERE":
                sphere.create(
                    bm,
                    plane,
                    direction,
                    radius=self.shape.sphere.radius,
                    subd=self.shape.sphere.subd,
                )
                self.update_bmesh(obj, bm, loop_triangles=True, destructive=True)
                self._boolean(self.pref.mode, obj, bm, ui)
            case "CORNER":
                faces_indexes = corner.create(bm, plane)
                faces = [
                    bmeshface.from_index(bm, faces_indexes[0]),
                    bmeshface.from_index(bm, faces_indexes[1]),
                ]
                corner.set_xy(
                    faces,
                    plane,
                    self.shape.corner.co,
                    direction,
                    (self.shape.corner.min, self.shape.corner.max),
                    local_space=True,
                )
                rotations = (self.shape.corner.min, self.shape.corner.max)
                extruded_face_indexes, edge_index = corner.extrude(
                    bm, faces, direction, normal, rotations, extrusion
                )
                corner.offset(
                    bm, extruded_face_indexes, direction, normal, rotations, offset
                )
                if self.pref.bevel.round.enable:
                    edge = bmeshedge.from_index(bm, edge_index)
                    corner.bevel(
                        bm,
                        edge,
                        bevel_round_offset,
                        bevel_segments=bevel_round_segments,
                    )
                self.update_bmesh(obj, bm, loop_triangles=True, destructive=True)
                self._boolean(self.pref.mode, obj, bm, ui)
            case "NGON":
                face = ngon.new(bm, self.pref.ngon)
                faces_indexes = [face.index]
                facet.set_z(face, normal, offset)
                if self.pref.bevel.round.enable:
                    face_index = facet.bevel_verts(
                        bm,
                        face,
                        bevel_round_offset,
                        bevel_segments=bevel_round_segments,
                    )
                    face = bmeshface.from_index(bm, face_index)
                    facet.remove_doubles(bm, face)
                if mode != "ADD":
                    extruded_faces = facet.extrude(bm, face, plane, extrusion)
                    self._recalculate_normals(bm, extruded_faces)
                self.update_bmesh(obj, bm, loop_triangles=True, destructive=True)
                if mode != "ADD":
                    self._boolean(self.pref.mode, obj, bm, ui)
            case "NHEDRON":
                face = ngon.new(bm, self.pref.ngon)
                faces_indexes = [face.index]
                facet.set_z(face, normal, offset)
                if self.pref.bevel.round.enable:
                    face_index = facet.bevel_verts(
                        bm,
                        face,
                        bevel_round_offset,
                        bevel_segments=bevel_round_segments,
                    )
                    face = bmeshface.from_index(bm, face_index)
                    facet.remove_doubles(bm, face)
                extruded_faces = facet.extrude(bm, face, plane, extrusion)
                self._recalculate_normals(bm, extruded_faces)
                if self.pref.bevel.fill.enable:
                    face_index = extruded_faces[-1]
                    face = bmeshface.from_index(bm, face_index)
                    edges = face.edges
                    verts_indicies = facet.bevel_edges(
                        bm, edges, bevel_fill_offset, bevel_segments=bevel_fill_segments
                    )
                    remove_doubles(bm, verts_indicies)
                self.update_bmesh(obj, bm, loop_triangles=True, destructive=True)
                self._boolean(self.pref.mode, obj, bm, ui)
            case "TRIANGLE":
                faces_indexes = triangle.create(bm, plane)
                face = bmeshface.from_index(bm, faces_indexes[0])
                triangle.set_xy(
                    face,
                    plane,
                    self.shape.triangle.co,
                    direction,
                    local_space=True,
                    symmetry=symmetry_draw,
                    flip=self.shape.triangle.flip,
                )
                facet.set_z(face, normal, offset)
                if self.pref.bevel.round.enable:
                    face_index = facet.bevel_verts(
                        bm,
                        face,
                        self.pref.bevel.round.offset,
                        bevel_segments=self.pref.bevel.round.segments,
                    )
                    face = bmeshface.from_index(bm, face_index)
                    facet.remove_doubles(bm, face)

                if mode != "ADD":
                    extruded_faces = facet.extrude(bm, face, plane, extrusion)
                    self._recalculate_normals(bm, extruded_faces)
                self.update_bmesh(obj, bm, loop_triangles=True, destructive=True)
                if mode != "ADD":
                    self._boolean(self.pref.mode, obj, bm, ui)
            case _:
                raise ValueError(f"Unsupported shape: {self.pref.shape}")

        return faces_indexes

    def _draw_invoke(self, context, event):
        mesh = draw.invoke(self, context)
        if self.config.mode != "ADD":
            self.data.copy.draw = set_copy(self.data.obj, self.data.copy.all)
        return mesh

    def _draw_modal(self, context, event):
        if self.config.mode != "ADD" and self.config.shape == "SPHERE":
            get_copy(self.data.obj, self.data.bm, self.data.copy.draw)
            super()._draw_modal(context, event)
            self._boolean(self.config.mode, self.data.obj, self.data.bm)
        else:
            super()._draw_modal(context, event)

    def _extrude_invoke(self, context, event):
        super()._extrude_invoke(context, event)
        if self.config.mode != "ADD":
            self.data.copy.draw = set_copy(self.data.obj, self.data.copy.all)

    def _extrude_modal(self, context, event):
        if self.config.mode != "ADD":
            get_copy(self.data.obj, self.data.bm, self.data.copy.draw)
        super()._extrude_modal(context, event)
        self._boolean(self.config.mode, self.data.obj, self.data.bm)

    def _boolean(self, mode, obj, bm, ui=False):
        if mode != "ADD":
            if ui:
                bm.faces.ensure_lookup_table()
                faces = [f for f in bm.faces if f.select]
                self.ui.faces.callback.update_batch(faces)

            if self.shape.volume == "3D":
                match mode:
                    case "UNION":
                        operation = "UNION"
                    case "CUT":
                        operation = "DIFFERENCE"
                    case "INTERSECT":
                        operation = "INTERSECT"
                    case "SLICE":
                        selected_faces = [f for f in bm.faces if f.select]
                        facet.solidify(bm, selected_faces)
                        self.update_bmesh(
                            obj, bm, loop_triangles=True, destructive=True
                        )
                        operation = "DIFFERENCE"
                    case "CARVE":
                        selected_faces = [f for f in bm.faces if f.select]
                        verts = [
                            (v.index, v.co.copy())
                            for v in bm.verts
                            if any(f in selected_faces for f in v.link_faces)
                        ]
                        edges = [
                            (e.verts[0].index, e.verts[1].index)
                            for e in bm.edges
                            if any(f in selected_faces for f in e.link_faces)
                        ]
                        faces = [[v.index for v in f.verts] for f in selected_faces]
                        operation = "DIFFERENCE"
                    case _:
                        operation = "DIFFERENCE"

                solver = addon.pref().tools.block.align.solver
                bpy.ops.mesh.intersect_boolean(
                    operation=operation,
                    use_swap=False,
                    use_self=False,
                    threshold=1e-06,
                    solver=solver,
                )
                self.update_bmesh(obj, bm, loop_triangles=True, destructive=True)

                if mode == "CARVE":
                    vert_map = {}
                    for old_idx, co in verts:
                        new_v = bm.verts.new(co)
                        vert_map[old_idx] = new_v
                    bm.verts.index_update()

                    for v1_idx, v2_idx in edges:
                        if v1_idx in vert_map and v2_idx in vert_map:
                            bm.edges.new((vert_map[v1_idx], vert_map[v2_idx]))

                    for f_verts in faces:
                        if all(idx in vert_map for idx in f_verts):
                            bm.faces.new([vert_map[idx] for idx in f_verts])

                    self.update_bmesh(obj, bm, loop_triangles=True, destructive=True)

    def _update_geometry(self, ui=False):
        get_copy(self.data.obj, self.data.bm, self.data.copy.init)

        obj = self.data.obj
        bm = self.data.bm

        self.store_props()
        faces_indexes = self.build_geometry(obj, bm, ui)
        self.data.draw.faces[0] = faces_indexes[0]
        self.update_bmesh(obj, bm, loop_triangles=True, destructive=True)

    def _bevel_invoke(self, context, event):
        super()._bevel_invoke(context, event)
        self._update_geometry(ui=True)

    def _bevel_modal(self, context, event):
        super()._bevel_modal(context, event)
        self._update_geometry(ui=True)

    def _finish(self, context):
        super()._finish(context)

        if self.mode != "BISECT":
            if self.config.mode != "ADD":
                if self.shape.volume == "2D":
                    extrude.uniform(self, context)
                    self._boolean(self.pref.mode, self.data.obj, self.data.bm)

            self.update_bmesh(
                self.data.obj, self.data.bm, loop_triangles=True, destructive=True
            )

    def _cancel(self, context):
        get_copy(self.data.obj, self.data.bm, self.data.copy.init)
        self.update_bmesh(
            self.data.obj, self.data.bm, loop_triangles=True, destructive=True
        )


classes = (BOUT_OT_BlockMeshTool,)
