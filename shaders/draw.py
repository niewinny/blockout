import bpy
import gpu
from mathutils import Vector
from gpu_extras.batch import batch_for_shader

class DrawPoints():
    def __init__(self, points, size, color):
        self.shader = gpu.shader.from_builtin('POINT_UNIFORM_COLOR' if bpy.app.version >= (4, 5, 0) else 'UNIFORM_COLOR')
        self.size = size
        self.color = color
        self.points = [Vector(p) for p in points]
        self.batch = None

    def create_batch(self):
        if not self.points or len(self.points) < 1:
            return batch_for_shader(self.shader, 'POINTS', {"pos": []})
        vertices = [p.to_3d() if hasattr(p, 'to_3d') else Vector(p) for p in self.points]
        return batch_for_shader(self.shader, 'POINTS', {"pos": vertices})

    def update_batch(self, points=None, color=None, size=None):
        if points is not None:
            self.points = [Vector(p) for p in points]
        if color is not None:
            self.color = color
        if size is not None:
            self.size = size
        self.batch = self.create_batch()

    def line_width(self, size):
        self.size = size

    def viewport_size(self, width, height):
        pass

    def clear(self):
        points = []
        self.update_batch(points)

    def draw(self, context):
        if not self.points or len(self.points) < 1:
            return
        if self.batch is None:
            self.batch = self.create_batch()
        width = context.area.width
        height = context.area.height
        quad_view = getattr(context.space_data, 'region_quadviews', None)
        if quad_view:
            width /= 2
            height /= 2
        gpu.state.depth_test_set('NONE')
        self.shader.bind()
        self.shader.uniform_float('color', self.color)
        gpu.state.point_size_set(self.size)
        gpu.state.blend_set('ALPHA')
        self.batch.draw(self.shader)


class DrawTools():
    def draw_tool(self, context):
        tools_active = self.tool(context)
        if tools_active:
            self.draw(context)

    def tool(self, context):
        active_tool = context.workspace.tools.from_space_view3d_mode(context.mode, create=False)
        bout_tools = active_tool and (active_tool.idname == 'bout.block_obj' or active_tool.idname == 'bout.block_mesh')
        return bout_tools


class DrawGradient():
    def __init__(self, points, colors):
        self.shader = gpu.shader.from_builtin('SMOOTH_COLOR')
        self.points = [Vector(pt) for pt in points]
        self.colors = colors
        self.batch = None
        self.width = 1

    def create_batch(self):
        return self.setup_batch(self.points, self.colors)

    def setup_batch(self, points, colors):
        if points is None or len(points) < 2:
            return batch_for_shader(self.shader, 'TRIS', {"pos": [], "color": []}, indices=[])
        vertices = [point.to_2d() for point in self.points]
        return batch_for_shader(self.shader, 'TRIS', {"pos": vertices, "color": colors}, indices=[(0, 1, 2), (2, 3, 0)])

    def update_batch(self, points, colors=None):
        self.points = [Vector(pt) for pt in points]
        if colors is not None:
            self.colors = colors
        self.batch = self.setup_batch(self.points, self.colors)

    def draw(self, context):
        if len(self.points) < 2:
            return

        if self.batch is None:
            self.batch = self.create_batch()

        width = context.area.width
        height = context.area.height
        quad_view = context.space_data.region_quadviews
        if quad_view:
            width /= 2
            height /= 2

        gpu.state.depth_test_set('NONE')
        self.shader.bind()
        gpu.state.blend_set('ALPHA')
        self.batch.draw(self.shader)

    def line_width(self, width):
        pass

    def viewport_size(self, width, height):
        pass


class DrawLine(DrawTools):
    def __init__(self, points, width, color, depth=False):
        shader_name = 'POLYLINE_FLAT_COLOR'
        self.shader = gpu.shader.from_builtin(shader_name)
        self.width = width
        self.color = color
        self.points = [Vector(p) for p in points]
        self.depth = depth
        self.batch = None

    def create_batch(self):
        return self.setup_batch(self.points, self.color)

    def setup_batch(self, points, color):
        if points is None or len(points) < 2:
            return batch_for_shader(self.shader, 'LINES', {"pos": [], "color": []}, indices=[])
        direction = (points[1] - points[0]).normalized()
        extension_factor = 1e4
        point_a_far = points[0] - direction * extension_factor
        point_b_far = points[1] + direction * extension_factor
        vertices = [point_a_far[:], point_b_far[:]]
        vertex_colors = [color for _ in vertices]
        return batch_for_shader(self.shader, 'LINES', {"pos": vertices, "color": vertex_colors}, indices=[(0, 1)])

    def update_batch(self, points, color=None):
        self.points = [Vector(p) for p in points]
        if color is not None:
            self.color = color
        self.batch = self.setup_batch(self.points, self.color)

    def clear(self):
        '''Clear the points list'''
        points = []
        self.update_batch(points)

    def depth_test_set(self, value):
        value = 'GREATER_EQUAL' if self.depth else 'NONE'
        gpu.state.depth_test_set(value)

    def viewport_size(self, width, height):
        self.shader.uniform_float('viewportSize', (width, height))

    def line_width(self, width):
        self.shader.uniform_float('lineWidth', width)

    def draw(self, context):
        if not self.points or len(self.points) < 1:
            return

        if self.batch is None:
            self.batch = self.create_batch()

        width = context.area.width
        height = context.area.height
        quad_view = context.space_data.region_quadviews
        if quad_view:
            width /= 2
            height /= 2

        self.depth_test_set('NONE')
        self.shader.bind()
        self.viewport_size(width, height)
        self.line_width(self.width)
        gpu.state.blend_set('ALPHA')
        self.batch.draw(self.shader)


