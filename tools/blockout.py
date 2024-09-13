from pathlib import Path
import bpy

from ..import utils


class BOUT_MT_Blockout(bpy.types.WorkSpaceTool):
    bl_space_type = 'VIEW_3D'
    bl_context_mode = 'EDIT_MESH'
    bl_idname = 'bout.blockout'
    bl_label = 'Blockout'
    bl_description = 'Tool for blocking out a mesh'
    bl_icon = 'ops.generic.select_circle'
    bl_widget = 'BOUT_GGT_Blockout'
    bl_keymap = (
        ('view3d.select_box', {'type': 'LEFTMOUSE', 'value': 'CLICK_DRAG'}, {'properties': [('mode', 'SET')]}),
        ('view3d.select_box', {'type': 'LEFTMOUSE', 'value': 'CLICK_DRAG', 'ctrl': True}, {'properties': [('mode', 'SUB')]}),
        ('view3d.select_box', {'type': 'LEFTMOUSE', 'value': 'CLICK_DRAG', 'shift': True}, {'properties': [('mode', 'ADD')]}),

    )

    def draw_settings(context, layout, tool):
        row = layout.row(align=True)


class scene(bpy.types.PropertyGroup):
    running: bpy.props.BoolProperty(name="Running", default=False, update=utils.gizmo.refresh)


types_classes = (
    scene,
)
