import itertools
from dataclasses import dataclass
from typing import List, Set, Optional
import bpy
import bmesh
from mathutils import Vector


@dataclass
class GeometryData:
    faces: List[bmesh.types.BMFace]
    edges: Set[bmesh.types.BMEdge]
    verts: Set[bmesh.types.BMVert]
    faces_indices: List[int]
    edges_indices: List[int]
    verts_indices: List[int]


@dataclass
class LoopData:
    edges: List[bmesh.types.BMEdge]
    verts: List[bmesh.types.BMVert]
    ordered_verts: List[bmesh.types.BMVert]
    active_vert: Optional[bmesh.types.BMVert]


@dataclass
class ExtrusionData:
    geom: List[bmesh.types.BMFace]
    prev_vert: bmesh.types.BMVert
    current_vert: bmesh.types.BMVert
    next_vert: Optional[bmesh.types.BMVert]


class BOUT_OT_Sweep(bpy.types.Operator):
    bl_idname = 'bout.sweep'
    bl_label = 'Sweep'
    bl_options = {'REGISTER', 'UNDO', 'BLOCKING'}
    bl_description = "Sweep selected faces along the selected loop"

    remove_swept_faces: bpy.props.BoolProperty(
        name="Remove swept faces",
        default=True,
        description="Remove the swept faces after the sweep operation"
    )

    @classmethod
    def poll(cls, context):
        return context.area.type == 'VIEW_3D' and context.mode == 'EDIT_MESH'

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.prop(self, 'remove_swept_faces')

    def execute(self, context):
        obj = context.object
        me = obj.data
        bm = bmesh.from_edit_mesh(me)

        # Get selected geometry data
        geometry_data = self.get_geometry_data(bm)
        if not geometry_data.faces:
            self.report({'ERROR'}, "No faces selected")
            return {'CANCELLED'}

        # Get loop data
        loop_data = self.get_loop_data(bm, geometry_data)
        if not loop_data.edges:
            self.report({'ERROR'}, "No loop edges selected")
            return {'CANCELLED'}
        if not loop_data.verts:
            self.report({'ERROR'}, "No loop vertices selected")
            return {'CANCELLED'}
        if not loop_data.active_vert:
            self.report({'ERROR'}, "Active vertex is not in loop vertices")
            return {'CANCELLED'}
        if len(loop_data.ordered_verts) < 2:
            self.report({'ERROR'}, "Edge loop is too short")
            return {'CANCELLED'}

        # Deselect all geometry to avoid interference
        self.deselect_all(bm)

        # Duplicate the initial geometry
        prev_geom = self.duplicate_geometry(bm, geometry_data)
        for elem in prev_geom:
            elem.select_set(True)

        # Initialize extrusion data
        extrusion_data = ExtrusionData(
            geom=prev_geom,
            prev_vert=loop_data.ordered_verts[0],
            current_vert=loop_data.ordered_verts[1],
            next_vert=None
        )

        # Sweep along the loop
        for i in range(1, len(loop_data.ordered_verts)):
            extrusion_data.current_vert = loop_data.ordered_verts[i]
            extrusion_data.next_vert = loop_data.ordered_verts[i + 1] if i + 1 < len(loop_data.ordered_verts) else None

            # Extrude and project the geometry
            extrusion_data.geom = self.extrude_and_project(bm, extrusion_data)

            extrusion_data.prev_vert = extrusion_data.current_vert

        if self.remove_swept_faces:
            self.remove_original_geometry(bm, geometry_data)

        bm.select_flush_mode()
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        bmesh.update_edit_mesh(me)
        return {'FINISHED'}

    def get_geometry_data(self, bm) -> GeometryData:
        """Get selected geometry data."""
        faces = [f for f in bm.faces if f.select]
        edges = set(e for f in faces for e in f.edges)
        verts = set(v for f in faces for v in f.verts)
        faces_indices = [f.index for f in faces]
        edges_indices = [e.index for e in edges]
        verts_indices = [v.index for v in verts]
        return GeometryData(faces, edges, verts, faces_indices, edges_indices, verts_indices)

    def get_loop_data(self, bm, geometry_data: GeometryData) -> LoopData:
        """Get loop data and build ordered vertices."""
        loop_edges = [e for e in bm.edges if e.select and e not in geometry_data.edges]
        loop_verts = [v for v in bm.verts if v.select and v not in geometry_data.verts]
        active_vert = self.get_active_vertex(bm, loop_verts)
        ordered_verts = self.build_loop(active_vert, loop_edges) if active_vert else []
        return LoopData(loop_edges, loop_verts, ordered_verts, active_vert)

    def get_active_vertex(self, bm, loop_verts):
        """Get the active vertex from the selection history."""
        active_elem = bm.select_history.active
        if isinstance(active_elem, bmesh.types.BMVert) and active_elem in loop_verts:
            return active_elem
        return None

    def build_loop(self, active_vert, loop_edges):
        """Build an ordered list of vertices along the loop starting from the active vertex."""
        loop_verts_ordered = [active_vert]
        visited_edges = set()
        current_vert = active_vert

        while True:
            next_vert, next_edge = self.find_next_vert(current_vert, loop_edges, visited_edges)
            if next_vert is None:
                break
            loop_verts_ordered.append(next_vert)
            visited_edges.add(next_edge)
            current_vert = next_vert

        return loop_verts_ordered

    def find_next_vert(self, current_vert, loop_edges, visited_edges):
        """Find the next vertex in the loop."""
        for edge in current_vert.link_edges:
            if edge in loop_edges and edge not in visited_edges:
                other_vert = edge.other_vert(current_vert)
                return other_vert, edge
        return None, None

    def deselect_all(self, bm):
        """Deselect all geometry."""
        for elem in itertools.chain(bm.faces, bm.edges, bm.verts):
            elem.select_set(False)

    def duplicate_geometry(self, bm, geometry_data: GeometryData):
        """Duplicate the initial geometry."""
        geom = geometry_data.faces + list(geometry_data.edges) + list(geometry_data.verts)
        ret = bmesh.ops.duplicate(bm, geom=geom)
        return ret['geom']

    def extrude_and_project(self, bm, extrusion_data: ExtrusionData):
        """Extrude the geometry and project onto the plane at the current vertex."""
        prev_geom = extrusion_data.geom
        prev_vert = extrusion_data.prev_vert
        current_vert = extrusion_data.current_vert
        next_vert = extrusion_data.next_vert

        # Compute vectors for normal calculation
        vec_next = (next_vert.co - current_vert.co).normalized() if next_vert else Vector((0, 0, 0))
        vec_prev = -(current_vert.co - prev_vert.co).normalized() if prev_vert else Vector((0, 0, 0))

        # Calculate the normal vector
        normal_vec = vec_next - vec_prev
        if normal_vec.length == 0:
            normal_vec = vec_prev if vec_prev.length != 0 else vec_next
        normal_vec.normalize()

        # Compute the projection direction
        direction_vec = (current_vert.co - prev_vert.co).normalized()

        # Extrude the previous geometry
        res = bmesh.ops.extrude_face_region(bm, geom=prev_geom)
        extruded_geom = res['geom']

        # Get the new vertices
        extruded_verts = [elem for elem in extruded_geom if isinstance(elem, bmesh.types.BMVert)]

        for elem in extruded_geom:
            elem.select_set(True)

        # Project the extruded vertices onto the plane at current_vert along direction_vec
        plane_point = current_vert.co
        plane_normal = normal_vec
        dot = direction_vec.dot(plane_normal)

        if dot != 0:
            for vert in extruded_verts:
                t = -((vert.co - plane_point).dot(plane_normal)) / dot
                vert.co += direction_vec * t

        return extruded_geom

    def remove_original_geometry(self, bm, geometry_data: GeometryData):
        """Remove the original swept geometry."""
        faces_to_remove = [f for f in bm.faces if f.index in geometry_data.faces_indices]
        edges_to_remove = [e for e in bm.edges if e.index in geometry_data.edges_indices]
        verts_to_remove = [v for v in bm.verts if v.index in geometry_data.verts_indices]
        for face in faces_to_remove:
            bm.faces.remove(face)
        for edge in edges_to_remove:
            if edge.is_valid:
                bm.edges.remove(edge)
        for vert in verts_to_remove:
            if vert.is_valid:
                bm.verts.remove(vert)


classes = (
    BOUT_OT_Sweep,
)
