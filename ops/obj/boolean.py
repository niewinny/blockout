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


class BOUT_OT_ModBoolean(bpy.types.Operator):
    bl_idname = "bout.mod_boolean"
    bl_label = "Boolean"
    bl_options = {'REGISTER', 'UNDO', 'BLOCKING', 'GRAB_CURSOR'}
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

    solver: bpy.props.EnumProperty(
        name="Solver",
        items= get_solver_items,
        default=0
    )

    flip: bpy.props.BoolProperty(
        name="Flip",
        default=False
    )


    @classmethod
    def poll(cls, context):
        return context.area.type == 'VIEW_3D' and context.mode in {'EDIT_MESH', 'OBJECT'}

    def execute(self, context):
        active_object = context.active_object
        selected_objects = context.selected_objects[:]

        if active_object in selected_objects:
            selected_objects.remove(active_object)

        if self.flip:
            self._boolean_active_to_selected(selected_objects, active_object)
            # Keep the boolean source (active) selected, deselect objects with modifiers
            update_selection(context, [active_object], selected_objects)
        else:
            self._boolean_selected_to_active(selected_objects, active_object)
            # Keep the boolean sources (selected) selected, deselect object with modifiers (active)
            update_selection(context, selected_objects, [active_object])

        return {'FINISHED'}
    

    def _boolean_active_to_selected(self, selected_objects, active_object):
        prepare_boolean_object(active_object)

        for obj in selected_objects:

            mod = modifier.add(obj, "Boolean", 'BOOLEAN')
            mod.operation = self.operation
            mod.object = active_object

            attributes = get_boolean_properties(self.solver)
            for key, value in attributes:
                setattr(mod, key, value)


    def _boolean_selected_to_active(self, selected_objects, active_object):
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


class BOUT_OT_ModBooleanSlice(bpy.types.Operator):
    bl_idname = "bout.mod_boolean_slice"
    bl_label = "Boolean Slice"
    bl_options = {'REGISTER', 'UNDO', 'BLOCKING', 'GRAB_CURSOR'}
    bl_description = "Slice objects into two parts using boolean operations"

    solver: bpy.props.EnumProperty(
        name="Solver",
        items= get_solver_items,
        default=0
    )

    flip: bpy.props.BoolProperty(
        name="Flip",
        default=False
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.objects_with_modifiers: list = []

    @classmethod
    def poll(cls, context):
        return context.area.type == 'VIEW_3D' and context.mode in {'EDIT_MESH', 'OBJECT'}

    def execute(self, context):
        active_object = context.active_object
        selected_objects = context.selected_objects[:]

        if active_object in selected_objects:
            selected_objects.remove(active_object)

        if self.flip:
            self._slice_active_to_selected(context, selected_objects, active_object)
            # Deselect all and select only the boolean source object
            all_objects = selected_objects + self.objects_with_modifiers
            update_selection(context, [active_object], all_objects)
        else:
            self._slice_selected_to_active(context, selected_objects, active_object)
            # Deselect all and select only the boolean source objects
            all_objects = [active_object] + self.objects_with_modifiers
            update_selection(context, selected_objects, all_objects)

        return {'FINISHED'}

    def _slice_active_to_selected(self, context, selected_objects, active_object):
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

    def _slice_selected_to_active(self, context, selected_objects, active_object):
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


class BOUT_OT_ModBooleanCarve(bpy.types.Operator):
    bl_idname = "bout.mod_boolean_carve"
    bl_label = "Boolean Carve"
    bl_options = {'REGISTER', 'UNDO', 'BLOCKING', 'GRAB_CURSOR'}
    bl_description = "Carve into objects using boolean operations"

    solver: bpy.props.EnumProperty(
        name="Solver",
        items= get_solver_items,
        default=0
    )

    offset: bpy.props.FloatProperty(
        name="Offset",
        description="Offset distance for carving",
        default=0.001,
        min=0.0,
        subtype='DISTANCE'
    )

    flip: bpy.props.BoolProperty(
        name="Flip",
        default=False
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.carved_objects: list = []

    @classmethod
    def poll(cls, context):
        return context.area.type == 'VIEW_3D' and context.mode in {'EDIT_MESH', 'OBJECT'}

    def execute(self, context):
        active_object = context.active_object
        selected_objects = context.selected_objects[:]

        if active_object in selected_objects:
            selected_objects.remove(active_object)

        if self.flip:
            self._carve_active_to_selected(context, selected_objects, active_object)
            # Deselect all source objects, select only carved objects
            all_sources = selected_objects + [active_object]
            update_selection(context, self.carved_objects, all_sources)
            # Hide the boolean source after selection update
            active_object.hide_set(True)
        else:
            self._carve_selected_to_active(context, selected_objects, active_object)
            # Deselect all source objects, select only carved objects
            all_sources = selected_objects + [active_object]
            update_selection(context, self.carved_objects, all_sources)
            # Hide the boolean sources after selection update
            for obj in selected_objects:
                obj.hide_set(True)

        return {'FINISHED'}

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

    def _carve_active_to_selected(self, context, selected_objects, active_object):
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


    def _carve_selected_to_active(self, context, selected_objects, active_object):
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
