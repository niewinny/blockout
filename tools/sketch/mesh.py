from pathlib import Path
import bpy

from ...utils import gizmo, addon
from .common import draw_align


class BOUT_MT_Sketch(bpy.types.WorkSpaceTool):
    bl_space_type = 'VIEW_3D'
    bl_context_mode = 'EDIT_MESH'
    bl_idname = 'bout.sketch'
    bl_label = 'Sketch'
    bl_description = 'Tool for blocking out a mesh'
    bl_icon = 'ops.generic.select_circle'
    bl_options = {'KEYMAP_FALLBACK'}
    bl_keymap = (
        ('bout.draw_mesh_tool', {'type': 'LEFTMOUSE', 'value': 'CLICK_DRAG'}, {'properties': []}),
        ('bout.set_custom_plane', {'type': 'SPACE', 'value': 'PRESS'}, {'properties': []}),
    )

    def draw_settings(context, layout, tool):
        sketch = addon.pref().tools.sketch
        layout.prop(sketch.mesh, 'shape')
        layout.label(text="Align:")
        label = "None" 
        mode = sketch.align.mode
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
        sketch = addon.pref().tools.sketch
        draw_align(layout, sketch)
        if sketch.align.mode == 'FACE':
            layout.prop(sketch.mesh, 'pick')


class Pref(bpy.types.PropertyGroup):
    shape: bpy.props.EnumProperty(
        name="Shape",
        description="Shape",
        items=[('POLYGON', 'Polygon', 'Polygon'),
               ('RECTANGLE', 'Rectangle', 'Rectangle'),
               ('CIRCLE', 'Circle', 'Circle')],
        default='RECTANGLE')
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
)
