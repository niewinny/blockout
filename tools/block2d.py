from pathlib import Path
import bpy

from ..utils import addon, gizmo


class BOUT_MT_Mesh_Block2D(bpy.types.WorkSpaceTool):
    bl_space_type = 'VIEW_3D'
    bl_context_mode = 'EDIT_MESH'
    bl_idname = 'bout.block2d'
    bl_label = 'Block 2D'
    bl_description = 'Tool for cutting a mesh'
    bl_icon = 'ops.generic.select_circle'
    bl_widget = 'BOUT_GGT_Blockout'
    bl_keymap = (
        ('bout.mesh_line_cut_tool', {'type': 'LEFTMOUSE', 'value': 'CLICK_DRAG'}, {'properties': [('release_confirm', True)]}),

    )

    def draw_settings(context, layout, tool):
        row = layout.row(align=True)

        block2d = addon.pref().tools.block2d
        row.prop(block2d, 'mode', expand=True)


class Pref(bpy.types.PropertyGroup):
    mode: bpy.props.EnumProperty(name="Mode", description="Mode", items=[('CUT', 'Cut', 'Cut'), ('SLICE', 'Slice', 'Slice'), ('BISECT', 'Bisect', 'Bisect')], default='CUT')

class Scene(bpy.types.PropertyGroup):
    running: bpy.props.BoolProperty(name="Running", default=False, update=gizmo.refresh)


types_classes = (
    Pref,
    Scene,
)