class DrawPolyline():
    def __init__(self, points, width, color):
        shader_name = 'POLYLINE_FLAT_COLOR'
        self.shader = gpu.shader.from_builtin(shader_name)
        self.width = width
        self.color = color
        self.points = points
        self.batch = None

    def create_batch(self):
        '''Create a batch for the shader'''

        vertices = [point for edge in self.points for point in edge]
        indices = [(i, i + 1) for i in range(0, len(vertices), 2)]
        return batch_for_shader(self.shader, 'LINES', {"pos": vertices, "color": [self.color]*len(vertices)}, indices=indices)

    def update_batch(self, points, color=None, width=None):
        '''Update the batch with new points'''
        self.points = points
        if color:
            self.color = color
        if width:
            self.width = width
        self.batch = self.create_batch()

    def clear(self):
        '''Clear the points list'''
        points = []
        self.update_batch(points)

    def line_width(self, width):
        self.shader.uniform_float('lineWidth', width)

    def viewport_size(self, width, height):
        self.shader.uniform_float('viewportSize', (width, height))

    def draw(self, context):
        if not self.points or len(self.points) < 1:
            return

        if self.batch is None:
            self.batch = self.create_batch()

        width = context.area.width
        height = context.area.height
        quad_view = context.space_data.region_quadviews
        if quad_view:
            width /= 2
            height /= 2

        gpu.state.depth_test_set('NONE')
        self.shader.bind()
        self.viewport_size(width, height)
        self.line_width(self.width)
        gpu.state.blend_set('ALPHA')
        self.batch.draw(self.shader)


class DrawPlane():
    def __init__(self, plane_co, plane_no, size=1.0, color=(1.0, 1.0, 1.0, 1.0)):
        self.shader = gpu.shader.from_builtin('FLAT_COLOR')
        self.plane_co = Vector(plane_co)
        self.plane_no = Vector(plane_no).normalized()
        self.size = size
        self.color = color
        self.batch = None

    def create_batch(self):
        # Create four points forming a plane
        up = Vector((0, 0, 1))
        if abs(self.plane_no.dot(up)) > 0.999:
            up = Vector((0, 1, 0))
        right = self.plane_no.cross(up).normalized()
        up = right.cross(self.plane_no).normalized()

        half_size = self.size / 2
        corners = [
            self.plane_co + right * half_size + up * half_size,
            self.plane_co - right * half_size + up * half_size,
            self.plane_co - right * half_size - up * half_size,
            self.plane_co + right * half_size - up * half_size,
        ]

        vertices = [corner.to_3d() for corner in corners]
        indices = [(0, 1, 2), (2, 3, 0)]
        colors = [self.color] * 4

        return batch_for_shader(self.shader, 'TRIS', {"pos": vertices, "color": colors}, indices=indices)

    def update_batch(self, plane_co=None, plane_no=None, size=None, color=None):
        if plane_co:
            self.plane_co = Vector(plane_co)
        if plane_no:
            self.plane_no = Vector(plane_no).normalized()
        if size:
            self.size = size
        if color:
            self.color = color
        self.batch = self.create_batch()

    def draw(self, context):
        if self.batch is None:
            self.batch = self.create_batch()

        width = context.area.width
        height = context.area.height
        quad_view = context.space_data.region_quadviews
        if quad_view:
            width /= 2
            height /= 2

        gpu.state.depth_test_set('NONE')
        self.shader.bind()
        self.shader.uniform_float("color", self.color)
        gpu.state.blend_set('ALPHA')
        self.batch.draw(self.shader)

    def line_width(self, width):
        pass

    def viewport_size(self, width, height):
        pass


class DrawFace():
    def __init__(self, points, color):
        self.points = points
        self.color = color
        self.width = 1

        # Create shader but not batch yet
        self.shader = gpu.shader.from_builtin('UNIFORM_COLOR')
        self.batch = None

    def create_batch(self):
        vertices = self.points
        indices = [(0, i, i + 1) for i in range(1, len(vertices) - 1)]
        attributes = {"pos": vertices}

        # Create a batch for the shader
        return batch_for_shader(self.shader, 'TRIS', attributes, indices=indices)

    def update_batch(self, points):
        vertices = points
        indices = [(0, i, i + 1) for i in range(1, len(vertices) - 1)]
        attributes = {"pos": vertices}

        # Update batch for the shader
        self.batch = batch_for_shader(self.shader, 'TRIS', attributes, indices=indices)

    def draw(self, context):
        if not self.points or len(self.points) < 3:
            return

        if self.batch is None:
            self.batch = self.create_batch()

        width = context.area.width
        height = context.area.height
        quad_view = context.space_data.region_quadviews
        if quad_view:
            width /= 2
            height /= 2

        gpu.state.depth_test_set('NONE')
        self.shader.bind()
        self.shader.uniform_float('color', self.color)
        gpu.state.blend_set('ALPHA')
        self.batch.draw(self.shader)

    def line_width(self, width):
        pass

    def viewport_size(self, width, height):
        pass


