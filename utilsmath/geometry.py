"""Geometry functions"""

from mathutils import Vector


def bbox_center(coords):
    """Center of the axis-aligned bounding box of ``coords``.

    The caller decides the coordinate space by what it passes (e.g. local
    vertex coords, or world-space points).

    Args:
        coords: iterable of points (``Vector`` or 3-sequences).

    Returns:
        The AABB center, or the origin when ``coords`` is empty.
    """
    coords = [Vector(c) for c in coords]
    if not coords:
        return Vector((0.0, 0.0, 0.0))
    lo = Vector((
        min(c.x for c in coords),
        min(c.y for c in coords),
        min(c.z for c in coords),
    ))
    hi = Vector((
        max(c.x for c in coords),
        max(c.y for c in coords),
        max(c.z for c in coords),
    ))
    return (lo + hi) * 0.5


def distance_point_to_segment(p, v1, v2) -> float:
    """Calculate the distance between a point and a segment

    Args:
        p (Vector): Point
        v1 (Vector): Segment start
        v2 (Vector): Segment end

    """

    v = v2 - v1
    w = p - v1

    c1 = w.dot(v)
    if c1 <= 0:
        return (p - v1).length

    c2 = v.dot(v)
    if c2 <= c1:
        return (p - v2).length

    b = c1 / c2
    pb = v1 + b * v
    return (p - pb).length
