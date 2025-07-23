from ...utils import modifier, addon


def add_modifier(bool_obj, obj, operation='DIFFERENCE'):
    '''Add the boolean modifier'''
    mod = modifier.add(bool_obj, "Boolean", 'BOOLEAN')
    mod.operation = operation
    mod.solver = addon.pref().tools.block.align.solver
    mod.object = obj
    mod.show_in_editmode = True

    return mod


def clear_modifiers(modifiers):
    '''Clear all boolean modifiers'''
    if not modifiers.booleans:
        return

    for mod in modifiers.booleans:
        modifier.remove(mod.obj, mod.mod)
