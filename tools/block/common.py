def draw_align(layout, context, block):
    '''Draw align properties'''

    layout.use_property_split = False
    row = layout.row(align=True)
    row.scale_y = 0.8
    row.scale_x = 0.8
    row.prop(context.scene.bout.align, 'mode', expand=True)
    layout.separator()
    layout.use_property_split = True
    layout.prop(block.align, 'offset')
    layout.prop(block.align, 'increments')
    layout.prop(block.align, 'absolute', text="Absolute increments snap")
    layout.use_property_split = True
    col = layout.column(align=True)
    if context.scene.bout.align.mode == 'FACE':
        col.prop(block.align, 'face')
    if context.scene.bout.align.mode == 'CUSTOM':
        col = layout.column(align=True, heading='Location')
        col.prop(context.scene.bout.align, 'location', text='Location', expand=True)
        col = layout.column(align=True, heading='Rotation')
        col.prop(context.scene.bout.align, 'rotation', text='Rotation', expand=True)



def draw_type(layout, block):
    '''Draw type properties'''

    layout.use_property_split = False
    col = layout.column(align=True)
    col.scale_y = 1.6
    col.prop(block, 'mode', expand=True)


def draw_shape(layout, block):
    '''Draw type properties'''

    layout.use_property_split = False
    col = layout.column(align=True)
    col.scale_y = 1.6
    col.prop(block, 'shape', expand=True)
