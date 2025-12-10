# filepath: c:\Users\Pixelkom\AppData\Roaming\Blender Foundation\Blender\AR\extensions\user_default\blockout\utilsbmesh\sphere.py
import bmesh
from mathutils import Matrix, Vector


def create(bm, plane, direction=None, subd=1, radius=None):
    """
    Create a spherical mesh at the given location and orientation.

    :param bm: The bmesh object to modify.
    :param plane: A tuple (location, normal) defining the orientation and center.
    :param direction: Optional direction vector to define the orientation. If None, one will be generated.
    :param subd: Number of subdivisions (0 gives 6 faces/cube, 1 gives 24 faces, higher values give more detail).
    :param radius: The radius of the sphere. Defaults to 1.0.
    :return: List of Vert objects making up the sphere.
    """
    location, normal = plane
    normal = normal.normalized()

    faces = []

    # Build coordinate axes
    if direction is not None:
        # Use the provided direction to build the coordinate system
        x_axis = direction.normalized()
    else:
        # We'll pick an arbitrary axis that is perpendicular to the normal
        if abs(normal.z) < 0.9999:
            x_axis = normal.cross(Vector((0, 0, 1))).normalized()
        else:
            x_axis = normal.cross(Vector((0, 1, 0))).normalized()

    y_axis = normal.cross(x_axis).normalized()

    # Build the transformation matrix
    rotation_matrix = Matrix((x_axis, y_axis, normal)).transposed()
    matrix = rotation_matrix.to_4x4()
    matrix.translation = location

    # Step 1: Create a cube positioned along plane and direction
    result = bmesh.ops.create_cube(
        bm,
        size=0.001,  # Starting with a unit cube
        matrix=matrix,
    )

    cube_verts = result["verts"]

    # Step 2: Subdivide the cube if needed to get more detail
    if subd > 0:
        # Get all edges from the created cube
        edges = []
        for v in cube_verts:
            v.select = True
            edges.extend([e for e in v.link_edges if e not in edges])

        # Subdivide the cube
        subd_result = bmesh.ops.subdivide_edges(
            bm, edges=edges, cuts=subd, use_grid_fill=True
        )

        for f in subd_result["geom"]:
            if isinstance(f, bmesh.types.BMFace):
                f.select = True
                faces.append(f)

    verts = set()
    for f in faces:
        verts.update(f.verts)
    verts = list(verts)

    # Ensure lookup tables are updated
    bm.verts.ensure_lookup_table()
    bm.verts.index_update()
    bm.edges.ensure_lookup_table()
    bm.edges.index_update()
    bm.faces.ensure_lookup_table()
    bm.faces.index_update()

    if radius is None:
        initial_tiny_radius = 0.0001
    else:
        initial_tiny_radius = radius
    for v in verts:
        local_co = v.co - matrix.translation
        # Make sure we don't have zero-length vectors
        if local_co.length > 0:
            local_co.normalize()
            local_co *= initial_tiny_radius
        else:
            # Fallback for zero-length vectors
            local_co = Vector((initial_tiny_radius, 0, 0))
        v.co = local_co + matrix.translation

    bm.select_flush(True)

    faces_indexes = [f.index for f in faces]

    return faces_indexes


def set_radius(faces, plane, loc, direction, radius=None, snap_value=0):
    """
    Set the radius for sphere faces based on distance from center to mouse point.

    :param faces: List of Face objects making up the sphere
    :param plane: A tuple (location, normal) defining the orientation and center
    :param loc: Location vector for calculating radius (can be None if radius is provided)
    :param direction: Direction vector to define orientation
    :param radius: Optional radius value. If provided, used directly instead of calculating from loc
    :param snap_value: Snap value for radius
    :return: Tuple of (radius, point_3d) where point_3d is the point on sphere surface
    """
    # Unpack plane data
    location, normal = plane
    normal = normal.normalized()

    # Build coordinate axes using the provided direction
    x_axis = direction.normalized()
    y_axis = normal.cross(x_axis).normalized()

    # Build the transformation matrix
    rotation_matrix = Matrix((x_axis, y_axis, normal)).transposed()
    matrix = rotation_matrix.to_4x4()
    matrix.translation = location

    # Calculate radius from loc if not provided directly
    if radius is None:
        if loc is None:
            raise ValueError("Either radius or loc must be provided to set_radius")
        radius = (loc - location).length
    elif radius < 0:
        radius = abs(radius)  # Handle negative radius from numeric input

    # Don't modify the radius if it's very small - this avoids the blink
    if radius < 0.001:
        radius = 0.0001

    # Apply snapping if needed
    if snap_value != 0 and radius >= 0.001:
        radius = round(radius / snap_value) * snap_value

    # Calculate a point on the sphere surface in the direction of mouse_point
    if loc is not None:
        direction_to_mouse = loc - location
        if direction_to_mouse.length > 0:
            direction_to_mouse = direction_to_mouse.normalized()
            point_3d = location + (direction_to_mouse * radius)
        else:
            point_3d = location + (x_axis * radius)
    else:
        # If no loc provided, use the x_axis as default direction
        point_3d = location + (x_axis * radius)

    # Extract all unique vertices from the faces and update their positions
    verts = set()
    for f in faces:
        for v in f.verts:
            verts.add(v)

    # Update the positions of the vertices
    for v in verts:
        local_co = v.co - location
        if local_co.length > 0:
            local_co.normalize()
            v.co = location + (local_co * radius)

    return radius, point_3d
