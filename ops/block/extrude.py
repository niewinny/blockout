from ...utils import view3d
from mathutils import Vector
from ...bmeshutils import facet
from .data import Vert, ExtrudeEdge


def invoke(self, context, event):
    '''Extrude the mesh'''

    self.mode = 'EXTRUDE'
    self.shape.volume = '3D'
    self.mouse.extrude = self.mouse.co

    region = context.region
    rv3d = context.region_data

    obj = self.data.obj
    bm = self.data.bm

    draw_face = bm.faces[self.data.draw.face]
    plane = self.data.draw.plane

    extruded_faces = facet.extrude(bm, draw_face, plane, 0.0)
    self.data.extrude.faces = extruded_faces
    self.data.draw.face = extruded_faces[0]

    extrude_face = bm.faces[self.data.extrude.faces[-1]]
    self.data.extrude.verts = [Vert(index=v.index, co=v.co.copy()) for v in extrude_face.verts]
    draw_face = bm.faces[self.data.draw.face]
    self.data.draw.verts = [Vert(index=v.index, co=v.co.copy()) for v in draw_face.verts]

    extrude_edges = [e.index for v in extrude_face.verts for e in v.link_edges]
    extrude_face_edges = [e.index for e in extrude_face.edges]
    extrude_edges = list(set(extrude_edges) - set(extrude_face_edges))

    self.data.extrude.edges = [ExtrudeEdge(index=e, position='MID') for e in extrude_edges] + [ExtrudeEdge(index=e, position='END') for e in extrude_face_edges]

    self.update_bmesh(obj, bm, loop_triangles=True, destructive=True)

    self.ui.xaxis.callback.clear()
    self.ui.yaxis.callback.clear()
    self.ui.guid.callback.clear()

    # self.set_offset()

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
    plane = self.data.draw.plane
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
    increments = self.config.form.increments if event.ctrl else 0.0
    dz = facet.set_z(face, normal, extrude, verts, snap_value=increments)

    draw_face = bm.faces[self.data.extrude.faces[0]]
    draw_verts = [v.co for v in self.data.draw.verts]
    if self.data.extrude.symmetry:
        facet.set_z(draw_face, normal, -dz, draw_verts, snap_value=increments)
    else:
        offset = self.config.align.offset if self.config.mode != 'CREATE' else 0.0
        facet.set_z(draw_face, normal, offset, draw_verts, snap_value=increments)

    # Update the extrusion value
    self.data.extrude.value = dz

    bevel_verts = [obj.matrix_world @ v.co.copy() for v in face.verts]
    self.data.bevel.origin = sum(bevel_verts, Vector()) / len(bevel_verts)

    extrude_faces = [bm.faces[index] for index in self.data.extrude.faces]

    if self.config.mode != 'CREATE':
        self.ui.faces.callback.update_batch(extrude_faces)

    self.update_bmesh(obj, bm, loop_triangles=True, destructive=True)
