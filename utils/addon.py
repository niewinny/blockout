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
    return bpy.context.preferences.addons[_package_name].preferences
