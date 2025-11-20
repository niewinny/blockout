import math


class Draw:
    """Draw an arrow gizmo."""

    def __init__(self, gm, matrix_basis):
        # Create gizmo
        self.gz = self.create(gm, matrix_basis)

    def create(self, gm, matrix_basis):
        """Create the arrow gizmo."""

        gz = gm.gizmos.new("GIZMO_GT_arrow_3d")
        gz.color = (1.0, 1.0, 0.0)
        gz.color_highlight = gz.color[:3]
        gz.alpha = 0.6
        gz.alpha_highlight = 1.0
        gz.scale_basis = 1.0
        gz.matrix_basis = matrix_basis
        gz.hide = False
        gz.hide_select = False
        gz.draw_options = {"STEM"}
        gz.draw_style = "BOX"
        gz.line_width = 2
        gz.use_draw_value = False
        gz.use_draw_modal = False
        gz.length = 1.0
        gz.aspect = (1.0, 1.0)

        return gz

    def operator(self, operator, properties=None):
        """Set the operator for the arrow gizmo."""

        op_props = self.gz.target_set_operator(operator)
        if properties:
            for prop, value in properties.items():
                if isinstance(value, dict):
                    nested_op = getattr(op_props, prop)
                    for nested_prop, nested_value in value.items():
                        setattr(nested_op, nested_prop, nested_value)
                else:
                    setattr(op_props, prop, value)


def adjust_alpha_by_view_direction(view_direction, arrow_direction, alpha=0.6):
    """
    Adjust the alpha of the arrow based on the view direction and the arrow direction.

    :param view_direction: The direction the user is looking at the arrow from.
    :type view_direction: mathutils.Vector
    :param arrow_direction: The direction the arrow is pointing.
    :type arrow_direction: mathutils.Vector
    :param alpha: The alpha value to be adjusted.
    :type alpha: float
    :return: The adjusted alpha value.
    :rtype: float
    """
    angle_to_positive = float(view_direction.angle(arrow_direction))
    angle_to_negative = float(view_direction.angle(-arrow_direction))
    angle = min(angle_to_positive, angle_to_negative)
    deg_a = math.radians(45)
    deg_b = math.radians(15)
    if angle > deg_a:
        return alpha
    elif angle < deg_b:
        return 0
    else:
        return alpha * (angle - deg_b) / (deg_a - deg_b)
