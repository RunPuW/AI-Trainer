"""
Squat Validator - Integrates geometry, FSM, and frame capture for squat analysis.

This module provides a high-level interface for squat validation,
combining all the low-level components into a cohesive system.
"""

import os
import sys
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from geometry import SquatGeometry
from fsm import SquatFSM, SquatState, SquatRep
from frame_capture import FrameCaptureManager


@dataclass
class ValidationResult:
    """Result of a single frame validation."""
    state: str
    rep_count: int
    knee_angle: float
    hip_angle: float
    errors: List[str]
    warnings: List[str]
    error_details: List[Dict]
    angles: Dict[str, float]
    current_rep: Optional[Dict] = None


class SquatValidator:
    """
    High-level squat validator.

    Combines geometry analysis, state machine, and frame capture
    into a single easy-to-use interface.

    Usage:
        validator = SquatValidator("configs/movement_rules.json")

        # Process each frame
        result = validator.validate(landmarks)

        # Get session summary
        summary = validator.get_summary()

        # Save captured error frames
        validator.save_captures()
    """

    def __init__(
        self,
        rules_path: str = "configs/movement_rules.json",
        capture_errors: bool = True,
        capture_cooldown: float = 3.0,
        max_captures: int = 50,
    ):
        # Initialize components
        self.geometry = SquatGeometry()
        self.fsm = SquatFSM(rules_path)

        # Frame capture (optional)
        self.capture_enabled = capture_errors
        if capture_errors:
            self.frame_capture = FrameCaptureManager(
                output_dir="captured_frames",
                cooldown_seconds=capture_cooldown,
                max_captures_per_error=5,
                max_total_captures=max_captures,
            )
        else:
            self.frame_capture = None

        # Current frame for capture
        self._current_frame = None

        # Set up callbacks
        self.fsm.on_error_with_data = self._on_error

        # Statistics
        self.total_frames = 0
        self.error_frames = 0

    def _on_error(self, error_type: str, error_description: str, angles: Dict):
        """Callback for error detection."""
        if not self.capture_enabled or self._current_frame is None:
            return

        captured = self.frame_capture.capture_frame(
            frame=self._current_frame,
            error_type=error_type,
            error_description=error_description,
            rep_number=self.fsm.rep_count,
            angles=angles,
            state=self.fsm.state.value,
        )

        if captured:
            self.error_frames += 1

    def validate(self, landmarks, frame=None) -> Optional[ValidationResult]:
        """
        Validate a single frame.

        Args:
            landmarks: MediaPipe pose landmarks
            frame: Optional video frame for error capture

        Returns:
            ValidationResult or None if no person detected
        """
        self.total_frames += 1
        self._current_frame = frame

        # Geometry analysis
        geo = self.geometry.analyze(landmarks)
        if geo is None:
            return None

        # FSM update
        status = self.fsm.update(geo)

        return ValidationResult(
            state=status["state"],
            rep_count=status["rep_count"],
            knee_angle=status["knee_angle"],
            hip_angle=status["hip_angle"],
            errors=status["errors"],
            warnings=status["warnings"],
            error_details=status.get("error_details", []),
            angles=status.get("angles", {}),
            current_rep=status.get("current_rep"),
        )

    def reset(self):
        """Reset the validator for a new session."""
        self.fsm.reset()
        if self.frame_capture:
            self.frame_capture.reset()
        self.total_frames = 0
        self.error_frames = 0

    def get_summary(self) -> Dict:
        """Get session summary."""
        fsm_summary = self.fsm.get_session_summary()

        return {
            **fsm_summary,
            "total_frames": self.total_frames,
            "error_frames": self.error_frames,
            "error_rate": self.error_frames / max(1, self.total_frames),
            "captured_frames": len(self.frame_capture.captures) if self.frame_capture else 0,
        }

    def get_error_summary(self) -> Dict[str, int]:
        """Get error type counts."""
        if self.frame_capture:
            return self.frame_capture.get_error_summary()
        return {}

    def save_captures(self, session_id: Optional[str] = None) -> List[str]:
        """Save captured error frames."""
        if self.frame_capture:
            return self.frame_capture.save_captures(session_id)
        return []

    def get_captures_for_report(self) -> List[Dict]:
        """Get capture data for report generation."""
        if self.frame_capture:
            return self.frame_capture.get_captures_for_report()
        return []

    # Convenience properties
    @property
    def rep_count(self) -> int:
        return self.fsm.rep_count

    @property
    def current_state(self) -> str:
        return self.fsm.state.value

    @property
    def is_in_progress(self) -> bool:
        return self.fsm.state in [SquatState.DESCENDING, SquatState.BOTTOM, SquatState.ASCENDING]
