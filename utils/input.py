"""Numeric input utilities for modal operators.

Provides:
- Key mapping for Blender events
- NumericInput class for handling keyboard number entry

Note: Comma is silently replaced with period for international number formats.
"""

# Key mapping for Blender events to characters (digits and decimal only)
KEY_TO_CHAR = {
    "ZERO": "0",
    "ONE": "1",
    "TWO": "2",
    "THREE": "3",
    "FOUR": "4",
    "FIVE": "5",
    "SIX": "6",
    "SEVEN": "7",
    "EIGHT": "8",
    "NINE": "9",
    "NUMPAD_0": "0",
    "NUMPAD_1": "1",
    "NUMPAD_2": "2",
    "NUMPAD_3": "3",
    "NUMPAD_4": "4",
    "NUMPAD_5": "5",
    "NUMPAD_6": "6",
    "NUMPAD_7": "7",
    "NUMPAD_8": "8",
    "NUMPAD_9": "9",
    "PERIOD": ".",
    "NUMPAD_PERIOD": ".",
}

NUMERIC_KEYS = set(KEY_TO_CHAR.keys())
SIGN_KEYS = {"MINUS", "NUMPAD_MINUS"}


def is_numeric_key(event_type: str) -> bool:
    """Check if an event type is a numeric input key.

    :param event_type: The Blender event type string.
    :type event_type: str
    :return: True if the event type is a numeric key.
    :rtype: bool
    """
    return event_type in NUMERIC_KEYS


def is_sign_key(event_type: str) -> bool:
    """Check if an event type is a sign toggle key.

    :param event_type: The Blender event type string.
    :type event_type: str
    :return: True if the event type is a sign key.
    :rtype: bool
    """
    return event_type in SIGN_KEYS


def _get_char(event_type: str) -> str:
    """Get the character for a key event type.

    :param event_type: The Blender event type string.
    :type event_type: str
    :return: The corresponding character, or empty string if not found.
    :rtype: str
    """
    return KEY_TO_CHAR.get(event_type, "")


def _parse_number(text: str) -> tuple[float | None, str]:
    """Parse a number string.

    :param text: The text to parse.
    :type text: str
    :return: Tuple of (result, error_message).
    :rtype: tuple[float | None, str]
    """
    if not text or text.strip() == "":
        return None, "Empty"

    text = text.strip().replace(",", ".")
    if text == "-":
        return None, "Incomplete"

    try:
        return float(text), ""
    except ValueError:
        return None, "Invalid number"


class NumericInput:
    """Handles numeric keyboard input during modal operations.

    Example usage::

        ni = NumericInput()

        # In modal:
        if is_numeric_key(event.type):
            ni.start(current_value, index)
            ni.add_char(event.type)

        # Get parsed value:
        value, error = ni.try_parse()

        # Format for display:
        text = ni.format_value(0, some_value)

    :ivar active: Whether numeric input mode is active.
    :vartype active: bool
    :ivar buffer: Current input buffer string.
    :vartype buffer: str
    :ivar active_index: Index of the value being edited.
    :vartype active_index: int
    :ivar stored_value: Value stored before editing started.
    :vartype stored_value: float
    :ivar error: Whether the current buffer has a parse error.
    :vartype error: bool
    """

    def __init__(self):
        self.active: bool = False
        self.buffer: str = ""
        self.active_index: int = 0
        self.stored_value: float = 0.0
        self.error: bool = False

    def start(self, stored_value: float = 0.0, index: int = 0) -> None:
        """Start numeric input mode.

        :param stored_value: The value to store for potential revert.
        :type stored_value: float
        :param index: The index of the value being edited.
        :type index: int
        """
        self.active = True
        self.buffer = ""
        self.error = False
        self.active_index = index
        self.stored_value = stored_value

    def stop(self) -> None:
        """Stop numeric input mode and clear buffer."""
        self.active = False
        self.buffer = ""
        self.error = False

    def add_char(self, event_type: str) -> None:
        """Add character from key event to buffer.

        :param event_type: The Blender event type string.
        :type event_type: str
        """
        char = _get_char(event_type)
        if not char:
            return  # Invalid key, ignore
        if char == ".":
            if "." in self.buffer:
                return  # Already has decimal point, ignore
            if not self.buffer or self.buffer == "-":
                self.buffer += "0."
                return
        self.buffer += char

    def toggle_sign(self) -> None:
        """Toggle the sign of the buffer.

        Adds or removes a minus sign at the start of the buffer.
        """
        if not self.buffer:
            self.buffer = "-"
        elif self.buffer.startswith("-"):
            self.buffer = self.buffer[1:]
        else:
            self.buffer = "-" + self.buffer

    def backspace(self) -> str:
        """Remove last character from buffer.

        :return: Action to take: 'apply' (buffer has chars), 'revert' (buffer empty),
                 or 'cancel' (was already empty).
        :rtype: str
        """
        if self.buffer:
            self.buffer = self.buffer[:-1]
            self.error = False
            return "apply" if self.buffer else "revert"
        return "cancel"

    def cycle(self, num_values: int) -> None:
        """Cycle to next editable value.

        :param num_values: Total number of editable values. Must be > 0.
        :type num_values: int
        """
        if num_values <= 0:
            return  # Invalid, ignore silently
        self.active_index = (self.active_index + 1) % num_values
        self.buffer = ""
        self.error = False

    def try_parse(self) -> tuple[float | None, bool]:
        """Try to parse buffer as a float.

        :return: Tuple of (parsed value or None, has_error flag).
        :rtype: tuple[float | None, bool]
        """
        if not self.buffer:
            return None, False

        result, error = _parse_number(self.buffer)
        self.error = bool(error)
        return result, self.error

    def format_value(
        self, editing_index: int, value: float, is_int: bool = False
    ) -> str:
        """Format value for display, showing buffer if being edited.

        :param editing_index: Index of the value to check against active_index.
        :type editing_index: int
        :param value: The value to format.
        :type value: float
        :param is_int: If True, format as integer.
        :type is_int: bool
        :return: Formatted string representation.
        :rtype: str
        """
        if self.active and self.active_index == editing_index:
            indicator = "[!" if self.error else "["
            return f"{indicator}{self.buffer}]"
        return f"{int(value)}" if is_int else f"{value:.4f}"
