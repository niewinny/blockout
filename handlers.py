from .tools.block import custom


def unregister_draw_handlers():
    """Handler to remove draw handlers"""
    custom.remove()


def register():
    pass


def unregister():
    """Unregister handlers and clean up draw handlers"""
    unregister_draw_handlers()
