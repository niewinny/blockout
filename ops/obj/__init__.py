import bpy

from . import block
from . import custom_plane


classes = (
    *block.classes,
    *custom_plane.classes,
)
