import bpy
from bpy.props import BoolProperty, CollectionProperty, StringProperty, IntProperty
from bpy.types import Operator, PropertyGroup, UIList


class BOUT_PT_ApplyModifiersObjectItem(PropertyGroup):
    """Property group for object items in the list"""

    obj_name: StringProperty(name="Object Name")
    modifier_count: IntProperty(name="Modifier Count", default=0)


class BOUT_UL_ApplyModifiersObjectList(UIList):
    """UIList for displaying objects with modifiers"""

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            layout.label(text=item.obj_name, icon='OBJECT_DATA')
            layout.label(text=f"({item.modifier_count})")
        elif self.layout_type in {'GRID'}:
            layout.alignment = 'CENTER'
            layout.label(text="", icon='OBJECT_DATA')


class BOUT_PT_ApplyModifiersItem(PropertyGroup):
    """Property group for individual modifier items"""

    modifier_name: StringProperty(name="Modifier Name")
    modifier_type: StringProperty(name="Modifier Type")
    obj_name: StringProperty(name="Object Name")
    apply: BoolProperty(name="Apply", default=True)
    group_index: IntProperty(name="Group Index", default=0)


class BOUT_PT_ApplyModifiersGroup(PropertyGroup):
    """Property group for modifier groups"""

    enabled: BoolProperty(name="Enabled", default=True)
    show_expanded: BoolProperty(name="Show Expanded", default=True)
    obj_name: StringProperty(name="Object Name")  # Add object name to groups


