import math

import bmesh
import bpy
from mathutils import Vector

from ...utils import view3d
from ...utils.types import DrawMatrix
from ...utilsbmesh import orientation


def _apply_axis_snap(op, detected_axis):
    """Cache the detected (snap_x, snap_y) tuple and seed it into the
    active shape's ``symmetry_x``/``symmetry_y`` when present, so pulling
    along an axis enables mirror symmetry there.
    """
    op.data.draw.axis_snap = detected_axis
    sd = op.shape.data
    if hasattr(sd, "symmetry_x"):
        sd.symmetry_x, sd.symmetry_y = detected_axis


def _resolve_face_index(op, hit_bm, hit_obj_eval, hit_data):
    """Safely get face or return fallback orientation for instanced objects"""

    # Check if the face index is valid for this mesh (important for instanced objects)
    if op.ray.index >= len(hit_bm.faces) or op.ray.index < 0:
        # Face index is out of bounds - this can happen with instanced objects
        # Fall back to using the raycast normal directly
        direction_world = orientation.direction_from_normal(op.ray.normal)
        plane_world = (op.ray.location, op.ray.normal)

        hit_bm.free()
        del hit_obj_eval
        del hit_data

        op.report({"INFO"}, "Fallback: Geometry is not real")
        return None, direction_world, plane_world

    return hit_bm.faces[op.ray.index], None, None


def build(op, context):
    """Get the orientation for the drawing"""

    if context.scene.bout.align.mode == "CUSTOM":
        direction, plane = custom_orientation(op, context)
    elif op.ray.hit:
        if op.config.shape in {"CORNER"}:
            direction, plane = edge_orientation(op, context)
        else:
            direction, plane = face_orientation(op, context)
    else:
        direction, plane = None, None

    if direction is None:
        direction, plane = world_orientation(op, context)

    if op.config.mode != "ADD" and op.config.type == "EDIT_MESH":
        bpy.ops.mesh.select_all(action="DESELECT")

    if op.config.align.absolute:
        increments = op.config.align.increments
        custom_matrix = DrawMatrix.from_property(context.scene.bout.align.matrix)
        custom_plane = custom_matrix.location, custom_matrix.normal
        plane = orientation.snap_plane(plane, custom_plane, direction, increments)

    op.data.draw.matrix.from_plane(plane, direction)


def make_local(op):
    """Make the orientation local to the object"""
    op.data.draw.matrix.to_local(op.data.obj)


def face_orientation(op, context):
    """Get the orientation from the face"""

    depsgraph = context.view_layer.depsgraph
    depsgraph.update()
    hit_obj = op.ray.obj

    # Get the evaluated data
    hit_obj_eval = hit_obj.evaluated_get(depsgraph)
    hit_data = hit_obj_eval.to_mesh(preserve_all_data_layers=True, depsgraph=depsgraph)

    hit_bm = bmesh.new()
    hit_bm.from_mesh(hit_data)
    hit_bm.faces.ensure_lookup_table()

    hit_face, fallback_direction, fallback_plane = _resolve_face_index(
        op, hit_bm, hit_obj_eval, hit_data
    )

    if hit_face is None:
        return fallback_direction, fallback_plane

    loc = op.ray.location

    align_face = op.config.align.face
    match align_face:
        case "PLANAR":
            direction_local = orientation.direction_from_normal(hit_face.normal)
        case "EDGE":
            _edge, direction_local, _normal_local = (
                orientation.direction_from_closest_edge(hit_obj, hit_face, loc)
            )

    direction_world = op.ray.obj.matrix_world.to_3x3() @ direction_local
    plane_world = (op.ray.location, op.ray.normal)

    hit_bm.free()
    del hit_obj_eval
    del hit_data

    return direction_world, plane_world


