import math

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
    symmetry=False,
    flip=False,
):
    """
    Expand the triangle face. The `loc` parameter is always provided.
    If `local_space` is True, `loc` is given in the plane's local coordinate system.
    If `local_space` is False, `loc` is given in global coordinate system and will be transformed.
    If `symmetry` is True, the triangle will be symmetric along the x-axis of the plane's local coordinate system.
    If `flip` is True, the triangle's right angle will be flipped.
    """

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
        # Handle both Vector and tuple types
        if isinstance(loc, tuple):
            x1, y1 = loc
        else:
            x1, y1 = loc.x, loc.y
    else:
        # Transform loc from object local space to plane's local space
        if isinstance(loc, tuple):
            # If loc is a tuple, convert to Vector first
            loc = Vector((loc[0], loc[1], 0))
        mouse_local = matrix_inv @ loc
        x1, y1 = mouse_local.x, mouse_local.y

    # New Logic: Free Rotation & Perfect Shapes
    # We treat (0,0) as the Start Point.
    # (x1, y1) is the "Height" point.

    # Vector from Start to Height Point
    v_height = Vector((x1, y1, 0))
    height_len = v_height.length

    if height_len < 1e-6:
        # Avoid division by zero / degenerate triangles
        v_local = [Vector((0, 0, 0))] * 3
        point_3d = location
        return (x1, y1), point_3d

    # Apply snap_value to height if provided
    if snap_value > 0:
        # Round height to nearest snap_value increment
        height_len = round(height_len / snap_value) * snap_value
        # Recalculate v_height with snapped length
        if v_height.length > 1e-6:
            v_height = v_height.normalized() * height_len
            x1, y1 = v_height.x, v_height.y

    # Axis Snapping
    # Check if v_height is close to X or Y axis
    # We are in plane local space. X is (1,0,0), Y is (0,1,0)

    # Threshold angle in radians (e.g., 5 degrees)
    threshold = math.radians(5)

    # Calculate angle with X axis
    # v_height is (x, y, 0). Angle with X (1,0,0) is atan2(y, x)
    angle = math.atan2(v_height.y, v_height.x)

    # Normalize angle to [-pi, pi]
    # atan2 returns [-pi, pi]

    # Check proximity to 0, pi/2, pi, -pi/2
    # 0: X axis
    # pi/2: Y axis
    # pi: -X axis
    # -pi/2: -Y axis

    snap_occured = False

    if abs(angle) < threshold:  # Snap to +X
        v_height = Vector((height_len, 0, 0))
        snap_occured = True
    elif abs(angle - math.pi / 2) < threshold:  # Snap to +Y
        v_height = Vector((0, height_len, 0))
        snap_occured = True
    elif abs(abs(angle) - math.pi) < threshold:  # Snap to -X
        v_height = Vector((-height_len, 0, 0))
        snap_occured = True
    elif abs(angle + math.pi / 2) < threshold:  # Snap to -Y
        v_height = Vector((0, -height_len, 0))
        snap_occured = True

    if snap_occured:
        # Update x1, y1 to match snapped vector
        x1, y1 = v_height.x, v_height.y

    # Local Y axis for the triangle is the direction of the height vector
    local_y = v_height.normalized()
    # Local X axis is perpendicular to Local Y (in the plane)
    # We want it to be consistent, let's say rotated -90 degrees (clockwise)
    local_x = Vector((local_y.y, -local_y.x, 0))

    # Calculate vertices based on symmetry
    if symmetry:  # "Perfect" Triangle (Equilateral)
        # Width for equilateral triangle: height * 2 / sqrt(3)
        width = height_len * 2 / math.sqrt(3)
        half_width = width / 2

        # Vertices:
        # v1: Base Point 1 (Base Center + half_width * local_x)
        # v2: Base Point 2 (Base Center - half_width * local_x)
        # v3: Apex (Start Point = 0,0,0)

        p1 = v_height + local_x * half_width
        p2 = v_height - local_x * half_width
        p3 = Vector((0, 0, 0))

        v_local = [p1, p2, p3]

    else:  # "Half" Triangle (Right Angle)
        # "half if no symetry" -> Right triangle.
        width = height_len / math.sqrt(3)

        # Vertices:
        # v1: Base Corner 1 (Right Angle) = v_height
        # v2: Base Corner 2 = v_height + Width * local_x
        # v3: Apex (Start Point = 0,0,0)

        p1 = v_height
        p2 = v_height + local_x * width
        p3 = Vector((0, 0, 0))

        if flip:
            p2 = v_height - local_x * width

        v_local = [p1, p2, p3]

    # Unpack the local vertex positions
    v1_local, v2_local, v3_local = v_local

    # Transform local coordinates back to object local space and update vertex positions
    v1.co = matrix @ v1_local
    v2.co = matrix @ v2_local
    v3.co = matrix @ v3_local

    # Compute the 3D point corresponding to (x1, y1, 0) in plane's local space
    point_local = Vector((x1, y1, 0))
    point_3d = matrix @ point_local

    # Calculate height (distance from origin to mouse point)
    height = math.sqrt(x1**2 + y1**2)

    # Calculate angle (rotation around normal)
    # atan2 gives us the angle from +X axis
    rotation_angle = math.atan2(y1, x1)

    # Return height, angle, and point_3d (3D point)
    return (height, rotation_angle), point_3d
