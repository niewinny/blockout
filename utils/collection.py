"""Blender collection management utilities.

Functions for creating, retrieving, and managing collections in Blender scenes.
"""

import bpy


def get(name):
    """Get a collection by name.

    :param name: The collection name to search for.
    :type name: str
    :return: The collection if found, None otherwise.
    :rtype: bpy.types.Collection | None
    """
    return bpy.data.collections.get(name)


def create(name, color_tag="COLOR_01"):
    """Create a new collection and link it to the active scene.

    :param name: The name for the new collection.
    :type name: str
    :param color_tag: The color tag for the collection.
    :type color_tag: str
    :return: The newly created collection.
    :rtype: bpy.types.Collection
    """
    coll = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(coll)
    coll.color_tag = color_tag
    return coll


def append(objs, name, color_tag="COLOR_01"):
    """Move objects to a collection, creating it if needed.

    Unlinks objects from their current collections before linking to the target.

    :param objs: Iterable of objects to move.
    :type objs: Iterable[bpy.types.Object]
    :param name: The target collection name.
    :type name: str
    :param color_tag: Color tag if collection is created.
    :type color_tag: str
    :return: The target collection.
    :rtype: bpy.types.Collection
    """
    coll = get(name) or create(name, color_tag)

    for obj in objs:
        for c in obj.users_collection:
            c.objects.unlink(obj)
        coll.objects.link(obj)

    return coll