class DrawGrid(DrawTools):
    def __init__(self, origin, normal, direction, spacing, size, color=(1.0, 1.0, 1.0, 1.0)):
        self.shader = gpu.shader.from_builtin('UNIFORM_COLOR')
        self.origin = Vector(origin)
        self.normal = Vector(normal).normalized()
        self.direction = Vector(direction).normalized()
        self.spacing = spacing
        self.size = size  # Half-size of the grid extent
        self.color = color
        self.batch = None

    def create_batch(self):
        # Find two orthogonal vectors on the plane
        normal = self.normal
        direction = self.direction
        u = direction.normalized()
        v = normal.cross(u).normalized()

        # Calculate grid lines
        extent = self.size
        spacing = self.spacing

        # Calculate the number of lines in each direction from the origin
        num_lines = int(extent / spacing) + 1

        vertices = []

        # Generate lines parallel to u (varying along v) in both directions
        for i in range(-num_lines, num_lines + 1):
            offset = i * spacing
            line_start = self.origin + (v * offset) - (u * extent)
            line_end = self.origin + (v * offset) + (u * extent)
            vertices.extend([line_start, line_end])

        # Generate lines parallel to v (varying along u) in both directions
        for i in range(-num_lines, num_lines + 1):
            offset = i * spacing
            line_start = self.origin + (u * offset) - (v * extent)
            line_end = self.origin + (u * offset) + (v * extent)
            vertices.extend([line_start, line_end])

        # Create indices for the batch
        indices = [(i, i + 1) for i in range(0, len(vertices), 2)]

        # Create and return the batch
        return batch_for_shader(self.shader, 'LINES', {"pos": vertices}, indices=indices)

    def update_batch(self, origin=None, normal=None, spacing=None, size=None, color=None):
        if origin:
            self.origin = Vector(origin)
        if normal:
            self.normal = Vector(normal).normalized()
        if spacing:
            self.spacing = spacing
        if size:
            self.size = size
        if color:
            self.color = color
        self.batch = self.create_batch()

    def draw(self, context):
        if self.batch is None:
            self.batch = self.create_batch()

        width = context.area.width
        height = context.area.height
        quad_view = context.space_data.region_quadviews
        if quad_view:
            width /= 2
            height /= 2

        gpu.state.depth_test_set('NONE')
        self.shader.bind()
        self.shader.uniform_float('color', self.color)
        gpu.state.blend_set('ALPHA')
        self.batch.draw(self.shader)

    def line_width(self, width):
        pass

    def viewport_size(self, width, height):
        pass


class DrawBMeshFaces():
    def __init__(self, obj, faces, color=(1.0, 1.0, 1.0, 1.0)):
        self.shader = gpu.shader.from_builtin('UNIFORM_COLOR')
        self.color = color
        self.faces = faces
        self.obj = obj
        self.batch = None

        self.vertices = []
        self.indices = []

    def create_batch(self):

        if not self.faces:
            return batch_for_shader(self.shader, 'TRIS', {"pos": self.vertices}, indices=self.indices)

        self.vertices = []
        self.indices = []

        vert_index_map = {}
        vert_count = 0

        matrix = self.obj.matrix_world

        for face in self.faces:
            face_indices = []
            for loop in face.loops:
                vert = loop.vert
                co = matrix @ Vector(vert.co)
                if vert not in vert_index_map:
                    vert_index_map[vert] = vert_count
                    self.vertices.append(co)
                    face_indices.append(vert_count)
                    vert_count += 1
                else:
                    face_indices.append(vert_index_map[vert])

            # Triangulate the face by creating triangle indices from the loop indices
            for i in range(1, len(face_indices) - 1):
                self.indices.append((face_indices[0], face_indices[i], face_indices[i + 1]))

        return batch_for_shader(self.shader, 'TRIS', {"pos": self.vertices}, indices=self.indices)

    def update_batch(self, bmesh_faces, color=None):
        self.faces = bmesh_faces
        if color is not None:
            self.color = color
        self.batch = self.create_batch()

    def clear(self):
        self.faces = []
        self.vertices = []
        self.indices = []
        self.batch = self.create_batch()

    def draw(self, context):
        if not self.vertices:
            return

        if self.batch is None:
            self.batch = self.create_batch()

        width = context.area.width
        height = context.area.height
        quad_view = context.space_data.region_quadviews
        if quad_view:
            width /= 2
            height /= 2

        gpu.state.depth_test_set('NONE')
        self.shader.bind()
        self.shader.uniform_float('color', self.color)
        gpu.state.blend_set('ALPHA')
        self.batch.draw(self.shader)

    def line_width(self, width):
        pass

    def viewport_size(self, width, height):
        pass
