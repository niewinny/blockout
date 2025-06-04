from . import menus
from . import popups


classes = (
    *menus.classes,
    *popups.classes,
)


def register():
    menus.register()


def unregister():
    menus.unregister()
