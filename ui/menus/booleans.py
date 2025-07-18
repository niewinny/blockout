import bpy


class BOUT_MT_ObjectBoolean(bpy.types.Menu):
    bl_idname = "BOUT_MT_ObjectBoolean"
    bl_label = "Booleans"

    def draw(self, _context):
        layout = self.layout
        layout.operator_context = "INVOKE_DEFAULT"

        layout.separator()

        # Standard boolean operations
        cut_op = layout.operator("bout.mod_boolean", text="Cut")
        cut_op.operation = 'DIFFERENCE'
        
        union_op = layout.operator("bout.mod_boolean", text="Union")
        union_op.operation = 'UNION'
        
        intersect_op = layout.operator("bout.mod_boolean", text="Intersect")
        intersect_op.operation = 'INTERSECT'
        
        layout.separator()
        
        # Special boolean operations
        layout.operator("bout.mod_boolean_slice", text="Slice")
        layout.operator("bout.mod_boolean_carve", text="Carve")
