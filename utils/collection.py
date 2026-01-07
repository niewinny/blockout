import bpy


def get(name):
    """Get a collection by name, or None if not found"""
    return bpy.data.collections.get(name)


def create(name, color_tag="COLOR_01"):
    """Create a new collection and link to scene"""
    coll = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(coll)
    coll.color_tag = color_tag
    return coll


def append(objs, name, color_tag="COLOR_01"):
    """Append objects to a collection, creating if needed"""
    coll = get(name) or create(name, color_tag)

    for obj in objs:
        for c in obj.users_collection:
            c.objects.unlink(obj)
        coll.objects.link(obj)

    return coll
