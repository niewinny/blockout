from pathlib import Path
import bpy

from ..utils import gizmo, addon


class BOUT_MT_Sketch(bpy.types.WorkSpaceTool):
    bl_space_type = 'VIEW_3D'
    bl_context_mode = 'EDIT_MESH'
    bl_idname = 'bout.sketch'
    bl_label = 'Sketch'
    bl_description = 'Tool for blocking out a mesh'
    bl_icon = 'ops.generic.select_circle'
    bl_options = {'KEYMAP_FALLBACK'}
    bl_keymap = (
        ('bout.draw_tool', {'type': 'LEFTMOUSE', 'value': 'CLICK_DRAG'}, {'properties': []}),

    )

    def draw_settings(context, layout, tool):
        sketch = addon.pref().tools.sketch
        layout.prop(sketch, 'shape')
        layout.prop(sketch, 'align')


class Pref(bpy.types.PropertyGroup):
    shape: bpy.props.EnumProperty(name="Shape", description="Shape", items=[('POLYGON', 'Polygon', 'Polygon'), ('RECTANGLE', 'Rectangle', 'Rectangle'), ('CIRCLE', 'Circle', 'Circle')], default='RECTANGLE')
    align: bpy.props.EnumProperty(
        name="Align", 
        description="Align mesh to the face", 
        items=[('NORMAL', 'Normal', 'Normal'), 
               ('CLOSEST', 'Closest', 'Closest'), 
               ('LONGEST', 'Longest', 'Longest'), 
               ('ACTIVE', 'Active', 'Active')],
        default='NORMAL')

class Scene(bpy.types.PropertyGroup):
    running: bpy.props.BoolProperty(name="Running", default=False, update=gizmo.refresh)


types_classes = (
    Pref,
    Scene,
)