class BOUT_OT_ApplyModifiers(Operator):
    bl_idname = "bout.apply_modifiers"
    bl_label = "Apply Modifiers"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = "Apply modifiers with grouping and selective application"

    modifier_items: CollectionProperty(type=BOUT_PT_ApplyModifiersItem)
    modifier_groups: CollectionProperty(type=BOUT_PT_ApplyModifiersGroup)
    object_items: CollectionProperty(type=BOUT_PT_ApplyModifiersObjectItem)
    active_object_index: IntProperty(name="Active Object", default=0)

    @classmethod
    def poll(cls, context):
        return (context.area.type == 'VIEW_3D' and
                context.mode == 'OBJECT' and
                len(context.selected_objects) > 0)

    def invoke(self, context, _event):
        """Populate the modifier list and show the property panel"""
        self.modifier_items.clear()
        self.modifier_groups.clear()
        self.object_items.clear()

        # Collect all modifiers from selected objects and build object list
        for obj in context.selected_objects:
            if obj.type == 'MESH' and obj.modifiers:
                self._collect_modifiers(obj)

                # Add to object list
                obj_item = self.object_items.add()
                obj_item.obj_name = obj.name
                obj_item.modifier_count = len(obj.modifiers)

        if not self.modifier_items:
            self.report({'WARNING'}, "No modifiers found on selected objects")
            return {'CANCELLED'}

        # Create modifier groups based on boolean breaking points
        self._create_modifier_groups()

        # Set first object as active
        self.active_object_index = 0

        # Show the property panel
        return context.window_manager.invoke_props_dialog(self, width=400, confirm_text='Apply Modifiers')

    def _get_active_object_name(self):
        """Get the name of the currently active object"""
        if 0 <= self.active_object_index < len(self.object_items):
            return self.object_items[self.active_object_index].obj_name
        return None

    def _collect_modifiers(self, obj):
        """Collect modifiers from an object"""
        for modifier in obj.modifiers:
            item = self.modifier_items.add()
            item.modifier_name = modifier.name
            item.modifier_type = modifier.type
            item.obj_name = obj.name
            item.apply = True

    def _create_modifier_groups(self):
        """Create modifier groups based on boolean breaking points"""
        # Group modifiers by object first
        obj_modifiers = {}
        for item in self.modifier_items:
            if item.obj_name not in obj_modifiers:
                obj_modifiers[item.obj_name] = []
            obj_modifiers[item.obj_name].append(item)

        # Process each object's modifiers
        for obj_name, modifiers in obj_modifiers.items():
            self._create_groups_for_object(obj_name, modifiers)

    def _create_groups_for_object(self, obj_name, modifiers):
        """Create groups for a specific object's modifiers"""
        if not modifiers:
            return

        group_start = 0

        for i, item in enumerate(modifiers):
            # Check if this modifier is a boolean and should create a breaking point
            if item.modifier_type == 'BOOLEAN':
                # Check if the next modifier exists and is NOT a boolean
                is_last = i == len(modifiers) - 1
                next_is_not_boolean = not is_last and modifiers[i + 1].modifier_type != 'BOOLEAN'

                # Create a section break after boolean if it's the last modifier or followed by non-boolean
                if is_last or next_is_not_boolean:
                    # Create group from group_start to current index (inclusive)
                    group = self.modifier_groups.add()
                    group.enabled = True  # Will be set to False for last section later
                    group.show_expanded = True
                    group.obj_name = obj_name

                    # Assign group index to modifiers in this group
                    for j in range(group_start, i + 1):
                        modifiers[j].group_index = len(self.modifier_groups) - 1

                    group_start = i + 1

        # Handle any remaining modifiers (non-boolean or after last boolean group)
        if group_start < len(modifiers):
            group = self.modifier_groups.add()
            group.enabled = True  # Will be set to False for last section later
            group.show_expanded = True
            group.obj_name = obj_name

            # Assign group index to remaining modifiers
            for k in range(group_start, len(modifiers)):
                modifiers[k].group_index = len(self.modifier_groups) - 1

        # Set last section of this object to disabled by default (only if multiple sections)
        # Find all groups for this object and count them
        obj_groups = []
        for idx, group in enumerate(self.modifier_groups):
            if group.obj_name == obj_name:
                obj_groups.append(idx)

        # Only disable last section if there are multiple sections
        if len(obj_groups) > 1:
            last_group_index = obj_groups[-1]
            self.modifier_groups[last_group_index].enabled = False

    def _get_modifier_icon(self, modifier_type):
        """Get the appropriate icon for a modifier type"""
        icon_map = {
            'ARRAY': 'MOD_ARRAY',
            'BEVEL': 'MOD_BEVEL',
            'BOOLEAN': 'MOD_BOOLEAN',
            'BUILD': 'MOD_BUILD',
            'DECIMATE': 'MOD_DECIM',
            'EDGE_SPLIT': 'MOD_EDGESPLIT',
            'MIRROR': 'MOD_MIRROR',
            'SOLIDIFY': 'MOD_SOLIDIFY',
            'SUBSURF': 'MOD_SUBSURF',
            'TRIANGULATE': 'MOD_TRIANGULATE',
            'WIREFRAME': 'MOD_WIREFRAME',
            'SKIN': 'MOD_SKIN',
            'ARMATURE': 'MOD_ARMATURE',
            'CAST': 'MOD_CAST',
            'CURVE': 'MOD_CURVE',
            'DISPLACE': 'MOD_DISPLACE',
            'HOOK': 'MOD_HOOK',
            'LAPLACIANDEFORM': 'MOD_MESHDEFORM',
            'LATTICE': 'MOD_LATTICE',
            'MESH_DEFORM': 'MOD_MESHDEFORM',
            'SHRINKWRAP': 'MOD_SHRINKWRAP',
            'SIMPLE_DEFORM': 'MOD_SIMPLEDEFORM',
            'SMOOTH': 'MOD_SMOOTH',
            'CORRECTIVE_SMOOTH': 'MOD_SMOOTH',
            'LAPLACIANSMOOTH': 'MOD_SMOOTH',
            'SURFACE_DEFORM': 'MOD_MESHDEFORM',
            'WARP': 'MOD_WARP',
            'WAVE': 'MOD_WAVE',
            'CLOTH': 'MOD_CLOTH',
            'COLLISION': 'MOD_PHYSICS',
            'DYNAMIC_PAINT': 'MOD_DYNAMICPAINT',
            'EXPLODE': 'MOD_EXPLODE',
            'FLUID': 'MOD_FLUIDSIM',
            'OCEAN': 'MOD_OCEAN',
            'PARTICLE_INSTANCE': 'MOD_PARTICLE_INSTANCE',
            'PARTICLE_SYSTEM': 'MOD_PARTICLES',
            'SOFT_BODY': 'MOD_SOFT',
            'SURFACE': 'MOD_PHYSICS',
            'SIMULATION': 'MOD_PHYSICS',
        }
        return icon_map.get(modifier_type, 'MODIFIER')

    def draw(self, _context):
        """Draw the property panel"""
        layout = self.layout

        if not self.modifier_items:
            layout.label(text="No modifiers found", icon='INFO')
            return

        layout.separator()

        # Object selection list at top
        if len(self.object_items) > 1:
            layout.label(text="Select Object:", icon='OBJECT_DATA')
            layout.template_list(
                "BOUT_UL_ApplyModifiersObjectList", "",
                self, "object_items",
                self, "active_object_index",
                rows=min(len(self.object_items), 4)
            )
            layout.separator()
        elif len(self.object_items) == 1:
            layout.label(text=f"Object: {self.object_items[0].obj_name}", icon='OBJECT_DATA')
            layout.separator()

        # Get currently selected object
        active_obj_name = self._get_active_object_name()
        if not active_obj_name:
            layout.label(text="No object selected", icon='ERROR')
            return

        # Show only modifiers for the selected object
        obj_modifiers = [item for item in self.modifier_items if item.obj_name == active_obj_name]

        if not obj_modifiers:
            layout.label(text="No modifiers found for this object", icon='INFO')
            return

        # Sort modifiers by their original order
        obj_modifiers.sort(key=lambda x: next(i for i, mod_item in enumerate(self.modifier_items) if mod_item == x))

        # Group modifiers by sections for this object
        sections = {}
        for item in obj_modifiers:
            if item.group_index not in sections:
                sections[item.group_index] = []
            sections[item.group_index].append(item)

        # Draw modifiers in flat structure
        for group_index in sorted(sections.keys()):
            section_modifiers = sections[group_index]
            group = self.modifier_groups[group_index]

            for i, item in enumerate(section_modifiers):
                is_last_in_section = (i == len(section_modifiers) - 1)

                row = layout.row()

                if is_last_in_section:
                    # Last modifier in section gets extra checkbox (section enable/disable)
                    row.prop(group, "enabled", text="")
                else:
                    # Add empty space to align with section checkbox
                    row.label(text="", icon='BLANK1')

                # Modifier checkbox
                sub_row = row.row()
                sub_row.enabled = group.enabled
                sub_row.prop(item, "apply", text="")

                # Modifier icon and name
                icon = self._get_modifier_icon(item.modifier_type)
                sub_row.label(text=item.modifier_name, icon=icon)

        layout.separator()

    def execute(self, context):
        """Apply the selected modifiers"""
        if not self.modifier_items:
            return {'CANCELLED'}

        # Group modifiers by object for processing
        obj_modifiers = {}
        for item in self.modifier_items:
            if item.obj_name not in obj_modifiers:
                obj_modifiers[item.obj_name] = []
            obj_modifiers[item.obj_name].append(item)

        applied_count = 0

        # Process each object
        for obj_name, modifiers in obj_modifiers.items():
            obj = bpy.data.objects.get(obj_name)
            if not obj:
                continue

            # Set the object as active to apply modifiers
            context.view_layer.objects.active = obj

            # Apply modifiers in reverse order (from last to first)
            # This prevents index shifting issues
            modifiers_to_apply = []

            for item in reversed(modifiers):
                # Check if the group is enabled and the modifier is selected
                group_enabled = True
                if item.group_index < len(self.modifier_groups):
                    group_enabled = self.modifier_groups[item.group_index].enabled

                if item.apply and group_enabled:
                    modifier = obj.modifiers.get(item.modifier_name)
                    if modifier:
                        modifiers_to_apply.append(modifier)

            # Apply the modifiers
            for modifier in modifiers_to_apply:
                try:
                    bpy.ops.object.modifier_apply(modifier=modifier.name)
                    applied_count += 1
                except (RuntimeError, ValueError) as e:
                    self.report({'WARNING'}, f"Failed to apply {modifier.name} on {obj_name}: {str(e)}")

        self.report({'INFO'}, f"Applied {applied_count} modifiers")
        return {'FINISHED'}


types_classes = (
    BOUT_PT_ApplyModifiersObjectItem,
    BOUT_PT_ApplyModifiersItem,
    BOUT_PT_ApplyModifiersGroup,
)

classes = (
    BOUT_UL_ApplyModifiersObjectList,
    BOUT_OT_ApplyModifiers,
)
