from pathlib import Path

import tomllib

from . import (
    btypes,
    gizmo,
    ops,
    preferences,
    registry,
    tools,
    ui,
    utils,
)

_manifest_path = Path(__file__).parent / "blender_manifest.toml"
with _manifest_path.open("rb") as _f:
    _manifest = tomllib.load(_f)

__version__ = _manifest["version"]
__version_tuple__ = tuple(int(x) for x in __version__.split("."))

__all__ = ["btypes", "gizmo", "ops", "preferences", "registry", "tools", "ui", "utils"]


def register():
    registry.register()


def unregister():
    registry.unregister()
