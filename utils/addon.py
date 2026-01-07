from pathlib import Path

import bpy
import tomllib

_manifest_path = Path(__file__).parent.parent / "blender_manifest.toml"
with _manifest_path.open("rb") as _f:
    _manifest = tomllib.load(_f)

_package_name = __name__.rsplit(".", 2)[0]

version: str = _manifest["version"]
version_tuple: tuple[int, ...] = tuple(int(x) for x in version.split("."))


def pref():
    return bpy.context.preferences.addons[_package_name].preferences
