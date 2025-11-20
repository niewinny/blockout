from ...utils import modifier


def add_modifier(obj, merge_threshold=0.001, type="FILL"):
    """Add the bevel modifier"""
    mod = modifier.add(obj, "Weld", "WELD")
    mod.merge_threshold = merge_threshold

    return mod, type
