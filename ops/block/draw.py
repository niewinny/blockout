import math

from mathutils import Matrix, Vector

from ...utils import view3d
from ...utilsbmesh import circle, corner, ngon, rectangle, sphere, triangle


def _build_plane_matrix(plane, direction):
    """Build transformation matrix for plane local space."""
    location, normal = plane
    x_axis = direction.normalized()
    y_axis = normal.cross(x_axis).normalized()
    rotation_matrix = Matrix((x_axis, y_axis, normal)).transposed()
    matrix = rotation_matrix.to_4x4()
    matrix.translation = location
    return matrix


def _mouse_to_local(op, mouse_point):
    """Convert mouse point to plane local coordinates with optional snapping."""
    plane = op.data.draw.matrix.plane
    direction = op.data.draw.matrix.direction
    snap = op.config.align.increments if op.config.snap else 0.0

    matrix = _build_plane_matrix(plane, direction)
    matrix_inv = matrix.inverted_safe()
    mouse_local = matrix_inv @ mouse_point
    x, y = mouse_local.x, mouse_local.y

    if snap != 0:
        x = round(x / snap) * snap
        y = round(y / snap) * snap

    return x, y


def invoke(self, context):
    """Build the mesh data"""

    obj = self.data.obj
    bm = self.data.bm

    plane = self.data.draw.matrix.plane
    direction = self.data.draw.matrix.direction

    if plane is None:
        self.report({"ERROR"}, "Failed to detect drawing plane")
        return False

    shape = self.config.shape
    match shape:
        case "RECTANGLE":
            self.data.draw.faces = rectangle.create(bm, plane)
        case "NGON":
            self.data.draw.faces, self.data.draw.verts = ngon.create(bm, plane)
        case "NHEDRON":
            self.data.draw.faces, self.data.draw.verts = ngon.create(bm, plane)
        case "BOX":
            self.data.draw.faces = rectangle.create(bm, plane)
        case "CIRCLE":
            self.data.draw.faces = circle.create(
                bm, plane, verts_number=self.shape.circle.verts
            )
        case "CYLINDER":
            self.data.draw.faces = circle.create(
                bm, plane, verts_number=self.shape.circle.verts
            )
        case "SPHERE":
            self.data.draw.faces = sphere.create(
                bm, plane, direction, subd=self.shape.sphere.subd
            )
        case "CORNER":
            self.data.draw.faces = corner.create(bm, plane)
        case "TRIANGLE":
            self.data.draw.faces = triangle.create(bm, plane)
        case "PRISM":
            self.data.draw.faces = triangle.create(bm, plane)

    if self.config.shape in {"SPHERE"}:
        self.shape.volume = "3D"

    self.update_bmesh(obj, bm, loop_triangles=True, destructive=True)
    return True


