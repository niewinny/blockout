"""
Modifier utility functions
"""

import bpy
import os
from .nodes import load_from_file


def add(obj, _name, _type):
    """
    Add a modifier to the object
    :param obj: Object to add the modifier to
    :param type: Modifier type
    :return: Modifier object
    """

    if obj and obj.type == 'MESH':
        modifier = obj.modifiers.new(name=_name, type=_type)
        modifier.show_expanded = False

        return modifier

    return None


def remove(obj, modifier):
    """
    Remove a modifier from the object
    :param obj: Object to remove the modifier from
    :param modifier: Modifier to remove
    """

    if obj:
        obj.modifiers.remove(modifier)


def get(obj, _type, _id):
    """
    Get a modifier from the object based on id position
    :param obj: Object to get the modifier from
    :param type: Modifier type
    :param id: Modifier id
    :return: Modifier object
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
    """
    Get the path to the default asset file (smooth_by_angle.blend) based on Blender's installation directory.
    :return: Full path to the asset file.
    """
    blender_exe_path = bpy.app.binary_path
    blender_dir = os.path.dirname(blender_exe_path)
    asset_file = os.path.join(blender_dir, "4.4", "datafiles", "assets", "geometry_nodes", "smooth_by_angle.blend")

    if not os.path.exists(asset_file):
        print(f"Asset file not found: {asset_file}")
        return None

    return asset_file


def auto_smooth(obj):
    """
    Set auto smooth on the object.
    :param obj: Object to set auto smooth on.
    :return: Modifier object
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
        if modifier.type == 'NODES':
            if modifier.node_group:
                if modifier.node_group.name == node_group_name:
                    return None

    modifier = obj.modifiers.new(name=node_group_name, type='NODES')
    modifier.node_group = node_group
    modifier.use_pin_to_last = True
    modifier.show_expanded = False

    return modifier
