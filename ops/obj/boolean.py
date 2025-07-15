from dataclasses import dataclass
import bpy

from ...utils import modifier


@dataclass
class Boolean:
    '''Dataclass for the modifier data'''
    obj: bpy.types.Object = None
    mod: bpy.types.Modifier = None


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
        items=(
            ('FAST', "Fast", "Fast"),
            ('EXACT', "Exact", "Exact"),
        ),
        default='FAST'
    )

    flip: bpy.props.BoolProperty(
        name="Flip",
        default=False
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.mode: str = 'OFFSET'
        self.booleans: list = []

    @classmethod
    def poll(cls, context):
        return context.area.type == 'VIEW_3D' and context.mode in {'EDIT_MESH', 'OBJECT'}

    def execute(self, context):
        active_object = context.active_object
        selected_objects = context.selected_objects

        if active_object in selected_objects:
            selected_objects.remove(active_object)

        if self.flip:
            self._boolean_active_to_selected(selected_objects, active_object)
        else:
            self._boolean_selected_to_active(selected_objects, active_object)

        return {'FINISHED'}

    def _bevel_properties(self):
        attributes = [
            ("solver", self.solver),
            ("show_in_editmode", True),
        ]
        return attributes

    def _set_smooth(self, obj):
        mesh = obj.data
        values = [True] * len(mesh.polygons)
        mesh.polygons.foreach_set("use_smooth", values)
        modifier.auto_smooth(obj)

    def _boolean_active_to_selected(self, selected_objects, active_object):

        active_object.display_type = 'WIRE'
        active_object.hide_render = True
        self._set_smooth(active_object)

        for obj in selected_objects:

            mod = modifier.add(obj, "Boolean", 'BOOLEAN')
            mod.operation = self.operation
            mod.object = active_object

            atributes = self._bevel_properties()
            for key, value in atributes:
                setattr(mod, key, value)

            self.booleans.append(Boolean(obj=obj, mod=mod))

    def _boolean_selected_to_active(self, selected_objects, active_object):

        for obj in selected_objects:

            self._set_smooth(obj)
            obj.display_type = 'WIRE'
            obj.hide_render = True

            mod = modifier.add(active_object, "Boolean", 'BOOLEAN')
            mod.operation = self.operation
            mod.object = obj

            atributes = self._bevel_properties()
            for key, value in atributes:
                setattr(mod, key, value)

            self.booleans.append(Boolean(obj=obj, mod=mod))

    def draw(self, _context):
        '''Draw the operator options'''
        layout = self.layout
        layout.use_property_split = True

        layout.prop(self, 'operation')
        layout.prop(self, 'solver')

        layout.separator()
        layout.prop(self, 'flip')


classes = (
    BOUT_OT_ModBoolean,
)
