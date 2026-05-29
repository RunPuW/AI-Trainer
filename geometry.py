"""
geometry.py - geometrycalculatemodule
based_on MediaPipe 33 item姿态landmark, calculatesquatplacerequire angle, 距离 ratio. 
place anglereturnvalueas度(°). 
"""

import math
from typing import Dict, List, Optional, Tuple
import numpy as np


# MediaPipe Pose Landmark searchpull_up(partial常use)
class PoseLandmark:
    NOSE = 0
    LEFT_SHOULDER = 11
    RIGHT_SHOULDER = 12
    LEFT_ELBOW = 13
    RIGHT_ELBOW = 14
    LEFT_WRIST = 15
    RIGHT_WRIST = 16
    LEFT_HIP = 23
    RIGHT_HIP = 24
    LEFT_KNEE = 25
    RIGHT_KNEE = 26
    LEFT_ANKLE = 27
    RIGHT_ANKLE = 28
    LEFT_HEEL = 29
    RIGHT_HEEL = 30
    LEFT_FOOT_INDEX = 31
    RIGHT_FOOT_INDEX = 32


def calculate_angle(a: Tuple[float, float], b: Tuple[float, float], c: Tuple[float, float]) -> float:
    """
    calculate三point形成 夹angle(  b astoppoint). 
    returnanglevalue 0°-180°. 
    """
    ba = np.array([a[0] - b[0], a[1] - b[1]])
    bc = np.array([c[0] - b[0], c[1] - b[1]])

    cos_angle = np.dot(ba, bc) / (np.linalg.norm(ba) * np.linalg.norm(bc) + 1e-6)
    cos_angle = np.clip(cos_angle, -1.0, 1.0)
    angle = np.degrees(np.arccos(cos_angle))
    return float(angle)


def calculate_vector_angle(v1: Tuple[float, float], v2: Tuple[float, float]) -> float:
    """
    calculate两itemtowardamountmid 夹angle. 
    returnanglevalue 0°-180°. 
    """
    vec1 = np.array(v1)
    vec2 = np.array(v2)
    cos_angle = np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2) + 1e-6)
    cos_angle = np.clip(cos_angle, -1.0, 1.0)
    return float(np.degrees(np.arccos(cos_angle)))


def calculate_tilt_angle(p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
    """
    Calculate tilt angle of a line segment relative to the upward vertical direction.

    In image coordinates (y increases downward):
      - Positive angle = rightward lean
      - Negative angle = leftward lean
      - Vertical (p1 above p2) = 180 degrees (downward direction)
      - Horizontal = +/- 90 degrees

    Returns signed angle in degrees (-180 to 180).
    """
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]  # image coords: y increases downward
    return math.degrees(math.atan2(dx, -dy))


def get_landmark_xy(landmarks, idx: int) -> Optional[Tuple[float, float]]:
    """
    from MediaPipe landmarks  providegetref定searchpull_up  (x, y) sitmark. 
    landmarks Yes PoseLandmarkerResult    NormalizedLandmark list. 
    """
    if landmarks is None or idx >= len(landmarks):
        return None
    lm = landmarks[idx]
    return (lm.x, lm.y)


def get_midpoint(p1: Optional[Tuple[float, float]], p2: Optional[Tuple[float, float]]) -> Optional[Tuple[float, float]]:
    """calculate两point  point. """
    if p1 is None or p2 is None:
        return None
    return ((p1[0] + p2[0]) / 2.0, (p1[1] + p2[1]) / 2.0)


