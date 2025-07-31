from . tools.block import custom


def unregister_draw_handlers():
    '''Handler to remove draw handlers'''
    custom.remove()


def register_undo_post_handlers():
    '''Register handler for undo operations'''
    custom.register_undo_post()


def unregister_undo_post_handlers():
    '''Unregister handler for undo operations'''
    custom.unregister_undo_post()


def unregister_redo_post_handlers():
    '''Unregister handler for redo operations'''
    custom.unregister_redo_post()


def register_redo_post_handlers():
    '''Register handler for redo operations'''
    custom.register_redo_post()


def register():
    register_undo_post_handlers()
    register_redo_post_handlers()


def unregister():
    unregister_undo_post_handlers()
    unregister_redo_post_handlers()
    unregister_draw_handlers()
