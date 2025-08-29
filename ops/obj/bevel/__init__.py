from .pinned import BOUT_OT_ModBevelPinned
from .unpinned import BOUT_OT_ModBevel, BevelModifierItem
from .properties import Theme, SceneBase, ScenePinned, Scene


types_classes = (
    Theme,
    SceneBase,
    ScenePinned,
    Scene,
)


classes = (
    BevelModifierItem,
    BOUT_OT_ModBevelPinned,
    BOUT_OT_ModBevel,
)