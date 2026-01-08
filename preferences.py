import bpy
from . import btypes
from . import __package__ as base_package


LINKS = [
    ("Support Development", "https://superhivemarket.com/creators/ezelar", "FUND"),
    ("Report Issues", "https://github.com/niewinny/blockout", "URL"),
    ("Documentation", "https://blockout.ezelar.com", "HELP"),
    ("Twitter", "https://twitter.com/_arutkowski", "X"),
]


class BOUT_OT_OpenURL(bpy.types.Operator):
    bl_idname = "bout.open_url"
    bl_label = "Open URL"
    bl_description = "Open URL in browser"

    url: bpy.props.StringProperty()

    def execute(self, context):
        import webbrowser
        webbrowser.open(self.url)
        return {"FINISHED"}


class BOUT_Preference(bpy.types.AddonPreferences):
    bl_idname = base_package

    settings: bpy.props.EnumProperty(
        name="Settings",
        description="Settings to display",
        items=[
            ("INFO", "Info", ""),
            ("THEME", "Theme", ""),
            ("DEBUG", "Debug", ""),
        ],
        default="INFO",
    )

    debug: bpy.props.BoolProperty(
        name="Debug",
        description="Enable debug mode",
        default=False,
    )

    theme: bpy.props.PointerProperty(type=btypes.Theme)
    tools: bpy.props.PointerProperty(type=btypes.Tools)

    def draw(self, context):
        layout = self.layout
        column = layout.column(align=True)
        split = column.split(factor=0.2)
        col = split.column(align=True)
        col.prop(self, "settings", expand=True)
        col = split.column(align=True)
        col.use_property_split = True

        if self.settings == "INFO":
            self.draw_info(col)

        elif self.settings == "THEME":
            flow = col.grid_flow(
                row_major=False,
                columns=0,
                even_columns=True,
                even_rows=False,
                align=False,
            )

            theme = context.preferences.addons[base_package].preferences.theme

            self.theme_layout(flow, theme.axis)
            self.theme_layout(flow, theme.ops.obj.bevel)
            self.theme_layout(flow, theme.ops.block)

        elif self.settings == "DEBUG":
            col.prop(self, "debug")

    def draw_info(self, layout):
        box = layout.box()
        col = box.column(align=True)

        row = col.row()
        row.alignment = "CENTER"
        row.scale_y = 2.0
        row.label(text="BLOCKOUT")

        col.separator()
        for label, url, icon in LINKS:
            op = col.operator("bout.open_url", text=label, icon=icon)
            op.url = url

    def theme_layout(self, layout, theme):
        """Draw a theme layout"""
        for prop in theme.bl_rna.properties:
            if prop.identifier == "name" or prop.identifier == "rna_type":
                continue

            layout.prop(theme, prop.identifier)
        layout.separator()


classes = (BOUT_OT_OpenURL, BOUT_Preference)
