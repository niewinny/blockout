import bpy
import bmesh
from mathutils import Vector

from ...utils import modifier


def get_solver_items(self, context):
    """Get boolean solver items based on Blender version"""
    if bpy.app.version >= (5, 0, 0):
        # Blender 5.0+ uses FLOAT instead of FAST
        return (
            ('FLOAT', "Float", "Float solver"),
            ('EXACT', "Exact", "Exact solver"),
            ('MANIFOLD', "Manifold", "Manifold solver"),
        )
    else:
        # Pre-5.0 uses FAST
        return (
            ('FAST', "Fast", "Fast solver"),
            ('EXACT', "Exact", "Exact solver"),
            ('MANIFOLD', "Manifold", "Manifold solver"),
        )


def update_selection(context, objects_to_select, objects_to_deselect=None):
    """Update object selection with proper error handling"""
    if objects_to_deselect:
        for obj in objects_to_deselect:
            try:
                obj.select_set(False)
            except ReferenceError:
                # Object has been removed or is no longer valid
                pass
    
    for obj in objects_to_select:
        try:
            obj.select_set(True)
        except ReferenceError:
            # Object has been removed or is no longer valid
            pass
    
    if objects_to_select:
        # Find a valid object to set as active
        for obj in reversed(objects_to_select):
            try:
                context.view_layer.objects.active = obj
                break
            except ReferenceError:
                continue


def set_smooth(obj):
    """Set smooth shading on object"""
    mesh = obj.data
    values = [True] * len(mesh.polygons)
    mesh.polygons.foreach_set("use_smooth", values)
    modifier.auto_smooth(obj)


def get_boolean_properties(solver):
    """Get boolean modifier properties"""
    attributes = [
        ("solver", solver),
        ("show_in_editmode", True),
    ]
    return attributes


def prepare_boolean_object(obj):
    """Prepare object as boolean source (wireframe, hide render, smooth)"""
    obj.display_type = 'WIRE'
    obj.hide_render = True
    set_smooth(obj)


class BooleanOperatorBase(bpy.types.Operator):
    """Base class for boolean operators with common functionality"""
    bl_options = {'REGISTER', 'UNDO', 'BLOCKING', 'GRAB_CURSOR'}
    
    solver: bpy.props.EnumProperty(
        name="Solver",
        items=get_solver_items,
        default=0
    )
    
    flip: bpy.props.BoolProperty(
        name="Flip",
        default=False
    )
    
    @classmethod
    def poll(cls, context):
        return context.area.type == 'VIEW_3D' and context.mode in {'EDIT_MESH', 'OBJECT'}
    
    def get_objects(self, context):
        """Get active and selected objects, excluding active from selected list"""
        active_object = context.active_object
        selected_objects = context.selected_objects[:]
        
        if active_object in selected_objects:
            selected_objects.remove(active_object)
            
        return active_object, selected_objects
    
    def execute(self, context):
        """Common execute method that handles the flip logic"""
        active_object, selected_objects = self.get_objects(context)
        
        # Validate selection
        validation_result = self.validate_selection(selected_objects)
        if validation_result:
            return validation_result
        
        if self.flip:
            result = self.apply_operation_active_to_selected(context, selected_objects, active_object)
        else:
            result = self.apply_operation_selected_to_active(context, selected_objects, active_object)
        
        # Handle post-operation selection if defined
        if hasattr(self, 'update_selection_after_operation'):
            self.update_selection_after_operation(context, active_object, selected_objects)
        
        return {'FINISHED'}
    
    def validate_selection(self, selected_objects):
        """Validate that we have enough objects for boolean operation"""
        if len(selected_objects) < 1:
            self.report({'WARNING'}, "Not enough objects selected for boolean operation")
            return {'CANCELLED'}
        return None
    
    def apply_operation_active_to_selected(self, context, selected_objects, active_object):
        """Override this method in subclasses to implement active->selected operation"""
        raise NotImplementedError("Subclasses must implement apply_operation_active_to_selected")
    
    def apply_operation_selected_to_active(self, context, selected_objects, active_object):
        """Override this method in subclasses to implement selected->active operation"""
        raise NotImplementedError("Subclasses must implement apply_operation_selected_to_active")


