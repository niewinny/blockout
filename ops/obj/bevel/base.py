import bpy
from mathutils import Vector
from ....utils import infobar, modifier
from .data import Mouse, Distance, DrawUI
from . import utils


class BevelOperatorBase(bpy.types.Operator):
    """Base class for bevel operators with shared functionality"""

    bl_options = {"REGISTER", "UNDO", "BLOCKING", "GRAB_CURSOR"}

    # Pin state for modifiers
    pin: bpy.props.BoolProperty(
        name="Pin to Last",
        description="Pin modifier to last",
        default=False,
        options={"HIDDEN", "SKIP_SAVE"},
    )

    use_clamp_overlap: bpy.props.BoolProperty(name="Clamp Overlap", default=False)
    loop_slide: bpy.props.BoolProperty(name="Loop Slide", default=False)

    harden_normals: bpy.props.BoolProperty(name="Harden Normals", default=True)

    width_type: bpy.props.EnumProperty(
        name="Width Type",
        items=(
            ("OFFSET", "Offset", "Offset the bevel width"),
            ("WIDTH", "Width", "Set the bevel width"),
            ("PERCENT", "Percent", "Set the bevel width in percent"),
            ("DEPTH", "Depth", "Set the bevel depth"),
            ("ABSOLUTE", "Absolute", "Set the bevel width in absolute units"),
        ),
        default="OFFSET",
    )
    width: bpy.props.FloatProperty(
        name="Offset", default=0.1, step=0.1, min=0, precision=3
    )
    segments: bpy.props.IntProperty(name="Segments", default=1, min=1, max=32)

    limit_method: bpy.props.EnumProperty(
        name="Limit Method",
        items=(
            ("NONE", "None", "No limit"),
            ("ANGLE", "Angle", "Limit by angle"),
            ("WEIGHT", "Weight", "Limit by weight"),
            ("VGROUP", "Vertex Group", "Limit by vertex group"),
        ),
        default="ANGLE",
    )
    angle_limit: bpy.props.FloatProperty(
        name="Angle",
        default=0.523599,
        min=0,
        max=3.14159,
        precision=4,
        step=10,
        subtype="ANGLE",
        description="Angle limit for beveling",
    )
    edge_weight: bpy.props.StringProperty(
        name="Edge Weight", default="bevel_weight_edge"
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.mode: str = "OFFSET"
        self.precision: bool = False
        self.snapping_ctrl: bool = False
        self.mouse: Mouse = Mouse()
        self.distance: Distance = Distance()
        self.ui: DrawUI = DrawUI()

        self.bevels: list = []

        self.saved_segments: int = 1
        self.saved_width: float = 0.0

    @classmethod
    def poll(cls, context):
        return context.area.type == "VIEW_3D" and context.mode in {
            "EDIT_MESH",
            "OBJECT",
        }

    def invoke(self, context, event):
        self._get_scene_properties(context)

        active_object = (
            context.active_object
            if context.active_object and context.active_object.select_get()
            else None
        )
        selected_objects = list(
            set(filter(None, context.selected_objects + [active_object]))
        )

        if not selected_objects:
            self.report({"WARNING"}, "No objects selected for bevel operation")
            return {"CANCELLED"}

        self.mouse.median = (
            sum([o.location for o in selected_objects], Vector())
            / len(selected_objects)
            if selected_objects
            else Vector()
        )

        self.mouse.co = utils.get_intersect_point(context, event, self.mouse.median)
        self.mouse.init = self.mouse.co if self.mouse.co else self.mouse.median

        infobar.draw(context, event, self._infobar_hotkeys, blank=True)

        self._update_info(context)
        context.window.cursor_set("SCROLL_XY")
        self._setup_bevel(selected_objects, active_object)

        utils.setup_drawing(context, self.ui)
        context.window_manager.modal_handler_add(self)
        return {"RUNNING_MODAL"}

    def execute(self, context):
        active_object = (
            context.active_object
            if context.active_object and context.active_object.select_get()
            else None
        )
        selected_objects = list(
            set(filter(None, context.selected_objects + [active_object]))
        )

        self._update_bevel(selected_objects)
        self._set_scene_properties(context)

        return {"FINISHED"}

    def _bevel_properties(self):
        attributes = [
            "width",
            "harden_normals",
            "segments",
            "use_clamp_overlap",
            "loop_slide",
            "limit_method",
            "angle_limit",
            "edge_weight",
        ]
        return attributes

    def _get_bevel_properties(self, mod):
        attributes = self._bevel_properties()
        for attr in attributes:
            setattr(self, attr, getattr(mod, attr))

    def _set_bevel_properties(self, mod):
        attributes = self._bevel_properties()
        for attr in attributes:
            setattr(mod, attr, getattr(self, attr))

    def _update_bevel(self, selected_objects):
        for obj in selected_objects:
            mod = modifier.get(obj, "BEVEL", -1)
            if not mod:
                mod = modifier.add(obj, "Bevel", "BEVEL")
                mod.miter_outer = "MITER_ARC"
            self._set_bevel_properties(mod)

            # Apply pin state if set
            if self.pin:
                mod.use_pin_to_last = True

    def modal(self, context, event):
        if event.type == "MOUSEMOVE":
            intersect_point = utils.get_intersect_point(
                context, event, self.mouse.median
            )

            if intersect_point:
                self.mouse.co = intersect_point
                if self.mode == "OFFSET":
                    self._set_width()
                elif self.mode == "SEGMENTS":
                    self._set_segments(context, event)

                self._update_info(context)

            self._update_drawing(context)
            context.area.tag_redraw()

        elif event.type == "LEFTMOUSE":
            self._set_scene_properties(context)
            self._end(context)
            return {"FINISHED"}

        elif event.type in {"RET", "NUMPAD_ENTER", "SPACE"} and event.value == "PRESS":
            self._set_scene_properties(context)
            self._end(context)
            return {"FINISHED"}

        elif event.type in {"RIGHTMOUSE", "ESC"} and event.value == "PRESS":
            self._cancel()
            self._end(context)
            return {"CANCELLED"}

        elif event.type in {"LEFT_SHIFT", "RIGHT_SHIFT"} and event.value == "PRESS":
            self.precision = True
            self.distance.precision = self._calculate_distance()

        elif event.type in {"LEFT_SHIFT", "RIGHT_SHIFT"} and event.value == "RELEASE":
            self.precision = False

        elif event.type in {"LEFT_CTRL", "RIGHT_CTRL"} and event.value == "PRESS":
            self.snapping_ctrl = True

        elif event.type in {"LEFT_CTRL", "RIGHT_CTRL"} and event.value == "RELEASE":
            self.snapping_ctrl = False

        elif event.type == "S" and event.value == "PRESS":
            if not self.mode == "SEGMENTS":
                self.mode = "SEGMENTS"
                self.mouse.co = utils.get_intersect_point(
                    context, event, self.mouse.median
                )
                distance = self._calculate_distance()
                self.distance.length = distance - self.distance.delta
                self.mouse.saved = Vector((event.mouse_region_x, event.mouse_region_y))
                self.saved_segments = self.segments
                self._update_info(context)

        elif event.type == "A" and event.value == "PRESS":
            if not self.mode == "OFFSET":
                self.mode = "OFFSET"
                self.mouse.co = utils.get_intersect_point(
                    context, event, self.mouse.median
                )
                distance = self._calculate_distance()
                self.distance.delta = distance - self.distance.length

        elif event.type == "N" and event.value == "PRESS":
            self.harden_normals = not self.harden_normals
            for b in self.bevels:
                b.mod.harden_normals = self.harden_normals

        elif event.type == "L" and event.value == "PRESS":
            # Cycle through limit methods
            limit_methods = ["NONE", "ANGLE", "WEIGHT", "VGROUP"]
            current_index = limit_methods.index(self.limit_method)
            self.limit_method = limit_methods[(current_index + 1) % len(limit_methods)]
            for b in self.bevels:
                b.mod.limit_method = self.limit_method
            self._update_info(context)

        elif (
            event.type == "WHEELUPMOUSE"
            or event.type == "NUMPAD_PLUS"
            or event.type == "EQUAL"
        ):
            if event.value == "PRESS":
                self.segments += 1
                for b in self.bevels:
                    b.mod.segments = self.segments
                self._update_info(context)
                self._update_drawing(context)

        elif (
            event.type == "WHEELDOWNMOUSE"
            or event.type == "NUMPAD_MINUS"
            or event.type == "MINUS"
        ):
            if event.value == "PRESS":
                self.segments -= 1
                for b in self.bevels:
                    b.mod.segments = self.segments
                self._update_info(context)
                self._update_drawing(context)

        elif event.type == "UP_ARROW" and event.value == "PRESS":
            # Increase angle limit if in ANGLE mode
            if self.limit_method == "ANGLE":
                self.angle_limit = min(
                    self.angle_limit + 0.0174533, 3.14159
                )  # +1 degree
                for b in self.bevels:
                    b.mod.angle_limit = self.angle_limit
                self._update_info(context)
                self._update_drawing(context)

        elif event.type == "DOWN_ARROW" and event.value == "PRESS":
            # Decrease angle limit if in ANGLE mode
            if self.limit_method == "ANGLE":
                self.angle_limit = max(self.angle_limit - 0.0174533, 0.0)  # -1 degree
                for b in self.bevels:
                    b.mod.angle_limit = self.angle_limit
                self._update_info(context)
                self._update_drawing(context)

        return {"RUNNING_MODAL"}

    def _calculate_distance(self):
        """Calculate the distance based on the initial and current mouse position"""
        return utils.calculate_distance(
            self.mouse.median, self.mouse.init, self.mouse.co
        )

    def _set_width(self):
        """Set the offset based on the initial and current mouse position"""
        distance = self._calculate_distance()

        if self.precision:
            delta_distance = distance - self.distance.precision
            distance = self.distance.precision + (delta_distance * 0.1)

        distance += self.saved_width
        distance = distance if distance > self.distance.delta else self.distance.delta
        offset = distance - self.distance.delta

        # Apply snapping if Ctrl is held
        if self.snapping_ctrl:
            if self.precision:  # Both Shift and Ctrl held - snap to 0.01
                offset = round(offset / 0.01) * 0.01
            else:  # Only Ctrl held - snap to 0.1
                offset = round(offset / 0.1) * 0.1

        self.width = offset
        for b in self.bevels:
            b.mod.width = offset

    def _set_segments(self, context, event):
        """Set the segments based on the initial and current mouse position"""
        self.segments = utils.set_segments_from_mouse(
            context, event, self.mouse.median, self.mouse.saved, self.saved_segments
        )
        for b in self.bevels:
            b.mod.segments = self.segments

    def _update_info(self, context):
        """Update header with the current settings"""

        info = f"Offset: {self.width:.3f}    Segments: {self.segments}"

        # Add limit method info
        if self.limit_method != "NONE":
            info += f"    Limit: {self.limit_method}"
            if self.limit_method == "ANGLE":
                angle_formatted = utils.format_angle(self.angle_limit)
                info += f" ({angle_formatted}°)"

        # Add modifier count if available
        count_text = self._get_modifier_count_text()
        if count_text:
            info += f"    Modifiers: {count_text}"

        context.area.header_text_set(self._get_header_text() + "   " + info)

    def _get_header_text(self):
        """Get header text for operator type - to be overridden by subclasses"""
        return "Bevel"

    def draw(self, _context):
        """Draw the operator options"""
        layout = self.layout
        layout.use_property_split = True

        layout.prop(self, "width")
        layout.prop(self, "segments")

        layout.separator()

        layout.prop(self, "limit_method")
        if self.limit_method == "ANGLE":
            layout.prop(self, "angle_limit")
        elif self.limit_method == "WEIGHT":
            layout.prop(self, "edge_weight")

        layout.separator()

        header, body = layout.panel("geometry_panel", default_closed=True)
        header.label(text="Geometry")
        if body:
            col = body.column()
            col.prop(self, "use_clamp_overlap")
            col.prop(self, "loop_slide")

        header, body = layout.panel("shading_panel", default_closed=True)
        header.label(text="Shading")
        if body:
            col = body.column()
            col.prop(self, "harden_normals")

        layout.separator(factor=2)

    def _cancel(self):
        """Cancel the operator"""
        for b in self.bevels:
            if b.new:
                modifier.remove(b.obj, b.mod)

    def _end(self, context):
        """Cleanup and finish the operator"""
        infobar.remove(context)
        context.area.header_text_set(text=None)
        context.window.cursor_set("CROSSHAIR")

        self.ui.guide.remove()
        self.ui.interface.remove()

        context.area.tag_redraw()

    def _get_scene_properties(self, context):
        """Get scene properties - uses base by default, override for different storage"""
        scene_props = context.scene.bout.ops.obj.bevel.base
        self.segments = scene_props.segments
        self.harden_normals = scene_props.harden_normals
        self.angle_limit = scene_props.angle_limit

    def _set_scene_properties(self, context):
        """Set scene properties - uses base by default, override for different storage"""
        scene_props = context.scene.bout.ops.obj.bevel.base
        scene_props.segments = self.segments
        scene_props.harden_normals = self.harden_normals
        scene_props.angle_limit = self.angle_limit

    def _get_modifier_count_text(self):
        """Get modifier count text for display - override in subclasses"""
        return None

    def _update_drawing(self, context):
        """Update the drawing"""
        utils.update_drawing(
            context,
            self.ui,
            self.mouse.median,
            self.mouse.co,
            self.width,
            self.segments,
            self.limit_method,
            self.angle_limit,
            self._get_modifier_count_text(),
        )

    def _infobar_hotkeys(self, layout, _context, _event):
        """Draw the infobar hotkeys"""
        row = layout.row(align=True)
        row.label(text="", icon="MOUSE_MOVE")
        row.label(text="Adjust Radius")
        row.separator(factor=6.0)
        row.label(text="", icon="MOUSE_LMB")
        row.label(text="Confirm")
        row.separator(factor=6.0)
        row.label(text="", icon="MOUSE_RMB")
        row.label(text="Cancel")
        row.separator(factor=6.0)
        row.label(text="", icon="EVENT_A")
        row.label(text="Offset")
        row.separator(factor=6.0)
        row.label(text="", icon="EVENT_S")
        row.label(text="Segments")
        row.separator(factor=6.0)
        row.label(text="", icon="EVENT_L")
        row.label(text="Limit Method")

    def _setup_bevel(self, selected_objects, active_object):
        """Setup bevel modifiers - to be overridden by subclasses"""
        raise NotImplementedError("Subclasses must implement _setup_bevel")
