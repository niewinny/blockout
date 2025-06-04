from pathlib import Path
import bpy
from ... import bl_info
from ...utils import addon
from .common import draw_align, draw_type, draw_shape


class BOUT_MT_BlockObj(bpy.types.WorkSpaceTool):
    bl_space_type = 'VIEW_3D'
    bl_context_mode = 'OBJECT'
    bl_idname = 'bout.block_obj'
    bl_label = 'BlockOut'
    bl_description = f'v: {bl_info["version"][0]}.{bl_info["version"][1]}.{bl_info["version"][2]}\n\nDraw a mesh interactively\n • LMB - Draw a mesh\n • D - open the options Menu\n • SPACE - set custom plane to align to\n • SPACE + ALT - move custom plane'
    bl_icon = (Path(__file__).parent.parent.parent / "icons" / "cat").as_posix()
    bl_keymap = (
        ('bout.block_obj_tool', {'type': 'LEFTMOUSE', 'value': 'CLICK_DRAG'}, {'properties': []}),
        ('bout.obj_set_custom_plane', {'type': 'SPACE', 'value': 'PRESS'}, {'properties': [('mode', 'SET')]}),
        ('bout.obj_set_custom_plane', {'type': 'SPACE', 'value': 'PRESS', 'alt': True}, {'properties': [('mode', 'MOVE')]}),
        ('view3d.select_box', {'type': 'LEFTMOUSE', 'value': 'CLICK_DRAG', 'shift': True}, {'properties': [('mode', 'ADD')]}),
        ('bout.block_popup', {'type': 'D', 'value': 'PRESS'}, {}),
        ('bout.mod_bevel', {'type': 'B', 'value': 'PRESS'}, {}),
    )

    def draw_settings(context, layout, tool):
        block = addon.pref().tools.block
        layout.label(text="Shape:")
        row = layout.row(align=True)

        label = "None  "
        icon = 'MESH_CUBE'
        _shape = block.shape
        match _shape:
            case 'BOX': (label, icon) = ("Box", 'MESH_CUBE')
            case 'CYLINDER': (label, icon) = ("Cylinder", 'MESH_CYLINDER')
            case 'RECTANGLE': (label, icon) = ("Rectangle", 'MESH_PLANE')
            case 'NGON': (label, icon) = ("N-gon", 'LIGHTPROBE_PLANE')
            case 'NHEDRON': (label, icon) = ("N-hedron", 'LIGHTPROBE_SPHERE')
            case 'CIRCLE': (label, icon) = ("Circle", 'MESH_CIRCLE')
            case 'SPHERE': (label, icon) = ("Sphere", 'MESH_UVSPHERE')
            case 'CORNER': (label, icon) = ("Corner", 'AREA_DOCK')
        row.popover('BOUT_PT_ShapeObj', text=label, icon=icon)

        label = "None  "
        _type = block.mode
        match _type:
            case 'CUT': label = "Cut"
            case 'ADD': label = "Add"
            case 'SLICE': label = "Slice"
            case 'INTERSECT': label = "Intersect"
            case 'CARVE': label = "Carve"
            case 'UNION': label = "Union"
        row.popover('BOUT_PT_TypeObj', text=label)

        layout.separator()
        layout.label(text="Align:")
        label = "None"
        mode = context.scene.bout.align.mode
        match mode:
            case 'FACE': label, icon = ("Face", "ORIENTATION_NORMAL")
            case 'CUSTOM': label, icon = ("Custom", "OBJECT_ORIGIN")
        layout.popover('BOUT_PT_AlignObj', text=label, icon=icon)


class BOUT_PT_AlignObj(bpy.types.Panel):
    bl_label = "Align"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'WINDOW'
    bl_description = "Select how object is aligned to the surface\n • Face - align to the face of the selected/visible object\n • Custom - align to the custom plane"
    bl_context = 'objectmode'

    def draw(self, context):
        layout = self.layout
        block = addon.pref().tools.block
        draw_align(layout, context, block)
        layout.separator()
        layout.prop(block.obj, 'pick')


class BOUT_PT_ShapeObj(bpy.types.Panel):
    bl_label = "Shape"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'WINDOW'
    bl_description = "Pick shape of the object\n • Box\n • Cylinder\n • Rectangle\n • Circle\n • Sphere\n • N-gon\n • N-hedron\n • Corner"
    bl_context = 'objectmode'

    def draw(self, context):
        layout = self.layout
        block = addon.pref().tools.block
        draw_shape(layout, block)


class BOUT_PT_TypeObj(bpy.types.Panel):
    bl_label = "Type"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'WINDOW'
    bl_description = "Select type of the operation\n • Cut - boolean difference object into another\n • Add - add new object\n • Slice - Slice object into another\n • Intersect - boolean intersect object into another \n • Carve - carve object into another \n • Union - boolean union object into another"
    bl_context = 'objectmode'

    def draw(self, context):
        layout = self.layout
        block = addon.pref().tools.block
        draw_type(layout, block)


class Pref(bpy.types.PropertyGroup):
    pick: bpy.props.EnumProperty(
        name="Pick",
        description="Pick objects",
        items=[('SELECTED', 'Selected', 'Selected'),
            ('VISIBLE', 'Visible', 'Visible')], 
        default='VISIBLE')


types_classes = (
    Pref,
)

classes = (
    BOUT_PT_ShapeObj,
    BOUT_PT_AlignObj,
    BOUT_PT_TypeObj,
)
