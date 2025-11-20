import bpy
from ....utils import modifier
from .base import BevelOperatorBase
from .data import Bevel


class BevelModifierItem(bpy.types.PropertyGroup):
    """Stores data for each edited modifier in redo panel"""

    obj_name: bpy.props.StringProperty(name="Object Name")
    mod_name: bpy.props.StringProperty(name="Modifier Name")
    mod_index: bpy.props.IntProperty(name="Modifier Index")
    was_created: bpy.props.BoolProperty(
        name="Was Created",
        description="Whether this modifier was created by the operator",
    )

    # Store all bevel properties
    width: bpy.props.FloatProperty(name="Width", precision=3, min=0)
    segments: bpy.props.IntProperty(name="Segments", default=1, min=1, max=32)
    harden_normals: bpy.props.BoolProperty(name="Harden Normals")
    limit_method: bpy.props.StringProperty(name="Limit Method")
    angle_limit: bpy.props.FloatProperty(name="Angle Limit", subtype="ANGLE")
    edge_weight: bpy.props.StringProperty(name="Edge Weight")
    use_clamp_overlap: bpy.props.BoolProperty(name="Clamp Overlap")
    loop_slide: bpy.props.BoolProperty(name="Loop Slide")


def update_selected_modifier(self, context):
    """Update operator properties when a different modifier is selected"""
    # Save the previous modifier's state before switching
    if hasattr(self, "_previous_index") and 0 <= self._previous_index < len(
        self.edited_modifiers
    ):
        prev_item = self.edited_modifiers[self._previous_index]
        # Save current operator values to previous item
        prev_item.width = self.width
        prev_item.segments = self.segments
        prev_item.harden_normals = self.harden_normals
        prev_item.limit_method = self.limit_method
        prev_item.angle_limit = self.angle_limit
        prev_item.edge_weight = self.edge_weight
        prev_item.use_clamp_overlap = self.use_clamp_overlap
        prev_item.loop_slide = self.loop_slide

    # Load the newly selected modifier's properties
    if 0 <= self.selected_modifier_index < len(self.edited_modifiers):
        item = self.edited_modifiers[self.selected_modifier_index]

        # Update operator properties to match selected modifier
        self.width = item.width
        self.segments = item.segments
        self.harden_normals = item.harden_normals
        self.limit_method = item.limit_method
        self.angle_limit = item.angle_limit
        self.edge_weight = item.edge_weight
        self.use_clamp_overlap = item.use_clamp_overlap
        self.loop_slide = item.loop_slide

    # Remember current index for next switch
    self._previous_index = self.selected_modifier_index


