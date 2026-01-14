"""Node group loading utilities.

Provides functions for loading node groups from external .blend files.
"""

import bpy
import os


def load_from_file(filepath, node_group_name):
    """Load a node group from a .blend file.

    :param filepath: File path to the .blend file.
    :type filepath: str
    :param node_group_name: Name of the node group to load.
    :type node_group_name: str
    :return: The loaded node group, or None if not found.
    :rtype: bpy.types.NodeTree | None
    """
    if not os.path.exists(filepath):
        print(f"File does not exist: {filepath}")
        return None

    with bpy.data.libraries.load(filepath, link=False) as (data_from, data_to):
        if node_group_name in data_from.node_groups:
            data_to.node_groups.append(node_group_name)

    return bpy.data.node_groups.get(node_group_name)
