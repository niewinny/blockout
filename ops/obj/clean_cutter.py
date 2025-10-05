import bpy


class BOUT_OT_CleanCutter(bpy.types.Operator):
    bl_idname = "object.bout_clean_cutter"
    bl_label = "Clean Cutter"
    bl_description = "Clean selected cutter objects by removing wireframe display, enabling render, and moving to active collection"
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(cls, context):
        return context.selected_objects and context.mode == 'OBJECT'
    
    def check_modifier_usage(self, obj):
        """Check if object is used by any modifier in the scene"""
        for scene_obj in bpy.data.objects:
            if scene_obj.type == 'MESH' and scene_obj != obj:
                for modifier in scene_obj.modifiers:
                    # Check if modifier references this object
                    if hasattr(modifier, 'object') and modifier.object == obj:
                        return True, scene_obj
        return False, None
    
    def invoke(self, context, event):
        # Check if any selected wireframe objects are used by modifiers
        objects_in_use = []
        for obj in context.selected_objects:
            if obj.type == 'MESH' and obj.display_type == 'WIRE':
                is_used, used_by = self.check_modifier_usage(obj)
                if is_used:
                    objects_in_use.append((obj, used_by))
        
        # If objects are in use, show dialog
        if objects_in_use:
            self.objects_in_use = objects_in_use
            self.should_duplicate = True
            return context.window_manager.invoke_props_dialog(self, width=400, confirm_text="Duplicate")
        
        # Otherwise execute directly
        self.should_duplicate = False
        return self.execute(context)
    
    def draw(self, context):
        # Only show UI if objects are in use (for the warning dialog)
        if hasattr(self, 'objects_in_use'):
            layout = self.layout
            
            col = layout.column(align=True)
            col.label(text="Warning: Selected objects are used by modifiers!", icon='ERROR')
            col.separator()
            
            col.label(text="Objects in use:")
            box = col.box()
            for obj, used_by in self.objects_in_use[:5]:  # Show first 5
                box.label(text=f"  • {obj.name} (used by {used_by.name})", icon='DOT')
            if len(self.objects_in_use) > 5:
                box.label(text=f"  ... and {len(self.objects_in_use) - 5} more", icon='DOT')
            
            col.separator()
            col.label(text="Cleaned duplicates will be created.", icon='INFO')
            col.label(text="Originals will remain as cutters.", icon='INFO')
        # If no objects in use, draw nothing (empty redo panel)
    
    def execute(self, context):
        cleaned_count = 0
        duplicated_count = 0
        active_collection = context.collection
        new_selection = []
        
        for obj in context.selected_objects:
            if obj.type == 'MESH':
                # Skip objects that aren't wireframe (not cutters)
                if obj.display_type != 'WIRE':
                    continue
                    
                # Check if we should duplicate
                should_duplicate = self.should_duplicate
                
                if should_duplicate:
                    # Create duplicate
                    new_obj = obj.copy()
                    new_obj.data = obj.data.copy()
                    new_obj.name = obj.name + "_cleaned"
                    
                    # Link to active collection
                    active_collection.objects.link(new_obj)
                    
                    # Work with the duplicate
                    target_obj = new_obj
                    duplicated_count += 1
                    new_selection.append(new_obj)
                else:
                    # Work with original
                    target_obj = obj
                    new_selection.append(obj)
                
                # Remove wireframe display
                if target_obj.display_type == 'WIRE':
                    target_obj.display_type = 'TEXTURED'
                
                # Enable rendering
                if target_obj.hide_render:
                    target_obj.hide_render = False
                
                # Set flat shading
                mesh = target_obj.data
                mesh.polygons.foreach_set("use_smooth", [False] * len(mesh.polygons))
                mesh.update()
                
                # Clear parenting while keeping transformation
                if target_obj.parent:
                    # Store the world matrix before clearing parent
                    world_matrix = target_obj.matrix_world.copy()
                    target_obj.parent = None
                    target_obj.matrix_parent_inverse.identity()
                    # Restore the world matrix to keep object in same position
                    target_obj.matrix_world = world_matrix
                
                # Only move from Cutters collection if not duplicating
                if not should_duplicate:
                    # Move from Cutters collection to active collection
                    # First check if object is in Cutters collection
                    in_cutters = False
                    for collection in target_obj.users_collection:
                        if collection.name == "Cutters":
                            in_cutters = True
                            collection.objects.unlink(target_obj)
                    
                    # Link to active collection if it was in Cutters
                    if in_cutters and target_obj.name not in active_collection.objects:
                        active_collection.objects.link(target_obj)
                
                cleaned_count += 1
        
        # Update selection to cleaned objects
        bpy.ops.object.select_all(action='DESELECT')
        for obj in new_selection:
            obj.select_set(True)
        if new_selection:
            context.view_layer.objects.active = new_selection[0]
        
        if duplicated_count > 0:
            self.report({'INFO'}, f"Cleaned {cleaned_count} object(s) ({duplicated_count} duplicated)")
        else:
            self.report({'INFO'}, f"Cleaned {cleaned_count} cutter object(s)")
        return {'FINISHED'}


classes = (
    BOUT_OT_CleanCutter,
)