"""
Modifier utility functions
"""

import bpy
import os
from .nodes import load_from_file


def add(obj, _name, _type):
    """Add a modifier to the object.

    :param obj: Object to add the modifier to.
    :type obj: bpy.types.Object
    :param _name: Name for the modifier.
    :type _name: str
    :param _type: Modifier type (e.g., 'BOOLEAN', 'BEVEL').
    :type _type: str
    :return: The created modifier, or None if object is not a mesh.
    :rtype: bpy.types.Modifier | None
    """

    if obj and obj.type == "MESH":
        modifier = obj.modifiers.new(name=_name, type=_type)
        modifier.show_expanded = False

        return modifier

    return None


def remove(obj, modifier):
    """Remove a modifier from the object.

    :param obj: Object to remove the modifier from.
    :type obj: bpy.types.Object
    :param modifier: Modifier to remove.
    :type modifier: bpy.types.Modifier
    """

    if obj:
        obj.modifiers.remove(modifier)


def get(obj, _type, _id):
    """Get a modifier from the object based on index position.

    :param obj: Object to get the modifier from.
    :type obj: bpy.types.Object
    :param _type: Modifier type to filter by.
    :type _type: str
    :param _id: Index of the modifier (-1 for last).
    :type _id: int
    :return: The modifier, or None if not found.
    :rtype: bpy.types.Modifier | None
    """

    if obj:
        modifiers = [modifier for modifier in obj.modifiers if modifier.type == _type]

        if modifiers:
            if _id < 0:
                return modifiers[-1]
            else:
                return modifiers[_id]

    return None


def _auto_smooth_file_path():
    """Get the path to the Smooth by Angle asset file.

    Locates smooth_by_angle.blend in Blender's installation directory.

    :return: Full path to the asset file, or None if not found.
    :rtype: str | None
    """
    blender_exe_path = bpy.app.binary_path
    blender_dir = os.path.dirname(blender_exe_path)
    blender_version = ".".join(bpy.app.version_string.split(".")[:2])
    asset_file = os.path.join(
        blender_dir,
        blender_version,
        "datafiles",
        "assets",
        "geometry_nodes",
        "smooth_by_angle.blend",
    )

    if not os.path.exists(asset_file):
        print(f"Asset file not found: {asset_file}")
        return None

    return asset_file


def auto_smooth(obj):
    """Add Smooth by Angle geometry nodes modifier to the object.

    Loads the node group from Blender's assets if not already loaded.
    Skips if the modifier already exists on the object.

    :param obj: Object to add auto smooth to.
    :type obj: bpy.types.Object
    :return: The created modifier, or None if skipped or failed.
    :rtype: bpy.types.NodesModifier | None
    """
    node_group_name = "Smooth by Angle"

    # Check if the node group is already loaded
    node_group = bpy.data.node_groups.get(node_group_name)
    if not node_group:
        # Get the path to the default asset file
        asset_file = _auto_smooth_file_path()
        if not asset_file:
            print("Asset file could not be located.")
            return None

        # Load the node group from the file
        node_group = load_from_file(asset_file, node_group_name)
        if not node_group:
            print(f"Node group '{node_group_name}' could not be loaded.")
            return None

    for modifier in obj.modifiers:
        if modifier.type == "NODES":
            if modifier.node_group:
                if modifier.node_group.name == node_group_name:
                    return None

    modifier = obj.modifiers.new(name=node_group_name, type="NODES")
    modifier.node_group = node_group
    modifier.use_pin_to_last = True
    modifier.show_expanded = False

    return modifier
