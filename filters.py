"""
filters.py - 信号filtermodule
provide供 EMA (refnum移actionaverage) filterer, used_forflat滑 MediaPipe output jointangle sitmark, 
缓解singlecameradetection 抖action噪声. 
"""

from collections import deque
from typing import Dict, List, Optional


class EMAFilter:
    """
    singlechangeamount EMA filterer. 

    公style: y_t = alpha * x_t + (1 - alpha) * y_{t-1}

    alpha 越big, tonewdata越敏感, flat滑度越low; 
    alpha 越small, flat滑度越high, but滞back越big. 
    """

    def __init__(self, alpha: float = 0.3, initial_value: Optional[float] = None):
        if not 0 < alpha <= 1.0:
            raise ValueError(f"alpha must be in (0, 1], got {alpha}")
        self.alpha = alpha
        self._value: Optional[float] = initial_value

    def update(self, measurement: float) -> float:
        """inputnew测amountvalue, returnfilterback value. """
        if self._value is None:
            self._value = measurement
        else:
            self._value = self.alpha * measurement + (1 - self.alpha) * self._value
        return self._value

    def reset(self, value: Optional[float] = None):
        """resetfiltererstate. """
        self._value = value

    @property
    def value(self) -> Optional[float]:
        return self._value


class MultiEMAFilter:
    """
    manychangeamount EMA filterermanageer. 
    asperitemjointpointorangle维护独立  EMA filterer. 
    """

    def __init__(self, alpha: float = 0.3):
        self.alpha = alpha
        self._filters: Dict[str, EMAFilter] = {}

    def update(self, key: str, measurement: float) -> float:
        """updateref定 key  filterer. """
        if key not in self._filters:
            self._filters[key] = EMAFilter(alpha=self.alpha)
        return self._filters[key].update(measurement)

    def update_batch(self, measurements: Dict[str, float]) -> Dict[str, float]:
        """batchamountupdatemanyitem测amountvalue. """
        return {k: self.update(k, v) for k, v in measurements.items()}

    def get(self, key: str) -> Optional[float]:
        """getgetref定 key  currentfiltervalue. """
        filt = self._filters.get(key)
        return filt.value if filt else None

    def reset(self, key: Optional[str] = None):
        """resetref定 key orallfilterer. """
        if key is None:
            self._filters.clear()
        elif key in self._filters:
            self._filters[key].reset()

    def reset_all(self):
        """resetplace filterer. """
        self._filters.clear()


class VelocityDetector:
    """
    based_on EMA filterback numvaluecalculatevelocity(framebetweenBadsplit). 
    used_for FSM stateconvert  velocitythresholdjudge. 
    """

    def __init__(self, alpha: float = 0.3):
        self.alpha = alpha
        self._ema = EMAFilter(alpha=alpha)
        self._prev_value: Optional[float] = None
        self._velocity: float = 0.0

    def update(self, value: float) -> float:
        """
        inputnewvalue, returncurrentvelocity(correcttableshowascending, 负tableshowdescending). 
        velocitythisbodyalso经pass EMA flat滑. 
        """
        filtered = self._ema.update(value)
        if self._prev_value is not None:
            raw_velocity = filtered - self._prev_value
            self._velocity = self.alpha * raw_velocity + (1 - self.alpha) * self._velocity
        self._prev_value = filtered
        return self._velocity

    def reset(self):
        self._ema.reset()
        self._prev_value = None
        self._velocity = 0.0

    @property
    def velocity(self) -> float:
        return self._velocity


class StableDetector:
    """
    Stability detector: triggers when N consecutive frames satisfy a condition,
    and optionally requires M consecutive false frames before resetting (hysteresis).

    This prevents single-frame jitter from resetting a stable state.
    """

    def __init__(self, threshold_frames: int = 3, hysteresis_frames: int = 1):
        self.threshold_frames = threshold_frames
        self.hysteresis_frames = hysteresis_frames
        self._counter: int = 0
        self._false_counter: int = 0
        self._state: bool = False

    def update(self, condition: bool) -> bool:
        """
        Feed current frame condition. Returns True when stable state is reached.

        With hysteresis_frames > 1, the state won't reset until
        hysteresis_frames consecutive False values are observed.
        """
        if condition:
            self._counter += 1
            self._false_counter = 0
            if self._counter >= self.threshold_frames:
                self._state = True
        else:
            self._counter = 0
            self._false_counter += 1
            if self._false_counter >= self.hysteresis_frames:
                self._state = False
        return self._state

    def reset(self):
        self._counter = 0
        self._false_counter = 0
        self._state = False

    @property
    def state(self) -> bool:
        return self._state
