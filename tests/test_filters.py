"""
Tests for filters.py - EMAFilter, VelocityDetector, StableDetector.
"""

import pytest
from filters import EMAFilter, VelocityDetector, StableDetector


class TestEMAFilter:
    """Tests for EMAFilter."""

    def test_initial_value_set_on_first_update(self, ema_filter):
        result = ema_filter.update(100.0)
        assert result == 100.0

    def test_convergence_toward_constant(self, ema_filter):
        """After many updates with the same value, output should converge."""
        for _ in range(50):
            result = ema_filter.update(100.0)
        assert abs(result - 100.0) < 0.01

    def test_smoothing_reduces_spike(self, ema_filter):
        """EMA should smooth out a single spike."""
        ema_filter.update(100.0)
        ema_filter.update(100.0)
        spike = ema_filter.update(200.0)
        # Should be pulled toward 200 but not equal to it
        assert spike < 200.0
        assert spike > 100.0

    def test_reset_clears_state(self, ema_filter):
        ema_filter.update(100.0)
        ema_filter.reset()
        assert ema_filter.value is None

    def test_reset_with_value(self, ema_filter):
        ema_filter.update(100.0)
        ema_filter.reset(value=50.0)
        assert ema_filter.value == 50.0

    def test_invalid_alpha_raises(self):
        with pytest.raises(ValueError):
            EMAFilter(alpha=0.0)
        with pytest.raises(ValueError):
            EMAFilter(alpha=-0.1)
        with pytest.raises(ValueError):
            EMAFilter(alpha=1.5)

    def test_alpha_1_is_no_smoothing(self):
        """With alpha=1.0, output should always equal input."""
        f = EMAFilter(alpha=1.0)
        assert f.update(10.0) == 10.0
        assert f.update(20.0) == 20.0


class TestVelocityDetector:
    """Tests for VelocityDetector."""

    def test_stationary_gives_zero_velocity(self, velocity_detector):
        """Constant input should converge to zero velocity."""
        velocity_detector.update(100.0)
        for _ in range(20):
            vel = velocity_detector.update(100.0)
        assert abs(vel) < 0.1

    def test_increasing_gives_positive_velocity(self, velocity_detector):
        """Monotonically increasing input should give positive velocity."""
        for i in range(10):
            vel = velocity_detector.update(float(i * 10))
        assert vel > 0

    def test_decreasing_gives_negative_velocity(self, velocity_detector):
        """Monotonically decreasing input should give negative velocity."""
        for i in range(10):
            vel = velocity_detector.update(float(100 - i * 10))
        assert vel < 0

    def test_reset(self, velocity_detector):
        for i in range(5):
            velocity_detector.update(float(i))
        velocity_detector.reset()
        assert velocity_detector.velocity == 0.0

    def test_first_update_returns_zero(self, velocity_detector):
        """First update has no previous value, so velocity should be 0."""
        vel = velocity_detector.update(50.0)
        assert vel == 0.0


class TestStableDetector:
    """Tests for StableDetector."""

    def test_requires_n_consecutive_true(self, stable_detector):
        """Should not trigger until threshold_frames consecutive True values."""
        assert stable_detector.update(True) is False  # 1
        assert stable_detector.update(True) is False  # 2
        assert stable_detector.update(True) is True   # 3 (threshold met)

    def test_interruption_resets_counter(self, stable_detector):
        """A single False should reset the counter."""
        stable_detector.update(True)  # 1
        stable_detector.update(True)  # 2
        stable_detector.update(False)  # reset
        assert stable_detector.update(True) is False  # back to 1
        assert stable_detector.update(True) is False  # 2

    def test_stays_true_while_condition_holds(self, stable_detector):
        """Once triggered, should stay True while condition is True."""
        for _ in range(3):
            stable_detector.update(True)
        assert stable_detector.update(True) is True
        assert stable_detector.update(True) is True

    def test_reset(self, stable_detector):
        for _ in range(5):
            stable_detector.update(True)
        stable_detector.reset()
        assert stable_detector.state is False

    def test_threshold_1_triggers_immediately(self):
        """With threshold=1, first True should trigger."""
        det = StableDetector(threshold_frames=1)
        assert det.update(True) is True
