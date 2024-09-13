import bpy
from mathutils import Matrix



class Draw:
    def __init__(self, gm, verts, color, alpha):

        self.color = color
        self.alpha = alpha
        self.verts = verts

        # Create gizmo
        self.gizmo = self.create(gm)

    def create(self, gm):
        # Define gizmos for X arrow (Red)

        gz = gm.gizmos.new(BOUT_FaceGizmo.bl_idname)
        if hasattr(gz, 'verts'):
            gz.verts = self.verts
        gz.setup()
        gz.alpha = self.alpha
        gz.alpha_highlight = self.alpha * 2
        gz.color = self.color
        gz.color_highlight = self.color
        gz.scale_basis = 1.0

        return gz

    def is_modal(self):
        return self.gizmo.is_modal

    def hide(self, set=False):
        if set:
            self.gizmo.hide = True
        else:
            self.gizmo.hide = False

    def operator(self, operator, properties=None):

        op_props = self.gizmo.target_set_operator(operator)
        if properties:
            for prop, value in properties.items():
                setattr(op_props, prop, value)

    def update(self, matrix_basis):

        self.gizmo.matrix_basis = matrix_basis


class BOUT_FaceGizmo(bpy.types.Gizmo):
    bl_idname = "BOUT_GT_face"
    # Assume verts will be set directly on this object before calling setup
    verts = []
    custom_shape = None

    def setup(self):
        # Now 'self.verts' should have been set, and you can use it:
        if len(self.verts) >= 4:  # Ensure there are enough verts
            tris_verts = [self.verts[0], self.verts[1], self.verts[3], self.verts[1], self.verts[2], self.verts[3]]
            self.custom_shape = self.new_custom_shape('TRIS', tris_verts)

    def draw(self, _context):
        # Draw the custom shape
        self.draw_custom_shape(self.custom_shape, matrix=Matrix())

    def draw_select(self, _context, select_id):
        # Draw the custom shape
        self.draw_custom_shape(self.custom_shape, matrix=Matrix(), select_id=select_id)
