import bpy


class BOUT_MT_MatrixOperations(bpy.types.Menu):
    bl_idname = "BOUT_MT_MatrixOperations"
    bl_label = "Matrix Operations"

    def draw(self, _context):
        layout = self.layout
        
        layout.operator("bout.store_matrix", text="Store Matrix")
        layout.operator("bout.restore_matrix", text="Restore Matrix")


class BOUT_MT_ObjectMode(bpy.types.Menu):
    bl_idname = "BOUT_MT_ObjectMode"
    bl_label = "Blockout"

    def draw(self, _context):
        layout = self.layout
        layout.operator_context = "INVOKE_DEFAULT"

        layout.separator()
        op = layout.operator("bout.mod_bevel", text="Bevel (Unpinned)")
        op.all_mode = True
        layout.operator("bout.mod_bevel_pinned", text="Bevel Pinned")
        layout.separator()

        # Standard boolean operations
        cut_op = layout.operator("bout.mod_boolean", text="Cut")
        cut_op.operation = 'DIFFERENCE'
        union_op = layout.operator("bout.mod_boolean", text="Union")
        union_op.operation = 'UNION'
        intersect_op = layout.operator("bout.mod_boolean", text="Intersect")
        intersect_op.operation = 'INTERSECT'

        # Special boolean operations
        layout.operator("bout.mod_boolean_slice", text="Slice")
        layout.operator("bout.mod_boolean_carve", text="Carve")

        layout.separator()
        layout.operator("bout.apply_modifiers")

        layout.separator()

        layout.operator("bout.veil")
        layout.operator("bout.unveil")

        layout.separator()

        # Matrix operations submenu
        layout.menu("BOUT_MT_MatrixOperations", text="Matrix")
