from ...utils import view3d, modifier


def invoke(self, context, event):
    '''Bevel the mesh'''

    self.data.bevel.round.segments_stored = self.data.bevel.round.segments
    self.data.bevel.round.offset_stored = self.data.bevel.round.offset
    self.data.bevel.fill.offset_stored = self.data.bevel.fill.offset
    self.data.bevel.fill.segments_stored = self.data.bevel.fill.segments
    self.mouse.bevel = self.mouse.co

    if self.mode != 'BEVEL':
        # volume = self.shape.volume
        # self.data.bevel.type = volume
        self.ui.zaxis.callback.clear()
        self.mode = 'BEVEL'


def modal(self, context, event):
    '''Bevel the mesh'''
    region = context.region
    rv3d = context.region_data

    init_point = self.data.bevel.origin

    mouse_bevel_3d = view3d.region_2d_to_location_3d(region, rv3d, self.mouse.bevel, init_point)
    mouse_co_3d = view3d.region_2d_to_location_3d(region, rv3d, self.mouse.co, init_point)

    point2d = view3d.location_3d_to_region_2d(region, rv3d, init_point)

    if self.data.bevel.mode == 'OFFSET':
        delta_3d = (init_point - mouse_co_3d).length - (init_point - mouse_bevel_3d).length

        # Update stored offset and mouse position when shift state changes
        if event.shift != self.data.bevel.precision:
            if self.data.bevel.type == 'ROUND':
                self.data.bevel.round.offset_stored = self.data.bevel.round.offset
            else:
                self.data.bevel.fill.offset_stored = self.data.bevel.fill.offset

            self.mouse.bevel = self.mouse.co
            mouse_bevel_3d = mouse_co_3d
            delta_3d = 0
            self.data.bevel.precision = event.shift

        adjustment_factor = 0.1 if event.shift else 1.0
        if self.data.bevel.type == 'ROUND':
            self.data.bevel.round.offset = self.data.bevel.round.offset_stored + delta_3d * adjustment_factor
        else:
            self.data.bevel.fill.offset = self.data.bevel.fill.offset_stored + delta_3d * adjustment_factor

    if self.data.bevel.mode == 'SEGMENTS':

        delta_2d = (point2d - self.mouse.co).length - (point2d - self.mouse.bevel).length
        if self.data.bevel.type == 'ROUND':
            self.data.bevel.round.segments = max(1, int(self.data.bevel.round.segments_stored + delta_2d / 50))
        else:
            self.data.bevel.fill.segments = max(1, int(self.data.bevel.fill.segments_stored + delta_2d / 50))

    self.ui.guid.callback.update_batch([(init_point, mouse_co_3d)])


def set_edge_weight(bm, edges_indexes, type='ROUND'):
    '''Set the edge weight'''

    if type == 'ROUND':
        bw = bm.edges.layers.float.get('bout_bevel_weight_edge_round')
        if not bw:
            bw = bm.edges.layers.float.new('bout_bevel_weight_edge_round')
    else:
        bw = bm.edges.layers.float.get('bout_bevel_weight_edge_fill')
        if not bw:
            bw = bm.edges.layers.float.new('bout_bevel_weight_edge_fill')

    edges = [bm.edges[index] for index in edges_indexes]
    for edge in edges:
        edge[bw] = 1.0


def clean_edge_weight(bm, edges_indexes):
    '''Delete the edge weight'''

    bw_round = bm.edges.layers.float.get('bout_bevel_weight_edge_round')
    bw_fill = bm.edges.layers.float.get('bout_bevel_weight_edge_fill')

    edges = [bm.edges[index] for index in edges_indexes]

    if bw_round:
        for edge in edges:
            edge[bw_round] = 0.0
    if bw_fill:
        for edge in edges:
            edge[bw_fill] = 0.0


def del_edge_weight(bm, type='ALL'):
    '''Delete the edge weight'''

    if type == 'ROUND' or type == 'ALL':
        bw = bm.edges.layers.float.get('bout_bevel_weight_edge_round')
        if bw:
            bm.edges.layers.float.remove(bw)
    if type == 'FILL' or type == 'ALL':
        bw = bm.edges.layers.float.get('bout_bevel_weight_edge_fill')
        if bw:
            bm.edges.layers.float.remove(bw)


def add_modifier(obj, width, segments, type='ROUND'):
    '''Add the bevel modifier'''
    mod = modifier.add(obj, "Bevel", 'BEVEL')
    mod.width = width
    mod.segments = segments
    mod.use_pin_to_last = True
    mod.limit_method = 'WEIGHT'
    if type == 'ROUND':
        mod.edge_weight = "bout_bevel_weight_edge_round"
    else:
        mod.edge_weight = "bout_bevel_weight_edge_fill"

    return mod, type
