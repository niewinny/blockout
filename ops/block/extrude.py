from ...utils import view3d
from ...utils.types import DrawVert
from mathutils import Vector
from ...utilsbmesh import facet, corner
from .data import ExtrudeEdge


def invoke(self, context, event):
    '''Extrude the mesh'''

    self.mode = 'EXTRUDE'
    self.shape.volume = '3D'
    self.mouse.extrude = self.mouse.co

    region = context.region
    rv3d = context.region_data

    obj = self.data.obj
    bm = self.data.bm

    draw_faces = [bm.faces[index] for index in self.data.draw.faces]
    draw_face = draw_faces[0]
    plane = self.data.draw.matrix.plane
    normal = self.data.draw.matrix.normal
    direction = self.data.draw.matrix.direction
    rotations = (self.shape.corner.min, self.shape.corner.max)
    offset = self.config.align.offset

    shape = self.config.shape
    match shape:
        case 'CORNER':  
            self.data.extrude.value = 0.2
            extruded_faces_indexes, mid_edge_index = corner.extrude(bm, draw_faces, direction, normal, rotations, self.data.extrude.value)
            self.data.extrude.faces = extruded_faces_indexes
            self.data.extrude.edges = [ExtrudeEdge(index=mid_edge_index, position='MID')]
            corner.offset(bm, extruded_faces_indexes, direction, normal, rotations, offset)

        case _:
            extruded_faces_indexes = facet.extrude(bm, draw_face, plane, 0.0)

            self.data.extrude.faces = extruded_faces_indexes
            self.data.draw.faces[0] = extruded_faces_indexes[0]
            extrude_face = bm.faces[self.data.extrude.faces[-1]]
            self.data.extrude.verts = [DrawVert(index=v.index, co=v.co.copy()) for v in extrude_face.verts]
            draw_face = bm.faces[self.data.draw.faces[0]]
            self.data.draw.verts = [DrawVert(index=v.index, co=v.co.copy()) for v in draw_face.verts]

            extrude_edges = [e.index for v in extrude_face.verts for e in v.link_edges]
            extrude_face_edges = [e.index for e in extrude_face.edges]
            extrude_edges = list(set(extrude_edges) - set(extrude_face_edges))

            self.data.extrude.edges = [ExtrudeEdge(index=e, position='MID') for e in extrude_edges] + [ExtrudeEdge(index=e, position='END') for e in extrude_face_edges]

    self.update_bmesh(obj, bm, loop_triangles=True, destructive=True)

    self.ui.xaxis.callback.clear()
    self.ui.yaxis.callback.clear()
    self.ui.guid.callback.clear()
    self.ui.interface.callback.clear()
    self.ui.vert.callback.clear()

    plane_world = (obj.matrix_world @ plane[0], obj.matrix_world.to_3x3() @ plane[1])
    line_origin = view3d.region_2d_to_plane_3d(region, rv3d, self.mouse.extrude, plane_world)
    self.data.extrude.origin = line_origin
    point1 = line_origin
    point2 = line_origin + plane_world[1]
    self.ui.zaxis.callback.update_batch((point1, point2))


def modal(self, context, event):
    '''Set the extrusion'''

    obj = self.data.obj
    bm = self.data.bm
    matrix_world = obj.matrix_world

    face = bm.faces[self.data.extrude.faces[-1]]
    plane = self.data.draw.matrix.plane
    normal = plane[1]
    verts = [v.co for v in self.data.extrude.verts]

    region = context.region
    rv3d = context.region_data

    # Compute line_origin in world space
    line_origin = self.data.extrude.origin

    # Use world space normal for line_direction
    line_direction = matrix_world.to_3x3() @  normal

    # Calculate extrusion using region_2d_to_line_3d
    _, extrude = view3d.region_2d_to_line_3d(region, rv3d, self.mouse.co, line_origin, line_direction)

    if extrude is None:
        # Handle the case where the line and ray are parallel
        self.data.extrude.value = 0.0
        return

    # Update the mesh with the new extrusion value
    increments = self.config.align.increments if event.ctrl else 0.0
    dz = facet.set_z(face, normal, extrude, verts, snap_value=increments)

    draw_face = bm.faces[self.data.extrude.faces[0]]
    draw_verts = [v.co for v in self.data.draw.verts]
    if self.data.extrude.symmetry:
        facet.set_z(draw_face, normal, -dz, draw_verts, snap_value=increments)
    else:
        offset = self.config.align.offset if self.config.mode != 'ADD' else 0.0
        facet.set_z(draw_face, normal, offset, draw_verts)

    # Update the extrusion value
    self.data.extrude.value = dz

    bevel_verts = [obj.matrix_world @ v.co.copy() for v in face.verts]
    self.data.bevel.origin = sum(bevel_verts, Vector()) / len(bevel_verts)

    extrude_faces = [bm.faces[index] for index in self.data.extrude.faces]

    if self.config.mode != 'ADD':
        self.ui.faces.callback.update_batch(extrude_faces)

    point = self.data.extrude.origin + self.data.draw.matrix.plane[1] * (self.data.extrude.value / 2)
    point_2d = view3d.location_3d_to_region_2d(region, rv3d, point)
    width = f"{self.data.extrude.value:.3f}"
    lines = [
        {"point": point_2d, "text_tuple": (f"Z: {width}",)},
    ]
    self.ui.interface.callback.update_batch(lines)

    self.update_bmesh(obj, bm, loop_triangles=True, destructive=True)
