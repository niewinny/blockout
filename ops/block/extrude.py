from mathutils import Vector

from ...utils import view3d
from ...utils.scene import ray_cast
from ...utils.types import DrawVert
from ...utilsbmesh import corner, facet
from .data import ExtrudeEdge


def invoke(self, context, event):
    """Extrude the mesh"""

    self.mode = "EXTRUDE"
    self.shape.volume = "3D"
    self.mouse.extrude = self.mouse.co

    region = context.region
    rv3d = context.region_data

    obj = self.data.obj
    bm = self.data.bm

    draw_faces = [bm.faces[index] for index in self.data.draw.faces]
    draw_face = draw_faces[0]
    plane = self.data.draw.matrix.plane
    normal = self.data.draw.matrix.normal
    direction = self.data.draw.matrix.direction
    rotations = (self.shape.corner.min, self.shape.corner.max)
    offset = self.config.align.offset

    shape = self.config.shape
    match shape:
        case "CORNER":
            self.data.extrude.value = 0.2
            extruded_faces_indexes, mid_edge_index = corner.extrude(
                bm, draw_faces, direction, normal, rotations, self.data.extrude.value
            )
            self.data.extrude.faces = extruded_faces_indexes
            self.data.extrude.edges = [
                ExtrudeEdge(index=mid_edge_index, position="MID")
            ]
            corner.offset(
                bm, extruded_faces_indexes, direction, normal, rotations, offset
            )

        case _:
            extruded_faces_indexes = facet.extrude(bm, draw_face, plane, 0.0)

            self.data.extrude.faces = extruded_faces_indexes
            self.data.draw.faces[0] = extruded_faces_indexes[0]
            extrude_face = bm.faces[self.data.extrude.faces[-1]]
            self.data.extrude.verts = [
                DrawVert(index=v.index, co=v.co.copy()) for v in extrude_face.verts
            ]
            draw_face = bm.faces[self.data.draw.faces[0]]
            self.data.draw.verts = [
                DrawVert(index=v.index, co=v.co.copy()) for v in draw_face.verts
            ]

            extrude_edges = [e.index for v in extrude_face.verts for e in v.link_edges]
            extrude_face_edges = [e.index for e in extrude_face.edges]
            extrude_edges = list(set(extrude_edges) - set(extrude_face_edges))

            self.data.extrude.edges = [
                ExtrudeEdge(index=e, position="MID") for e in extrude_edges
            ] + [ExtrudeEdge(index=e, position="END") for e in extrude_face_edges]

    self.update_bmesh(obj, bm, loop_triangles=True, destructive=True)

    self.ui.xaxis.callback.clear()
    self.ui.yaxis.callback.clear()
    self.ui.guid.callback.clear()
    self.ui.interface.callback.clear()
    self.ui.vert.callback.clear()

    plane_world = (obj.matrix_world @ plane[0], obj.matrix_world.to_3x3() @ plane[1])
    line_origin = view3d.region_2d_to_plane_3d(
        region, rv3d, self.mouse.extrude, plane_world
    )
    self.data.extrude.origin = line_origin
    point1 = line_origin
    point2 = line_origin + plane_world[1]
    self.ui.zaxis.callback.update_batch((point1, point2))


def modal(self, context, event):
    """Set the extrusion based on mouse or numeric input."""
    obj = self.data.obj
    bm = self.data.bm
    ni = self.data.numeric_input

    # Ensure lookup tables are valid after destructive updates
    bm.faces.ensure_lookup_table()
    bm.verts.ensure_lookup_table()

    face = bm.faces[self.data.extrude.faces[-1]]
    normal = self.data.draw.matrix.plane[1]
    verts = [v.co for v in self.data.extrude.verts]

    region = context.region
    rv3d = context.region_data

    # Only calculate from mouse when not in numeric input mode
    if not ni.active:
        matrix_world = obj.matrix_world
        line_origin = self.data.extrude.origin
        line_direction = matrix_world.to_3x3() @ normal

        _, extrude = view3d.region_2d_to_line_3d(
            region, rv3d, self.mouse.co, line_origin, line_direction
        )

        if extrude is not None:
            increments = self.config.align.increments if self.config.snap else 0.0
            if increments > 0:
                extrude = round(extrude / increments) * increments
            self.data.extrude.value = extrude

    # Update geometry using current value
    dz = self.data.extrude.value
    increments = self.config.align.increments if self.config.snap else 0.0
    dz = facet.set_z(face, normal, dz, verts, snap_value=increments)
    self.data.extrude.value = dz  # Update with snapped value

    draw_face = bm.faces[self.data.extrude.faces[0]]
    draw_verts = [v.co for v in self.data.draw.verts]
    if self.data.extrude.symmetry:
        facet.set_z(draw_face, normal, -dz, draw_verts, snap_value=increments)
    else:
        facet.set_z(draw_face, normal, 0, draw_verts)

    bevel_verts = [obj.matrix_world @ v.co.copy() for v in face.verts]
    self.data.bevel.origin = sum(bevel_verts, Vector()) / len(bevel_verts)

    extrude_faces = [bm.faces[index] for index in self.data.extrude.faces]

    if self.config.mode != "ADD":
        self.ui.faces.callback.update_batch(extrude_faces)

    _, normal = self.data.draw.matrix.plane
    normal_global = obj.matrix_world.to_3x3() @ normal
    point_global = self.data.extrude.origin + normal_global * (dz / 2)
    _update_ui(self, region, rv3d, point_global, dz)

    self.update_bmesh(obj, bm, loop_triangles=True, destructive=True)


