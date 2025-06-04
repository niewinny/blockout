

class Draw:
    '''Draw an arrow gizmo.'''

    def __init__(self, gm, matrix_basis):

        # Create gizmo
        self.gz = self.create(gm, matrix_basis)

    def create(self, gm, matrix_basis):
        '''Create the arrow gizmo.'''

        gz = gm.gizmos.new("GIZMO_GT_blank_3d")
        gz.color = (1.0, 1.0, 0.0)
        gz.color_highlight = gz.color[:3]
        gz.alpha = 1.0
        gz.scale_basis = 1.0
        gz.matrix_basis = matrix_basis
        gz.hide = False
        gz.hide_select = False
        gz.draw_options = {'STEM'}
        gz.draw_style = 'BOX'
        gz.line_width = 2
        gz.use_draw_value = False
        gz.use_draw_modal = False
        gz.draw_options = {'STEM'}

        return gz

    def operator(self, operator, properties=None):
        '''Set the operator for the arrow gizmo.'''

        op_props = self.gz.target_set_operator(operator)
        if properties:
            for prop, value in properties.items():
                if isinstance(value, dict):
                    nested_op = getattr(op_props, prop)
                    for nested_prop, nested_value in value.items():
                        setattr(nested_op, nested_prop, nested_value)
                else:
                    setattr(op_props, prop, value)
