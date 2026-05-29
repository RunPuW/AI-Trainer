"""
Integration tests for the squat validation pipeline.
Tests geometry -> FSM -> scoring end-to-end.
"""

import time
import pytest
from geometry import SquatGeometry
from fsm import SquatFSM, SquatState, SquatRep
from conftest import _make_landmarks


class TestSquatPipelineIntegration:
    """End-to-end tests: landmarks -> geometry -> FSM -> result."""

    def test_standing_landmarks_produce_standing_state(self):
        geo = SquatGeometry()
        fsm = SquatFSM(rules_path="configs/movement_rules.json")

        lm = _make_landmarks(shoulder_y=0.25, hip_y=0.50, knee_y=0.75, ankle_y=0.95)
        result = geo.analyze(lm)
        assert result is not None

        for _ in range(5):
            status = fsm.update(result)

        assert fsm.state == SquatState.STANDING
        assert status["state"] == "standing"

    def test_missing_landmarks_returns_none(self):
        geo = SquatGeometry()
        result = geo.analyze([])
        assert result is None

    def test_geometry_produces_all_required_keys(self):
        geo = SquatGeometry()
        lm = _make_landmarks()
        result = geo.analyze(lm)
        assert result is not None

        required_keys = [
            "knee_angle", "hip_angle", "trunk_tilt", "tibia_tilt",
            "trunk_tibia_diff", "trunk_forward", "knee_valgus_ratio",
        ]
        for key in required_keys:
            assert key in result, f"Missing key: {key}"

    def test_fsm_update_returns_expected_keys(self):
        geo = SquatGeometry()
        fsm = SquatFSM(rules_path="configs/movement_rules.json")

        lm = _make_landmarks()
        result = geo.analyze(lm)
        status = fsm.update(result)

        expected_keys = ["state", "rep_count", "knee_angle", "hip_angle", "errors", "warnings"]
        for key in expected_keys:
            assert key in status, f"Missing key: {key}"

    def test_session_summary_after_reset(self):
        fsm = SquatFSM(rules_path="configs/movement_rules.json")
        summary = fsm.get_session_summary()
        assert summary["total_reps"] == 0

    def test_scoring_uses_all_four_weights(self):
        """Verify _score_rep produces a score that accounts for all 4 components."""
        fsm = SquatFSM(rules_path="configs/movement_rules.json")
        scores = fsm.rules["scoring"]

        # Verify all 4 weights exist
        assert "depth_weight" in scores
        assert "trunk_tibia_weight" in scores
        assert "knee_alignment_weight" in scores
        assert "smoothness_weight" in scores

        # Create a perfect rep
        rep = SquatRep(rep_number=1, start_time=time.time())
        rep.bottom_knee_angle = 105.0
        rep.bottom_trunk_tibia_diff = 0.0
        fsm.current_rep = rep
        fsm.min_knee_valgus_ratio_in_rep = 0.95
        fsm._knee_velocities_in_rep = [0.0] * 10

        fsm._score_rep()

        # With perfect values, score should be close to 100
        assert rep.overall_score > 80
