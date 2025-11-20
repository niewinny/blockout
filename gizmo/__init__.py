"""This module is a collection of gizmos for Addon"""

import bpy
from . import group
from . import types


classes = (
    *types.classes,
    *group.classes,
)
