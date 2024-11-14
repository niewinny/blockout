def draw_align(layout, sketch):
    '''Draw align properties'''

    layout.use_property_split = False
    row = layout.row(align=True)
    row.scale_y = 0.8
    row.scale_x = 0.8
    row.prop(sketch.align, 'mode', expand=True)
    layout.separator()
    layout.use_property_split = True
    layout.prop(sketch.align, 'offset')
    layout.use_property_split = True
    col = layout.column(align=True)
    if sketch.align.mode == 'FACE':
        col.prop(sketch.align, 'face')
    if sketch.align.mode == 'VIEW':
        col.prop(sketch.align, 'view')
    if sketch.align.mode == 'CUSTOM':
        col.prop(sketch.align.custom, 'location')
        col.prop(sketch.align.custom, 'normal')
        col.prop(sketch.align.custom, 'direction')
        layout.separator()
        col = layout.column(align=True, heading='Grid')
        col.use_property_decorate = True
        col.prop(sketch.align.grid, 'enable', text='')
        col2 = col.column(align=True)
        col2.enabled = sketch.align.grid.enable
        col2.prop(sketch.align.grid, 'spacing')
        col2.prop(sketch.align.grid, 'size')


def draw_type(layout, sketch):
    '''Draw type properties'''

    layout.use_property_split = False
    row = layout.row(align=True)
    row.scale_y = 0.8
    row.scale_x = 0.8
    row.prop(sketch, 'mode', expand=True)
    layout.separator()
    layout.use_property_split = True
    layout.prop(sketch, 'geomety')
    layout.prop(sketch, 'increments')
    layout.use_property_split = True
    col = layout.column(align=True)
    if sketch.geomety == 'MESH':
        col.enabled = False
    col.prop(sketch, 'origin')


def draw_form(layout, form):
    '''Draw type properties'''

    layout.use_property_split = True
    layout.prop(form, 'increments')
