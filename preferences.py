import bpy
from . import btypes
from . import __package__ as base_package


class BOUT_Preference(bpy.types.AddonPreferences):
    bl_idname = base_package

    settings: bpy.props.EnumProperty(
        name='Settings',
        description='Settings to display',
        items=[
            ('OPTIONS', 'Options', ''),
            ('THEME', 'Theme', '')
        ],
        default='OPTIONS'
    )

    theme: bpy.props.PointerProperty(type=btypes.Theme)
    tools: bpy.props.PointerProperty(type=btypes.Tools)

    def draw(self, context):
        layout = self.layout
        column = layout.column(align=True)
        split = column.split(factor=0.2)
        col = split.column(align=True)
        col.prop(self, 'settings', expand=True)
        col = split.column(align=True)
        col.use_property_split = True

        if self.settings == 'OPTIONS':

            col = column.column(align=True)

        elif self.settings == 'THEME':
            flow = col.grid_flow(row_major=False, columns=0, even_columns=True, even_rows=False, align=False)

            theme = context.preferences.addons[base_package].preferences.theme

            self.theme_layout(flow, theme.axis)
            self.theme_layout(flow, theme.ops.obj.bevel)
            self.theme_layout(flow, theme.ops.block)

    def theme_layout(self, layout, theme):
        '''Draw a theme layout'''
        for prop in theme.bl_rna.properties:
            if prop.identifier == 'name' or prop.identifier == 'rna_type':
                continue

            layout.prop(theme, prop.identifier)
        layout.separator()


classes = (
    BOUT_Preference,
)