class BOUT_OT_ModBoolean(BooleanOperatorBase):
    bl_idname = "bout.mod_boolean"
    bl_label = "Boolean"
    bl_description = "Boolean Objects together"

    operation: bpy.props.EnumProperty(
        name="Operation",
        items=(
            ('UNION', "Union", "Union"),
            ('INTERSECT', "Intersect", "Intersect"),
            ('DIFFERENCE', "Difference", "Difference"),
        ),
        default='DIFFERENCE'
    )
    
    def update_selection_after_operation(self, context, active_object, selected_objects):
        """Update selection based on flip state"""
        if self.flip:
            # Keep the boolean source (active) selected, deselect objects with modifiers
            update_selection(context, [active_object], selected_objects)
        else:
            # Keep the boolean sources (selected) selected, deselect object with modifiers (active)
            update_selection(context, selected_objects, [active_object])

    def apply_operation_active_to_selected(self, context, selected_objects, active_object):
        """Apply boolean from active object to selected objects"""
        prepare_boolean_object(active_object)

        for obj in selected_objects:
            mod = modifier.add(obj, "Boolean", 'BOOLEAN')
            mod.operation = self.operation
            mod.object = active_object

            attributes = get_boolean_properties(self.solver)
            for key, value in attributes:
                setattr(mod, key, value)

    def apply_operation_selected_to_active(self, context, selected_objects, active_object):
        """Apply boolean from selected objects to active object"""
        for obj in selected_objects:
            prepare_boolean_object(obj)

            mod = modifier.add(active_object, "Boolean", 'BOOLEAN')
            mod.operation = self.operation
            mod.object = obj

            attributes = get_boolean_properties(self.solver)
            for key, value in attributes:
                setattr(mod, key, value)


    def draw(self, _context):
        '''Draw the operator options'''
        layout = self.layout
        layout.use_property_split = True

        layout.prop(self, 'operation')
        layout.prop(self, 'solver')

        layout.separator()
        layout.prop(self, 'flip')


class BOUT_OT_ModBooleanSlice(BooleanOperatorBase):
    bl_idname = "bout.mod_boolean_slice"
    bl_label = "Boolean Slice"
    bl_description = "Slice objects into two parts using boolean operations"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.objects_with_modifiers: list = []
    
    def update_selection_after_operation(self, context, active_object, selected_objects):
        """Update selection to show only boolean source objects"""
        if self.flip:
            # Deselect all and select only the boolean source object
            all_objects = selected_objects + self.objects_with_modifiers
            update_selection(context, [active_object], all_objects)
        else:
            # Deselect all and select only the boolean source objects
            all_objects = [active_object] + self.objects_with_modifiers
            update_selection(context, selected_objects, all_objects)

    def apply_operation_active_to_selected(self, context, selected_objects, active_object):
        prepare_boolean_object(active_object)

        for obj in selected_objects:
            # Create duplicate for the intersect part
            duplicate = obj.copy()
            duplicate.data = obj.data.copy()
            context.collection.objects.link(duplicate)
            duplicate.location = obj.location
            duplicate.name = obj.name + "_slice"

            # Apply difference to original
            mod_diff = modifier.add(obj, "Boolean", 'BOOLEAN')
            mod_diff.operation = 'DIFFERENCE'
            mod_diff.object = active_object

            # Apply intersect to duplicate
            mod_int = modifier.add(duplicate, "Boolean", 'BOOLEAN')
            mod_int.operation = 'INTERSECT'
            mod_int.object = active_object

            # Apply properties to both modifiers
            attributes = get_boolean_properties(self.solver)
            for key, value in attributes:
                setattr(mod_diff, key, value)
                setattr(mod_int, key, value)

            self.objects_with_modifiers.extend([obj, duplicate])

    def apply_operation_selected_to_active(self, context, selected_objects, active_object):
        # Create duplicate of active object for the intersect part
        active_duplicate = active_object.copy()
        active_duplicate.data = active_object.data.copy()
        context.collection.objects.link(active_duplicate)
        active_duplicate.location = active_object.location
        active_duplicate.name = active_object.name + "_slice"

        for obj in selected_objects:
            prepare_boolean_object(obj)

            # Apply difference to original active
            mod_diff = modifier.add(active_object, "Boolean", 'BOOLEAN')
            mod_diff.operation = 'DIFFERENCE'
            mod_diff.object = obj

            # Apply intersect to duplicate active
            mod_int = modifier.add(active_duplicate, "Boolean", 'BOOLEAN')
            mod_int.operation = 'INTERSECT'
            mod_int.object = obj

            attributes = get_boolean_properties(self.solver)
            for key, value in attributes:
                setattr(mod_diff, key, value)
                setattr(mod_int, key, value)

        
        # Track objects with modifiers outside the loop
        self.objects_with_modifiers.extend([active_object, active_duplicate])

    def draw(self, _context):
        '''Draw the operator options'''
        layout = self.layout
        layout.use_property_split = True

        layout.prop(self, 'solver')
        layout.separator()
        layout.prop(self, 'flip')


