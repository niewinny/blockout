from pathlib import Path

import bpy
import tomllib

from .. import __package__ as _package_name

_manifest_path = Path(__file__).parent.parent / "blender_manifest.toml"
with _manifest_path.open("rb") as _f:
    _manifest = tomllib.load(_f)

version: str = _manifest["version"]
version_tuple: tuple[int, ...] = tuple(int(x) for x in version.split("."))


def pref():
    prefs = bpy.context.preferences
    if not prefs or not _package_name:
        raise RuntimeError("Preferences not available")
    return prefs.addons[_package_name].preferences