class BOUT_OT_ModBevel(BevelOperatorBase):
    """Unified bevel operator for unpinned modifiers"""

    bl_idname = "object.bout_mod_bevel"
    bl_label = "Bevel"
    bl_description = "Edit unpinned bevel modifiers"

    all_mode: bpy.props.BoolProperty(
        name="All Mode",
        description="Edit all unpinned modifiers at once",
        default=False,
    )
    current_index: bpy.props.IntProperty(default=0)
    unpinned_count: bpy.props.IntProperty(default=0)

    # Collection for redo panel
    edited_modifiers: bpy.props.CollectionProperty(type=BevelModifierItem)
    selected_modifier_index: bpy.props.IntProperty(
        name="Selected Modifier",
        description="Index of selected modifier in redo panel",
        default=0,
        update=update_selected_modifier,
    )

    def execute(self, context):
        """Override execute to handle mode-specific behavior"""
        # Check if this is a redo operation (collection has items)
        if self.edited_modifiers:
            # First save the current modifier state if we have a valid selection
            if 0 <= self.selected_modifier_index < len(self.edited_modifiers):
                current_item = self.edited_modifiers[self.selected_modifier_index]
                # Update the collection item with current operator values
                current_item.width = self.width
                current_item.segments = self.segments
                current_item.harden_normals = self.harden_normals
                current_item.limit_method = self.limit_method
                current_item.angle_limit = self.angle_limit
                current_item.edge_weight = self.edge_weight
                current_item.use_clamp_overlap = self.use_clamp_overlap
                current_item.loop_slide = self.loop_slide

            # Apply all modifier states from the collection
            for item in self.edited_modifiers:
                # Find the object
                obj = bpy.data.objects.get(item.obj_name)
                if not obj:
                    continue

                # Check if modifier exists
                mod = None
                if item.mod_name in obj.modifiers:
                    mod = obj.modifiers[item.mod_name]
                elif item.was_created:
                    # Modifier was created by operator but doesn't exist now - recreate it
                    mod = modifier.add(obj, item.mod_name, "BEVEL")
                    mod.miter_outer = "MITER_ARC"

                if mod:
                    # Apply the stored properties to the modifier
                    mod.width = item.width
                    mod.segments = item.segments
                    mod.harden_normals = item.harden_normals
                    mod.limit_method = item.limit_method
                    mod.angle_limit = item.angle_limit
                    mod.edge_weight = item.edge_weight
                    mod.use_clamp_overlap = item.use_clamp_overlap
                    mod.loop_slide = item.loop_slide

            self._set_scene_properties(context)
            return {"FINISHED"}

        # Normal execute (not redo) - handle non-modal execution
        active_object = (
            context.active_object
            if context.active_object and context.active_object.select_get()
            else None
        )
        selected_objects = list(
            set(filter(None, context.selected_objects + [active_object]))
        )

        # Check if coming from modal (has bevels)
        if hasattr(self, "bevels") and self.bevels:
            if self.all_mode:
                # All mode - update all modifiers
                self._update_bevel(selected_objects)
            else:
                # Single mode - only update the current modifier
                for b in self.bevels:
                    self._set_bevel_properties(b.mod)
        else:
            # Direct execution - track existing modifiers first
            existing_modifiers = set()
            for obj in selected_objects:
                for mod in obj.modifiers:
                    if mod.type == "BEVEL" and not mod.use_pin_to_last:
                        existing_modifiers.add((obj.name, mod.name))

            # Create/update modifiers
            self._update_bevel(selected_objects)

            # Populate edited_modifiers for redo panel
            self.edited_modifiers.clear()
            for obj in selected_objects:
                for mod in obj.modifiers:
                    if mod.type == "BEVEL" and not mod.use_pin_to_last:
                        item = self.edited_modifiers.add()
                        item.obj_name = obj.name
                        item.mod_name = mod.name
                        item.mod_index = list(obj.modifiers).index(mod)
                        item.was_created = (
                            obj.name,
                            mod.name,
                        ) not in existing_modifiers

                        # Copy all properties from modifier
                        item.width = mod.width
                        item.segments = mod.segments
                        item.harden_normals = mod.harden_normals
                        item.limit_method = mod.limit_method
                        item.angle_limit = mod.angle_limit
                        item.edge_weight = mod.edge_weight
                        item.use_clamp_overlap = mod.use_clamp_overlap
                        item.loop_slide = mod.loop_slide

                        # Set name for display in list
                        item.name = f"{obj.name}: {mod.name}"

            # Initialize the previous index for state tracking
            if self.edited_modifiers:
                self._previous_index = 0

        self._set_scene_properties(context)
        return {"FINISHED"}

    def _get_header_text(self):
        mode_text = "All" if self.all_mode else "Single"
        return f"Bevel {mode_text}"

    def _setup_bevel(self, selected_objects, active_object, target_index=None):
        self.bevels.clear()  # Clear any existing bevels

        if self.all_mode:
            # All mode - work with all selected objects
            # Process active object first with modifiers in reverse order
            if active_object and active_object.type == "MESH":
                unpinned_bevels = [
                    m
                    for m in active_object.modifiers
                    if m.type == "BEVEL" and not m.use_pin_to_last
                ]

                # Add in reverse order (last modifier first)
                for mod in reversed(unpinned_bevels):
                    # Store initial width for relative adjustment
                    self.bevels.append(
                        Bevel(
                            obj=active_object,
                            mod=mod,
                            new=False,
                            initial_width=mod.width,
                        )
                    )

            # Process other objects with modifiers in reverse order
            for obj in selected_objects:
                if obj != active_object and obj.type == "MESH":
                    unpinned_bevels = [
                        m
                        for m in obj.modifiers
                        if m.type == "BEVEL" and not m.use_pin_to_last
                    ]

                    # Add in reverse order (last modifier first)
                    for mod in reversed(unpinned_bevels):
                        # Store initial width for relative adjustment
                        self.bevels.append(
                            Bevel(obj=obj, mod=mod, new=False, initial_width=mod.width)
                        )

            if self.bevels:
                # Start with first modifier (which is last modifier of active object)
                self.current_index = 0
                self._get_bevel_properties(self.bevels[0].mod)
                self.saved_width = self.bevels[0].mod.width
            else:
                # No unpinned modifiers found - create new ones
                # Process non-active objects first
                for obj in selected_objects:
                    if obj != active_object and obj.type == "MESH":
                        mod = modifier.add(obj, "Bevel", "BEVEL")
                        mod.miter_outer = "MITER_ARC"
                        self.bevels.append(
                            Bevel(obj=obj, mod=mod, new=True, initial_width=0.0)
                        )

                # Process active object last
                if active_object and active_object.type == "MESH":
                    mod = modifier.add(active_object, "Bevel", "BEVEL")
                    mod.miter_outer = "MITER_ARC"
                    self.bevels.append(
                        Bevel(obj=active_object, mod=mod, new=True, initial_width=0.0)
                    )

                if self.bevels:
                    self.width = 0.0
                    # Apply operator properties to ALL newly created modifiers
                    for bevel in self.bevels:
                        if bevel.new:
                            self._set_bevel_properties(bevel.mod)
                    self.saved_width = 0.0

            self.unpinned_count = len(self.bevels)
        else:
            # Single mode - work with all selected objects but edit one at a time
            # Process active object first with modifiers in reverse order
            if active_object and active_object.type == "MESH":
                unpinned_bevels = [
                    m
                    for m in active_object.modifiers
                    if m.type == "BEVEL" and not m.use_pin_to_last
                ]

                # Add in reverse order (last modifier first)
                for mod in reversed(unpinned_bevels):
                    self.bevels.append(Bevel(obj=active_object, mod=mod, new=False))

            # Process other objects with modifiers in reverse order
            for obj in selected_objects:
                if obj != active_object and obj.type == "MESH":
                    unpinned_bevels = [
                        m
                        for m in obj.modifiers
                        if m.type == "BEVEL" and not m.use_pin_to_last
                    ]

                    # Add in reverse order (last modifier first)
                    for mod in reversed(unpinned_bevels):
                        self.bevels.append(Bevel(obj=obj, mod=mod, new=False))

            if self.bevels:
                # Use target_index if provided, otherwise start with first modifier
                if target_index is not None and 0 <= target_index < len(self.bevels):
                    self.current_index = target_index
                else:
                    self.current_index = 0

                current_bevel = self.bevels[self.current_index]
                self._get_bevel_properties(current_bevel.mod)
                self.saved_width = current_bevel.mod.width
            else:
                # No unpinned modifiers found - create new one on active object
                if active_object and active_object.type == "MESH":
                    mod = modifier.add(active_object, "Bevel", "BEVEL")
                    mod.miter_outer = "MITER_ARC"
                    self.width = 0.0
                    self._set_bevel_properties(mod)
                    self.bevels.append(Bevel(obj=active_object, mod=mod, new=True))
                    self.saved_width = 0.0
                    self.current_index = 0

            self.unpinned_count = len(self.bevels)

    def _get_modifier_count_text(self):
        """Get modifier count text for display"""
        if self.unpinned_count > 0:
            if self.all_mode:
                return f"All({self.current_index + 1})"
            else:
                return f"{self.unpinned_count}({self.current_index + 1})"
        return None

    def _navigate_modifier(self, direction):
        """Navigate between modifiers"""
        if not self.bevels:
            return

        if self.all_mode:
            # All mode - just navigate for display
            if direction == "NEXT":
                self.current_index = (self.current_index + 1) % len(self.bevels)
            else:
                self.current_index = (self.current_index - 1) % len(self.bevels)

            # Update display to show current modifier's properties
            if self.current_index < len(self.bevels):
                current_bevel = self.bevels[self.current_index]
                self.width = current_bevel.mod.width
                self.segments = current_bevel.mod.segments
        else:
            # Single mode - navigate through all modifiers across all objects
            if direction == "NEXT":
                self.current_index = (self.current_index + 1) % len(self.bevels)
            else:
                self.current_index = (self.current_index - 1) % len(self.bevels)

            # Update to new modifier
            current_bevel = self.bevels[self.current_index]
            self._get_bevel_properties(current_bevel.mod)

            # Calculate what saved_width should be so current mouse position = new modifier's width
            # Formula: new_mod.width = (distance + saved_width) - distance.delta
            # Rearranged: saved_width = new_mod.width + distance.delta - distance
            current_distance = self._calculate_distance()
            self.saved_width = (
                current_bevel.mod.width + self.distance.delta - current_distance
            )

    def _set_width(self):
        """Set the width based on mode"""
        if self.all_mode:
            # All mode - relative adjustment for each modifier
            distance = self._calculate_distance()

            if self.precision:
                delta_distance = distance - self.distance.precision
                distance = self.distance.precision + (delta_distance * 0.1)

            # Calculate the adjustment amount
            adjustment = distance - self.distance.delta

            # Apply relative changes to each modifier with individual snapping
            for bevel in self.bevels:
                new_width = bevel.initial_width + adjustment

                # Apply snapping if Ctrl is held - snap each modifier's width individually
                if self.snapping_ctrl:
                    if self.precision:  # Both Shift and Ctrl held - snap to 0.01
                        new_width = round(new_width / 0.01) * 0.01
                    else:  # Only Ctrl held - snap to 0.1
                        new_width = round(new_width / 0.1) * 0.1

                bevel.mod.width = max(0.0, new_width)

            # Update display width to show current modifier's actual width
            if self.current_index < len(self.bevels):
                self.width = self.bevels[self.current_index].mod.width
            else:
                self.width = adjustment
        else:
            # Single mode - only edit current modifier
            distance = self._calculate_distance()

            if self.precision:
                delta_distance = distance - self.distance.precision
                distance = self.distance.precision + (delta_distance * 0.1)

            distance += self.saved_width
            distance = (
                distance if distance > self.distance.delta else self.distance.delta
            )
            offset = distance - self.distance.delta

            # Apply snapping if Ctrl is held
            if self.snapping_ctrl:
                if self.precision:  # Both Shift and Ctrl held - snap to 0.01
                    offset = round(offset / 0.01) * 0.01
                else:  # Only Ctrl held - snap to 0.1
                    offset = round(offset / 0.1) * 0.1

            self.width = offset
            # Only update the current modifier in single mode
            if self.current_index < len(self.bevels):
                self.bevels[self.current_index].mod.width = offset

    def modal(self, context, event):
        # Check for finish events to store modifiers before completing
        if event.type == "LEFTMOUSE":
            self._store_edited_modifiers()
            return super().modal(context, event)

        elif event.type in {"RET", "NUMPAD_ENTER", "SPACE"} and event.value == "PRESS":
            self._store_edited_modifiers()
            return super().modal(context, event)

        # Handle segments and harden normals for mode-specific behavior
        elif event.type == "N" and event.value == "PRESS":
            self.harden_normals = not self.harden_normals
            if self.all_mode:
                # All mode - update all modifiers
                for b in self.bevels:
                    b.mod.harden_normals = self.harden_normals
            else:
                # Single mode - only update current modifier
                if self.current_index < len(self.bevels):
                    self.bevels[
                        self.current_index
                    ].mod.harden_normals = self.harden_normals
            return {"RUNNING_MODAL"}

        elif event.type == "L" and event.value == "PRESS":
            # Cycle through limit methods
            limit_methods = ["NONE", "ANGLE", "WEIGHT", "VGROUP"]
            current_index = limit_methods.index(self.limit_method)
            self.limit_method = limit_methods[(current_index + 1) % len(limit_methods)]

            if self.all_mode:
                # All mode - update all modifiers
                for b in self.bevels:
                    b.mod.limit_method = self.limit_method
            else:
                # Single mode - only update current modifier
                if self.current_index < len(self.bevels):
                    self.bevels[self.current_index].mod.limit_method = self.limit_method

            self._update_info(context)
            self._update_drawing(context)
            return {"RUNNING_MODAL"}

        elif (
            event.type == "WHEELUPMOUSE"
            or event.type == "NUMPAD_PLUS"
            or event.type == "EQUAL"
        ):
            if event.value == "PRESS":
                self.segments += 1
                if self.all_mode:
                    # All mode - update all modifiers
                    for b in self.bevels:
                        b.mod.segments = self.segments
                else:
                    # Single mode - only update current modifier
                    if self.current_index < len(self.bevels):
                        self.bevels[self.current_index].mod.segments = self.segments
                self._update_info(context)
                self._update_drawing(context)
                return {"RUNNING_MODAL"}

        elif (
            event.type == "WHEELDOWNMOUSE"
            or event.type == "NUMPAD_MINUS"
            or event.type == "MINUS"
        ):
            if event.value == "PRESS":
                self.segments -= 1
                if self.all_mode:
                    # All mode - update all modifiers
                    for b in self.bevels:
                        b.mod.segments = self.segments
                else:
                    # Single mode - only update current modifier
                    if self.current_index < len(self.bevels):
                        self.bevels[self.current_index].mod.segments = self.segments
                self._update_info(context)
                self._update_drawing(context)
                return {"RUNNING_MODAL"}

        elif event.type == "UP_ARROW" and event.value == "PRESS":
            # Increase angle limit if in ANGLE mode
            if self.limit_method == "ANGLE":
                self.angle_limit = min(
                    self.angle_limit + 0.0174533, 3.14159
                )  # +1 degree
                if self.all_mode:
                    # All mode - update all modifiers
                    for b in self.bevels:
                        b.mod.angle_limit = self.angle_limit
                else:
                    # Single mode - only update current modifier
                    if self.current_index < len(self.bevels):
                        self.bevels[
                            self.current_index
                        ].mod.angle_limit = self.angle_limit
                self._update_info(context)
                self._update_drawing(context)
                return {"RUNNING_MODAL"}

        elif event.type == "DOWN_ARROW" and event.value == "PRESS":
            # Decrease angle limit if in ANGLE mode
            if self.limit_method == "ANGLE":
                self.angle_limit = max(self.angle_limit - 0.0174533, 0.0)  # -1 degree
                if self.all_mode:
                    # All mode - update all modifiers
                    for b in self.bevels:
                        b.mod.angle_limit = self.angle_limit
                else:
                    # Single mode - only update current modifier
                    if self.current_index < len(self.bevels):
                        self.bevels[
                            self.current_index
                        ].mod.angle_limit = self.angle_limit
                self._update_info(context)
                self._update_drawing(context)
                return {"RUNNING_MODAL"}

        # Handle mode toggle
        elif event.type == "G" and event.value == "PRESS":
            # Store current state before switching
            old_index = self.current_index
            old_bevels = self.bevels[:] if self.bevels else []
            was_all_mode = self.all_mode

            # Toggle mode
            self.all_mode = not self.all_mode

            # Re-setup with new mode
            active_object = (
                context.active_object
                if context.active_object and context.active_object.select_get()
                else None
            )
            selected_objects = list(
                set(filter(None, context.selected_objects + [active_object]))
            )

            # Determine target index for Single mode if switching to it
            target_index = None
            if not self.all_mode and was_all_mode and old_index < len(old_bevels):
                # Switching to Single mode - use the same index from All mode
                # since both modes now use the same list structure
                target_index = old_index

            self._setup_bevel(selected_objects, active_object, target_index)

            # Reset distance calculation after mode switch for both modes
            current_distance = self._calculate_distance()

            if self.bevels:
                if self.all_mode:
                    # Switching to All mode - keep same index since both modes use same list
                    self.current_index = (
                        min(old_index, len(self.bevels) - 1)
                        if self.bevels and old_index > 0
                        else 0
                    )

                    # Reset distance.delta so current mouse position = 0 adjustment from current state
                    self.distance.delta = current_distance
                else:
                    # Switching to Single mode - reset saved_width to match current modifier
                    if self.bevels and self.current_index < len(self.bevels):
                        current_mod = self.bevels[self.current_index].mod
                        self.saved_width = (
                            current_mod.width + self.distance.delta - current_distance
                        )

            # Update display
            self._update_info(context)
            self._update_drawing(context)
            return {"RUNNING_MODAL"}

        # Handle navigation
        if event.type == "TAB" and event.value == "PRESS":
            if self.unpinned_count > 1:
                if event.shift:
                    self._navigate_modifier("PREVIOUS")
                else:
                    self._navigate_modifier("NEXT")
                self._update_info(context)
                self._update_drawing(context)
                return {"RUNNING_MODAL"}

        # Call parent modal
        return super().modal(context, event)

    def _store_edited_modifiers(self):
        """Store all edited modifiers in collection for redo panel"""
        self.edited_modifiers.clear()

        for bevel in self.bevels:
            item = self.edited_modifiers.add()
            item.obj_name = bevel.obj.name
            item.mod_name = bevel.mod.name
            item.mod_index = list(bevel.obj.modifiers).index(bevel.mod)
            item.was_created = (
                bevel.new
            )  # Track if this modifier was created by the operator

            # Copy all properties from modifier
            item.width = bevel.mod.width
            item.segments = bevel.mod.segments
            item.harden_normals = bevel.mod.harden_normals
            item.limit_method = bevel.mod.limit_method
            item.angle_limit = bevel.mod.angle_limit
            item.edge_weight = bevel.mod.edge_weight
            item.use_clamp_overlap = bevel.mod.use_clamp_overlap
            item.loop_slide = bevel.mod.loop_slide

            # Set name for display in list
            item.name = f"{bevel.obj.name}: {bevel.mod.name}"

        # Initialize the previous index for state tracking
        self._previous_index = self.selected_modifier_index

    def draw(self, context):
        """Draw the operator UI with modifier list for redo panel"""
        layout = self.layout

        # If we have edited modifiers, show the list
        if self.edited_modifiers:
            # Create a box for the modifier list
            box = layout.box()
            box.label(text="Select Modifier to Edit:", icon="MODIFIER")

            # Show the list of modifiers
            row = box.row()
            row.template_list(
                "UI_UL_list",
                "bevel_modifiers_list",
                self,
                "edited_modifiers",
                self,
                "selected_modifier_index",
                rows=3,
                maxrows=6,
            )

        layout.separator()

        # Show standard properties from parent
        super().draw(context)

    def _infobar_hotkeys(self, layout, _context, _event):
        """Draw the infobar hotkeys"""
        super()._infobar_hotkeys(layout, _context, _event)

        row = layout.row(align=True)
        row.separator(factor=6.0)
        row.label(text="", icon="EVENT_G")
        row.label(text="Toggle Mode")

        if self.unpinned_count > 1:
            row.separator(factor=6.0)
            row.label(text="", icon="EVENT_TAB")
            row.label(text="Next/Previous")
