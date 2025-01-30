from ...utils import modifier


def add_modifier(bool_obj, obj):
    '''Add the boolean modifier'''
    mod = modifier.add(bool_obj, "Boolean", 'BOOLEAN')
    mod.operation = 'DIFFERENCE'
    mod.solver = 'FAST'
    mod.object = obj
    mod.show_in_editmode = True

    return mod


def clear_modifiers(modifiers):
    '''Clear all boolean modifiers'''
    if not modifiers.booleans:
        return

    for mod in modifiers.booleans:
        modifier.remove(mod.obj, mod.mod)
