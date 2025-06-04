
def draw(context, event, func, blank=False):

    def header(self, context):
        if blank:
            infobar_blank(self, context, event, func)
        else:
            infobar_main(self, context, event, func)

    context.workspace.status_text_set(header)


def remove(context):
    context.workspace.status_text_set(None)


def infobar_blank(self, context, event, func):
    layout = self.layout

    if func:
        func(layout, context, event)
    infobar_copiedlines(layout, context)


def infobar_main(self, context, event, func):
    layout = self.layout
    row = self.layout.row(align=True)
    row.label(text='', icon='MOUSE_MOVE')
    row.label(text='Adjust')
    row.separator(factor=8.0)
    row.label(text='', icon='MOUSE_LMB')
    row.label(text='Confirm')
    row.separator(factor=8.0)
    row.label(text='', icon='MOUSE_MMB')
    row.label(text='Rotate View')
    row.separator(factor=8.0)
    row.label(text='', icon='MOUSE_RMB')
    row.label(text='Cancel')
    row.separator(factor=8.0)

    if func:
        func(layout, context, event)

    infobar_copiedlines(layout, context)


def infobar_copiedlines(layout, context):

    layout.separator_spacer()

    # Report Messages
    layout.template_reports_banner()

    layout.separator_spacer()

    row = layout.row()
    row.alignment = 'RIGHT'

    # Stats & Info
    row.label(text=context.screen.statusbar_info(), translate=False)

    # Progress Bar
    row.template_running_jobs()
