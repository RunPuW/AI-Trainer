"""
Tests for geometry.py - angle calculations and SquatGeometry.
"""

import math
import pytest
from geometry import calculate_angle, calculate_tilt_angle, get_midpoint, SquatGeometry


class TestCalculateAngle:
    """Tests for calculate_angle(a, b, c) where b is the vertex."""

    def test_straight_line_returns_180(self):
        """Three collinear points should give 180 degrees."""
        angle = calculate_angle((0, 0), (1, 0), (2, 0))
        assert abs(angle - 180.0) < 0.1

    def test_right_angle(self):
        """Perpendicular vectors should give 90 degrees."""
        angle = calculate_angle((0, 1), (0, 0), (1, 0))
        assert abs(angle - 90.0) < 0.1

    def test_acute_angle(self):
        """45-degree angle."""
        angle = calculate_angle((0, 1), (0, 0), (1, 1))
        assert abs(angle - 45.0) < 0.5

    def test_degenerate_coincident_points(self):
        """Coincident points should not crash; angle is undefined but should return a number."""
        angle = calculate_angle((1, 1), (1, 1), (2, 2))
        assert 0 <= angle <= 180

    def test_symmetry(self):
        """Angle should be the same regardless of which side the arms are on."""
        a1 = calculate_angle((0, 1), (0, 0), (1, 0))
        a2 = calculate_angle((1, 0), (0, 0), (0, 1))
        assert abs(a1 - a2) < 0.01


class TestCalculateTiltAngle:
    """Tests for calculate_tilt_angle(p1, p2).

    The function measures angle from the upward vertical direction.
    In image coordinates (y increases downward):
      - Downward vertical line (p1 above p2) -> 180 degrees
      - Upward vertical line (p1 below p2) -> 0 degrees
      - Horizontal line -> 90 degrees
    """

    def test_downward_vertical_returns_180(self):
        """A line from upper point to lower point (normal body direction) = 180."""
        angle = calculate_tilt_angle((0.5, 0.3), (0.5, 0.7))
        assert abs(angle - 180.0) < 0.1

    def test_upward_vertical_returns_0(self):
        """A line from lower point to upper point = 0."""
        angle = calculate_tilt_angle((0.5, 0.7), (0.5, 0.3))
        assert angle < 0.1

    def test_horizontal_line_returns_90(self):
        """A horizontal line segment should have 90 tilt."""
        angle = calculate_tilt_angle((0.3, 0.5), (0.7, 0.5))
        assert abs(angle - 90.0) < 0.1

    def test_45_degree_right_lean(self):
        """Down-right diagonal: 180 - 45 = 135 degrees from upward vertical."""
        angle = calculate_tilt_angle((0.3, 0.3), (0.5, 0.5))
        assert abs(angle - 135.0) < 1.0


class TestGetMidpoint:
    def test_midpoint(self):
        assert get_midpoint((0, 0), (2, 2)) == (1.0, 1.0)

    def test_midpoint_none_input(self):
        assert get_midpoint(None, (1, 1)) is None
        assert get_midpoint((1, 1), None) is None


class TestSquatGeometry:
    """Tests for SquatGeometry.analyze()."""

    def test_standing_pose_returns_valid_data(self, squat_geometry, standing_landmarks):
        result = squat_geometry.analyze(standing_landmarks)
        assert result is not None
        # In standing pose, knee angle should be close to 180
        assert result["knee_angle"] > 160
        # Hip angle should be close to 180
        assert result["hip_angle"] > 160

    def test_squatting_pose_has_smaller_knee_angle(self, squat_geometry, squatting_landmarks):
        result = squat_geometry.analyze(squatting_landmarks)
        assert result is not None
        # Squatting should have smaller knee angle than standing
        assert result["knee_angle"] < 150

    def test_missing_landmarks_returns_none(self, squat_geometry):
        """If required landmarks are missing, should return None."""
        result = squat_geometry.analyze([])
        assert result is None

    def test_knee_valgus_ratio_present(self, squat_geometry, standing_landmarks):
        result = squat_geometry.analyze(standing_landmarks)
        assert result is not None
        assert result["knee_valgus_ratio"] is not None
        # Good alignment: ratio close to 1.0
        assert result["knee_valgus_ratio"] > 0.5

    def test_heel_lift_ratio_present(self, squat_geometry, standing_landmarks):
        result = squat_geometry.analyze(standing_landmarks)
        assert result is not None
        assert result["heel_lift_ratio"] is not None
        # Standing with flat feet: heel lift should be near 0
        assert result["heel_lift_ratio"] < 0.2

    def test_last_valid_data_cached(self, squat_geometry, standing_landmarks):
        squat_geometry.analyze(standing_landmarks)
        assert squat_geometry.get_last_valid() is not None

    def test_bilateral_symmetry(self, squat_geometry, standing_landmarks):
        """Left and right knee angles should be nearly equal in a symmetric pose."""
        result = squat_geometry.analyze(standing_landmarks)
        assert result is not None
        assert abs(result["left_knee_angle"] - result["right_knee_angle"]) < 1.0
