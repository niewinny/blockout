import bpy
from bpy.props import EnumProperty, BoolProperty, CollectionProperty, StringProperty, IntProperty
from bpy.types import Operator, PropertyGroup, UIList
from mathutils import Matrix


class BOUT_PT_MatrixObjectItem(PropertyGroup):
    """Property group for object items in the list"""
    name: StringProperty(name="Object Name")
    has_parent: BoolProperty(name="Has Parent", default=False)


class BOUT_UL_MatrixObjectList(UIList):
    """UIList for displaying objects"""
    
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            row = layout.row()
            if item.has_parent:
                row.label(text=item.name, icon='LINKED')
                row.label(text="Has Parent", icon='INFO')
            else:
                row.label(text=item.name, icon='OBJECT_DATA')
        elif self.layout_type in {'GRID'}:
            layout.alignment = 'CENTER'
            layout.label(text="", icon='OBJECT_DATA' if not item.has_parent else 'LINKED')


class BOUT_OT_StoreMatrix(Operator):
    bl_idname = "bout.store_matrix"
    bl_label = "Store Matrix"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = "Store the transformation matrix of selected objects"

    matrix_type: EnumProperty(
        name="Matrix Type",
        description="Which matrix slot to use",
        items=[
            ('BASE', 'Base', 'Store as base matrix'),
            ('POSED', 'Posed', 'Store as posed matrix')
        ],
        default='BASE'
    )
    
    # Collection to display selected objects
    object_items: CollectionProperty(type=BOUT_PT_MatrixObjectItem)
    active_object_index: IntProperty(name="Active Object", default=0)

    @classmethod
    def poll(cls, context):
        return (context.area.type == 'VIEW_3D' and
                context.mode == 'OBJECT' and
                len(context.selected_objects) > 0)

    def invoke(self, context, event):
        # Clear and populate object list
        self.object_items.clear()
        for obj in context.selected_objects:
            item = self.object_items.add()
            item.name = obj.name
            item.has_parent = obj.parent is not None
        
        # Show the property panel
        return context.window_manager.invoke_props_dialog(self, width=300, confirm_text='Store')

    def draw(self, context):
        layout = self.layout
        
        # Check if we're in undo panel (collection is empty after execute)
        if len(self.object_items) == 0:
            # Undo panel - use property split for cleaner look
            layout.use_property_split = True
            layout.prop(self, "matrix_type")
        else:
            # Invoke panel - show expanded enum and object list
            layout.prop(self, "matrix_type", expand=True)
            layout.separator()
            
            # Object list
            valid_count = sum(1 for item in self.object_items if not item.has_parent)
            layout.label(text=f"Objects to store ({valid_count} of {len(self.object_items)} selected):")
            
            # UIList for better performance with many objects
            layout.template_list(
                "BOUT_UL_MatrixObjectList", "",
                self, "object_items",
                self, "active_object_index",
                rows=min(len(self.object_items), 6)
            )

    def execute(self, context):
        count = 0
        skipped = 0
        
        for obj in context.selected_objects:
            # Skip objects with parents
            if obj.parent:
                skipped += 1
                continue
                
            # Get the world matrix as a flat list of floats
            matrix_flat = [obj.matrix_world[i][j] for i in range(4) for j in range(4)]
            
            # Store in the appropriate property
            if self.matrix_type == 'BASE':
                obj.bout.matrix_base = matrix_flat
            else:
                obj.bout.matrix_posed = matrix_flat
            
            count += 1
        
        # Clear the collection after use
        self.object_items.clear()
        
        if skipped > 0:
            self.report({'WARNING'}, f"Stored {self.matrix_type.lower()} matrix for {count} object(s), skipped {skipped} parented object(s)")
        else:
            self.report({'INFO'}, f"Stored {self.matrix_type.lower()} matrix for {count} object(s)")
        return {'FINISHED'}
    
    def cancel(self, context):
        # Clear the collection if cancelled
        self.object_items.clear()
        return {'CANCELLED'}


class BOUT_OT_RestoreMatrix(Operator):
    bl_idname = "bout.restore_matrix"
    bl_label = "Restore Matrix"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = "Restore the transformation matrix of selected objects"

    matrix_type: EnumProperty(
        name="Matrix Type",
        description="Which matrix slot to restore from",
        items=[
            ('BASE', 'Base', 'Restore from base matrix'),
            ('POSED', 'Posed', 'Restore from posed matrix')
        ],
        default='BASE'
    )
    
    # Collection to display selected objects
    object_items: CollectionProperty(type=BOUT_PT_MatrixObjectItem)
    active_object_index: IntProperty(name="Active Object", default=0)

    @classmethod
    def poll(cls, context):
        return (context.area.type == 'VIEW_3D' and
                context.mode == 'OBJECT' and
                len(context.selected_objects) > 0)

    def invoke(self, context, event):
        # Clear and populate object list
        self.object_items.clear()
        for obj in context.selected_objects:
            item = self.object_items.add()
            item.name = obj.name
            item.has_parent = obj.parent is not None
        
        # Show the property panel
        return context.window_manager.invoke_props_dialog(self, width=300, confirm_text='Restore')

    def draw(self, context):
        layout = self.layout
        
        # Check if we're in undo panel (collection is empty after execute)
        if len(self.object_items) == 0:
            # Undo panel - use property split for cleaner look
            layout.use_property_split = True
            layout.prop(self, "matrix_type")
        else:
            # Invoke panel - show expanded enum and object list
            layout.prop(self, "matrix_type", expand=True)
            layout.separator()
            
            # Object list
            valid_count = sum(1 for item in self.object_items if not item.has_parent)
            layout.label(text=f"Objects to restore ({valid_count} of {len(self.object_items)} selected):")
            
            # UIList for better performance with many objects
            layout.template_list(
                "BOUT_UL_MatrixObjectList", "",
                self, "object_items",
                self, "active_object_index",
                rows=min(len(self.object_items), 6)
            )

    def execute(self, context):
        count = 0
        skipped = 0
        
        for obj in context.selected_objects:
            # Skip objects with parents
            if obj.parent:
                skipped += 1
                continue
                
            # Get the stored matrix
            if self.matrix_type == 'BASE':
                matrix_flat = obj.bout.matrix_base
            else:
                matrix_flat = obj.bout.matrix_posed
            
            # The property returns a Matrix object when subtype='MATRIX'
            # But it's transposed! We need to transpose it back
            matrix_4x4 = matrix_flat.transposed()
            
            # Apply the world matrix to restore absolute position
            obj.matrix_world = matrix_4x4
            count += 1
        
        # Clear the collection after use
        self.object_items.clear()
        
        if skipped > 0:
            self.report({'WARNING'}, f"Restored {self.matrix_type.lower()} matrix for {count} object(s), skipped {skipped} parented object(s)")
        else:
            self.report({'INFO'}, f"Restored {self.matrix_type.lower()} matrix for {count} object(s)")
        
        return {'FINISHED'}
    
    def cancel(self, context):
        # Clear the collection if cancelled
        self.object_items.clear()
        return {'CANCELLED'}


types_classes = (
    BOUT_PT_MatrixObjectItem,
)

classes = (
    BOUT_UL_MatrixObjectList,
    BOUT_OT_StoreMatrix,
    BOUT_OT_RestoreMatrix,
)