class SquatGeometry:
    """
    squatmovementgeometryanalysiser. 
    perframeinput MediaPipe   33 itemlandmark, calculateplace need geometry特征. 
    """

    def __init__(self):
        self.last_valid_data: Optional[Dict] = None

    @staticmethod
    def _signed_knee_deviation(hip: Tuple[float, float],
                                knee: Tuple[float, float],
                                ankle: Tuple[float, float]) -> float:
        """
        Signed perpendicular distance from knee point to hip-ankle line,
        normalized by leg length (hip-ankle distance).

        Negative = knee deviates toward body midline (valgus direction).
        Positive = knee deviates outward.
        """
        dx = ankle[0] - hip[0]
        dy = ankle[1] - hip[1]
        leg_len = math.sqrt(dx * dx + dy * dy)
        if leg_len < 1e-6:
            return 0.0
        # Cross product: (knee - hip) x (ankle - hip)
        # In image coords (y down), sign indicates left/right deviation
        cross = (knee[0] - hip[0]) * dy - (knee[1] - hip[1]) * dx
        return cross / leg_len

    def analyze(self, landmarks) -> Optional[Dict]:
        """
        analysis frame姿态data, returnpackagecontainsplace geometry特征 char典. 
        iflandmark缺失, return None. 
        """
        # providegetclose键sitmark
        left_shoulder = get_landmark_xy(landmarks, PoseLandmark.LEFT_SHOULDER)
        right_shoulder = get_landmark_xy(landmarks, PoseLandmark.RIGHT_SHOULDER)
        left_hip = get_landmark_xy(landmarks, PoseLandmark.LEFT_HIP)
        right_hip = get_landmark_xy(landmarks, PoseLandmark.RIGHT_HIP)
        left_knee = get_landmark_xy(landmarks, PoseLandmark.LEFT_KNEE)
        right_knee = get_landmark_xy(landmarks, PoseLandmark.RIGHT_KNEE)
        left_ankle = get_landmark_xy(landmarks, PoseLandmark.LEFT_ANKLE)
        right_ankle = get_landmark_xy(landmarks, PoseLandmark.RIGHT_ANKLE)
        left_heel = get_landmark_xy(landmarks, PoseLandmark.LEFT_HEEL)
        right_heel = get_landmark_xy(landmarks, PoseLandmark.RIGHT_HEEL)
        left_foot_index = get_landmark_xy(landmarks, PoseLandmark.LEFT_FOOT_INDEX)
        right_foot_index = get_landmark_xy(landmarks, PoseLandmark.RIGHT_FOOT_INDEX)

        # checknecessarypointYesNostore 
        required = [left_shoulder, right_shoulder, left_hip, right_hip,
                    left_knee, right_knee, left_ankle, right_ankle]
        if any(p is None for p in required):
            return None

        # calculate point(代tablebodybody line)
        shoulder_mid = get_midpoint(left_shoulder, right_shoulder)
        hip_mid = get_midpoint(left_hip, right_hip)
        knee_mid = get_midpoint(left_knee, right_knee)
        ankle_mid = get_midpoint(left_ankle, right_ankle)

        # === coreanglecalculate ===

        # 1. knee_jointangle(bigleg smallleg夹angle)
        left_knee_angle = calculate_angle(left_hip, left_knee, left_ankle)
        right_knee_angle = calculate_angle(right_hip, right_knee, right_ankle)
        knee_angle = (left_knee_angle + right_knee_angle) / 2.0

        # 2. hip_jointangle(trunk bigleg夹angle)
        left_hip_angle = calculate_angle(left_shoulder, left_hip, left_knee)
        right_hip_angle = calculate_angle(right_shoulder, right_hip, right_knee)
        hip_angle = (left_hip_angle + right_hip_angle) / 2.0

        # 3. trunktiltleanangle(肩-hip_连line相regarding垂directdirection tiltlean)
        trunk_tilt = calculate_tilt_angle(shoulder_mid, hip_mid)

        # 4. tibiatiltleanangle(knee_-ankle连line相regarding垂directdirection tiltlean)
        left_tibia_tilt = calculate_tilt_angle(left_knee, left_ankle)
        right_tibia_tilt = calculate_tilt_angle(right_knee, right_ankle)
        tibia_tilt = (left_tibia_tilt + right_tibia_tilt) / 2.0

        # 5. trunk-tibiaBadvalue(trunk-tibia angle)
        trunk_tibia_diff = trunk_tilt - tibia_tilt

        # 6. trunkforward_leanangle( hip_astoppoint, 肩-hip_ 垂directtowarddowndirection 夹angle)
        # this里directconnuse trunk_tilt tableshowforward_lean程度
        trunk_forward = trunk_tilt

        # === knee_valgusdetection ===
        knee_valgus_ratio = None
        if left_knee and right_knee and left_foot_index and right_foot_index:
            knee_width = abs(left_knee[0] - right_knee[0])
            foot_width = abs(left_foot_index[0] - right_foot_index[0])
            if foot_width > 1e-6:
                knee_valgus_ratio = knee_width / foot_width

        # === signed knee deviation (primary valgus metric) ===
        left_knee_dev = self._signed_knee_deviation(left_hip, left_knee, left_ankle)
        right_knee_dev = self._signed_knee_deviation(right_hip, right_knee, right_ankle)
        # For a person facing the camera: left knee dev negative = valgus (toward midline),
        # right knee dev negative = valgus (toward midline).
        # Both knees caving inward → both deviations negative → avg negative.
        knee_deviation_avg = (left_knee_dev + right_knee_dev) / 2.0

        # === stance width ratio (ankle width / shoulder width, front view metric) ===
        shoulder_width = abs(left_shoulder[0] - right_shoulder[0])
        ankle_width = abs(left_ankle[0] - right_ankle[0])
        stance_width_ratio = None
        if shoulder_width > 1e-6:
            stance_width_ratio = ankle_width / shoulder_width

        # === heel抬起detection ===
        # In image coords (y down): ankle.y > heel.y normally.
        # When heel lifts, heel.y decreases -> (ankle.y - heel.y) increases.
        # So positive avg_drop means heel is lifting.
        heel_lift_ratio = None
        if left_heel and right_heel and left_ankle and right_ankle:
            # calculateheel footankle 垂direct距离ratio
            left_heel_drop = left_ankle[1] - left_heel[1]
            right_heel_drop = right_ankle[1] - right_heel[1]
            avg_drop = (left_heel_drop + right_heel_drop) / 2.0
            # 归 ize( smallleglengthas参考)
            shin_length = math.sqrt(
                (knee_mid[0] - ankle_mid[0])**2 + (knee_mid[1] - ankle_mid[1])**2
            ) if knee_mid and ankle_mid else 1.0
            if shin_length > 1e-6:
                heel_lift_ratio = max(0, avg_drop) / shin_length

        # === down蹲depth辅助refmark ===
        # hip垂directposition相regardingfootankle 归 izeheight
        hip_height_ratio = None
        if hip_mid and ankle_mid and shoulder_mid:
            total_height = abs(shoulder_mid[1] - ankle_mid[1])
            hip_height = abs(hip_mid[1] - ankle_mid[1])
            if total_height > 1e-6:
                hip_height_ratio = hip_height / total_height

        result = {
            # 原始sitmark(debuguse)
            "shoulder_mid": shoulder_mid,
            "hip_mid": hip_mid,
            "knee_mid": knee_mid,
            "ankle_mid": ankle_mid,

            # coreangle
            "left_knee_angle": left_knee_angle,
            "right_knee_angle": right_knee_angle,
            "knee_angle": knee_angle,

            "left_hip_angle": left_hip_angle,
            "right_hip_angle": right_hip_angle,
            "hip_angle": hip_angle,

            # tiltleananalysis
            "trunk_tilt": trunk_tilt,
            "tibia_tilt": tibia_tilt,
            "trunk_tibia_diff": trunk_tibia_diff,
            "trunk_forward": trunk_forward,

            # errordetection
            "knee_valgus_ratio": knee_valgus_ratio,
            "heel_lift_ratio": heel_lift_ratio,

            # signed knee deviation (primary valgus metric)
            "left_knee_deviation": left_knee_dev,
            "right_knee_deviation": right_knee_dev,
            "knee_deviation_avg": knee_deviation_avg,

            # stance width (front view metric)
            "stance_width_ratio": stance_width_ratio,

            # 辅助refmark
            "hip_height_ratio": hip_height_ratio,
        }

        self.last_valid_data = result
        return result

    def get_last_valid(self) -> Optional[Dict]:
        """getgetmostnear rep 效 analysisresult. """
        return self.last_valid_data
