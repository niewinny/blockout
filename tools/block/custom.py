import bpy
from ...utils.types import DrawMatrix
from ...utilsbmesh.orientation import get_vectors_from_align_rotation


def redraw(self, context):
    """Tag the 3D view for redraw to update gizmos"""
    for area in context.window.screen.areas:
        if area.type == "VIEW_3D":
            area.tag_redraw()


def update_location(cls, context):
    location = context.scene.bout.align.location

    matrix = DrawMatrix.from_property(context.scene.bout.align.matrix)
    direction = matrix.direction
    normal = matrix.normal

    new_matrix = DrawMatrix.new()
    new_matrix.from_plane((location, normal), direction)
    context.scene.bout.align.matrix = new_matrix.to_property()
    redraw(cls, context)


def update_rotation(cls, context):
    rotation = context.scene.bout.align.rotation
    normal, direction = get_vectors_from_align_rotation(rotation)

    matrix = DrawMatrix.from_property(context.scene.bout.align.matrix)
    location = matrix.location

    new_matrix = DrawMatrix.new()
    new_matrix.from_plane((location, normal), direction)
    context.scene.bout.align.matrix = new_matrix.to_property()
    redraw(cls, context)
