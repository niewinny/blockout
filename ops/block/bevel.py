from ...utils import view3d


def invoke(self, context, event):
    '''Bevel the mesh'''

    self.data.bevel.segments_stored = self.data.bevel.segments
    self.data.bevel.offset_stored = self.data.bevel.offset
    self.mouse.bevel = self.mouse.co

    if self.mode != 'BEVEL':
        volume = self.shapes.volume
        self.data.bevel.type = volume
        self.ui.zaxis.callback.clear()
        self.mode = 'BEVEL'


def modal(self, context):
    '''Bevel the mesh'''
    region = context.region
    rv3d = context.region_data

    init_point = self.data.bevel.origin

    mouse_bevel_3d = view3d.region_2d_to_location_3d(region, rv3d, self.mouse.bevel, init_point)
    mouse_co_3d = view3d.region_2d_to_location_3d(region, rv3d, self.mouse.co, init_point)

    point2d = view3d.location_3d_to_region_2d(region, rv3d, init_point)

    if self.data.bevel.mode == 'OFFSET':
        delta_3d = (init_point - mouse_co_3d).length - (init_point - mouse_bevel_3d).length
        self.data.bevel.offset = self.data.bevel.offset_stored + delta_3d

    if self.data.bevel.mode == 'SEGMENTS':
        delta_2d = (point2d - self.mouse.co).length - (point2d - self.mouse.bevel).length
        self.data.bevel.segments = max(1, int(self.data.bevel.segments_stored + delta_2d / 50))

    self.ui.guid.callback.update_batch([(init_point, mouse_co_3d)])


def set_edge_weight(bm, edges_indexes):
    '''Set the edge weight'''

    bw = bm.edges.layers.float.get('bout_bevel_weight_edge')
    if not bw:
        bw = bm.edges.layers.float.new('bout_bevel_weight_edge')
    edges = [bm.edges[index] for index in edges_indexes]
    for edge in edges:
        edge[bw] = 1.0


def clean_edge_weight(bm, edges_indexes):
    '''Delete the edge weight'''

    bw = bm.edges.layers.float.get('bout_bevel_weight_edge')
    if not bw:
        return
    edges = [bm.edges[index] for index in edges_indexes]
    for edge in edges:
        edge[bw] = 0.0


def del_edge_weight(bm):
    '''Delete the edge weight'''

    bw = bm.edges.layers.float.get('bout_bevel_weight_edge')
    if bw:
        bm.edges.layers.float.remove(bw)
