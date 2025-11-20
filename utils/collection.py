import bpy


def get_or_create_cutters_collection():
    """Get or create the Cutters collection for boolean cutter objects"""
    collection_name = "Cutters"

    # Check if collection already exists
    if collection_name in bpy.data.collections:
        return bpy.data.collections[collection_name]

    # Create new collection
    cutters_collection = bpy.data.collections.new(collection_name)

    # Link to scene collection
    bpy.context.scene.collection.children.link(cutters_collection)

    # Set collection properties for better visualization
    cutters_collection.color_tag = "COLOR_01"  # Red color tag for visibility

    # Unfortunately, Blender's API doesn't provide a direct way to collapse collections
    # in the outliner. Collections will appear expanded by default and users need to
    # manually collapse them. This is a limitation of the current Blender Python API.

    return cutters_collection


def move_to_cutters_collection(obj):
    """Move an object to the Cutters collection"""
    cutters_collection = get_or_create_cutters_collection()

    # Remove from all current collections
    for collection in obj.users_collection:
        collection.objects.unlink(obj)

    # Add to cutters collection
    cutters_collection.objects.link(obj)

    return cutters_collection
