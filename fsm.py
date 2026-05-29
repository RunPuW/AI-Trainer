"""
fsm.py -  限statemachinemodule
managesquatmovement 四itemstate: standing -> descending -> bottom -> ascending -> standing
and stateconvertwhenenterrowerrordetection. 
"""

import json
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Dict, List, Optional, Callable

from filters import EMAFilter, VelocityDetector, StableDetector


class SquatState(Enum):
    STANDING = "standing"
    DESCENDING = "descending"
    BOTTOM = "bottom"
    ASCENDING = "ascending"
    UNKNOWN = "unknown"


# All metric types that _check_errors actually implements.
# Camera views config should only reference these (plus "rep_count" and "rough_depth" as passthrough).
ALL_METRICS = [
    "trunk_forward_lean", "knee_valgus", "hip_dominant", "knee_dominant",
    "heel_lift", "insufficient_depth", "knee_asymmetry",
    "trunk_tibia_diff",
]


@dataclass
class BottomWindowTracker:
    """
    Accumulates error evidence during the bottom window of a rep.
    Bottom window = frames where knee_angle is within margin_deg of min_knee_angle.
    Replaces single-frame error triggering with temporal evidence accumulation.
    """
    margin_deg: float = 10.0
    frames: List[Dict] = field(default_factory=list)

    def update(self, knee_angle: float, min_knee_in_rep: float, geo: Dict):
        """Add frame to bottom window if within margin of deepest angle."""
        if abs(knee_angle - min_knee_in_rep) <= self.margin_deg:
            self.frames.append(geo)

    def has_evidence(self, metric_key: str, threshold: float,
                     min_ratio: float = 0.3) -> bool:
        """True if >= min_ratio of frames exceed threshold for given metric."""
        if not self.frames:
            return False
        hits = sum(1 for f in self.frames
                   if f.get(metric_key) is not None
                   and abs(f[metric_key]) > threshold)
        return (hits / len(self.frames)) >= min_ratio

    def peak_value(self, metric_key: str) -> Optional[float]:
        """Return the most extreme value of metric across all window frames."""
        vals = [f[metric_key] for f in self.frames
                if f.get(metric_key) is not None]
        return max(vals, key=abs) if vals else None

    def reset(self):
        self.frames.clear()


@dataclass
class SquatRep:
    """Single rep squat data record."""
    rep_number: int
    start_time: float
    end_time: Optional[float] = None
    duration_ms: Optional[float] = None

    # bottom frame data
    bottom_knee_angle: Optional[float] = None
    bottom_trunk_tibia_diff: Optional[float] = None
    bottom_trunk_forward: Optional[float] = None

    # error markers
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    # score
    depth_score: float = 0.0
    form_score: float = 0.0
    overall_score: float = 0.0

    def to_dict(self) -> Dict:
        return {
            "rep_number": self.rep_number,
            "duration_ms": self.duration_ms,
            "bottom_knee_angle": self.bottom_knee_angle,
            "bottom_trunk_tibia_diff": self.bottom_trunk_tibia_diff,
            "errors": self.errors,
            "warnings": self.warnings,
            "overall_score": self.overall_score,
        }