def _update_ui(self, region, rv3d, point_global, dz):
    """Update extrude UI elements."""

    point_2d = view3d.location_3d_to_region_2d(region, rv3d, point_global)
    lines = [
        {"point": point_2d, "text_tuple": (f"Z: {dz:.3f}",)},
    ]
    self.ui.interface.callback.update_batch(lines)


def uniform(self, context):
    """Finish 2D shapes by extruding them based on raycasting"""

    obj = self.data.obj
    bm = self.data.bm

    # Get the 2D face
    face_index = self.data.draw.faces[0]
    face = bm.faces[face_index]

    # Get face normal and plane
    plane = self.data.draw.matrix.plane
    normal = plane[1].normalized()

    # Transform normal to world space (use rotation part of matrix only)
    world_normal = (obj.matrix_world.to_3x3() @ normal).normalized()

    # Transform vertices to world space
    world_verts = [obj.matrix_world @ v.co for v in face.verts]

    # Calculate center of the face in world space
    face_center = sum(world_verts, Vector()) / len(world_verts)

    # Perform raycasts from opposite side to each vertex
    hit_distances = []
    ray_direction = -world_normal

    for vert_world in world_verts:
        # Start ray from far away in the opposite direction
        ray_origin = vert_world - ray_direction * 100000.0

        # Cast ray toward the vertex using proper object filtering
        ray = ray_cast._ray_cast(
            context, ray_origin, ray_direction, self.objects.selected
        )

        if ray.hit:
            distance = (ray.location - vert_world).length
            hit_distances.append(distance)

    # Calculate median distance for object bounds
    if hit_distances:
        hit_distances.sort()
        median_distance = hit_distances[len(hit_distances) // 2]
    else:
        # Default distance if no hits
        median_distance = 1.0

    # Cast rays from face center AND each vertex to find maximum extrusion distance
    extrusion_candidates = []

    # Cast from face center
    ray_origin = face_center - world_normal * (median_distance + 10.0)
    ray = ray_cast._ray_cast(context, ray_origin, world_normal, self.objects.selected)

    if ray.hit:
        distance = (ray.location - face_center).length
        extrusion_candidates.append(distance)

    # Cast from each vertex
    for vert_world in world_verts:
        ray_origin = vert_world - world_normal * (median_distance + 10.0)
        ray = ray_cast._ray_cast(
            context, ray_origin, world_normal, self.objects.selected
        )

        if ray.hit:
            distance = (ray.location - vert_world).length
            extrusion_candidates.append(distance)

    # Cast from middle of each edge and quarter points
    for edge in face.edges:
        edge_verts_world = [obj.matrix_world @ v.co for v in edge.verts]
        edge_mid = (edge_verts_world[0] + edge_verts_world[1]) / 2.0

        # Cast from edge middle
        ray_origin = edge_mid - world_normal * (median_distance + 10.0)
        ray = ray_cast._ray_cast(
            context, ray_origin, world_normal, self.objects.selected
        )

        if ray.hit:
            distance = (ray.location - edge_mid).length
            extrusion_candidates.append(distance)

        # Cast from midpoint between edge middle and first vertex
        quarter_point_1 = (edge_mid + edge_verts_world[0]) / 2.0
        ray_origin = quarter_point_1 - world_normal * (median_distance + 10.0)
        ray = ray_cast._ray_cast(
            context, ray_origin, world_normal, self.objects.selected
        )

        if ray.hit:
            distance = (ray.location - quarter_point_1).length
            extrusion_candidates.append(distance)

        # Cast from midpoint between edge middle and second vertex
        quarter_point_2 = (edge_mid + edge_verts_world[1]) / 2.0
        ray_origin = quarter_point_2 - world_normal * (median_distance + 10.0)
        ray = ray_cast._ray_cast(
            context, ray_origin, world_normal, self.objects.selected
        )

        if ray.hit:
            distance = (ray.location - quarter_point_2).length
            extrusion_candidates.append(distance)

    # Cast from midpoints between face center and each vertex
    for vert_world in world_verts:
        mid_point = (face_center + vert_world) / 2.0

        ray_origin = mid_point - world_normal * (median_distance + 10.0)
        ray = ray_cast._ray_cast(
            context, ray_origin, world_normal, self.objects.selected
        )

        if ray.hit:
            distance = (ray.location - mid_point).length
            extrusion_candidates.append(distance)

    # Pick the maximum extrusion value
    if extrusion_candidates:
        extrusion_value = max(extrusion_candidates)
        # Add offset
        offset = (
            self.config.align.offset if hasattr(self.config.align, "offset") else 0.1
        )
        extrusion_value += offset
    else:
        # Default minimal extrusion if no hits
        extrusion_value = 0.1

    # Perform the extrusion
    if extrusion_value > 0:
        # Store current face selection state
        was_selected = face.select

        # Extrude the face
        extruded_faces = facet.extrude(bm, face, plane, -extrusion_value)

        # Update shape volume to 3D
        self.shape.volume = "3D"

        # Update extrude data
        self.data.extrude.value = -extrusion_value
        self.data.extrude.faces = extruded_faces

        self.pref.extrusion = -extrusion_value

        # Restore selection if needed
        if was_selected:
            for face_idx in extruded_faces:
                bm.faces[face_idx].select_set(True)

        # Update the mesh
        self.update_bmesh(obj, bm, loop_triangles=True, destructive=True)
