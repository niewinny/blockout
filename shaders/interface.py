import bpy
import gpu
from gpu_extras.batch import batch_for_shader
from mathutils import Vector
import blf
import math


class InterfaceDraw():
    def __init__(self, lines, text_size=10, padding=14, text_padding=12, segments=16):
        self.shader = gpu.shader.from_builtin('UNIFORM_COLOR')
        self.lines = lines  # List of dictionaries with keys "point" and "text_tuple"
        self.text_size = text_size
        self.padding = padding
        self.text_padding = text_padding
        self.segments = segments
        self.color = (0.1, 0.1, 0.1, 0.6)
        self.text_color = (0.9, 0.9, 0.9, 1.0)
        self.font_id = 0
        self.text_height = 0
        self.box_height = 0
        self.radius = 0

        # Set font size with DPI compensation and calculate box dimensions
        self.batch = None  # Will be created in draw() with proper DPI

    def create_circle_vertices(self, center_x, center_y, start_angle, end_angle):
        '''Create vertices for a circle arc'''
        vertices = []
        # Add center point
        vertices.append((center_x, center_y))

        # Create vertices for the arc
        for i in range(self.segments + 1):
            angle = start_angle + (end_angle - start_angle) * (i / self.segments)
            x = center_x + self.radius * math.cos(angle)
            y = center_y + self.radius * math.sin(angle)
            vertices.append((x, y))

        return vertices

    def create_batch(self, dpi):
        '''Create a batch for the shader'''
        # Set font size with DPI and UI scale compensation
        ui_scale = bpy.context.preferences.view.ui_scale
        font_size = int(self.text_size * (dpi / 72.0) * ui_scale)
        blf.size(self.font_id, font_size)
        self.text_height = blf.dimensions(self.font_id, "Tg")[1]  # Use "Tg" to get max height including descenders
        self.box_height = self.text_height * 2.5  # Scale box height relative to text height
        self.radius = self.box_height / 2

        vertices = []
        indices = []

        # Process each line
        for _line_idx, line in enumerate(self.lines):
            # Ensure point is valid before creating Vector
            point_data = line.get("point")
            if not point_data:
                continue
            point = Vector(point_data)
            text_tuple = line.get("text_tuple", [])
            current_x = point.x
            total_boxes = len(text_tuple)
            line_start_vertex = len(vertices)

            # Calculate box widths for this line
            box_widths = []
            for i, text in enumerate(text_tuple):
                text_width = blf.dimensions(self.font_id, text)[0]
                is_first = i == 0
                is_last = i == len(text_tuple) - 1

                # Start with text width
                box_width = text_width

                # Add text padding on both sides
                box_width += self.text_padding * 2

                # Remove text padding where there's a cap
                if is_first:  # Remove left text_padding if first (has cap)
                    box_width -= self.text_padding
                if is_last:   # Remove right text_padding if last (has cap)
                    box_width -= self.text_padding

                box_widths.append(box_width)

            # Create boxes for this line
            current_x = point.x
            for i, box_width in enumerate(box_widths):
                is_first = i == 0
                is_last = i == total_boxes - 1

                if not is_first:
                    # Add padding between boxes
                    current_x += self.padding

                y = point.y + self.radius  # Center point y
                start_idx = len(vertices) - line_start_vertex

                # Left circle - only for first box
                if is_first:
                    left_center_x = current_x + self.radius
                    left_verts = self.create_circle_vertices(left_center_x, y, math.pi*3/2, math.pi/2)
                    vertices.extend(left_verts)

                    # Create indices for left circle
                    for j in range(len(left_verts) - 2):
                        indices.extend([(line_start_vertex + start_idx,
                                         line_start_vertex + start_idx + j + 1,
                                         line_start_vertex + start_idx + j + 2)])
                    start_idx = len(vertices) - line_start_vertex

                # Rectangle middle
                rect_left = current_x + (self.radius if is_first else 0)
                rect_right = rect_left + box_width
                vertices.extend([
                    (rect_left, y - self.radius),    # Bottom-left
                    (rect_right, y - self.radius),   # Bottom-right
                    (rect_right, y + self.radius),   # Top-right
                    (rect_left, y + self.radius),    # Top-left
                ])

                # Rectangle indices
                indices.extend([
                    (line_start_vertex + start_idx,
                     line_start_vertex + start_idx + 1,
                     line_start_vertex + start_idx + 2),
                    (line_start_vertex + start_idx,
                     line_start_vertex + start_idx + 2,
                     line_start_vertex + start_idx + 3),
                ])

                # Right circle - only for last box
                if is_last:
                    right_center_x = rect_right
                    right_verts = self.create_circle_vertices(right_center_x, y, -math.pi/2, math.pi/2)
                    right_start_idx = len(vertices) - line_start_vertex
                    vertices.extend(right_verts)

                    # Create indices for right circle
                    for j in range(len(right_verts) - 2):
                        indices.extend([(line_start_vertex + right_start_idx,
                                         line_start_vertex + right_start_idx + j + 1,
                                         line_start_vertex + right_start_idx + j + 2)])

                # Update x position for next box
                current_x = rect_right

        return batch_for_shader(self.shader, 'TRIS', {"pos": vertices}, indices=indices)

    def update_batch(self, lines=None):
        '''Update the batch with new lines'''
        if lines is not None:
            self.lines = lines
        self.batch = None  # Force recreation on next draw

    def clear(self):
        '''Clear all lines'''
        self.lines = []
        self.batch = None  # Force recreation on next draw

    def draw(self, context):
        '''Draw the interface'''
        # Get DPI and UI scale, recreate batch if needed
        dpi = context.preferences.system.dpi
        ui_scale = context.preferences.view.ui_scale
        if self.batch is None:
            self.batch = self.create_batch(dpi)

        # Draw rounded boxes
        self.shader.bind()
        self.shader.uniform_float("color", self.color)
        self.batch.draw(self.shader)

        # Draw text for each line with DPI and UI scale compensation
        font_size = int(self.text_size * (dpi / 72.0) * ui_scale)
        blf.size(self.font_id, font_size)

        for line in self.lines:
            point = Vector(line["point"])
            text_tuple = line["text_tuple"]
            current_x = point.x

            # Calculate box widths for this line
            box_widths = []
            for i, text in enumerate(text_tuple):
                text_width = blf.dimensions(self.font_id, text)[0]
                is_first = i == 0
                is_last = i == len(text_tuple) - 1

                # Start with text width
                box_width = text_width + self.text_padding * 2  # Always add padding for middle boxes

                # Remove padding where there's a cap
                if is_first:  # Remove left padding if first (has cap)
                    box_width -= self.text_padding
                if is_last:   # Remove right padding if last (has cap)
                    box_width -= self.text_padding

                box_widths.append(box_width)

            # Draw text for each box
            for i, (text, box_width) in enumerate(zip(text_tuple, box_widths)):
                is_first = i == 0
                is_last = i == len(text_tuple) - 1
                rect_left = current_x + (self.radius if is_first else 0)

                # Calculate text position based on caps
                text_width, text_height = blf.dimensions(self.font_id, text)

                if is_first and not is_last:
                    # Left cap - align text to right edge of its box
                    text_x = rect_left + box_width - text_width - self.text_padding
                elif not is_first and is_last:
                    # Right cap - align text to left edge of its box
                    text_x = rect_left + self.text_padding
                else:
                    # Both caps or no caps - center the text
                    text_x = rect_left + (box_width - text_width) / 2

                text_y = point.y + (self.box_height - text_height) / 2

                # Draw text
                blf.position(self.font_id, text_x, text_y, 0)
                blf.color(self.font_id, *self.text_color)
                blf.draw(self.font_id, text)

                # Update x position for next box
                current_x = rect_left + box_width
                if not is_last:
                    current_x += self.padding
