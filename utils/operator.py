import traceback
from functools import wraps


def safe(fn):
    """Decorator that calls self._cancel(context) if the method raises."""

    @wraps(fn)
    def wrapper(self, context, event):
        try:
            return fn(self, context, event)
        except Exception as e:
            traceback.print_exc()
            self.report({'ERROR'}, f"An error occurred: {e}")
            if hasattr(self, '_cancel'):
                self._cancel(context)
            return {"CANCELLED"}

    return wrapper
