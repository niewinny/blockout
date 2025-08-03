from ...utils import view3d, modifier
from ...utilsbmesh import bmeshface
from . import weld


def invoke(self, context, event):
    '''Bevel the mesh'''

    self.ui.interface.callback.clear()

    self.data.bevel.round.enable = True
    if self.data.bevel.type == 'FILL':
        self.data.bevel.fill.enable = True

    self.data.bevel.round.segments_stored = self.data.bevel.round.segments
    self.data.bevel.round.offset_stored = self.data.bevel.round.offset
    self.data.bevel.fill.offset_stored = self.data.bevel.fill.offset
    self.data.bevel.fill.segments_stored = self.data.bevel.fill.segments
    self.mouse.bevel = self.mouse.co

    if self.mode != 'BEVEL':
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

        if event.ctrl:
            round_to = 2 if event.shift else 1
            self.data.bevel.round.offset = round(self.data.bevel.round.offset, round_to)
            self.data.bevel.fill.offset = round(self.data.bevel.fill.offset, round_to)

    if self.data.bevel.mode == 'SEGMENTS':

        delta_2d = (point2d - self.mouse.co).length - (point2d - self.mouse.bevel).length
        if self.data.bevel.type == 'ROUND':
            self.data.bevel.round.segments = max(1, int(self.data.bevel.round.segments_stored + delta_2d / 50))
        else:
            self.data.bevel.fill.segments = max(1, int(self.data.bevel.fill.segments_stored + delta_2d / 50))

    ui(self, region, rv3d, init_point, mouse_co_3d)


def ui(self, region, rv3d, init_point, mouse_co_3d):
    '''Update the UI'''
    self.ui.guid.callback.update_batch([(init_point, mouse_co_3d)])

    init_point_2d = view3d.location_3d_to_region_2d(region, rv3d, init_point)
    point = (init_point_2d + self.mouse.co) / 2
    offset = self.data.bevel.round.offset if self.data.bevel.type == 'ROUND' else self.data.bevel.fill.offset
    segments = self.data.bevel.round.segments if self.data.bevel.type == 'ROUND' else self.data.bevel.fill.segments
    lines = [
        {"point": point, "text_tuple": (f"{self.data.bevel.type}".capitalize(), f"{offset:.3f}", f"{segments}")}
    ]
    self.ui.interface.callback.update_batch(lines)


def refresh(self, context):
    '''Refresh the bevel'''

    if self.config.type == 'OBJECT':

        if self.data.bevel.type == 'ROUND':
            segments = self.data.bevel.round.segments
            for mod in self.modifiers.bevels:
                if mod.type == 'ROUND':
                    mod.mod.segments = segments
        else:
            segments = self.data.bevel.fill.segments
            for mod in self.modifiers.bevels:
                if mod.type == 'FILL':
                    mod.mod.segments = segments

    region = context.region
    rv3d = context.region_data

    init_point = self.data.bevel.origin
    mouse_co_3d = view3d.region_2d_to_location_3d(region, rv3d, self.mouse.co, init_point)

    ui(self, region, rv3d, init_point, mouse_co_3d)


def update(self):
    '''Update the bevel'''
    bm = self.data.bm

    set_round_edges_indexes = [e.index for e in self.data.extrude.edges if e.position == 'MID']
    set_fill_edges_indexes = [e.index for e in self.data.extrude.edges if e.position == 'END']

    set_edge_weight(bm, set_round_edges_indexes, type='ROUND')
    set_edge_weight(bm, set_fill_edges_indexes, type='FILL')

    for m in self.modifiers.bevels:
        if m.type == 'ROUND':
            m.mod.affect = 'EDGES'
            m.mod.limit_method = 'WEIGHT'


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


