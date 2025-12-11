import bpy

from ....utils import modifier
from .base import BevelOperatorBase
from .data import Bevel


class BOUT_OT_ModBevelPinned(BevelOperatorBase):
    """Bevel operator for last pinned modifier"""

    bl_idname = "object.bout_mod_bevel_pinned"
    bl_label = "Bevel Pinned"
    bl_description = "Edit last pinned bevel modifier"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.pin = True

    def _get_header_text(self):
        return "Bevel (Pinned)"

    def _get_modifier_count_text(self):
        """Get modifier count text for display"""
        return "📌"  # Pinned icon

    def _get_scene_properties(self, context):
        """Get scene properties for pinned operator"""
        scene_props = context.scene.bout.ops.obj.bevel.pinned
        self.segments = scene_props.segments
        self.harden_normals = scene_props.harden_normals
        self.angle_limit = scene_props.angle_limit

    def _set_scene_properties(self, context):
        """Set scene properties for pinned operator"""
        scene_props = context.scene.bout.ops.obj.bevel.pinned
        scene_props.segments = self.segments
        scene_props.harden_normals = self.harden_normals
        scene_props.angle_limit = self.angle_limit

    def _setup_bevel(self, selected_objects, active_object):
        for obj in selected_objects:
            mod = modifier.get(obj, "BEVEL", -1)
            if not mod or not mod.use_pin_to_last:
                new = True
                mod = modifier.add(obj, "Bevel", "BEVEL")
                self.width = 0.0
                self._set_bevel_properties(mod)
                mod.use_pin_to_last = True
                mod.miter_outer = "MITER_ARC"

                # Move the modifier to the end of the stack after all other pinned modifiers
                # Find the last pinned modifier position
                last_pinned_index = -1
                for i, m in enumerate(obj.modifiers):
                    if m.use_pin_to_last:
                        last_pinned_index = i

                # If there are other pinned modifiers and our new modifier isn't already at the end
                if (
                    last_pinned_index >= 0
                    and obj.modifiers.find(mod.name) < last_pinned_index
                ):
                    # Move our modifier to the end (after the last pinned modifier)
                    for i in range(obj.modifiers.find(mod.name), last_pinned_index):
                        bpy.ops.object.modifier_move_down(modifier=mod.name)
            else:
                self._get_bevel_properties(mod)
                new = False

            self.bevels.append(Bevel(obj=obj, mod=mod, new=new))
            if obj == active_object:
                self.saved_width = mod.width
