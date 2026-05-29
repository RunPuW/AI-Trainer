"""
view_classifier.py - Camera view angle classifier
Classifies the camera perspective as front, side_left, side_right, or oblique
based on MediaPipe pose landmark geometry.

Uses heuristic features:
- Shoulder/hip/knee width ratios relative to torso height
- Left-right landmark visibility symmetry
- Overlap of bilateral landmarks (knees, hips)
"""

import math
from typing import Dict, Optional, Tuple

from geometry import get_landmark_xy, get_midpoint, PoseLandmark


class ViewClassifier:
    """Classify camera view angle from pose landmarks."""

    def __init__(self, config: Optional[Dict] = None):
        cfg = config or {}
        self.front_shoulder_ratio = cfg.get("front_shoulder_ratio", 0.35)
        self.front_hip_ratio = cfg.get("front_hip_ratio", 0.25)
        self.side_shoulder_ratio = cfg.get("side_shoulder_ratio", 0.25)
        self.side_hip_ratio = cfg.get("side_hip_ratio", 0.18)

    def classify(self, landmarks) -> Dict:
        """
        Classify camera view from landmarks.

        Returns:
            {
                "view_mode": "front" | "side_left" | "side_right" | "oblique" | "unknown",
                "confidence": float (0-1),
                "front_score": float,
                "side_score": float,
                "width_ratios": {"shoulder": float, "hip": float, "knee": float, "ankle": float},
                "warnings": [str],
            }
        """
        left_shoulder = get_landmark_xy(landmarks, PoseLandmark.LEFT_SHOULDER)
        right_shoulder = get_landmark_xy(landmarks, PoseLandmark.RIGHT_SHOULDER)
        left_hip = get_landmark_xy(landmarks, PoseLandmark.LEFT_HIP)
        right_hip = get_landmark_xy(landmarks, PoseLandmark.RIGHT_HIP)
        left_knee = get_landmark_xy(landmarks, PoseLandmark.LEFT_KNEE)
        right_knee = get_landmark_xy(landmarks, PoseLandmark.RIGHT_KNEE)
        left_ankle = get_landmark_xy(landmarks, PoseLandmark.LEFT_ANKLE)
        right_ankle = get_landmark_xy(landmarks, PoseLandmark.RIGHT_ANKLE)

        required = [left_shoulder, right_shoulder, left_hip, right_hip,
                     left_knee, right_knee, left_ankle, right_ankle]
        if any(p is None for p in required):
            return {
                "view_mode": "unknown",
                "confidence": 0.0,
                "front_score": 0.0,
                "side_score": 0.0,
                "width_ratios": {},
                "warnings": ["Insufficient landmarks for view classification"],
            }

        shoulder_mid = get_midpoint(left_shoulder, right_shoulder)
        hip_mid = get_midpoint(left_hip, right_hip)
        torso_height = abs(shoulder_mid[1] - hip_mid[1])
        if torso_height < 1e-6:
            torso_height = 0.01

        shoulder_width = abs(left_shoulder[0] - right_shoulder[0])
        hip_width = abs(left_hip[0] - right_hip[0])
        knee_width = abs(left_knee[0] - right_knee[0])
        ankle_width = abs(left_ankle[0] - right_ankle[0])

        sw_ratio = shoulder_width / torso_height
        hw_ratio = hip_width / torso_height
        kw_ratio = knee_width / torso_height
        aw_ratio = ankle_width / torso_height

        # Front score: bilateral landmarks well-separated
        front_score = 0.0
        front_score += 0.3 * min(1.0, sw_ratio / self.front_shoulder_ratio)
        front_score += 0.3 * min(1.0, hw_ratio / self.front_hip_ratio)
        front_score += 0.2 * min(1.0, kw_ratio / 0.15)
        front_score += 0.2 * self._visibility_symmetry(landmarks)

        # Side score: bilateral landmarks overlapping
        side_score = 0.0
        side_score += 0.35 * max(0.0, 1.0 - sw_ratio / self.side_shoulder_ratio)
        side_score += 0.35 * max(0.0, 1.0 - hw_ratio / self.side_hip_ratio)
        side_score += 0.15 * max(0.0, 1.0 - kw_ratio / 0.10)
        # Ankle overlap: in side view, ankles should also overlap
        side_score += 0.15 * max(0.0, 1.0 - aw_ratio / 0.10)

        front_score = max(0.0, min(1.0, front_score))
        side_score = max(0.0, min(1.0, side_score))

        warnings = []
        if front_score > 0.6 and front_score > side_score + 0.1:
            view_mode = "front"
            confidence = front_score
        elif side_score > 0.6 and side_score > front_score + 0.1:
            view_mode = self._determine_side_direction(landmarks)
            confidence = side_score
        else:
            view_mode = "oblique"
            confidence = 1.0 - abs(front_score - side_score)
            warnings.append("Camera angle is oblique - some metrics will be disabled")

        return {
            "view_mode": view_mode,
            "confidence": round(confidence, 3),
            "front_score": round(front_score, 3),
            "side_score": round(side_score, 3),
            "width_ratios": {
                "shoulder": round(sw_ratio, 3),
                "hip": round(hw_ratio, 3),
                "knee": round(kw_ratio, 3),
                "ankle": round(aw_ratio, 3),
            },
            "warnings": warnings,
        }

    def _visibility_symmetry(self, landmarks) -> float:
        """Left-right visibility symmetry (1.0 = perfect, 0.0 = very asymmetric)."""
        pairs = [
            (PoseLandmark.LEFT_SHOULDER, PoseLandmark.RIGHT_SHOULDER),
            (PoseLandmark.LEFT_HIP, PoseLandmark.RIGHT_HIP),
            (PoseLandmark.LEFT_KNEE, PoseLandmark.RIGHT_KNEE),
            (PoseLandmark.LEFT_ANKLE, PoseLandmark.RIGHT_ANKLE),
        ]
        diffs = []
        for left_idx, right_idx in pairs:
            if left_idx < len(landmarks) and right_idx < len(landmarks):
                left_vis = getattr(landmarks[left_idx], 'visibility', 0.5)
                right_vis = getattr(landmarks[right_idx], 'visibility', 0.5)
                diffs.append(abs(left_vis - right_vis))

        if not diffs:
            return 0.5
        avg_diff = sum(diffs) / len(diffs)
        return max(0.0, 1.0 - avg_diff * 2)

    def _determine_side_direction(self, landmarks) -> str:
        """Determine if side view is from left or right based on visibility."""
        left_vis = 0.0
        right_vis = 0.0

        for idx in [PoseLandmark.LEFT_SHOULDER, PoseLandmark.LEFT_HIP,
                     PoseLandmark.LEFT_KNEE, PoseLandmark.LEFT_ANKLE]:
            if idx < len(landmarks):
                left_vis += getattr(landmarks[idx], 'visibility', 0.5)

        for idx in [PoseLandmark.RIGHT_SHOULDER, PoseLandmark.RIGHT_HIP,
                     PoseLandmark.RIGHT_KNEE, PoseLandmark.RIGHT_ANKLE]:
            if idx < len(landmarks):
                right_vis += getattr(landmarks[idx], 'visibility', 0.5)

        return "side_left" if left_vis > right_vis else "side_right"


def get_enabled_metrics(view_mode: str, camera_views_config: Dict) -> Tuple[list, list]:
    """
    Get enabled and disabled metrics for a given view mode.

    Args:
        view_mode: "front", "side", "side_left", "side_right", "oblique"
        camera_views_config: the "camera_views" section from movement_rules.json

    Returns:
        (enabled_metrics, disabled_metrics)
    """
    config_key = "side" if view_mode in ("side_left", "side_right") else view_mode
    view_cfg = camera_views_config.get(config_key, camera_views_config.get("oblique", {}))
    return view_cfg.get("enabled_metrics", []), view_cfg.get("disabled_metrics", [])
