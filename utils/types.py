from dataclasses import dataclass, field
from typing import Tuple, List
from mathutils import Vector, Matrix


def _orthonormal_basis(normal: Vector, x_dir: Vector) -> List[Vector]:
    """Given a normal and an in-plane direction, compute an orthonormal basis [x, y, z]."""

    z = normal.normalized()
    x_proj = x_dir - (x_dir.dot(z)) * z
    norm_x = x_proj.length
    if norm_x < 1e-6:
        raise ValueError("x_dir is parallel to normal or too small to define X axis")
    x = x_proj / norm_x
    y = z.cross(x)
    return [x, y, z]


@dataclass
class DrawMatrix:
    """4x4 homogeneous transformation matrix encapsulation."""

    mat: Matrix = field(default_factory=lambda: Matrix.Identity(4))

    @classmethod
    def new(cls) -> "DrawMatrix":
        """Create a new blank DrawMatrix with identity matrix."""
        return cls(Matrix.Identity(4))

    @classmethod
    def from_property(cls, matrix_prop) -> "DrawMatrix":
        """Create a DrawMatrix from a float vector property."""
        # Convert the float vector (flat list of 16 values) to a 4x4 matrix
        matrix = Matrix(matrix_prop)
        return cls(matrix)

    def to_property(self) -> list:
        """Convert this matrix to a format suitable for a float vector property."""
        # Flatten the matrix to a list of 16 values in column-major order
        return [
            self.mat[0][0],
            self.mat[1][0],
            self.mat[2][0],
            self.mat[3][0],
            self.mat[0][1],
            self.mat[1][1],
            self.mat[2][1],
            self.mat[3][1],
            self.mat[0][2],
            self.mat[1][2],
            self.mat[2][2],
            self.mat[3][2],
            self.mat[0][3],
            self.mat[1][3],
            self.mat[2][3],
            self.mat[3][3],
        ]

    def from_plane(
        self, plane: Tuple[Vector, Vector], direction: Vector
    ) -> "DrawMatrix":
        """Update this matrix in-place from a plane (origin, normal) and in-plane X direction."""
        origin, normal = plane
        basis = _orthonormal_basis(normal, direction)

        # Create rotation matrix from basis vectors
        x_axis, y_axis, z_axis = basis
        rotation = Matrix((x_axis, y_axis, z_axis)).transposed()

        # Create 4x4 matrix with rotation and translation
        self.mat = rotation.to_4x4()
        self.mat.translation = origin

        return self

    def to_plane(self) -> Tuple[Vector, Vector, Vector]:
        """Extract (origin, x_dir, normal) from this transformation."""
        origin = self.location
        x_dir = self.direction.normalized()
        normal = self.normal.normalized()
        return origin, x_dir, normal

    def to_local(self, obj) -> "DrawMatrix":
        """Transform this matrix from world to local space of the given object."""
        world_to_local = obj.matrix_world.inverted_safe()
        self.mat = world_to_local @ self.mat

        return self

    @property
    def plane(self) -> Tuple[Vector, Vector]:
        """Get the plane definition as (origin, normal)."""
        return self.location, self.normal

    @property
    def location(self) -> Vector:
        """Translation component (origin of the plane)."""
        return Vector((self.mat[0][3], self.mat[1][3], self.mat[2][3]))

    @property
    def direction(self) -> Vector:
        """Local X-axis direction (in-plane)."""
        return Vector((self.mat[0][0], self.mat[1][0], self.mat[2][0]))

    @property
    def normal(self) -> Vector:
        """Local Z-axis direction (plane normal)."""
        return Vector((self.mat[0][2], self.mat[1][2], self.mat[2][2]))

    def copy(self) -> Matrix:
        """Convert this DrawMatrix to a mathutils Matrix."""
        return self.mat.copy()


@dataclass
class DrawVert:
    """Dataclass for storing options"""

    index: int = -1
    co: Vector = Vector()
    region: Vector = Vector()
