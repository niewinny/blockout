"""Custom data types for drawing and transformation operations.

Provides:
- DrawMatrix: 4x4 transformation matrix wrapper for plane-based operations.
- DrawVert: Vertex data storage for drawing operations.
"""

from dataclasses import dataclass, field
from typing import Tuple, List
from mathutils import Vector, Matrix


def _orthonormal_basis(normal: Vector, x_dir: Vector) -> List[Vector]:
    """Compute an orthonormal basis from a normal and in-plane direction.

    :param normal: The normal vector (Z axis).
    :type normal: mathutils.Vector
    :param x_dir: The in-plane X direction hint.
    :type x_dir: mathutils.Vector
    :return: List of [x, y, z] orthonormal basis vectors.
    :rtype: list[mathutils.Vector]
    :raises ValueError: If x_dir is parallel to normal.
    """

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
    """4x4 homogeneous transformation matrix encapsulation.

    :ivar mat: The underlying 4x4 matrix.
    :vartype mat: mathutils.Matrix
    """

    mat: Matrix = field(default_factory=lambda: Matrix.Identity(4))

    @classmethod
    def new(cls) -> "DrawMatrix":
        """Create a new DrawMatrix with identity matrix.

        :return: A new DrawMatrix instance.
        :rtype: DrawMatrix
        """
        return cls(Matrix.Identity(4))

    @classmethod
    def from_property(cls, matrix_prop) -> "DrawMatrix":
        """Create a DrawMatrix from a flat float vector property.

        :param matrix_prop: Flat list of 16 floats in column-major order.
        :type matrix_prop: list[float]
        :return: A new DrawMatrix instance.
        :rtype: DrawMatrix
        """
        # Convert the float vector (flat list of 16 values) to a 4x4 matrix
        matrix = Matrix(matrix_prop)
        return cls(matrix)

    def to_property(self) -> list:
        """Convert matrix to flat list for float vector property.

        :return: List of 16 floats in column-major order.
        :rtype: list[float]
        """
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
        """Update matrix in-place from a plane and X direction.

        :param plane: Tuple of (origin, normal) vectors.
        :type plane: tuple[mathutils.Vector, mathutils.Vector]
        :param direction: The in-plane X direction.
        :type direction: mathutils.Vector
        :return: Self for method chaining.
        :rtype: DrawMatrix
        """
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
        """Extract plane definition from this transformation.

        :return: Tuple of (origin, x_dir, normal) vectors.
        :rtype: tuple[mathutils.Vector, mathutils.Vector, mathutils.Vector]
        """
        origin = self.location
        x_dir = self.direction.normalized()
        normal = self.normal.normalized()
        return origin, x_dir, normal

    def to_local(self, obj) -> "DrawMatrix":
        """Transform matrix from world to object local space.

        :param obj: The object whose local space to transform into.
        :type obj: bpy.types.Object
        :return: Self for method chaining.
        :rtype: DrawMatrix
        """
        world_to_local = obj.matrix_world.inverted_safe()
        self.mat = world_to_local @ self.mat

        return self

    @property
    def plane(self) -> Tuple[Vector, Vector]:
        """Plane definition as (origin, normal).

        :return: Tuple of (location, normal) vectors.
        :rtype: tuple[mathutils.Vector, mathutils.Vector]
        """
        return self.location, self.normal

    @property
    def location(self) -> Vector:
        """Translation component (origin of the plane).

        :return: The translation vector.
        :rtype: mathutils.Vector
        """
        return Vector((self.mat[0][3], self.mat[1][3], self.mat[2][3]))

    @property
    def direction(self) -> Vector:
        """Local X-axis direction (in-plane).

        :return: The X-axis direction vector.
        :rtype: mathutils.Vector
        """
        return Vector((self.mat[0][0], self.mat[1][0], self.mat[2][0]))

    @property
    def normal(self) -> Vector:
        """Local Z-axis direction (plane normal).

        :return: The Z-axis normal vector.
        :rtype: mathutils.Vector
        """
        return Vector((self.mat[0][2], self.mat[1][2], self.mat[2][2]))

    def copy(self) -> Matrix:
        """Create a copy of the underlying matrix.

        :return: A copy of the matrix.
        :rtype: mathutils.Matrix
        """
        return self.mat.copy()


@dataclass
class DrawVert:
    """Vertex data for drawing operations.

    :ivar index: Vertex index (-1 if unset).
    :vartype index: int
    :ivar co: 3D world coordinates.
    :vartype co: mathutils.Vector
    :ivar region: 2D region coordinates.
    :vartype region: mathutils.Vector
    :ivar direction: Per-vert displacement axis (used by the CORNER
        extrude snapshot so each vert can slide along its own normal).
    :vartype direction: mathutils.Vector
    """

    index: int = -1
    co: Vector = Vector()
    region: Vector = Vector()
    direction: Vector = Vector()
