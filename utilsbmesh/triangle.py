from mathutils import Matrix, Vector


def create(bm, plane):
    """Create a triangle face"""

    location, normal = plane
    v1 = bm.verts.new(location)
    v2 = bm.verts.new(location)
    v3 = bm.verts.new(location)

    bm.verts.ensure_lookup_table()
    bm.verts.index_update()

    face = bm.faces.new((v1, v2, v3))
    face.normal = normal
    face.select_set(True)
    bm.select_flush(True)

    bm.faces.ensure_lookup_table()
    bm.faces.index_update()

    return [face.index]


def set_xy(
    face,
    plane,
    loc,
    direction,
    local_space=False,
    snap_value=0,
    symmetry=(False, False),
    flip=False,
):
    """
    Expand the triangle face. The `loc` parameter is always provided.
    If `local_space` is True, `loc` is given in the plane's local coordinate system.
    If `local_space` is False, `loc` is given in global coordinate system and will be transformed.
    If `symy` or `symx` is True, the triangle will be symmetric along the x-axis or y-axis of the plane's local coordinate system.
    If `flip` is True, the triangle's right angle will be flipped.
    """

    symx, symy = symmetry

    # Unpack plane data
    location, normal = plane

    # Unpack face vertices
    v1, v2, v3 = face.verts

    # Build consistent x and y axes for the plane's local coordinate system
    x_axis = direction.normalized()
    y_axis = normal.cross(x_axis).normalized()

    # Build the transformation matrix from plane local space to object local space
    rotation_matrix = Matrix((x_axis, y_axis, normal)).transposed()
    matrix = rotation_matrix.to_4x4()
    matrix.translation = location

    # Build the inverse matrix from object local space to plane local space
    matrix_inv = matrix.inverted_safe()

    # In plane local space, the initial point is at the origin
    # Adjust x0 and y0 based on symmetry
    if local_space:
        # Use loc directly as it is in plane's local space
        x1, y1 = loc.x, loc.y
    else:
        # Transform loc from object local space to plane's local space
        mouse_local = matrix_inv @ loc
        x1, y1 = mouse_local.x, mouse_local.y

    # Apply snapping if a snap_value is provided
    if snap_value != 0:
        x1 = round(x1 / snap_value) * snap_value
        y1 = round(y1 / snap_value) * snap_value

    # Adjust x0 and y0 based on symmetry
    x0 = -x1 if symy else 0
    y0 = -y1 if symx else 0

    dx = x1 - x0
    dy = y1 - y0

    # Determine the quadrant based on the signs of dx and dy
    quadrant_key = (dx >= 0, dy >= 0)

    # Map quadrants to vertex positions using a dictionary
    # The key is (dx >= 0, dy >= 0)
    # The value is a list of 3 vectors representing the triangle vertices

    if symx:
        # Symmetry Axis X (Mirror Y) -> Isosceles along X
        # v1: Origin (0, 0)
        # v2: Mirror of v3 (x1, -y1)
        # v3: Cursor (x1, y1)
        if flip:
            # Flip: Pointing the other way?
            # Let's assume flip inverts the X direction relative to the base
            # v1: (x1, 0)
            # v2: (0, -y1)
            # v3: (0, y1)
            v_local = [
                Vector((x1, 0, 0)),
                Vector((0, -y1, 0)),
                Vector((0, y1, 0)),
            ]
        else:
            v_local = [
                Vector((0, 0, 0)),
                Vector((x1, -y1, 0)),
                Vector((x1, y1, 0)),
            ]
    elif symy:
        # Symmetry Axis Y (Mirror X) -> Isosceles along Y
        # v1: Origin (0, 0)
        # v2: Mirror of v3 (-x1, y1)
        # v3: Cursor (x1, y1)
        if flip:
            # Flip: Pointing the other way
            # v1: (0, y1)
            # v2: (-x1, 0)
            # v3: (x1, 0)
            v_local = [
                Vector((0, y1, 0)),
                Vector((-x1, 0, 0)),
                Vector((x1, 0, 0)),
            ]
        else:
            v_local = [
                Vector((0, 0, 0)),
                Vector((-x1, y1, 0)),
                Vector((x1, y1, 0)),
            ]
    elif flip:
        vertex_assignments = {
            (True, True): [  # Quadrant I
                Vector((x0, y0, 0)),
                Vector((x0, y1, 0)),
                Vector((x1, y1, 0)),
            ],
            (False, True): [  # Quadrant II
                Vector((x0, y0, 0)),
                Vector((x0, y1, 0)),
                Vector((x1, y1, 0)),
            ],
            (False, False): [  # Quadrant III
                Vector((x0, y0, 0)),
                Vector((x0, y1, 0)),
                Vector((x1, y1, 0)),
            ],
            (True, False): [  # Quadrant IV
                Vector((x0, y0, 0)),
                Vector((x0, y1, 0)),
                Vector((x1, y1, 0)),
            ],
        }
        v_local = vertex_assignments.get(quadrant_key)
    else:
        vertex_assignments = {
            (True, True): [  # Quadrant I (dx >= 0, dy >= 0)
                Vector((x0, y0, 0)),  # v1_local
                Vector((x1, y0, 0)),  # v2_local
                Vector((x1, y1, 0)),  # v3_local
            ],
            (False, True): [  # Quadrant II (dx < 0, dy >= 0)
                Vector((x0, y0, 0)),
                Vector((x1, y0, 0)),
                Vector((x1, y1, 0)),
            ],
            (False, False): [  # Quadrant III (dx < 0, dy < 0)
                Vector((x0, y0, 0)),
                Vector((x1, y0, 0)),
                Vector((x1, y1, 0)),
            ],
            (True, False): [  # Quadrant IV (dx >= 0, dy < 0)
                Vector((x0, y0, 0)),
                Vector((x1, y0, 0)),
                Vector((x1, y1, 0)),
            ],
        }
        v_local = vertex_assignments.get(quadrant_key)

    if v_local is None:
        v_local = [Vector((x0, y0, 0))] * 3

    # Unpack the local vertex positions
    v1_local, v2_local, v3_local = v_local

    # Transform local coordinates back to object local space and update vertex positions
    v1.co = matrix @ v1_local
    v2.co = matrix @ v2_local
    v3.co = matrix @ v3_local

    # Compute the 3D point corresponding to (x1, y1, 0) in plane's local space
    point_local = Vector((x1, y1, 0))
    point_3d = matrix @ point_local

    # Return dx, dy (2D location), and point_3d (3D point)
    if symx:
        dy = dy / 2
    if symy:
        dx = dx / 2

    return (dx, dy), point_3d
