import bpy
import os
from bpy.types import Operator
from bpy.props import StringProperty


class BOUT_OT_SetAsset(Operator):
    """Set active object as blockout asset with Blockout tag"""
    bl_idname = "bout.set_asset"
    bl_label = "Set Asset"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.active_object is not None and context.mode == 'OBJECT'

    def execute(self, context):
        obj = context.active_object
        
        if obj is None:
            self.report({'ERROR'}, "No active object selected")
            return {'CANCELLED'}
        
        # Mark object as asset
        obj.asset_mark()
        
        # Add Blockout tag to metadata
        if obj.asset_data:
            tags = obj.asset_data.tags
            # Check if Blockout tag already exists
            if not any(tag.name == "Blockout" for tag in tags):
                new_tag = tags.new("Blockout")
        
        # Generate preview for the asset
        if obj.asset_data:
            # Set the object as active in context and generate preview
            context.view_layer.objects.active = obj
            obj.select_set(True)
            # Use the correct operator to generate asset preview
            bpy.ops.ed.lib_id_generate_preview()
        
        self.report({'INFO'}, f"Object '{obj.name}' marked as blockout asset")
        return {'FINISHED'}


class BOUT_OT_ClearAsset(Operator):
    """Clear asset and Blockout tag from selected objects"""
    bl_idname = "bout.clear_asset"
    bl_label = "Clear Asset"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return len(context.selected_objects) > 0 and context.mode == 'OBJECT'

    def execute(self, context):
        cleared_count = 0
        
        for obj in context.selected_objects:
            if obj.asset_data:
                # Remove Blockout tag if it exists
                tags = obj.asset_data.tags
                for tag in tags:
                    if tag.name == "Blockout":
                        tags.remove(tag)
                        break
                
                # Clear asset marking
                obj.asset_clear()
                cleared_count += 1
        
        if cleared_count > 0:
            self.report({'INFO'}, f"Cleared asset data from {cleared_count} object(s)")
        else:
            self.report({'WARNING'}, "No assets found in selected objects")
        
        return {'FINISHED'}


class BOUT_OT_OpenAssetsFile(Operator):
    """Open the blocks.blend asset file"""
    bl_idname = "bout.open_assets_file"
    bl_label = "Assets File"
    bl_options = {'REGISTER'}

    def execute(self, context):
        # Get the path to blocks.blend file
        assets_dir = os.path.dirname(__file__)
        blocks_file = os.path.join(assets_dir, "blocks.blend")
        
        if not os.path.exists(blocks_file):
            self.report({'ERROR'}, f"Assets file not found: {blocks_file}")
            return {'CANCELLED'}
        
        # Open the file
        bpy.ops.wm.open_mainfile(filepath=blocks_file)
        
        self.report({'INFO'}, "Opened blocks.blend asset file")
        return {'FINISHED'}


classes = (
    BOUT_OT_SetAsset,
    BOUT_OT_ClearAsset,
    BOUT_OT_OpenAssetsFile,
) 