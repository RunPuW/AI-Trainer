"""
Shared test fixtures for CyberTrainer tests.
"""

import sys
from pathlib import Path
from dataclasses import dataclass
from typing import List

import pytest

# Add project root to path
_root = str(Path(__file__).resolve().parent.parent)
if _root not in sys.path:
    sys.path.insert(0, _root)

from geometry import SquatGeometry, calculate_angle, calculate_tilt_angle
from filters import EMAFilter, VelocityDetector, StableDetector
from fsm import SquatFSM, SquatState


# ---------------------------------------------------------------------------
# Mock landmark simulating MediaPipe NormalizedLandmark
# ---------------------------------------------------------------------------
@dataclass
class MockLandmark:
    x: float
    y: float
    z: float = 0.0
    visibility: float = 0.9


def _make_landmarks(
    shoulder_y=0.3, hip_y=0.5, knee_y=0.7, ankle_y=0.9,
    shoulder_x_spread=0.15, knee_x_spread=0.10, foot_x_spread=0.12,
    heel_y_offset=0.02, foot_index_y_offset=0.03,
    ankle_x_offset=0.0,
):
    """
    Build a list of 33 MockLandmark objects simulating a frontal squat pose.
    Y increases downward (image coordinates). X centered at 0.5.

    ankle_x_offset: shift ankles forward (positive) to simulate knee bend.
    """
    lm = [MockLandmark(x=0.5, y=0.1)] * 33  # default: head area

    cx = 0.5  # center x

    # Shoulders (11, 12)
    lm[11] = MockLandmark(x=cx - shoulder_x_spread, y=shoulder_y)
    lm[12] = MockLandmark(x=cx + shoulder_x_spread, y=shoulder_y)

    # Elbows (13, 14) - not critical for squat, but fill them
    lm[13] = MockLandmark(x=cx - shoulder_x_spread - 0.05, y=shoulder_y + 0.15)
    lm[14] = MockLandmark(x=cx + shoulder_x_spread + 0.05, y=shoulder_y + 0.15)

    # Wrists (15, 16)
    lm[15] = MockLandmark(x=cx - shoulder_x_spread - 0.03, y=shoulder_y + 0.25)
    lm[16] = MockLandmark(x=cx + shoulder_x_spread + 0.03, y=shoulder_y + 0.25)

    # Hips (23, 24)
    lm[23] = MockLandmark(x=cx - shoulder_x_spread * 0.8, y=hip_y)
    lm[24] = MockLandmark(x=cx + shoulder_x_spread * 0.8, y=hip_y)

    # Knees (25, 26)
    lm[25] = MockLandmark(x=cx - knee_x_spread, y=knee_y)
    lm[26] = MockLandmark(x=cx + knee_x_spread, y=knee_y)

    # Ankles (27, 28) - offset forward to create knee bend
    lm[27] = MockLandmark(x=cx - knee_x_spread + ankle_x_offset, y=ankle_y)
    lm[28] = MockLandmark(x=cx + knee_x_spread - ankle_x_offset, y=ankle_y)

    # Heels (29, 30)
    lm[29] = MockLandmark(x=cx - knee_x_spread + ankle_x_offset, y=ankle_y - heel_y_offset)
    lm[30] = MockLandmark(x=cx + knee_x_spread - ankle_x_offset, y=ankle_y - heel_y_offset)

    # Foot index (31, 32)
    lm[31] = MockLandmark(x=cx - foot_x_spread + ankle_x_offset, y=ankle_y + foot_index_y_offset)
    lm[32] = MockLandmark(x=cx + foot_x_spread - ankle_x_offset, y=ankle_y + foot_index_y_offset)

    return lm


@pytest.fixture
def squat_geometry():
    """Fresh SquatGeometry instance."""
    return SquatGeometry()


@pytest.fixture
def ema_filter():
    """EMA filter with alpha=0.3."""
    return EMAFilter(alpha=0.3)


@pytest.fixture
def velocity_detector():
    """VelocityDetector with alpha=0.3."""
    return VelocityDetector(alpha=0.3)


@pytest.fixture
def stable_detector():
    """StableDetector with threshold=3 frames."""
    return StableDetector(threshold_frames=3)


@pytest.fixture
def standing_landmarks():
    """Landmarks simulating a standing pose (knee angle ~180, hip angle ~180)."""
    return _make_landmarks(
        shoulder_y=0.25, hip_y=0.50, knee_y=0.75, ankle_y=0.95,
        shoulder_x_spread=0.15, knee_x_spread=0.10,
    )


@pytest.fixture
def squatting_landmarks():
    """Landmarks simulating a deep squat pose (knee angle ~90).

    In a deep squat the ankles are forward of the knees, and the knee
    angle (hip-knee-ankle) is around 90-110 degrees.  We achieve this
    by placing the ankle at the SAME height as the knee but offset
    forward, so the thigh and shin segments form a right angle.
    """
    return _make_landmarks(
        shoulder_y=0.40, hip_y=0.45, knee_y=0.65, ankle_y=0.65,
        shoulder_x_spread=0.15, knee_x_spread=0.10,
        ankle_x_offset=0.10,
    )


@pytest.fixture
def squat_fsm():
    """SquatFSM with real config file."""
    return SquatFSM(rules_path=str(Path(_root) / "configs" / "movement_rules.json"))
