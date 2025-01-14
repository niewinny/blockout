"""
Modifier utility functions
"""


def add(obj, _name, _type):
    """
    Add a modifier to the object
    :param obj: Object to add the modifier to
    :param type: Modifier type
    :return: Modifier object
    """

    if obj and obj.type == 'MESH':
        modifier = obj.modifiers.new(name=_name, type=_type)

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
