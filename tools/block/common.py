def draw_align(layout, block):
    '''Draw align properties'''

    layout.use_property_split = False
    row = layout.row(align=True)
    row.scale_y = 0.8
    row.scale_x = 0.8
    row.prop(block.align, 'mode', expand=True)
    layout.separator()
    layout.use_property_split = True
    layout.prop(block.align, 'offset')
    layout.prop(block.align, 'increments')
    layout.use_property_split = True
    col = layout.column(align=True)
    if block.align.mode == 'FACE':
        col.prop(block.align, 'face')
    if block.align.mode == 'VIEW':
        col.prop(block.align, 'view')
    if block.align.mode == 'CUSTOM':
        col.prop(block.align.custom, 'location')
        col.prop(block.align.custom, 'normal')
        col.prop(block.align.custom, 'direction')
        layout.separator()
        col = layout.column(align=True, heading='Grid')
        col.use_property_decorate = True
        col.prop(block.align.grid, 'enable', text='')
        col2 = col.column(align=True)
        col2.enabled = block.align.grid.enable
        col2.prop(block.align.grid, 'spacing')
        col2.prop(block.align.grid, 'size')


def draw_type(layout, block):
    '''Draw type properties'''

    layout.use_property_split = False
    col = layout.column(align=True)
    col.scale_y = 1.6
    col.prop(block, 'mode', expand=True)


def draw_form(layout, form):
    '''Draw type properties'''

    layout.use_property_split = True


def draw_shape(layout, block):
    '''Draw type properties'''

    layout.use_property_split = False
    col = layout.column(align=True)
    col.scale_y = 1.6
    col.prop(block, 'shape', expand=True)
