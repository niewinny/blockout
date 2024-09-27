import bpy

keys = []


def register():

    wm = bpy.context.window_manager
    active_keyconfig = wm.keyconfigs.active
    addon_keyconfig = wm.keyconfigs.addon

    kc = addon_keyconfig

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


    del active_keyconfig
    del addon_keyconfig


def unregister():

    for km, kmi in keys:
        km.keymap_items.remove(kmi)

    keys.clear()