class BOUT_OT_ModBooleanCarve(BooleanOperatorBase):
    bl_idname = "bout.mod_boolean_carve"
    bl_label = "Boolean Carve"
    bl_description = "Carve into objects using boolean operations"

    offset: bpy.props.FloatProperty(
        name="Offset",
        description="Offset distance for carving",
        default=0.001,
        min=0.0,
        subtype='DISTANCE'
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.carved_objects: list = []
    
    def update_selection_after_operation(self, context, active_object, selected_objects):
        """Update selection to show only carved objects and hide sources"""
        # Deselect all source objects, select only carved objects
        all_sources = selected_objects + [active_object]
        update_selection(context, self.carved_objects, all_sources)
        
        # Hide the boolean sources after selection update
        if self.flip:
            active_object.hide_set(True)
        else:
            for obj in selected_objects:
                obj.hide_set(True)

    def _create_carve_duplicate(self, context, obj):
        """Create a duplicate object with faces moved inward for carving effect"""
        # Create duplicate
        new_obj = obj.copy()
        new_obj.data = obj.data.copy()
        new_obj.name = obj.name + "_carve"
        context.collection.objects.link(new_obj)
        
        # Move faces inward by offset
        if self.offset > 0:
            bm = bmesh.new()
            bm.from_mesh(new_obj.data)
            
            # Move all vertices inward along their normals
            for vert in bm.verts:
                # Calculate vertex normal as average of connected face normals
                vert_normal = sum((f.normal for f in vert.link_faces), start=Vector((0, 0, 0)))
                if vert_normal.length > 0:
                    vert_normal.normalize()
                    vert.co -= vert_normal * self.offset
            
            bm.to_mesh(new_obj.data)
            bm.free()
        
        return new_obj

    def apply_operation_active_to_selected(self, context, selected_objects, active_object):
        # Create carve duplicate if offset is specified
        if self.offset > 0:
            carve_obj = self._create_carve_duplicate(context, active_object)
            # Keep carve object visible
            carve_obj.display_type = 'TEXTURED'
            carve_obj.hide_render = False
            self.carved_objects.append(carve_obj)
        
        # Setup original object for boolean
        prepare_boolean_object(active_object)

        for obj in selected_objects:
            mod = modifier.add(obj, "Boolean", 'BOOLEAN')
            mod.operation = 'DIFFERENCE'
            mod.object = active_object

            attributes = get_boolean_properties(self.solver)
            for key, value in attributes:
                setattr(mod, key, value)


    def apply_operation_selected_to_active(self, context, selected_objects, active_object):
        for obj in selected_objects:
            # Create carve duplicate if offset is specified
            if self.offset > 0:
                carve_obj = self._create_carve_duplicate(context, obj)
                # Keep carve object visible
                carve_obj.display_type = 'TEXTURED'
                carve_obj.hide_render = False
                self.carved_objects.append(carve_obj)
            
            # Setup original object for boolean
            prepare_boolean_object(obj)

            mod = modifier.add(active_object, "Boolean", 'BOOLEAN')
            mod.operation = 'DIFFERENCE'
            mod.object = obj

            attributes = get_boolean_properties(self.solver)
            for key, value in attributes:
                setattr(mod, key, value)


    def draw(self, _context):
        '''Draw the operator options'''
        layout = self.layout
        layout.use_property_split = True

        layout.prop(self, 'offset')
        layout.prop(self, 'solver')
        layout.separator()
        layout.prop(self, 'flip')


classes = (
    BOUT_OT_ModBoolean,
    BOUT_OT_ModBooleanSlice,
    BOUT_OT_ModBooleanCarve,
)
