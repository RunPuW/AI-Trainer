"""
algorithms/__init__.py
Algorithm modules for movement analysis.
"""

import sys
from pathlib import Path

# Add project root so we can import top-level geometry/fsm modules
_root = str(Path(__file__).resolve().parent.parent)
if _root not in sys.path:
    sys.path.insert(0, _root)

from geometry import SquatGeometry, calculate_angle, calculate_tilt_angle  # noqa: E402
from fsm import SquatFSM, SquatState  # noqa: E402

__all__ = [
    "SquatGeometry",
    "SquatFSM",
    "SquatState",
    "calculate_angle",
    "calculate_tilt_angle",
]
