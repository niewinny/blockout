from ...utils import modifier, view3d
from ...utilsbmesh import bmeshface
from . import ui as block_ui
from . import weld

def _get_bevel_data(op):
    """Get the active bevel data (round or fill) based on type."""
    return op.data.bevel.round if op.data.bevel.type == "ROUND" else op.data.bevel.fill

def invoke(op, context, event):
    """Bevel the mesh"""

    op.data.bevel.round.enable = True
    if op.data.bevel.type == "FILL":
        op.data.bevel.fill.enable = True

    op.data.bevel.round.segments_stored = op.data.bevel.round.segments
    op.data.bevel.round.offset_stored = op.data.bevel.round.offset
    op.data.bevel.fill.offset_stored = op.data.bevel.fill.offset
    op.data.bevel.fill.segments_stored = op.data.bevel.fill.segments
    op.mouse.bevel = op.mouse.co

    if op.state.phase != "BEVEL":
        # Wipe any prior-phase handles (extrude zaxis, transform x/y/z guides,
        # edit vert markers, etc.) so only bevel's own UI shows up.
        block_ui.clear_phase(op)
        op.state.phase = "BEVEL"
        op.data.transform.active = "BEVEL"

def modal(op, context, event):
    """Bevel the mesh based on mouse or numeric input."""
    region = context.region
    rv3d = context.region_data
    ni = op.data.numeric_input
    init_point = op.data.bevel.origin
    bevel_data = _get_bevel_data(op)

    # Only calculate from mouse when not in numeric input mode
    if not ni.active:
        mouse_bevel_3d = view3d.region_2d_to_location_3d(
            region, rv3d, op.mouse.bevel, init_point
        )
        mouse_co_3d = view3d.region_2d_to_location_3d(
            region, rv3d, op.mouse.co, init_point
        )

        if op.data.bevel.mode == "OFFSET":
            delta_3d = (init_point - mouse_co_3d).length - (
                init_point - mouse_bevel_3d
            ).length

            # Handle shift state change for precision
            if event.shift != op.data.bevel.precision:
                bevel_data.offset_stored = bevel_data.offset
                op.mouse.bevel = op.mouse.co
                delta_3d = 0
                op.data.bevel.precision = event.shift

            adjustment_factor = 0.1 if event.shift else 1.0
            offset = bevel_data.offset_stored + delta_3d * adjustment_factor
            if op.config.snap:
                round_to = 2 if event.shift else 1
                offset = round(offset, round_to)
            bevel_data.offset = offset

        if op.data.bevel.mode == "SEGMENTS":
            point2d = view3d.location_3d_to_region_2d(region, rv3d, init_point)
            delta_2d = (point2d - op.mouse.co).length - (
                point2d - op.mouse.bevel
            ).length
            bevel_data.segments = max(
                1, int(bevel_data.segments_stored + delta_2d / 50)
            )

    # Update modifiers for OBJECT type
    _update_modifiers(op)

    # Update UI
    mouse_co_3d = view3d.region_2d_to_location_3d(
        region, rv3d, op.mouse.co, init_point
    )
    ui(op, region, rv3d, init_point, mouse_co_3d)

def _update_modifiers(op):
    """Update bevel modifiers based on current values."""
    if op.config.type != "OBJECT":
        return

    bevel_data = _get_bevel_data(op)
    bevel_type = op.data.bevel.type

    if not op.modifiers.bevels:
        return  # No bevel modifiers to update

    for mod in op.modifiers.bevels:
        if mod.type == bevel_type:
            mod.mod.width = max(0, bevel_data.offset)
            mod.mod.segments = max(1, bevel_data.segments)  # Ensure segments >= 1

def ui(op, region, rv3d, init_point, mouse_co_3d):
    """Update the UI"""
    if op.data.numeric_input.active:
        op.ui.guid.callback.clear()
    else:
        op.ui.guid.callback.update_batch([(init_point, mouse_co_3d)])

    init_point_2d = view3d.location_3d_to_region_2d(region, rv3d, init_point)
    point = (init_point_2d + op.mouse.co) / 2
    offset = (
        op.data.bevel.round.offset
        if op.data.bevel.type == "ROUND"
        else op.data.bevel.fill.offset
    )
    segments = (
        op.data.bevel.round.segments
        if op.data.bevel.type == "ROUND"
        else op.data.bevel.fill.segments
    )
    lines = [
        {
            "point": point,
            "text_tuple": (
                f"{op.data.bevel.type}".capitalize(),
                f"{offset:.3f}",
                f"{segments}",
            ),
        }
    ]
    op.ui.interface.callback.update_batch(lines)

def refresh(op, context):
    """Refresh the bevel"""
    _update_modifiers(op)

    region = context.region
    rv3d = context.region_data
    init_point = op.data.bevel.origin
    mouse_co_3d = view3d.region_2d_to_location_3d(
        region, rv3d, op.mouse.co, init_point
    )
    ui(op, region, rv3d, init_point, mouse_co_3d)

def update(op):
    """Update the bevel"""
    bm = op.data.bm

    set_round_edges_indexes = [
        e.index for e in op.data.extrude.edges if e.position == "MID"
    ]
    set_fill_edges_indexes = [
        e.index for e in op.data.extrude.edges if e.position == "END"
    ]

    set_edge_weight(bm, set_round_edges_indexes, type="ROUND")
    set_edge_weight(bm, set_fill_edges_indexes, type="FILL")

    for m in op.modifiers.bevels:
        if m.type == "ROUND":
            m.mod.affect = "EDGES"
            m.mod.limit_method = "WEIGHT"

