import bpy


class BOUT_GT_CustomAxis(bpy.types.Gizmo):
    bl_idname = "BOUT_GT_CustomAxis"

    def draw(self, context):
        if hasattr(self, "x_axis") and self.x_axis:
            self.x_axis.draw(context)
        if hasattr(self, "y_axis") and self.y_axis:
            self.y_axis.draw(context)

    def setup(self):
        self.x_axis = None
        self.y_axis = None
