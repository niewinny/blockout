from mathutils import Vector
from ...utilsbmesh import rectangle, circle, sphere, corner, ngon
from ...utils import view3d


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

    if self.config.shape in {"SPHERE"}:
        self.shape.volume = "3D"

    self.update_bmesh(obj, bm, loop_triangles=True, destructive=True)
    return True


def modal(self, context, event):
    obj = self.data.obj
    bm = self.data.bm

    region = context.region
    rv3d = context.region_data
    plane = self.data.draw.matrix.plane
    direction = self.data.draw.matrix.direction
    matrix_world = obj.matrix_world
    faces = [bm.faces[i] for i in self.data.draw.faces]
    shape = self.config.shape
    verts = self.data.draw.verts

    if shape not in ["NGON", "NHEDRON"]:
        bevel_verts = [obj.matrix_world @ v.co.copy() for v in faces[0].verts]
        self.data.bevel.origin = sum(bevel_verts, Vector()) / len(bevel_verts)

    mouse_point_on_plane = view3d.region_2d_to_plane_3d(
        region, rv3d, self.mouse.co, plane, matrix=matrix_world
    )
    if mouse_point_on_plane is None:
        self.report({"WARNING"}, "Mouse was outside the drawing plane")
        return

    increments = self.config.align.increments if self.config.snap else 0.0

    symmetry = self.data.draw.symmetry

    match shape:
        case "RECTANGLE":
            self.shape.rectangle.co, point = rectangle.set_xy(
                faces[0],
                plane,
                mouse_point_on_plane,
                direction,
                snap_value=increments,
                symmetry=symmetry,
            )
        case "NGON":
            self.data.draw.verts[0].region, point = ngon.set_xy(
                bm,
                verts[0].index,
                plane,
                mouse_point_on_plane,
                direction,
                snap_value=increments,
                symmetry=symmetry,
            )
        case "NHEDRON":
            self.data.draw.verts[0].region, point = ngon.set_xy(
                bm,
                verts[0].index,
                plane,
                mouse_point_on_plane,
                direction,
                snap_value=increments,
                symmetry=symmetry,
            )
        case "BOX":
            self.shape.rectangle.co, point = rectangle.set_xy(
                faces[0],
                plane,
                mouse_point_on_plane,
                direction,
                snap_value=increments,
                symmetry=symmetry,
            )
        case "CIRCLE":
            self.shape.circle.radius, point = circle.set_xy(
                faces[0], plane, mouse_point_on_plane, direction, snap_value=increments
            )
        case "CYLINDER":
            self.shape.circle.radius, point = circle.set_xy(
                faces[0], plane, mouse_point_on_plane, direction, snap_value=increments
            )
        case "SPHERE":
            self.shape.sphere.radius, point = sphere.set_radius(
                faces, plane, mouse_point_on_plane, direction, snap_value=increments
            )
        case "CORNER":
            self.shape.corner.co, point = corner.set_xy(
                faces,
                plane,
                mouse_point_on_plane,
                direction,
                (self.shape.corner.min, self.shape.corner.max),
                snap_value=increments,
            )

    self.update_bmesh(obj, bm)

    if self.config.mode != "ADD":
        self.ui.faces.callback.update_batch(faces)

    point_gloabal = matrix_world @ point
    location, _normal = plane

    match shape:
        case "RECTANGLE" | "BOX":
            width_x = self.shape.rectangle.co.x
            width_y = self.shape.rectangle.co.y
            direction = self.data.draw.matrix.direction
            point_x = point_gloabal - direction * (width_x / 2)
            point_y = point_gloabal - direction.cross(
                self.data.draw.matrix.plane[1]
            ) * (-width_y / 2)
            point_x_2d = view3d.location_3d_to_region_2d(region, rv3d, point_x)
            point_y_2d = view3d.location_3d_to_region_2d(region, rv3d, point_y)
            lines = [
                {"point": point_x_2d, "text_tuple": (f"X: {width_x:.3f}",)},
                {"point": point_y_2d, "text_tuple": (f"Y: {width_y:.3f}",)},
            ]
            self.ui.interface.callback.update_batch(lines)
        case "CIRCLE" | "CYLINDER":
            radius = self.shape.circle.radius
            mid_point = (location + point_gloabal) / 2
            point_2d = view3d.location_3d_to_region_2d(region, rv3d, mid_point)
            lines = [
                {
                    "point": point_2d,
                    "text_tuple": (f"R: {radius:.3f}", f"{self.shape.circle.verts}"),
                },
            ]
            self.ui.interface.callback.update_batch(lines)
            self.ui.guid.callback.update_batch([(location, point_gloabal)])
        case "SPHERE":
            radius = self.shape.sphere.radius
            mid_point = (location + point_gloabal) / 2
            point_2d = view3d.location_3d_to_region_2d(region, rv3d, mid_point)
            lines = [
                {
                    "point": point_2d,
                    "text_tuple": (f"R: {radius:.3f}", f"{self.shape.sphere.subd}"),
                },
            ]
            self.ui.interface.callback.update_batch(lines)
            self.ui.guid.callback.update_batch([(location, point_gloabal)])
        case "CORNER":
            width_x = self.shape.corner.co.x
            width_y = self.shape.corner.co.y
            direction = self.data.draw.matrix.direction
            fixed_width_x = abs(width_x) / 2
            if width_x < 0:
                fixed_width_x = (abs(width_x) - 2 * abs(width_x)) / 2
            point_x = point_gloabal - direction * fixed_width_x
            point_y = point_gloabal - direction.cross(
                self.data.draw.matrix.plane[1]
            ) * (-abs(width_y) / 2)
            point_x_2d = view3d.location_3d_to_region_2d(region, rv3d, point_x)
            point_y_2d = view3d.location_3d_to_region_2d(region, rv3d, point_y)
            lines = [
                {"point": point_x_2d, "text_tuple": (f"X: {width_x:.3f}",)},
                {"point": point_y_2d, "text_tuple": (f"Y: {width_y:.3f}",)},
            ]
            self.ui.interface.callback.update_batch(lines)
        case "NGON" | "NHEDRON":
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
