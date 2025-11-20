class Draw:
    def __init__(
        self,
        gm,
        matrix_basis,
        color,
        alpha,
        scale_basis,
        hide_select=False,
        line_width=2.0,
        draw_options={"FILL_SELECT", "ALIGN_VIEW"},
    ):
        self.color = color
        self.alpha = alpha
        self.scale_basis = scale_basis

        # Create gizmo
        self.gz = self.create(gm, matrix_basis, hide_select, line_width, draw_options)

    def create(self, gm, matrix_basis, hide_select, line_width, draw_options):
        # Define gizmos for X arrow (Red)
        gz = gm.gizmos.new("GIZMO_GT_move_3d")
        gz.color = self.color
        gz.color_highlight = self.color
        gz.alpha = self.alpha
        gz.alpha_highlight = 0.7
        gz.scale_basis = self.scale_basis
        gz.matrix_basis = matrix_basis
        gz.draw_style = "RING_2D"
        gz.draw_options = draw_options
        gz.line_width = line_width
        gz.select_bias = 10.0
        gz.hide_select = hide_select
        # gz.use_draw_modal = False

        return gz

    def is_modal(self):
        return self.gz.is_modal

    def hide(self, set=False):
        if set:
            self.gz.hide = True
        else:
            self.gz.hide = False

    def operator(self, operator, properties=None):
        op_props = self.gz.target_set_operator(operator)
        if properties:
            for prop, value in properties.items():
                setattr(op_props, prop, value)

    def update(self, matrix_basis):
        self.gz.matrix_basis = matrix_basis
