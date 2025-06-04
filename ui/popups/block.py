import bpy

from ...utils import addon


class BOUT_OT_block_popup(bpy.types.Operator):
    """Show block operations popup"""
    bl_idname = "bout.block_popup"
    bl_label = "Blockout"
    bl_options = {'INTERNAL'}

    def draw(self, context):
        layout = self.layout
        block = addon.pref().tools.block

        layout.label(text="Shape:")
        grid = layout.grid_flow(row_major=True, columns=3, even_columns=True,  even_rows=True, align=True)
        shapes = [
            ('BOX', 'MESH_CUBE'),
            ('CYLINDER', 'MESH_CYLINDER'),
            ('RECTANGLE', 'MESH_PLANE'),
            ('NGON', 'LIGHTPROBE_PLANE'),
            ('NHEDRON', 'LIGHTPROBE_SPHERE'),
            ('CIRCLE', 'MESH_CIRCLE'),
            ('SPHERE', 'MESH_UVSPHERE'),
            ('CORNER', 'AREA_DOCK'),
        ]
        for shape, icon in shapes:
            if shape:
                col = grid.column(align=True)
                col.scale_y = 1.6
                col.prop_enum(block, "shape", shape, icon=icon)
            else:
                col = grid.column(align=True)
                col.scale_y = 1.6
                col.label(text="")

        layout.separator(factor=2)

        layout.label(text="Mode:")
        grid = layout.grid_flow(row_major=True, columns=4, even_columns=True, even_rows=True, align=True)
        modes = [
            ('CUT'),
            ('ADD'),
            ('SLICE'),
            ('INTERSECT'),
            ('CARVE'),
            ('UNION'),
            (''),
            ('')
        ]
        for mode in modes:
            if mode:  # Only create button if mode is not empty
                col = grid.column(align=True)
                col.scale_y = 1.6
                col.prop_enum(block, "mode", mode)
            else:
                # Create empty space
                col = grid.column(align=True)
                col.scale_y = 1.6
                col.label(text="")

        layout.separator(factor=2)

        layout.label(text="Align:")
        col_align = layout.column(align=True)
        col_align.use_property_split = False
        row = col_align.row(align=True)
        row.scale_y = 0.8
        row.scale_x = 0.8
        row.prop(context.scene.bout.align, 'mode', expand=True)

        header, body = col_align.panel("align_panel", default_closed=True)
        header.label(text="Align Properties")

        if body:
            col_align.separator()
            col_align.use_property_split = True
            col_align.prop(block.align, 'offset')
            col_align.prop(block.align, 'increments')
            col_align.prop(block.align, 'absolute', text="Absolute increments snap")
            col_align.use_property_split = True
            col = col_align.column(align=True)
            if context.scene.bout.align.mode == 'FACE':
                col.prop(block.align, 'face')

            col.separator()
            col3 = col.column(align=True)
            if context.mode == 'EDIT_MESH':
                col3.prop(block.mesh, 'pick')
            else:
                col3.prop(block.obj, 'pick')


    def execute(self, context):
        return {'INTERFACE'}

    def invoke(self, context, event):
        return context.window_manager.invoke_popup(self, width=320)


classes = (
    BOUT_OT_block_popup,
)