class SquatFSM:
    """
    squat 限statemachine. 
    perframereceivegeometryanalysisdata, updatestateanddetectionerror. 
    """

    def __init__(self, rules_path: str = "configs/movement_rules.json"):
        with open(rules_path, "r", encoding="utf-8") as f:
            config = json.load(f)

        self.rules = config["movements"]["squat"]
        self.state_rules = self.rules["states"]
        self.error_rules = self.rules["error_thresholds"]
        self.standard = self._load_standard(rules_path)
        self.quality_standard = self.standard.get("quality", {})
        self.phase_standard = self.standard.get("phases", {})
        self.issue_catalog = self.standard.get("issue_catalog", {})

        # View-aware and temporal config
        self.camera_views_config = config.get("camera_views", {})
        self.temporal_config = config.get("temporal", {})
        self.view_classifier_config = config.get("view_classifier", {})

        # currentstate
        self.state = SquatState.UNKNOWN
        self.state_entry_time = time.time()
        self.frame_count_in_state = 0

        # redup计num
        self.rep_count = 0
        self.current_rep: Optional[SquatRep] = None
        self.rep_history: List[SquatRep] = []

        # cooldownctrlmake(avoid同 movementbymanyrep计num)
        self.last_rep_end_time = 0.0
        self.cooldown_seconds = self.error_rules.get("cooldown_seconds", 3.0)

        # filterer
        self.knee_filter = EMAFilter(alpha=config["filter"]["ema_alpha"])
        self.hip_filter = EMAFilter(alpha=config["filter"]["ema_alpha"])
        self.knee_velocity = VelocityDetector(alpha=config["filter"]["ema_alpha"])
        self.hip_velocity = VelocityDetector(alpha=config["filter"]["ema_alpha"])

        # stabledetectioner
        standing_frames = int(self._phase_value("standing", "stable_frames", 3))
        bottom_frames = int(self._phase_value("bottom", "stable_frames", 2))
        self.standing_stable = StableDetector(threshold_frames=standing_frames)
        self.bottom_stable = StableDetector(threshold_frames=bottom_frames)

        # bottom极valuelog(used_forscore)
        self.min_knee_angle_in_rep = 180.0
        self.max_trunk_tibia_diff_in_rep = 0.0
        self.max_trunk_forward_in_rep = 0.0
        self.min_knee_valgus_ratio_in_rep = 1.0
        self._knee_velocities_in_rep: List[float] = []

        # Bottom window tracker for temporal evidence accumulation
        margin = self.temporal_config.get("bottom_window_margin_deg", 10)
        self.bottom_window = BottomWindowTracker(margin_deg=margin)

        # Descending phase tracking
        self._desc_min_knee = 180.0
        self._prev_raw_knee_angle: Optional[float] = None

        # callback
        self.on_state_change: Optional[Callable[[SquatState, SquatState], None]] = None
        self.on_rep_complete: Optional[Callable[[SquatRep], None]] = None
        self.on_error_detected: Optional[Callable[[str], None]] = None
        self.on_error_with_data: Optional[Callable[[str, str, Dict], None]] = None  # (error_type, description, angles)

    def _load_standard(self, rules_path: str) -> Dict:
        """Load structured movement standards used by scoring and feedback."""
        rules_file = Path(rules_path)
        candidates = [
            rules_file.parent / "movement_standards.json",
            Path("configs") / "movement_standards.json",
        ]
        for path in candidates:
            try:
                if path.exists():
                    with open(path, "r", encoding="utf-8") as f:
                        return json.load(f).get("movements", {}).get("squat", {})
            except Exception:
                continue
        return {}

    def _quality_threshold(self, group: str, key: str, fallback):
        return self.quality_standard.get(group, {}).get(key, fallback)

    def _phase_value(self, phase: str, key: str, fallback):
        return self.phase_standard.get(phase, {}).get(key, fallback)

    def _issue_description(self, issue_type: str, fallback: str) -> str:
        issue = self.issue_catalog.get(issue_type, {})
        label = issue.get("label")
        cue = issue.get("cue")
        if label and cue:
            return f"{label}: {fallback}。{cue}"
        if label:
            return f"{label}: {fallback}"
        return fallback

    def reset(self):
        """resetstatemachineto初始state. """
        self.state = SquatState.UNKNOWN
        self.state_entry_time = time.time()
        self.frame_count_in_state = 0
        self.rep_count = 0
        self.current_rep = None
        self.rep_history.clear()
        self.last_rep_end_time = 0.0
        self.knee_filter.reset()
        self.hip_filter.reset()
        self.knee_velocity.reset()
        self.hip_velocity.reset()
        self.standing_stable.reset()
        self.bottom_stable.reset()
        self._desc_min_knee = 180.0  # descendingpass程minanglelog
        self._prev_raw_knee_angle = None
        self._reset_rep_extremes()

    def _reset_rep_extremes(self):
        self.min_knee_angle_in_rep = 180.0
        self.max_trunk_tibia_diff_in_rep = 0.0
        self.max_trunk_forward_in_rep = 0.0
        self.min_knee_valgus_ratio_in_rep = 1.0
        self._knee_velocities_in_rep = []
        self.bottom_window.reset()

    def _transition_to(self, new_state: SquatState):
        old_state = self.state
        self.state = new_state
        self.state_entry_time = time.time()
        self.frame_count_in_state = 0

        if self.on_state_change:
            self.on_state_change(old_state, new_state)

        # stateenterinwhen 特殊handlereason
        if new_state == SquatState.DESCENDING:
            # startnew  repredup
            self.rep_count += 1
            self.current_rep = SquatRep(
                rep_number=self.rep_count,
                start_time=time.time()
            )
            self._reset_rep_extremes()

        elif new_state == SquatState.STANDING and old_state == SquatState.ASCENDING:
            # complete repredup
            self._complete_rep()

    def _complete_rep(self):
        if self.current_rep is None:
            return

        now = time.time()
        self.current_rep.end_time = now
        self.current_rep.duration_ms = (now - self.current_rep.start_time) * 1000

        min_duration_ms = float(self._phase_value("complete", "min_rep_duration_ms", 700))
        if (
            self.current_rep.duration_ms < min_duration_ms
            or self.current_rep.bottom_knee_angle is None
        ):
            self.current_rep = None
            self.rep_count = max(0, self.rep_count - 1)
            self.last_rep_end_time = now
            return

        # score
        self._score_rep()

        # loghistory
        self.rep_history.append(self.current_rep)
        self.last_rep_end_time = now

        if self.on_rep_complete:
            self.on_rep_complete(self.current_rep)

        self.current_rep = None

    def _score_rep(self):
        """Score a single rep based on bottom window evidence and rep tracking."""
        rep = self.current_rep
        if rep is None:
            return

        scores = self.rules["scoring"]
        min_ratio = self.temporal_config.get("min_bottom_ratio", 0.3)

        # Depth score: use bottom window peak knee angle if available
        peak_knee = self.bottom_window.peak_value("knee_angle")
        ref_knee = peak_knee if peak_knee is not None else rep.bottom_knee_angle
        if ref_knee is not None:
            ideal = self._quality_threshold("depth", "ideal_knee_angle", 105)
            deviation = abs(ref_knee - ideal)
            depth_score = max(0, 100 - deviation * 3)
        else:
            depth_score = 0

        # Trunk-tibia alignment score: use bottom window evidence
        peak_ttd = self.bottom_window.peak_value("trunk_tibia_diff")
        ref_ttd = peak_ttd if peak_ttd is not None else rep.bottom_trunk_tibia_diff
        has_bottom_data = ref_ttd is not None
        if has_bottom_data:
            deviation = abs(ref_ttd)
            trunk_score = max(100 - deviation * 5, 0)
        else:
            trunk_score = 100  # no data = don't penalize

        # Knee alignment score: use bottom window evidence
        peak_dev = self.bottom_window.peak_value("knee_deviation_avg")
        if peak_dev is not None and peak_dev < 0:
            # Negative deviation = valgus, score based on severity
            knee_score = max(0, 100 + peak_dev * 1000)  # -0.05 → 50, -0.1 → 0
        else:
            # Fallback to ratio-based
            valgus = self.min_knee_valgus_ratio_in_rep
            if valgus < 0.85:
                knee_score = max(0, (valgus / 0.85) * 100)
            else:
                knee_score = 100 - (1.0 - valgus) * 200

        # Smoothness score
        knee_score = max(0, min(100, knee_score))
        smoothness_score = self._compute_smoothness_score()

        # Weighted overall score
        rep.overall_score = (
            depth_score * scores["depth_weight"] +
            trunk_score * scores["trunk_tibia_weight"] +
            knee_score * scores["knee_alignment_weight"] +
            smoothness_score * scores["smoothness_weight"]
        )
        rep.depth_score = depth_score
        rep.form_score = trunk_score

        # Add warnings for low scores (only when we have actual bottom window evidence)
        # Use "type: description" format consistent with _check_errors, and dedup
        existing_error_types = {e.split(":")[0] for e in rep.errors}
        existing_warning_types = {w.split(":")[0] for w in rep.warnings}

        shallow_angle = self._quality_threshold(
            "depth", "shallow_angle", self.error_rules.get("shallow_squat_angle", 130)
        )
        has_depth_evidence = self.bottom_window.has_evidence(
            "knee_angle", shallow_angle, min_ratio
        )
        if ((ref_knee is not None and depth_score < 60) or has_depth_evidence) \
                and "insufficient_depth" not in existing_error_types:
            if ref_knee is not None:
                desc = self._issue_description(
                    "insufficient_depth",
                    f"底部膝角 {ref_knee:.1f}°，浅蹲阈值 {shallow_angle:.1f}°",
                )
            else:
                desc = self._issue_description("insufficient_depth", "底部深度证据不足")
            rep.errors.append(f"insufficient_depth: {desc}")

        diff_max = self._quality_threshold(
            "alignment", "trunk_tibia_diff_abs_max", self.error_rules.get("trunk_tibia_diff_max", 10)
        )
        if has_bottom_data and abs(ref_ttd) > diff_max:
            warning_type = "hip_dominant" if ref_ttd > 0 else "knee_dominant"
            if warning_type not in existing_warning_types:
                desc = self._issue_description(
                    warning_type,
                    f"底部躯干-胫骨角度差 {ref_ttd:.1f}°，标准范围 ±{diff_max:.1f}°",
                )
                rep.warnings.append(f"{warning_type}: {desc}")

    def _compute_smoothness_score(self) -> float:
        """Compute smoothness score from velocity variance. Lower variance = smoother."""
        velocities = self._knee_velocities_in_rep
        if len(velocities) < 3:
            return 50.0  # not enough data, neutral score

        mean_vel = sum(velocities) / len(velocities)
        variance = sum((v - mean_vel) ** 2 for v in velocities) / len(velocities)
        std_dev = variance ** 0.5

        # std_dev of 0-2 is smooth, 2-5 is moderate, >5 is jerky
        if std_dev <= 2.0:
            return 100.0
        elif std_dev <= 5.0:
            return 100.0 - (std_dev - 2.0) * (40.0 / 3.0)  # 100 -> 60
        else:
            return max(0, 60.0 - (std_dev - 5.0) * 12.0)  # 60 -> 0

    def _check_errors(self, geo: Dict, filtered_knee: float, filtered_hip: float,
                      view_mode: str = "front",
                      enabled_metrics: Optional[List[str]] = None) -> tuple[List[str], List[str], List[Dict]]:
        """
        Check current frame for errors using filtered angle data.
        Only checks metrics that are enabled for the current camera view.

        Args:
            geo: raw geometry dict from geometry.analyze()
            filtered_knee: EMA-filtered knee angle
            filtered_hip: EMA-filtered hip angle
            view_mode: "front", "side_left", "side_right", "oblique"
            enabled_metrics: list of metric type strings to check (None = check all)

        Returns:
            (errors, warnings, error_details)
            error_details: [{"type": str, "description": str}, ...]
        """
        errors = []
        warnings = []
        error_details = []
        rules = self.error_rules
        metrics = enabled_metrics if enabled_metrics else ALL_METRICS

        # 1. Excessive forward lean (side view metric)
        if "trunk_forward_lean" in metrics:
            trunk_forward = geo.get("trunk_forward")
            trunk_forward_max = self._quality_threshold(
                "alignment", "trunk_forward_abs_max", rules["trunk_forward_max"]
            )
            if trunk_forward is not None and abs(trunk_forward) > trunk_forward_max:
                desc = self._issue_description(
                    "trunk_forward_lean",
                    f"躯干前倾 {abs(trunk_forward):.1f}°，标准上限 {trunk_forward_max:.1f}°",
                )
                # Only add to error_details; update() handles rep recording via error_details
                error_details.append({"type": "trunk_forward_lean", "description": desc})

        # 2. Knee valgus (front view metric) - primary: signed deviation, secondary: ratio
        if "knee_valgus" in metrics:
            dev = geo.get("knee_deviation_avg")
            dev_min = self._quality_threshold(
                "alignment",
                "knee_deviation_min",
                -rules.get("knee_deviation_threshold", 0.05),
            )
            if dev is not None and dev < dev_min:
                desc = self._issue_description(
                    "knee_valgus",
                    f"膝盖内扣偏移 {dev:.3f}，安全下限 {dev_min:.3f}",
                )
                error_details.append({"type": "knee_valgus", "description": desc})
            else:
                # Fallback to ratio-based detection
                knee_valgus = geo.get("knee_valgus_ratio")
                ratio_min = self._quality_threshold(
                    "alignment", "knee_valgus_ratio_min", rules["knee_valgus_ratio"]
                )
                if knee_valgus is not None and knee_valgus < ratio_min:
                    desc = self._issue_description(
                        "knee_valgus",
                        f"膝盖轨迹比例 {knee_valgus:.2f}，标准下限 {ratio_min:.2f}",
                    )
                    error_details.append({"type": "knee_valgus", "description": desc})

        # 3. Trunk-tibia imbalance (side view metric)
        if "trunk_tibia_diff" in metrics or "hip_dominant" in metrics or "knee_dominant" in metrics:
            ttd = geo.get("trunk_tibia_diff")
            diff_max = self._quality_threshold(
                "alignment", "trunk_tibia_diff_abs_max", rules["trunk_tibia_diff_max"]
            )
            if ttd is not None:
                if ttd > diff_max:
                    desc = self._issue_description(
                        "hip_dominant",
                        f"躯干-胫骨角度差 +{ttd:.1f}°，标准范围 ±{diff_max:.1f}°",
                    )
                    warnings.append(desc)
                    error_details.append({"type": "hip_dominant", "description": desc})
                elif ttd < -diff_max:
                    desc = self._issue_description(
                        "knee_dominant",
                        f"躯干-胫骨角度差 {ttd:.1f}°，标准范围 ±{diff_max:.1f}°",
                    )
                    warnings.append(desc)
                    error_details.append({"type": "knee_dominant", "description": desc})

        # 4. Heel lift (works in any view)
        if "heel_lift" in metrics:
            heel_lift = geo.get("heel_lift_ratio")
            heel_max = self._quality_threshold(
                "alignment", "heel_lift_ratio_max", rules.get("heel_lift_ratio", 0.1)
            )
            if heel_lift is not None and heel_lift > heel_max:
                desc = self._issue_description(
                    "heel_lift",
                    f"脚跟抬起比例 {heel_lift:.2f}，标准上限 {heel_max:.2f}",
                )
                warnings.append(desc)
                error_details.append({"type": "heel_lift", "description": desc})

        # 5. Insufficient depth (only in BOTTOM state, use filtered angle)
        if "insufficient_depth" in metrics and self.state == SquatState.BOTTOM:
            shallow_angle = self._quality_threshold(
                "depth", "shallow_angle", rules.get("shallow_squat_angle", 130)
            )
            if filtered_knee > shallow_angle:
                desc = self._issue_description(
                    "insufficient_depth",
                    f"底部膝角 {filtered_knee:.1f}°，浅蹲阈值 {shallow_angle:.1f}°",
                )
                warnings.append(desc)
                error_details.append({"type": "insufficient_depth", "description": desc})

        # 6. Left-right knee asymmetry (front view metric)
        if "knee_asymmetry" in metrics:
            left_knee = geo.get("left_knee_angle")
            right_knee = geo.get("right_knee_angle")
            if left_knee is not None and right_knee is not None:
                asymmetry = abs(left_knee - right_knee)
                asymmetry_threshold = self._quality_threshold(
                    "alignment",
                    "knee_asymmetry_abs_max",
                    rules.get("knee_asymmetry_threshold", 15.0),
                )
                if asymmetry > asymmetry_threshold:
                    desc = self._issue_description(
                        "knee_asymmetry",
                        f"左右膝角差 {asymmetry:.1f}°，标准上限 {asymmetry_threshold:.1f}°",
                    )
                    warnings.append(desc)
                    error_details.append({"type": "knee_asymmetry", "description": desc})

        return errors, warnings, error_details

    def update(self, geo: Dict, view_mode: str = "front",
               enabled_metrics: Optional[List[str]] = None) -> Dict:
        """
        Main update function, called per frame.
        Input: geometry.analyze() output dict.
        Returns: current state info dict.

        Args:
            geo: geometry analysis result
            view_mode: current camera view ("front", "side_left", "side_right", "oblique")
            enabled_metrics: list of metric types to check (None = check all, for backward compat)
        """
        self._state_updated_this_frame = False

        # filter
        raw_knee_angle = float(geo["knee_angle"])
        raw_knee_delta = (
            0.0 if self._prev_raw_knee_angle is None
            else raw_knee_angle - self._prev_raw_knee_angle
        )
        self._prev_raw_knee_angle = raw_knee_angle

        knee_angle = self.knee_filter.update(raw_knee_angle)
        hip_angle = self.hip_filter.update(geo["hip_angle"])
        knee_vel = self.knee_velocity.update(knee_angle)
        hip_vel = self.hip_velocity.update(hip_angle)
        rep_knee_angle = min(knee_angle, raw_knee_angle)

        # track knee velocity for smoothness scoring
        self._knee_velocities_in_rep.append(knee_vel)

        # update extreme values
        self.min_knee_angle_in_rep = min(self.min_knee_angle_in_rep, rep_knee_angle)
        ttd = geo.get("trunk_tibia_diff")
        if ttd is not None:
            self.max_trunk_tibia_diff_in_rep = max(
                self.max_trunk_tibia_diff_in_rep, abs(ttd)
            )
        tf = geo.get("trunk_forward")
        if tf is not None:
            self.max_trunk_forward_in_rep = max(
                self.max_trunk_forward_in_rep, tf
            )
        kv = geo.get("knee_valgus_ratio")
        if kv is not None:
            self.min_knee_valgus_ratio_in_rep = min(
                self.min_knee_valgus_ratio_in_rep, kv
            )

        self._update_state(knee_angle, hip_angle, knee_vel, hip_vel, raw_knee_angle, raw_knee_delta)

        # Bottom window tracking: only accumulate during BOTTOM/ASCENDING states
        # (during DESCENDING, min_knee hasn't stabilized yet — every frame would pass)
        if self.state in (SquatState.BOTTOM, SquatState.ASCENDING):
            bottom_geo = dict(geo)
            bottom_geo["knee_angle"] = rep_knee_angle
            self.bottom_window.update(rep_knee_angle, self.min_knee_angle_in_rep, bottom_geo)

        # Error detection (view-aware, use filtered values for stability)
        if self.state in (SquatState.DESCENDING, SquatState.BOTTOM, SquatState.ASCENDING):
            errors, warnings, error_details = self._check_errors(
                geo, knee_angle, hip_angle, view_mode, enabled_metrics
            )
        else:
            errors, warnings, error_details = [], [], []

        # stateconvert逻辑
        self._update_state(knee_angle, hip_angle, knee_vel, hip_vel, raw_knee_angle, raw_knee_delta)

        # updatecurrent rep bottomdata. Keep the deepest knee angle even when
        # the user rebounds from the bottom without a visible hold.
        if self.state in (SquatState.DESCENDING, SquatState.BOTTOM, SquatState.ASCENDING) and self.current_rep:
            if self.current_rep.bottom_knee_angle is None or rep_knee_angle < self.current_rep.bottom_knee_angle:
                self.current_rep.bottom_knee_angle = rep_knee_angle
                self.current_rep.bottom_trunk_tibia_diff = ttd
                self.current_rep.bottom_trunk_forward = tf

        self.frame_count_in_state += 1

        # structbuildreturninfo
        angles = {
            "knee_angle": knee_angle,
            "hip_angle": hip_angle,
            "trunk_tibia_diff": ttd,
            "trunk_forward": tf,
            "knee_valgus_ratio": kv,
            "heel_lift_ratio": geo.get("heel_lift_ratio"),
        }

        status = {
            "state": self.state.value,
            "rep_count": self.rep_count,
            "knee_angle": knee_angle,
            "hip_angle": hip_angle,
            "knee_velocity": knee_vel,
            "errors": errors,
            "warnings": warnings,
            "error_details": error_details,
            "angles": angles,
            "current_rep": self.current_rep.to_dict() if self.current_rep else None,
        }

        # Build sets of already-recorded error/warning types for dedup
        rep_error_types = set()
        rep_warning_types = set()
        if self.current_rep:
            for e in self.current_rep.errors:
                rep_error_types.add(e.split(":")[0] if ":" in e else e)
            for w in self.current_rep.warnings:
                rep_warning_types.add(w.split(":")[0] if ":" in w else w)

        # Fire callbacks and accumulate into rep (deduplicate on type key)
        for detail in error_details:
            etype = detail["type"]
            desc = detail["description"]

            if etype in ("trunk_forward_lean", "knee_valgus"):
                if self.on_error_detected:
                    self.on_error_detected(desc)
                if self.current_rep and etype not in rep_error_types:
                    self.current_rep.errors.append(f"{etype}: {desc}")
                    rep_error_types.add(etype)
            else:
                if self.current_rep and etype not in rep_warning_types:
                    self.current_rep.warnings.append(f"{etype}: {desc}")
                    rep_warning_types.add(etype)

            if self.on_error_with_data:
                self.on_error_with_data(etype, desc, angles)

        # Return accumulated errors/warnings from current rep for display
        # When no current_rep, build display from error_details (per-frame detection)
        if self.current_rep is None:
            frame_errors = [d["description"] for d in error_details
                           if d["type"] in ("trunk_forward_lean", "knee_valgus")]
            display_errors = frame_errors
        else:
            display_errors = [e.split(": ", 1)[1] if ": " in e else e for e in self.current_rep.errors]
        display_warnings = warnings if self.current_rep is None else [w.split(": ", 1)[1] if ": " in w else w for w in self.current_rep.warnings]

        status["errors"] = display_errors
        status["warnings"] = display_warnings

        return status

    def _update_state(self, knee_angle: float, hip_angle: float,
                      knee_vel: float, hip_vel: float,
                      raw_knee_angle: Optional[float] = None,
                      raw_knee_delta: float = 0.0):
        """stateconvertcore逻辑. """
        if getattr(self, "_state_updated_this_frame", False):
            return
        self._state_updated_this_frame = True

        standing = self.state_rules["standing"]
        descending = self.state_rules["descending"]
        bottom = self.state_rules["bottom"]
        ascending = self.state_rules["ascending"]
        standing_knee_min = self._phase_value("standing", "knee_angle_min", standing["knee_angle_min"])
        complete_knee_min = self._phase_value("complete", "knee_angle_min", standing_knee_min)
        descending_vel_max = self._phase_value(
            "descending", "knee_velocity_max", descending["knee_angle_velocity_threshold"]
        )
        bottom_knee_min = self._phase_value("bottom", "knee_angle_min", bottom["knee_angle_min"])
        bottom_knee_max = self._phase_value("bottom", "knee_angle_max", bottom["knee_angle_max"])
        ascending_vel_min = self._phase_value(
            "ascending", "knee_velocity_min", ascending["knee_angle_velocity_threshold"]
        )
        shallow_angle = self._quality_threshold(
            "depth", "shallow_angle", self.error_rules.get("shallow_squat_angle", 130)
        )
        raw_knee_angle = knee_angle if raw_knee_angle is None else raw_knee_angle
        state_knee_angle = min(knee_angle, raw_knee_angle)

        # cooldowncheck
        now = time.time()
        in_cooldown = (now - self.last_rep_end_time) < self.cooldown_seconds

        if self.state == SquatState.UNKNOWN:
            # 初始state: judgeYesNostanding
            if knee_angle > standing_knee_min:
                if self.standing_stable.update(True):
                    self._transition_to(SquatState.STANDING)

        elif self.state == SquatState.STANDING:
            # standing -> descending: knee_anglestart明显减small
            if knee_vel < descending_vel_max or raw_knee_delta < descending_vel_max:
                self._transition_to(SquatState.DESCENDING)

        elif self.state == SquatState.DESCENDING:
            # descending -> bottom: knee_angleenterinbottomrange, 且anglestable( 再明显descending)
            in_bottom_range = bottom_knee_min <= state_knee_angle <= bottom_knee_max
            velocity_slow = abs(knee_vel) < 1.0  # velocityconnnear0

            # Track min knee angle during descent for stability check
            self._desc_min_knee = min(self._desc_min_knee, state_knee_angle)

            # anglestableitem件: currentangle mostnearminangleBadvalueless5度
            angle_stable = abs(state_knee_angle - self._desc_min_knee) < 5.0
            raw_rebounded = raw_knee_delta > 1.0

            if in_bottom_range and (velocity_slow or raw_rebounded) and angle_stable:
                if self.bottom_stable.update(True):
                    self._transition_to(SquatState.BOTTOM)
                    self._desc_min_knee = 180.0  # reset
            # ifknee_anglealreadylessminvalue(蹲得passdeep), alsoenterinbottom
            elif knee_angle < bottom_knee_min:
                if self.bottom_stable.update(True):
                    self._transition_to(SquatState.BOTTOM)
                    self._desc_min_knee = 180.0  # reset
            elif knee_vel > ascending_vel_min or raw_rebounded:
                if self._desc_min_knee <= shallow_angle:
                    self._transition_to(SquatState.BOTTOM)
                else:
                    self._transition_to(SquatState.ASCENDING)
                self._desc_min_knee = 180.0

        elif self.state == SquatState.BOTTOM:
            # bottom -> ascending: knee_anglestart增big
            if knee_vel > ascending_vel_min or raw_knee_delta > 1.0:
                self._transition_to(SquatState.ASCENDING)
            # 超when保护:  bottom停留pass久
            elif self.frame_count_in_state > bottom["duration_max_frames"]:
                self._transition_to(SquatState.ASCENDING)

        elif self.state == SquatState.ASCENDING:
            # ascending -> standing: 回tostandinganglerange
            if max(knee_angle, raw_knee_angle) > complete_knee_min:
                if self.standing_stable.update(True):
                    if not in_cooldown:
                        self._transition_to(SquatState.STANDING)
                    else:
                        # cooldown , 保hold ascendingstatedirecttocooldownendbeam
                        pass

    def get_session_summary(self) -> Dict:
        """getgetwholetrainingsession 汇totaldata. """
        if not self.rep_history:
            return {"total_reps": 0, "message": "尚未completeanyredup"}

        scores = [r.overall_score for r in self.rep_history]
        durations = [r.duration_ms for r in self.rep_history if r.duration_ms]

        from collections import Counter
        # Normalize errors to type-only keys for summary (strip "type: description" → "type")
        error_types = []
        for r in self.rep_history:
            for e in r.errors:
                error_types.append(e.split(":")[0] if ":" in e else e)
        error_counts = Counter(error_types)

        return {
            "total_reps": len(self.rep_history),
            "avg_score": sum(scores) / len(scores),
            "best_score": max(scores),
            "worst_score": min(scores),
            "avg_duration_ms": sum(durations) / len(durations) if durations else 0,
            "error_summary": dict(error_counts),
            "reps": [r.to_dict() for r in self.rep_history],
        }