def uniform(self, bm, obj, extruded_faces):
    '''Update bevel after uniform extrusion from 2D to 3D'''
    from ...utilsbmesh import bmeshface
    
    # Get edges from bottom and top faces
    extruded_bot_edges = [e.index for e in bmeshface.from_index(bm, extruded_faces[0]).edges]
    extruded_top_edges = [e.index for e in bmeshface.from_index(bm, extruded_faces[-1]).edges]
    
    # Get middle edges (vertical edges) - all edges from side faces excluding top and bottom edges
    middle_edges = []
    for face_idx in extruded_faces[1:-1]:  # Skip first and last (bottom and top)
        face = bmeshface.from_index(bm, face_idx)
        for edge in face.edges:
            if edge.index not in extruded_bot_edges and edge.index not in extruded_top_edges:
                middle_edges.append(edge.index)
    
    # Remove duplicates
    middle_edges = list(set(middle_edges))
    
    # Set edge weights for ROUND bevel on middle edges only
    set_edge_weight(bm, middle_edges, type='ROUND')
    
    # Update existing ROUND bevel modifiers from vertex to edge mode
    for mod in self.modifiers.bevels:
        if mod.type == 'ROUND' and mod.mod:
            mod.mod.affect = 'EDGES'
            mod.mod.limit_method = 'WEIGHT'
            mod.mod.edge_weight = "bout_bevel_weight_edge_round"


def add_modifier(obj, width, segments, type='ROUND', limit_method='WEIGHT', affect='EDGES'):
    '''Add the bevel modifier'''
    mod = modifier.add(obj, "Bevel", 'BEVEL')
    mod.width = width
    mod.segments = segments
    mod.limit_method = limit_method
    mod.affect = affect

    if type == 'ROUND':
        mod.edge_weight = "bout_bevel_weight_edge_round"
    else:
        mod.edge_weight = "bout_bevel_weight_edge_fill"

    return mod, type


class mod():

    @staticmethod
    def edges(bm, obj, extruded_edges, round):
        bevel_round_enable = round[0]
        bevel_round_offset = round[1]
        bevel_round_segments = round[2]

        if bevel_round_enable and bevel_round_offset > 0.0:
            set_edge_weight(bm, extruded_edges, type='ROUND')
            add_modifier(obj, bevel_round_offset, bevel_round_segments, type='ROUND')
            weld.add_modifier(obj, type='ROUND')

    @staticmethod
    def verts(obj, round):
        bevel_round_enable = round[0]
        bevel_round_offset = round[1]
        bevel_round_segments = round[2]

        if bevel_round_enable and bevel_round_offset > 0.0:
            add_modifier(obj, bevel_round_offset, bevel_round_segments, type='ROUND', limit_method='ANGLE', affect='VERTICES')

    @staticmethod
    def faces(bm, obj, round, fill, extruded_faces):
        bevel_round_enable = round[0]
        bevel_round_offset = round[1]
        bevel_round_segments = round[2]
        bevel_fill_enable = fill[0]
        bevel_fill_offset = fill[1]
        bevel_fill_segments = fill[2]

        extruded_bot_edges = [e.index for e in bmeshface.from_index(bm, extruded_faces[0]).edges]
        extruded_top_edges = [e.index for e in bmeshface.from_index(bm, extruded_faces[-1]).edges]

        if bevel_round_enable and bevel_round_offset > 0.0:
            extruded_edges = [e.index for f_idx in extruded_faces[1:-1] for e in bmeshface.from_index(bm, f_idx).edges if e.index not in extruded_bot_edges and e.index not in extruded_top_edges]
            set_edge_weight(bm, extruded_edges, type='ROUND')
            add_modifier(obj, bevel_round_offset, bevel_round_segments, type='ROUND')
            weld.add_modifier(obj, type='ROUND')

        if bevel_fill_enable and bevel_fill_offset > 0.0:
            set_edge_weight(bm, extruded_top_edges, type='FILL')
            add_modifier(obj, bevel_fill_offset, bevel_fill_segments, type='FILL')
            weld.add_modifier(obj, type='FILL')
