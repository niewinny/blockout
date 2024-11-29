from pathlib import Path
import bpy

from ...utils import gizmo, addon
from .common import draw_align, draw_type, draw_form


class BOUT_MT_Block(bpy.types.WorkSpaceTool):
    bl_space_type = 'VIEW_3D'
    bl_context_mode = 'EDIT_MESH'
    bl_idname = 'bout.block'
    bl_label = 'Block'
    bl_description = 'Tool for blocking out a mesh'
    bl_icon = 'ops.generic.select_circle'
    bl_options = {'KEYMAP_FALLBACK'}
    bl_keymap = (
        ('bout.block_mesh_tool', {'type': 'LEFTMOUSE', 'value': 'CLICK_DRAG'}, {'properties': []}),
        ('bout.set_custom_plane', {'type': 'SPACE', 'value': 'PRESS'}, {'properties': []}),
    )

    def draw_settings(context, layout, tool):
        block = addon.pref().tools.block
        layout.prop(block.mesh, 'shape')
        label = "None  "
        _type = block.mesh.mode
        match _type:
            case 'CUT': label = "Cut"
            case 'CREATE': label = "Create"
            case 'SLICE':label = "Slice"
        layout.label(text="Form:")
        layout.popover('BOUT_PT_TypeMesh', text=label)
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
               ('CREATE', 'Create', 'Create'),
               ('SLICE', 'Slice', 'Slice')],
        default='CREATE')
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
    BOUT_PT_AlignMesh,
    BOUT_PT_TypeMesh,
)
