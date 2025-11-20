import bpy


class BOUT_OT_Veil(bpy.types.Operator):
    """Hide all mesh objects that are set to wire visibility"""

    bl_idname = "object.bout_veil"
    bl_label = "Veil Objects"
    bl_description = "Hide all mesh objects that are set to wire visibility"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        # Get the 3D view space

        space = context.space_data
        in_local_view = space and hasattr(space, "local_view") and space.local_view

        # Hide all non-selected wire mesh objects
        for obj in context.visible_objects:
            if (
                obj.type == "MESH"
                and obj.display_type == "WIRE"
                and not obj.select_get()
            ):
                # If in local view, first remove from local view
                if in_local_view:
                    obj.local_view_set(space, False)
                # Then hide the object
                obj.hide_set(True)

        return {"FINISHED"}


class BOUT_OT_Unveil(bpy.types.Operator):
    """Unhide all objects used as booleans in selected objects"""

    bl_idname = "object.bout_unveil"
    bl_label = "Unveil Objects"
    bl_description = "Unhide all objects used as booleans in selected objects"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        # Check if we're in local view (isolated objects)
        space = context.space_data
        in_local_view = space and hasattr(space, "local_view") and space.local_view

        selected_objects = context.selected_objects
        boolean_objects = set()

        for obj in selected_objects:
            if obj.type == "MESH":
                for mod in obj.modifiers:
                    if (
                        mod.type == "BOOLEAN"
                        and mod.object
                        and mod.object.name in bpy.data.objects
                    ):
                        boolean_objects.add(mod.object)

        for obj in boolean_objects:
            obj.hide_set(False)
            # If in local view, also add the object to local view
            if in_local_view and not obj.local_view_get(space):
                obj.local_view_set(space, True)

        return {"FINISHED"}


classes = (
    BOUT_OT_Veil,
    BOUT_OT_Unveil,
)