def set_edge_weight(bm, edges_indexes, type="ROUND"):
    """Set the edge weight"""

    if type == "ROUND":
        bw = bm.edges.layers.float.get("bout_bevel_weight_edge_round")
        if not bw:
            bw = bm.edges.layers.float.new("bout_bevel_weight_edge_round")
    else:
        bw = bm.edges.layers.float.get("bout_bevel_weight_edge_fill")
        if not bw:
            bw = bm.edges.layers.float.new("bout_bevel_weight_edge_fill")

    edges = [bm.edges[index] for index in edges_indexes]
    for edge in edges:
        edge[bw] = 1.0

def clean_edge_weight(bm, edges_indexes):
    """Delete the edge weight"""

    bw_round = bm.edges.layers.float.get("bout_bevel_weight_edge_round")
    bw_fill = bm.edges.layers.float.get("bout_bevel_weight_edge_fill")

    edges = [bm.edges[index] for index in edges_indexes]

    if bw_round:
        for edge in edges:
            edge[bw_round] = 0.0
    if bw_fill:
        for edge in edges:
            edge[bw_fill] = 0.0

def del_edge_weight(bm, type="ALL"):
    """Delete the edge weight"""

    if type == "ROUND" or type == "ALL":
        bw = bm.edges.layers.float.get("bout_bevel_weight_edge_round")
        if bw:
            bm.edges.layers.float.remove(bw)
    if type == "FILL" or type == "ALL":
        bw = bm.edges.layers.float.get("bout_bevel_weight_edge_fill")
        if bw:
            bm.edges.layers.float.remove(bw)

def uniform(op, bm, obj, extruded_faces):
    """Update bevel after uniform extrusion from 2D to 3D"""

    # Get edges from bottom and top faces
    extruded_bot_edges = [
        e.index for e in bmeshface.from_index(bm, extruded_faces[0]).edges
    ]
    extruded_top_edges = [
        e.index for e in bmeshface.from_index(bm, extruded_faces[-1]).edges
    ]

    # Get middle edges (vertical edges) - all edges from side faces excluding top and bottom edges
    middle_edges = []
    for face_idx in extruded_faces[1:-1]:  # Skip first and last (bottom and top)
        face = bmeshface.from_index(bm, face_idx)
        for edge in face.edges:
            if (
                edge.index not in extruded_bot_edges
                and edge.index not in extruded_top_edges
            ):
                middle_edges.append(edge.index)

    # Remove duplicates
    middle_edges = list(set(middle_edges))

    # Set edge weights for ROUND bevel on middle edges only
    set_edge_weight(bm, middle_edges, type="ROUND")

    # Update existing ROUND bevel modifiers from vertex to edge mode
    for mod in op.modifiers.bevels:
        if mod.type == "ROUND" and mod.mod:
            mod.mod.affect = "EDGES"
            mod.mod.limit_method = "WEIGHT"
            mod.mod.edge_weight = "bout_bevel_weight_edge_round"

def add_modifier(
    obj, width, segments, type="ROUND", limit_method="WEIGHT", affect="EDGES"
):
    """Add the bevel modifier"""
    mod = modifier.add(obj, "Bevel", "BEVEL")
    mod.width = width
    mod.segments = segments
    mod.limit_method = limit_method
    mod.affect = affect

    if type == "ROUND":
        mod.edge_weight = "bout_bevel_weight_edge_round"
    else:
        mod.edge_weight = "bout_bevel_weight_edge_fill"

    return mod, type

class mod:
    @staticmethod
    def edges(bm, obj, extruded_edges, round):
        bevel_round_enable = round[0]
        bevel_round_offset = round[1]
        bevel_round_segments = round[2]

        if bevel_round_enable and bevel_round_offset > 0.0:
            set_edge_weight(bm, extruded_edges, type="ROUND")
            add_modifier(obj, bevel_round_offset, bevel_round_segments, type="ROUND")
            weld.add_modifier(obj, type="ROUND")

    @staticmethod
    def verts(obj, round):
        bevel_round_enable = round[0]
        bevel_round_offset = round[1]
        bevel_round_segments = round[2]

        if bevel_round_enable and bevel_round_offset > 0.0:
            add_modifier(
                obj,
                bevel_round_offset,
                bevel_round_segments,
                type="ROUND",
                limit_method="ANGLE",
                affect="VERTICES",
            )

    @staticmethod
    def faces(bm, obj, round, fill, extruded_faces):
        bevel_round_enable = round[0]
        bevel_round_offset = round[1]
        bevel_round_segments = round[2]
        bevel_fill_enable = fill[0]
        bevel_fill_offset = fill[1]
        bevel_fill_segments = fill[2]

        extruded_bot_edges = [
            e.index for e in bmeshface.from_index(bm, extruded_faces[0]).edges
        ]
        extruded_top_edges = [
            e.index for e in bmeshface.from_index(bm, extruded_faces[-1]).edges
        ]

        if bevel_round_enable and bevel_round_offset > 0.0:
            extruded_edges = [
                e.index
                for f_idx in extruded_faces[1:-1]
                for e in bmeshface.from_index(bm, f_idx).edges
                if e.index not in extruded_bot_edges
                and e.index not in extruded_top_edges
            ]
            set_edge_weight(bm, extruded_edges, type="ROUND")
            add_modifier(obj, bevel_round_offset, bevel_round_segments, type="ROUND")
            weld.add_modifier(obj, type="ROUND")

        if bevel_fill_enable and bevel_fill_offset > 0.0:
            set_edge_weight(bm, extruded_top_edges, type="FILL")
            add_modifier(obj, bevel_fill_offset, bevel_fill_segments, type="FILL")
            weld.add_modifier(obj, type="FILL")
