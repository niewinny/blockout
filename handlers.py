from . tools.block import custom


def unregister_draw_handlers():
    '''Handler called after loading a file'''
    custom.remove()


def register_undo_post_handlers():
    '''Handler called after loading a file'''
    custom.register_undo_post()


def unregister_undo_post_handlers():
    '''Handler called after loading a file'''
    custom.unregister_undo_post()


def unregister_redo_post_handlers():
    '''Handler called after loading a file'''
    custom.unregister_redo_post()


def register_redo_post_handlers():
    '''Handler called after loading a file'''
    custom.register_redo_post()


def register():
    register_undo_post_handlers()
    register_redo_post_handlers()


def unregister():
    unregister_undo_post_handlers()
    unregister_redo_post_handlers()
    unregister_draw_handlers()
