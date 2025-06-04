import bpy


class BOUT_OT_Veil(bpy.types.Operator):
    """Hide all mesh objects that are set to wire visibility"""
    bl_idname = "bout.veil"
    bl_label = "Veil Objects"
    bl_description = "Hide all mesh objects that are set to wire visibility"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        for obj in bpy.context.visible_objects:
            if obj.type == 'MESH' and obj.visible_get() and obj.display_type == 'WIRE':
                if not obj.select_get():
                    obj.hide_set(True)

        return {'FINISHED'}

class BOUT_OT_Unveil(bpy.types.Operator):
    """Unhide all objects used as booleans in selected objects"""
    bl_idname = "bout.unveil"
    bl_label = "Unveil Objects"
    bl_description = "Unhide all objects used as booleans in selected objects"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):

        selected_objects = context.selected_objects
        boolean_objects = set()

        for obj in selected_objects:
            if obj.type == 'MESH':
                for mod in obj.modifiers:
                    if mod.type == 'BOOLEAN' and mod.object and mod.object.name in bpy.data.objects:
                        boolean_objects.add(mod.object)

        for obj in boolean_objects:
            obj.hide_set(False)

        return {'FINISHED'}

classes = (
    BOUT_OT_Veil,
    BOUT_OT_Unveil,
)