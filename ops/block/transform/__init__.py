"""Transform sub-ops for the block modify phase.

Shared helpers live in `common` (draw-plane basis, block vert lookup,
pivot calculation); the three sub-op modules (`translate`, `rotate`,
`scale`) consume them to keep their per-op logic focused on the actual
transform math.

Axis lock follows Blender's convention (see ``Transform.axis_lock`` and
``Transform.axis_lock_exclude`` in ``ops.block.data``):

- Translate/Scale:
  - ``X`` alone → constrain TO that axis (move/scale only on X).
  - ``Shift+X`` → exclude that axis (move/scale on Y and Z).
- Rotate: axis selects the rotation axis; ``Shift`` is ignored.
  ``X`` rotates about the plane's X axis (3D); 2D always rotates about
  the plane normal regardless of the key.
"""

from . import common, rotate, scale, translate

__all__ = ["common", "rotate", "scale", "translate"]
