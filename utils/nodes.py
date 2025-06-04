import bpy
import os


def load_from_file(filepath, node_group_name):
    """
    Load a node group from a file.
    :param filepath: File path to the .blend file.
    :param node_group_name: Node group name.
    :return: Node group object.
    """
    if not os.path.exists(filepath):
        print(f"File does not exist: {filepath}")
        return None

    with bpy.data.libraries.load(filepath, link=False) as (data_from, data_to):
        if node_group_name in data_from.node_groups:
            data_to.node_groups.append(node_group_name)

    return bpy.data.node_groups.get(node_group_name)