def modal(self, context, event):
    """Update draw geometry based on mouse or numeric input."""
    obj = self.data.obj
    bm = self.data.bm
    ni = self.data.numeric_input

    region = context.region
    rv3d = context.region_data
    plane = self.data.draw.matrix.plane
    direction = self.data.draw.matrix.direction
    matrix_world = obj.matrix_world
    faces = [bm.faces[i] for i in self.data.draw.faces]
    shape = self.config.shape
    verts = self.data.draw.verts
    symmetry = self.data.draw.symmetry
    increments = self.config.align.increments if self.config.snap else 0.0

    if shape not in ["NGON", "NHEDRON"]:
        bevel_verts = [obj.matrix_world @ v.co.copy() for v in faces[0].verts]
        self.data.bevel.origin = sum(bevel_verts, Vector()) / len(bevel_verts)

    # Only calculate from mouse when not in numeric input mode
    if not ni.active:
        mouse_point = view3d.region_2d_to_plane_3d(
            region, rv3d, self.mouse.co, plane, matrix=matrix_world
        )
        if mouse_point is None:
            self.report({"WARNING"}, "Mouse was outside the drawing plane")
            return {"RUNNING_MODAL"}

        # Calculate and set values from mouse
        match shape:
            case "RECTANGLE" | "BOX":
                x, y = _mouse_to_local(self, mouse_point)
                symx, symy = symmetry
                x0 = -x if symy else 0
                y0 = -y if symx else 0
                dx, dy = x - x0, y - y0
                if symx:
                    dy = dy / 2
                if symy:
                    dx = dx / 2
                self.shape.rectangle.co = Vector((dx, dy))

            case "CIRCLE" | "CYLINDER":
                x, y = _mouse_to_local(self, mouse_point)
                self.shape.circle.radius = math.hypot(x, y)

            case "SPHERE":
                x, y = _mouse_to_local(self, mouse_point)
                self.shape.sphere.radius = math.hypot(x, y)

            case "CORNER":
                x, y = _mouse_to_local(self, mouse_point)
                self.shape.corner.co = Vector((x, y))

            case "TRIANGLE" | "PRISM":
                x, y = _mouse_to_local(self, mouse_point)
                self.shape.triangle.height = math.hypot(x, y)
                self.shape.triangle.angle = math.atan2(y, x)

            case "NGON" | "NHEDRON":
                self.data.draw.verts[0].region, _ = ngon.set_xy(
                    bm,
                    verts[0].index,
                    plane,
                    mouse_point,
                    direction,
                    snap_value=increments,
                    symmetry=symmetry,
                )

    # Update geometry using current property values
    match shape:
        case "RECTANGLE" | "BOX":
            co = self.shape.rectangle.co
            _, point = rectangle.set_xy(
                faces[0],
                plane,
                Vector((co.x, co.y, 0)),
                direction,
                local_space=True,
                symmetry=symmetry,
            )
        case "NGON" | "NHEDRON":
            # Already handled above, just get point for UI
            point = bm.verts[verts[0].index].co
        case "CIRCLE" | "CYLINDER":
            _, point = circle.set_xy(
                faces[0], plane, None, direction, radius=self.shape.circle.radius
            )
        case "SPHERE":
            _, point = sphere.set_radius(
                faces, plane, None, direction, radius=self.shape.sphere.radius
            )
        case "CORNER":
            co = self.shape.corner.co
            _, point = corner.set_xy(
                faces,
                plane,
                Vector((co.x, co.y, 0)),
                direction,
                (self.shape.corner.min, self.shape.corner.max),
                local_space=True,
            )
        case "TRIANGLE" | "PRISM":
            h, a = self.shape.triangle.height, self.shape.triangle.angle
            _, point = triangle.set_xy(
                faces[0],
                plane,
                (h * math.cos(a), h * math.sin(a)),
                direction,
                local_space=True,
                symmetry=self.shape.triangle.symmetry,
                flip=self.shape.triangle.flip,
            )

    self.update_bmesh(obj, bm)

    if self.config.mode != "ADD":
        self.ui.faces.callback.update_batch(faces)

    # Update UI labels
    point_global = matrix_world @ point
    location, normal = plane
    location_global = matrix_world @ location
    normal_global = matrix_world.to_3x3() @ normal
    direction_global = matrix_world.to_3x3() @ direction

    _update_ui(
        self,
        shape,
        region,
        rv3d,
        point_global,
        location_global,
        normal_global,
        direction_global,
    )


