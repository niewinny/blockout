from pathlib import Path
import bpy

from ...utils import gizmo, addon
from .common import draw_align, draw_type, draw_form, draw_shape


class BOUT_MT_Block(bpy.types.WorkSpaceTool):
    bl_space_type = 'VIEW_3D'
    bl_context_mode = 'EDIT_MESH'
    bl_idname = 'bout.block'
    bl_label = 'Block'
    bl_description = 'Tool for blocking out a mesh'
    bl_icon = 'ops.generic.select_circle'
    bl_keymap = (
        ('bout.block_mesh_tool', {'type': 'LEFTMOUSE', 'value': 'CLICK_DRAG'}, {'properties': []}),
        ('bout.set_custom_plane', {'type': 'SPACE', 'value': 'PRESS'}, {'properties': []}),
        ('view3d.edit_mesh_extrude_manifold_normal', {'type': 'E', 'value': 'PRESS'}, {'properties': []}),
        ('view3d.select_box', {'type': 'LEFTMOUSE', 'value': 'CLICK_DRAG', 'shift': True}, {'properties': [('mode', 'ADD')]}),
    )

    def draw_settings(context, layout, tool):
        block = addon.pref().tools.block

        layout.label(text="Shape:")
        row = layout.row(align=True)

        label = "None  "
        icon = 'MESH_CUBE'
        _shape = block.mesh.shape
        match _shape:
            case 'RECTANGLE': (label, icon) = ("Rectangle", 'MESH_PLANE')
            case 'BOX': (label, icon) = ("Box", 'MESH_CUBE')
            case 'CIRCLE': (label, icon) = ("Circle", 'MESH_CIRCLE')
            case 'CYLINDER': (label, icon) = ("Cylinder", 'MESH_CYLINDER')
        row.popover('BOUT_PT_ShapeMesh', text=label, icon=icon)

        label = "None  "
        _type = block.mesh.mode
        match _type:
            case 'CUT': label = "Cut"
            case 'CREATE': label = "Create"
        row.popover('BOUT_PT_TypeMesh', text=label)
        layout.label(text="Align:")
        label = "None"
        mode = block.align.mode
        match mode:
            case 'VIEW': label = "View"
            case 'FACE': label = "Face"
            case 'CUSTOM': label = "Custom"
        layout.popover('BOUT_PT_AlignMesh', text=label)


class BOUT_PT_AlignMesh(bpy.types.Panel):
    bl_label = "Align"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'WINDOW'
    bl_context = 'editmesh'

    def draw(self, context):
        layout = self.layout
        block = addon.pref().tools.block
        draw_align(layout, block)
        if block.align.mode == 'FACE':
            layout.prop(block.mesh, 'pick')


class BOUT_PT_ShapeMesh(bpy.types.Panel):
    bl_label = "Shape"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'WINDOW'
    bl_context = 'editmesh'

    def draw(self, context):
        layout = self.layout
        block = addon.pref().tools.block
        mesh = block.mesh
        draw_shape(layout, mesh)


class BOUT_PT_TypeMesh(bpy.types.Panel):
    bl_label = "Type"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'WINDOW'
    bl_context = 'editmesh'

    def draw(self, context):
        layout = self.layout
        block = addon.pref().tools.block
        mesh = block.mesh
        draw_type(layout, mesh)
        form = block.form
        draw_form(layout, form)


class Pref(bpy.types.PropertyGroup):
    shape: bpy.props.EnumProperty(
        name="Shape",
        description="Shape",
        items=[('RECTANGLE', 'Rectangle', 'Rectangle', 'MESH_PLANE', 1),
               ('BOX', 'Box', 'Box', 'MESH_CUBE', 2),
               ('CIRCLE', 'Circle', 'Circle', 'MESH_CIRCLE', 3),
               ('CYLINDER', 'Cylinder', 'Cylinder', 'MESH_CYLINDER', 4)],
        default='BOX')
    mode: bpy.props.EnumProperty(
        name="Mode",
        description="Mode",
        items=[('CUT', 'Cut', 'Cut'),
               ('CREATE', 'Create', 'Create')],
        default='CUT')
    pick: bpy.props.EnumProperty(
        name="Pick",
        description="Pick objects",
        items=[('SELECTED', 'Edited', 'Edited'),
            ('VISIBLE', 'Visible', 'Visible')], 
        default='SELECTED')


class Scene(bpy.types.PropertyGroup):
    running: bpy.props.BoolProperty(name="Running", default=False, update=gizmo.refresh)


types_classes = (
    Pref,
    Scene,
)
classes = (
    BOUT_PT_ShapeMesh,
    BOUT_PT_AlignMesh,
    BOUT_PT_TypeMesh,
)
