import bpy

keys = []


def edit_mesh_hotkeys(kc):
    '''Edit Mesh Hotkeys'''

    km = kc.keymaps.new(name='Mesh', space_type='EMPTY')
    kmi = km.keymap_items.new('wm.call_menu', 'THREE', 'PRESS', alt=True)
    kmi.properties.name = 'BOUT_MT_Edit_Mesh'
    keys.append((km, kmi))

    km = kc.keymaps.new(name='Mesh', space_type='EMPTY')
    kmi = km.keymap_items.new('bout.loop_bisect', 'R', 'PRESS', alt=True)
    keys.append((km, kmi))

    km = kc.keymaps.new(name='Mesh', space_type='EMPTY')
    kmi = km.keymap_items.new('bout.edge_expand', 'E', 'PRESS', alt=True, shift=True)
    keys.append((km, kmi))

    km = kc.keymaps.new(name='Mesh', space_type='EMPTY')
    kmi = km.keymap_items.new('bout.set_active_tool', 'W', 'PRESS', alt=True, shift=True)
    keys.append((km, kmi))


def object_mode_hotkeys(kc):
    '''Object Mode Hotkeys'''

    km = kc.keymaps.new(name='Object Mode', space_type='EMPTY')
    kmi = km.keymap_items.new('bout.mod_boolean', 'MINUS', 'PRESS', alt=True)
    kmi.properties.operation = 'DIFFERENCE'
    keys.append((km, kmi))


def register():
    '''Register Keymaps'''

    wm = bpy.context.window_manager
    active_keyconfig = wm.keyconfigs.active
    addon_keyconfig = wm.keyconfigs.addon

    kc = addon_keyconfig

    edit_mesh_hotkeys(kc)
    object_mode_hotkeys(kc)

    del active_keyconfig
    del addon_keyconfig


def unregister():
    '''Unregister Keymaps'''

    for km, kmi in keys:
        km.keymap_items.remove(kmi)

    keys.clear()
