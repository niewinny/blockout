import bpy


class BOUT_MT_ObjectMode(bpy.types.Menu):
    bl_idname = "BOUT_MT_ObjectMode"
    bl_label = "Blockout"

    def draw(self, context):
        layout = self.layout
        layout.operator_context = "INVOKE_DEFAULT"

        layout.separator()
        op = layout.operator("object.bout_mod_bevel", text="Bevel (Unpinned)")
        op.all_mode = True
        layout.operator("object.bout_mod_bevel_pinned", text="Bevel Pinned")
        layout.separator()

        # Standard boolean operations
        cut_op = layout.operator("object.bout_mod_boolean", text="Cut")
        cut_op.operation = "DIFFERENCE"
        union_op = layout.operator("object.bout_mod_boolean", text="Union")
        union_op.operation = "UNION"
        intersect_op = layout.operator("object.bout_mod_boolean", text="Intersect")
        intersect_op.operation = "INTERSECT"

        # Special boolean operations
        layout.operator("object.bout_mod_boolean_slice", text="Slice")
        layout.operator("object.bout_mod_boolean_carve", text="Carve")

        layout.separator()
        layout.operator("object.bout_clean_cutter")

        layout.separator()
        layout.operator("object.bout_apply_modifiers")

        layout.separator()

        layout.operator("object.bout_veil")
        layout.operator("object.bout_unveil")
