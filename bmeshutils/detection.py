from dataclasses import dataclass
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from bpy_extras.view3d_utils import region_2d_to_origin_3d, region_2d_to_vector_3d, location_3d_to_region_2d



@dataclass
class _Vert:
    """Vertex class to handle vertex detection."""
    index: int = -1
    co: Vector = Vector((0, 0, 0))
    radius: float = 50.0  # Default radius


@dataclass
class _Edge:
    """Edge class to handle edge detection."""
    index: int = -1
    length: float = 0.0
    radius: float = 50.0  # Default radius


@dataclass
class _Face:
    """Face class to handle face detection."""
    index: int = -1
    normal: Vector = Vector((0, 0, 0))
    hit_loc: Vector = Vector((0, 0, 0))


@dataclass
class _Radius:
    """Radius class to handle radius detection."""
    vert: float = 50.0
    edge: float = 50.0


class Closest:
    """Class to handle mesh element detection based on the mouse cursor."""

    def __init__(self, context, bm, point):
        self.vert = None
        self.edge = None
        self.face = None

        self.radius = _Radius()

        self.bvh = BVHTree.FromBMesh(bm, epsilon=0.0)
        self.detect(context, bm, point)

    def __del__(self):
        self.finish()

    def finish(self):
        """Clean up the class."""
        self.vert = None
        self.edge = None
        self.face = None
        self.bvh = None

    def detect(self, context, bm, point):
        """Detect the closest element under the mouse cursor."""
        _direction, _origin, local_origin, local_direction = self._get_ray(context, point)
        hit_loc, index = self._ray_cast(local_origin, local_direction)

        if index is None:
            self.vert = None
            self.edge = None
            self.face = None
            return

        bm.verts.ensure_lookup_table()
        bm.edges.ensure_lookup_table()
        bm.faces.ensure_lookup_table()
        face = bm.faces[index]
        self.face = _Face(index=index, normal=face.normal, hit_loc=hit_loc)
        self.vert = self._detect_closest_vertex(context, point, face)
        self.edge = self._detect_closest_edge(context, hit_loc, face)

    def _get_ray(self, context, mouse_pos):
        """Compute the ray direction and origin from the mouse position."""
        region = context.region
        rv3d = context.region_data
        matrix = context.edit_object.matrix_world
        matrix_inv = matrix.inverted()
        direction = region_2d_to_vector_3d(region, rv3d, mouse_pos)
        origin = region_2d_to_origin_3d(region, rv3d, mouse_pos)
        local_origin = matrix_inv @ origin
        local_direction = matrix_inv.to_3x3() @ direction
        return direction, origin, local_origin, local_direction

    def _ray_cast(self, local_origin, local_direction):
        """Perform a ray cast and return the hit location and face index."""
        hit_loc, _normal, index, _dist = self.bvh.ray_cast(local_origin, local_direction)
        return hit_loc, index

    def _detect_closest_vertex(self, context, point, face):
        """Detect the closest vertex on the given face."""
        verts = [v for v in face.verts]
        verts_2d, valid_indices = self._verts_to_2darray(context, verts)
        closest_vert, closest_vert_2d = self._get_closest_vert(point, verts, verts_2d, valid_indices)

        if closest_vert and self._is_within_radius(point, closest_vert_2d, self.radius.vert):
            return _Vert(index=closest_vert.index, co=closest_vert.co, radius=self.radius.vert)
        else:
            return None

    def _detect_closest_edge(self, context, hit_loc, face):
        """Detect the closest edge on the given face to the hit location."""
        region = context.region
        rv3d = context.region_data
        matrix = context.edit_object.matrix_world
        closest_edge = None
        min_dist = float('inf')
        hit_loc_2d = location_3d_to_region_2d(region, rv3d, matrix @ hit_loc)
        if hit_loc_2d is None:
            return None

        for edge in face.edges:
            p1 = edge.verts[0].co
            p2 = edge.verts[1].co

            closest_point = self._closest_point_on_edge(p1, p2, hit_loc)
            closest_point_2d = location_3d_to_region_2d(region, rv3d, matrix @ closest_point)

            if closest_point_2d is not None and self._is_within_radius(hit_loc_2d, closest_point_2d, self.radius.edge):
                dist = np.linalg.norm(np.array(hit_loc_2d) - np.array(closest_point_2d))
                if dist < min_dist:
                    min_dist = dist
                    closest_edge = edge

        if closest_edge:
            return _Edge(index=closest_edge.index, length=closest_edge.calc_length(), radius=self.radius.edge)
        else:
            return None

    def _get_closest_vert(self, mouse_pos, verts, verts_2d, valid_indices):
        """Get the closest vertex to the mouse cursor."""
        co = np.array(mouse_pos, dtype=np.float32)
        distances = np.linalg.norm(verts_2d - co, axis=1)
        closest_index = np.argmin(distances)
        closest_vert = verts[valid_indices[closest_index]]
        closest_vert_2d = verts_2d[closest_index]
        return closest_vert, closest_vert_2d

    def _closest_point_on_edge(self, p1, p2, point):
        """Get the closest point on the edge to the given point."""
        edge_vec = p2 - p1
        edge_len = edge_vec.length

        # Safeguard: If the edge length is zero, return the first point (p1)
        if edge_len == 0:
            return p1

        edge_unit = edge_vec / edge_len
        point_vec = point - p1
        projection = point_vec.dot(edge_unit)
        projection = min(max(projection, 0), edge_len)
        closest_point = p1 + edge_unit * projection
        return closest_point

    def _is_within_radius(self, mouse_pos, point_2d, radius):
        """Check if the point is within the radius of the mouse cursor."""
        if point_2d is None:
            return False
        return np.linalg.norm(np.array(mouse_pos) - np.array(point_2d)) <= radius

    def _verts_to_2darray(self, context, verts):
        """Convert the vertices to the region coordinates."""
        region = context.region
        rv3d = context.region_data
        matrix = context.edit_object.matrix_world
        coords = [location_3d_to_region_2d(region, rv3d, matrix @ v.co) for v in verts]
        valid_coords = [c for c in coords if c is not None]
        valid_indices = np.array([i for i, c in enumerate(coords) if c is not None])
        return np.array(valid_coords, dtype=np.float32), valid_indices
