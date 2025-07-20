import bpy
import bmesh
import os
from . import orientation, window, ui
from .data import Mouse, CreatedData
from ...utils import scene, addon, modifier
from mathutils import Vector


class BOUT_OT_AssetImport(bpy.types.Operator):
    bl_idname = "bout.asset_import"
    bl_label = "Asset Drag and Drop"
    bl_description = "Custom drag and drop operator for Blockout assets"
    bl_options = {'REGISTER', 'UNDO', 'GRAB_CURSOR'}

    outside_view3d = True
    valid_drop_areas = []
    asset_shelf_areas = []

    @classmethod
    def poll(cls, context):
        active_tool = context.workspace.tools.from_space_view3d_mode(context.mode, create=False)
        blockout_tool = active_tool and (active_tool.idname == 'bout.block_mesh' or active_tool.idname == 'bout.block_obj')
        return blockout_tool

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.mouse = Mouse()
        self.data = CreatedData()
        self.ray = scene.ray_cast.Ray()
        self.ui = ui.DrawUI()
        self.mode = 'ADD'

    def draw(self, context):
        layout = self.layout


    def get_asset_from_context(self, context):
        """Check if we have a valid asset in context"""
        return hasattr(context, "asset") and context.asset is not None

    def deduplicate_geometry_node_groups(self, obj):
        """Check geometry node modifiers and reuse existing node groups if available"""
        if not obj or not obj.modifiers:
            return

        for modifier in obj.modifiers:
            if modifier.type == 'NODES' and modifier.node_group:
                current_node_group = modifier.node_group
                node_group_name = current_node_group.name

                # Remove potential suffix (.001, .002, etc.) to get base name
                base_name = node_group_name
                if '.' in base_name and base_name.split('.')[-1].isdigit():
                    base_name = '.'.join(base_name.split('.')[:-1])

                # Look for existing node group with the same base name
                existing_group = None
                for ng in bpy.data.node_groups:
                    if ng != current_node_group and (ng.name == base_name or ng.name.startswith(base_name + '.')):
                        # Verify it's the same type of node group
                        if ng.type == current_node_group.type:
                            existing_group = ng
                            break

                # If we found an existing group, replace the reference
                if existing_group:
                    print(f"Reusing existing node group '{existing_group.name}' instead of '{current_node_group.name}'")
                    modifier.node_group = existing_group

                    # Remove the duplicate node group if it has no users
                    if current_node_group.users == 0:
                        bpy.data.node_groups.remove(current_node_group)

    def import_asset(self, context):
        """Import or duplicate the asset based on whether it's local or external"""
        # Get the asset directly from context with error checking
        if not hasattr(context, 'asset') or context.asset is None:
            print("Error: No asset found in context")
            return None

        asset = context.asset

        if not hasattr(asset, 'name') or not asset.name:
            print("Error: Asset has no valid name")
            return None

        obj_name = asset.name

        # Check if this is a local asset (from current file)
        if hasattr(asset, 'local_id') and asset.local_id:
            # This is a local asset - we need to make a direct copy
            local_obj = asset.local_id

            # Create a new object with a copy of the data
            if local_obj.data and hasattr(local_obj.data, "copy"):
                # Deep copy the mesh data
                mesh_copy = local_obj.data.copy()

                # Create a new object with the copied data
                new_obj = bpy.data.objects.new(local_obj.name, mesh_copy)

                # Link the new object to the active collection
                context.collection.objects.link(new_obj)

                # Copy transforms
                new_obj.location = local_obj.location.copy()
                new_obj.rotation_euler = local_obj.rotation_euler.copy()
                new_obj.scale = local_obj.scale.copy()
                new_obj.hide_viewport = True

                # Copy modifiers from original object
                for mod in local_obj.modifiers:
                    new_modifier = new_obj.modifiers.new(mod.name, mod.type)
                    # Copy mod properties
                    for prop in mod.bl_rna.properties:
                        if not prop.is_readonly and prop.identifier != 'name':
                            try:
                                setattr(new_modifier, prop.identifier, getattr(mod, prop.identifier))
                            except Exception as e:
                                print(f"Warning: Could not copy modifier property {prop.identifier}: {e}")

                # Copy custom properties safely
                try:
                    for key, value in local_obj.items():
                        new_obj[key] = value
                except Exception as e:
                    print(f"Warning: Could not copy property {key}: {e}")

                # Deduplicate geometry node groups after copying
                self.deduplicate_geometry_node_groups(new_obj)

                return new_obj
            else:
                # Handle objects without mesh data (empties, cameras, etc.)
                new_obj = bpy.data.objects.new(local_obj.name, local_obj.data)
                context.collection.objects.link(new_obj)

                # Copy transforms
                new_obj.location = local_obj.location.copy()
                new_obj.rotation_euler = local_obj.rotation_euler.copy()
                new_obj.scale = local_obj.scale.copy()
                new_obj.hide_viewport = True

                return new_obj

        # This is an external asset - import it
        if not hasattr(asset, 'full_library_path') or not hasattr(asset, 'id_type'):
            print("Error: Asset missing required attributes for external import")
            return None

        blend_file_path = asset.full_library_path
        id_type = asset.id_type

        # Check asset validity
        if id_type != 'OBJECT':
            print(f"Error: Asset type '{id_type}' is not supported (only OBJECT)")
            return None

        if not blend_file_path or not os.path.exists(blend_file_path):
            print(f"Error: Blend file path does not exist: {blend_file_path}")
            return None

        # Set up the directory for the append operation
        directory = os.path.join(blend_file_path, "Object")

        # Store objects before append to identify new ones
        objects_before = set(bpy.data.objects)

        # Append the object using direct properties with error handling
        try:
            bpy.ops.wm.append(
                filepath=os.path.join(directory, obj_name),
                directory=directory,
                filename=obj_name,
                link=False,
                autoselect=False,
            )
        except Exception as e:
            print(f"Error appending asset '{obj_name}': {e}")
            return None

        # Find the newly imported object by comparing before/after
        objects_after = set(bpy.data.objects)
        new_objects = objects_after - objects_before

        # Look for exact name match first, then fallback to startswith
        target_obj = None
        for obj in new_objects:
            if obj.name == obj_name:
                target_obj = obj
                break

        if not target_obj:
            # Fallback to name matching for objects with suffixes (.001, etc.)
            matching_objects = [obj for obj in new_objects if obj.name.startswith(obj_name)]
            if matching_objects:
                target_obj = matching_objects[0]  # Take the first match

        if target_obj:
            if hasattr(target_obj, "asset_clear"):
                target_obj.asset_clear()
            target_obj.hide_viewport = True

            # Deduplicate geometry node groups after importing
            self.deduplicate_geometry_node_groups(target_obj)

            return target_obj
        else:
            print(f"Error: Could not find imported object '{obj_name}'")
            return None

    def update_object_position(self, context, position):
        """Update the object position based on mouse coordinates"""
        if not self.data.obj:
            return

        # Check if mouse is in a valid drop area
        area_info = window.is_mouse_in_valid_area(self, position)

        # Mouse is in a valid area, show the object
        self.outside_view3d = False
        self.data.obj.hide_viewport = False

        # Get 3D position from mouse using the correct region and region_3d
        region = area_info['region']
        rv3d = area_info['region_3d']

        orientation.build(self, context, region, rv3d)
        matrix = self.data.matrix.copy()

        self.data.obj.matrix_world = matrix


    def _add_boolean_modifier(self, bool_obj, obj, operation='DIFFERENCE'):
        '''Add the boolean modifier'''
        mod = modifier.add(bool_obj, "Boolean", 'BOOLEAN')
        mod.operation = operation
        mod.solver = addon.pref().tools.block.settings.solver
        mod.object = obj
        mod.show_in_editmode = True

        return mod


    def _setup_boolean(self, context):
        '''Setup the boolean'''
        selected = self.data.selected_objects
        mode = self.mode
        obj = self.data.obj

        # Handle special modes first
        if mode == 'CARVE':
            self._add_carve_obj(context, obj)

        if mode == 'SLICE':
            # Duplicate selected objects for SLICE mode
            duplicated_objs = self._duplicate_objects(context, selected)
            # Create INTERSECT boolean modifiers for duplicated objects
            self._create_boolean_modifiers(obj, None, duplicated_objs, 'INTERSECT')

        # Create main boolean modifiers for selected objects
        self._create_boolean_modifiers(obj, None, selected, mode)

        # Set parent relationship if there's an active object
        if context.active_object and context.active_object in selected:
            self._set_parent(obj, context.active_object)
        elif selected:
            self._set_parent(obj, selected[0])

        # Configure the boolean object appearance
        if hasattr(obj.data, 'shade_smooth'):
            obj.data.shade_smooth()

    def _create_boolean_modifiers(self, obj, bool_obj, selected_objs, mode):
        '''Create the boolean modifiers'''
        _selected = selected_objs[:]
        if bool_obj:
            _selected_set = set(_selected + [bool_obj])
        else:
            _selected_set = set(_selected)
        selected = list(_selected_set)

        for sel_obj in selected:
            match mode:
                case 'UNION': operation = 'UNION'
                case 'CUT': operation = 'DIFFERENCE'
                case 'INTERSECT': operation = 'INTERSECT'
                case 'SLICE': operation = 'DIFFERENCE'
                case 'CARVE': operation = 'DIFFERENCE'
                case _: operation = 'DIFFERENCE'
            self._add_boolean_modifier(sel_obj, obj, operation)

    def _duplicate_objects(self, context, objects_to_duplicate):
        """Duplicate objects for SLICE mode"""
        duplicated = []

        for o in objects_to_duplicate:
            new_obj = o.copy()
            new_obj.data = o.data.copy()
            context.collection.objects.link(new_obj)
            duplicated.append(new_obj)
            self._set_parent(new_obj, o)

        # Store reference to duplicated objects for potential cleanup
        self.data.duplicated_objects = duplicated

        return duplicated

    def _add_carve_obj(self, context, obj):
        """Create a carve object for CARVE mode"""
        new_obj = obj.copy()
        new_obj.data = obj.data.copy()
        new_obj.display_type = 'TEXTURED'
        new_obj.hide_render = False
        context.collection.objects.link(new_obj)

        # Store reference to carve object for potential cleanup
        if not hasattr(self.data, 'carve_obj'):
            self.data.carve_obj = new_obj

    def _set_parent(self, child_obj, parent_obj):
        """Set parent relationship between objects"""
        if parent_obj:
            # Store the child's current world matrix to preserve its position
            child_world_matrix = child_obj.matrix_world.copy()

            # Set the parent
            child_obj.parent = parent_obj

            # Calculate the correct matrix_parent_inverse to maintain world position
            child_obj.matrix_parent_inverse = parent_obj.matrix_world.inverted()

            # Restore the world position by setting matrix_world back
            child_obj.matrix_world = child_world_matrix


    def invoke(self, context, event):
        """Start the modal operator"""

        self.mode = addon.pref().tools.block.mode
        self.data.selected_objects = context.selected_objects[:]

        # Get asset info from context
        if not self.get_asset_from_context(context):
            return {'CANCELLED'}

        # Find all valid 3D view areas for dropping
        self.valid_drop_areas = window.find_valid_3d_areas(self, context)
        if not self.valid_drop_areas:
            return {'CANCELLED'}

        # Import the asset to create a preview object
        self.data.obj = self.import_asset(context)
        if not self.data.obj:
            return {'CANCELLED'}

        if len(self.data.selected_objects) == 0:
            self.mode = 'ADD'

        if self.mode != 'ADD':
            self.data.obj.display_type = 'WIRE'
            self.data.obj.hide_render = True
            self.data.obj.data.shade_smooth()

            if context.active_object:
                self._set_parent(self.data.obj, context.active_object)
            else:
                self._set_parent(self.data.obj, context.selected_objects[0])


        ui.setup(self, context)
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        """Handle modal events"""

        if event.type == 'MOUSEMOVE':
            self.mouse.window = Vector((event.mouse_x, event.mouse_y))

            area_info = window.is_mouse_in_valid_area(self, self.mouse.window)
            if area_info:
                context.window.cursor_set('SCROLL_XY')
                region = area_info['region']
                rv3d = area_info['region_3d']

                region_relative_x = self.mouse.window.x - area_info['left']
                region_relative_y = self.mouse.window.y - area_info['bot']
                self.mouse.area = Vector((region_relative_x, region_relative_y))

                self.ray = scene.ray_cast.selected(context, self.mouse.area, region=region, rv3d=rv3d)
                self.update_object_position(context, self.mouse.window)
                self.update_ui(context)

            else:
                self.clean_ui()
                self.data.obj.hide_viewport = True
                context.window.cursor_set('STOP')

            return {'RUNNING_MODAL'}

        elif event.type == 'LEFTMOUSE' and event.value == 'RELEASE':
            area_info = window.is_mouse_in_valid_area(self, self.mouse.window)

            bpy.ops.object.select_all(action='DESELECT')
            self.data.obj.select_set(True)
            context.view_layer.objects.active = self.data.obj

            if not area_info or self.outside_view3d:
                self._cancel()
                self._end(context)
                return {'CANCELLED'}

            if self.mode != 'ADD':
                self._setup_boolean(context)

            self._end(context)
            return {'FINISHED'}

        elif event.type in {'RIGHTMOUSE', 'ESC'}:
            self._cancel()
            self._end(context)
            return {'CANCELLED'}

        context.area.tag_redraw()
        return {'RUNNING_MODAL'}


    def execute(self, context):
        return {'FINISHED'}


    def clean_ui(self):
        '''Clear the UI drawing'''
        self.ui.xaxis.callback.update_batch(())
        self.ui.yaxis.callback.update_batch(())

    def update_ui(self, context):
        '''Update the drawing'''

        if context.scene.bout.align.mode != 'CUSTOM':
            plane = self.data.matrix.plane
            direction = self.data.matrix.direction
            world_origin, world_normal = plane
            x_axis_point = world_origin + direction
            y_direction = world_normal.cross(direction).normalized()
            y_axis_point = world_origin + y_direction
            self.ui.xaxis.callback.update_batch((world_origin, x_axis_point))
            self.ui.yaxis.callback.update_batch((world_origin, y_axis_point))

        if self.mode != 'ADD':
            bm = bmesh.new()
            bm.from_mesh(self.data.obj.data)
            bm.faces.ensure_lookup_table()
            faces = bm.faces
            self.ui.faces.callback.update_batch(faces)
            bm.free()

    def _cancel(self):
        if self.data.obj:
            bpy.data.objects.remove(self.data.obj, do_unlink=True)

        # Clean up duplicated objects if they exist
        if hasattr(self.data, 'duplicated_objects'):
            for obj in self.data.duplicated_objects:
                if obj and obj.name in bpy.data.objects:
                    mesh_data = obj.data
                    bpy.data.objects.remove(obj, do_unlink=True)
                    if mesh_data and mesh_data.users == 0:
                        bpy.data.meshes.remove(mesh_data)

        # Clean up carve object if it exists
        if hasattr(self.data, 'carve_obj'):
            if self.data.carve_obj and self.data.carve_obj.name in bpy.data.objects:
                mesh_data = self.data.carve_obj.data
                bpy.data.objects.remove(self.data.carve_obj, do_unlink=True)
                if mesh_data and mesh_data.users == 0:
                    bpy.data.meshes.remove(mesh_data)

    def _end(self, context):
        self.mouse = None
        self.ray = None
        self.data = None

        self.ui.clear()
        self.ui.clear_higlight()

        context.window.cursor_set('DEFAULT')


classes = (
    BOUT_OT_AssetImport,
)