def edge_orientation(op, context):
    """Get the orientation from the edge"""

    depsgraph = context.view_layer.depsgraph
    depsgraph.update()
    hit_obj = op.ray.obj

    hit_obj_eval = hit_obj.evaluated_get(depsgraph)
    hit_data = hit_obj_eval.to_mesh(preserve_all_data_layers=True, depsgraph=depsgraph)

    hit_bm = bmesh.new()
    hit_bm.from_mesh(hit_data)
    hit_bm.faces.ensure_lookup_table()

    hit_face, fallback_direction, fallback_plane = _resolve_face_index(
        op, hit_bm, hit_obj_eval, hit_data
    )

    if hit_face is None:
        op.shape.corner.rotation_a = 0.0
        op.shape.corner.rotation_b = 0.0
        return fallback_direction, fallback_plane

    matrix = op.ray.obj.matrix_world
    loc_world = op.ray.location

    edge, direction_local, normal_local = orientation.direction_from_closest_edge(
        hit_obj, hit_face, loc_world
    )
    direction_world = op.ray.obj.matrix_world.to_3x3() @ direction_local

    linked_faces = edge.link_faces
    other_face = [f for f in linked_faces if f != hit_face][0]
    other_normal = matrix.to_3x3() @ other_face.normal

    # Get the world-space coordinates of the edge's vertices
    v1_world = matrix @ edge.verts[0].co
    v2_world = matrix @ edge.verts[1].co

    # Compute the closest point on the segment to loc_world
    edge_vec = v2_world - v1_world
    edge_len = edge_vec.length
    if edge_len == 0:
        point_on_edge = v1_world
    else:
        edge_unit = edge_vec / edge_len
        point_vec = loc_world - v1_world
        projection = point_vec.dot(edge_unit)
        projection = min(max(projection, 0), edge_len)
        point_on_edge = v1_world + edge_unit * projection

    world_normal = matrix.to_3x3() @ normal_local
    world_normal.normalize()
    plane_world = (point_on_edge, world_normal)
    op.shape.corner.rotation_a = 0.0

    direction_world.normalize()

    normal_projected = (
        world_normal - world_normal.dot(direction_world) * direction_world
    )
    normal_projected.normalize()

    other_projected = other_normal - other_normal.dot(direction_world) * direction_world
    other_projected.normalize()

    dot_product = normal_projected.dot(other_projected)
    dot_product = max(
        min(dot_product, 1.0), -1.0
    )  # Clamp to avoid floating point errors
    angle = math.acos(dot_product)

    cross_product = normal_projected.cross(other_projected)
    if cross_product.dot(direction_world) < 0:
        angle = -angle

    op.shape.corner.rotation_b = angle

    hit_bm.free()
    del hit_obj_eval
    del hit_data

    return direction_world, plane_world


def custom_orientation(op, context):
    """Get the orientation from the custom plane"""

    # Create DrawMatrix from the matrix property
    custom_matrix = DrawMatrix.from_property(context.scene.bout.align.matrix)
    custom_location = custom_matrix.location
    custom_normal = custom_matrix.normal
    custom_direction = custom_matrix.direction

    custom_plane = (custom_location, custom_normal)

    # Get a point on the plane by projecting mouse.init onto the plane
    region = context.region
    rv3d = context.region_data

    location_world = view3d.region_2d_to_plane_3d(
        region, rv3d, op.mouse.init, custom_plane
    )

    if location_world is None:
        return None, custom_plane

    location_world, detected_axis = orientation.point_on_axis(
        region, rv3d, custom_plane, custom_direction, location_world, distance=30
    )

    _apply_axis_snap(op, detected_axis)

    axis = context.scene.bout.axis
    axis.highlight.x, axis.highlight.y = detected_axis

    plane_world = (location_world, custom_normal)

    return custom_direction, plane_world


def world_orientation(op, context):
    """Get the world orientation"""

    # Get a point on the plane by projecting mouse.init onto the plane
    region = context.region
    rv3d = context.region_data

    orientations = [
        (Vector((1, 0, 0)), Vector((0, 0, 0)), Vector((0, 0, 1))),  # First try: Z-up
        (Vector((0, 0, 1)), Vector((0, 0, 0)), Vector((0, 1, 0))),  # Second try: Y-up
        (Vector((0, 0, 1)), Vector((0, 0, 0)), Vector((1, 0, 0))),  # Third try: X-up
    ]

    for direction, location, normal in orientations:
        world_plane = (location, normal)
        location_world = view3d.region_2d_to_plane_3d(
            region, rv3d, op.mouse.init, world_plane
        )
        if location_world is not None:
            world_direction = direction
            world_normal = normal
            break
    else:
        return None, None

    location_world, detected_axis = orientation.point_on_axis(
        region, rv3d, world_plane, world_direction, location_world, distance=30
    )

    _apply_axis_snap(op, detected_axis)

    axis = context.scene.bout.axis
    axis.highlight.x, axis.highlight.y = detected_axis

    plane_world = (location_world, world_normal)

    return world_direction, plane_world