def _update_ui(self, shape, region, rv3d, point_global, location, normal, direction):
    """Update UI labels for current shape."""
    match shape:
        case "RECTANGLE" | "BOX":
            width_x = self.shape.rectangle.co.x
            width_y = self.shape.rectangle.co.y
            point_x = point_global - direction * (width_x / 2)
            point_y = point_global - direction.cross(normal) * (-width_y / 2)
            point_x_2d = view3d.location_3d_to_region_2d(region, rv3d, point_x)
            point_y_2d = view3d.location_3d_to_region_2d(region, rv3d, point_y)
            if point_x_2d is None or point_y_2d is None:
                return
            lines = [
                {"point": point_x_2d, "text_tuple": (f"X: {width_x:.3f}",)},
                {"point": point_y_2d, "text_tuple": (f"Y: {width_y:.3f}",)},
            ]
            self.ui.interface.callback.update_batch(lines)

        case "CIRCLE" | "CYLINDER":
            radius = self.shape.circle.radius
            mid_point = (location + point_global) / 2
            point_2d = view3d.location_3d_to_region_2d(region, rv3d, mid_point)
            if point_2d is None:
                return
            lines = [
                {
                    "point": point_2d,
                    "text_tuple": (f"R: {radius:.3f}", f"{self.shape.circle.verts}"),
                },
            ]
            self.ui.interface.callback.update_batch(lines)
            if self.data.numeric_input.active:
                self.ui.guid.callback.clear()
            else:
                self.ui.guid.callback.update_batch([(location, point_global)])

        case "SPHERE":
            radius = self.shape.sphere.radius
            mid_point = (location + point_global) / 2
            point_2d = view3d.location_3d_to_region_2d(region, rv3d, mid_point)
            if point_2d is None:
                return
            lines = [
                {
                    "point": point_2d,
                    "text_tuple": (f"R: {radius:.3f}", f"{self.shape.sphere.subd}"),
                },
            ]
            self.ui.interface.callback.update_batch(lines)
            if self.data.numeric_input.active:
                self.ui.guid.callback.clear()
            else:
                self.ui.guid.callback.update_batch([(location, point_global)])

        case "CORNER":
            width_x = self.shape.corner.co.x
            width_y = self.shape.corner.co.y
            fixed_width_x = abs(width_x) / 2
            if width_x < 0:
                fixed_width_x = (abs(width_x) - 2 * abs(width_x)) / 2
            point_x = point_global - direction * fixed_width_x
            point_y = point_global - direction.cross(normal) * (-abs(width_y) / 2)
            point_x_2d = view3d.location_3d_to_region_2d(region, rv3d, point_x)
            point_y_2d = view3d.location_3d_to_region_2d(region, rv3d, point_y)
            if point_x_2d is None or point_y_2d is None:
                return
            lines = [
                {"point": point_x_2d, "text_tuple": (f"X: {width_x:.3f}",)},
                {"point": point_y_2d, "text_tuple": (f"Y: {width_y:.3f}",)},
            ]
            self.ui.interface.callback.update_batch(lines)

        case "TRIANGLE" | "PRISM":
            v_height = point_global - location
            height = v_height.length

            symx = self.shape.triangle.symmetry
            if symx:
                width = height * 2 / math.sqrt(3)
            else:
                width = height / math.sqrt(3)

            mid_height = location + v_height / 2
            if height > 0:
                width_dir = v_height.cross(normal).normalized()
            else:
                width_dir = Vector((1, 0, 0))

            if symx:
                mid_width = point_global + width_dir * (width / 4)
            else:
                mid_width = point_global + width_dir * (width / 2)

            point_h_2d = view3d.location_3d_to_region_2d(region, rv3d, mid_height)
            point_w_2d = view3d.location_3d_to_region_2d(region, rv3d, mid_width)
            if point_h_2d is None or point_w_2d is None:
                return

            lines = [
                {"point": point_w_2d, "text_tuple": (f"W: {width:.3f}",)},
                {"point": point_h_2d, "text_tuple": (f"H: {height:.3f}",)},
            ]
            self.ui.interface.callback.update_batch(lines)

        case "NGON" | "NHEDRON":
            matrix_world = self.data.obj.matrix_world
            verts = self.data.draw.verts
            self.ui.vert.callback.update_batch(
                [matrix_world @ v.co.copy() for v in verts]
            )

            dx, dy = self.data.draw.verts[0].region
            point_x_2d = self.mouse.co.copy()
            point_x_2d.x += 20
            point_y_2d = self.mouse.co.copy()
            point_y_2d.x += 140
            lines = [
                {"point": point_x_2d, "text_tuple": (f"X: {dx:.3f}",)},
                {"point": point_y_2d, "text_tuple": (f"Y: {dy:.3f}",)},
            ]
            self.ui.interface.callback.update_batch(lines)


def update_ui(self, context):
    """Update the drawing"""

    if context.scene.bout.align.mode != "CUSTOM":
        plane = self.data.draw.matrix.plane
        direction = self.data.draw.matrix.direction
        world_origin, world_normal = plane
        x_axis_point = world_origin + direction
        y_direction = world_normal.cross(direction).normalized()
        y_axis_point = world_origin + y_direction
        self.ui.xaxis.callback.update_batch((world_origin, x_axis_point))
        self.ui.yaxis.callback.update_batch((world_origin, y_axis_point))
