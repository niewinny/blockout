from pathlib import Path
import bpy

from ..utils import addon, gizmo


class BOUT_MT_Mesh_Sketch(bpy.types.WorkSpaceTool):
    bl_space_type = 'VIEW_3D'
    bl_context_mode = 'EDIT_MESH'
    bl_idname = 'bout.sketch'
    bl_label = 'Sketch'
    bl_description = 'Tool for cutting a mesh'
    bl_icon = 'ops.generic.select_circle'
    bl_widget = 'BOUT_GGT_Blockout'
    bl_keymap = (
        ('bout.mesh_line_cut_tool', {'type': 'LEFTMOUSE', 'value': 'CLICK_DRAG'}, {'properties': [('release_confirm', True)]}),
    )

    def draw_settings(context, layout, tool):
        sketch = addon.pref().tools.sketch

        layout.prop(sketch, 'mode')

class Pref(bpy.types.PropertyGroup):
    mode: bpy.props.EnumProperty(name="Mode", description="Mode", items=[('CUT', 'Cut', 'Cut'), ('SLICE', 'Slice', 'Slice'), ('BISECT', 'Bisect', 'Bisect')], default='CUT')


class Scene(bpy.types.PropertyGroup):
    running: bpy.props.BoolProperty(name="Running", default=False, update=gizmo.refresh)


types_classes = (
    Pref,
    Scene,
)
