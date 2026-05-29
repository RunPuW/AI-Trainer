"""
overlay.py - can视ize langaudiofeedbackmodule
use OpenCV  videoframeupperdrawskeleton, angle, stateinfo, 
anduse pyttsx3 enterrowrealwhenlangaudiofeedback. 
"""

import time
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np

# 尝试import pyttsx3, if canuseruleuse备usesquare案
try:
    import pyttsx3
    _TTS_AVAILABLE = True
except ImportError:
    _TTS_AVAILABLE = False


# colordefine (B, G, R)
COLOR_BONE = (128, 128, 128)       # skeletonlineitem
COLOR_CORRECT = (0, 255, 0)        # correct/normal
COLOR_WARNING = (0, 255, 255)      # warning
COLOR_ERROR = (0, 0, 255)          # error
COLOR_TEXT = (255, 255, 255)       # textchar
COLOR_BG = (0, 0, 0)               # back景

# skeletonconnectdefine(MediaPipe 33 point)
SKELETON_CONNECTIONS = [
    (11, 12),  # left_shoulder-right_shoulder
    (11, 13),  # left_shoulder-leftelbow
    (13, 15),  # leftelbow-leftwrist
    (12, 14),  # right_shoulder-rightelbow
    (14, 16),  # rightelbow-rightwrist
    (11, 23),  # left_shoulder-left_hip
    (12, 24),  # right_shoulder-right_hip
    (23, 24),  # left_hip-right_hip
    (23, 25),  # left_hip-left_knee
    (25, 27),  # left_knee-leftankle
    (24, 26),  # right_hip-right_knee
    (26, 28),  # right_knee-rightankle
    (27, 29),  # leftankle-leftwith
    (29, 31),  # leftwith-leftfootsharp
    (28, 30),  # rightankle-rightwith
    (30, 32),  # rightwith-rightfootsharp
]


class FeedbackManager:
    """
    feedbackmanageer: 负责langaudio播报 画面textcharprovideshow. 
    usecooldowntimeavoidredup播报. 
    """

    def __init__(self, cooldown_seconds: float = 3.0):
        self.cooldown_seconds = cooldown_seconds
        self.last_spoken: Dict[str, float] = {}
        self.tts_engine = None

        if _TTS_AVAILABLE:
            try:
                self.tts_engine = pyttsx3.init()
                self.tts_engine.setProperty("rate", 180)  # lang速
                self.tts_engine.setProperty("volume", 0.9)
            except Exception:
                self.tts_engine = None

    def speak(self, text: str, key: Optional[str] = None):
        """
        langaudio播报textthis. 
        key used_forcooldownctrlmake, same key  cooldowntimeinner willredup播报. 
        """
        now = time.time()
        cache_key = key or text

        if cache_key in self.last_spoken:
            if now - self.last_spoken[cache_key] < self.cooldown_seconds:
                return

        self.last_spoken[cache_key] = now

        if self.tts_engine:
            self.tts_engine.say(text)
            self.tts_engine.runAndWait()

    def speak_async(self, text: str, key: Optional[str] = None):
        """异步langaudio播报( 阻plugmainline程, but pyttsx3 thisbodycancan仍 阻plug). """
        # 简singlereal现: directconncall speak
        # 如require真correct异步, can改use threading
        self.speak(text, key)

    def reset(self):
        self.last_spoken.clear()


class OverlayRenderer:
    """
    OpenCV 画面renderer. 
    负责drawskeleton, anglemark注, state面boardetc. 
    """

    def __init__(self, feedback_cooldown: float = 3.0):
        self.feedback = FeedbackManager(cooldown_seconds=feedback_cooldown)
        self.frame_width = 640
        self.frame_height = 480

    def set_frame_size(self, width: int, height: int):
        self.frame_width = width
        self.frame_height = height

    def draw_skeleton(self, frame: np.ndarray, landmarks,
                      visibility_threshold: float = 0.5):
        """
         frameupperdrawskeleton连line. 
        landmarks: MediaPipe PoseLandmarkerResult    landmarks
        """
        h, w = frame.shape[:2]

        # draw连line
        for start_idx, end_idx in SKELETON_CONNECTIONS:
            if start_idx >= len(landmarks) or end_idx >= len(landmarks):
                continue
            lm1 = landmarks[start_idx]
            lm2 = landmarks[end_idx]

            if lm1.visibility < visibility_threshold or lm2.visibility < visibility_threshold:
                continue

            p1 = (int(lm1.x * w), int(lm1.y * h))
            p2 = (int(lm2.x * w), int(lm2.y * h))
            cv2.line(frame, p1, p2, COLOR_BONE, 2)

        # drawjointpoint
        for idx, lm in enumerate(landmarks):
            if lm.visibility < visibility_threshold:
                continue
            cx, cy = int(lm.x * w), int(lm.y * h)
            cv2.circle(frame, (cx, cy), 3, COLOR_CORRECT, -1)

    def draw_angle_arc(self, frame: np.ndarray,
                       center: Tuple[int, int],
                       p1: Tuple[int, int],
                       p2: Tuple[int, int],
                       angle: float,
                       color: Tuple[int, int, int] = COLOR_CORRECT):
        """
         jointhandledrawangle弧line numvalue. 
        """
        # draw弧line
        radius = 20
        # calculate起始 终止angle
        angle1 = np.degrees(np.arctan2(p1[1] - center[1], p1[0] - center[0]))
        angle2 = np.degrees(np.arctan2(p2[1] - center[1], p2[0] - center[0]))

        # 确保draw Yesinnerangle
        if abs(angle1 - angle2) > 180:
            if angle1 < angle2:
                angle1 += 360
            else:
                angle2 += 360

        start_angle = min(angle1, angle2)
        end_angle = max(angle1, angle2)

        cv2.ellipse(frame, center, (radius, radius), 0,
                    start_angle, end_angle, color, 2)

        # drawanglenumvalue
        text = f"{angle:.0f}"
        text_size = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)[0]
        text_pos = (center[0] - text_size[0] // 2, center[1] - radius - 5)
        cv2.putText(frame, text, text_pos, cv2.FONT_HERSHEY_SIMPLEX,
                    0.5, color, 2)

    def draw_knee_angles(self, frame: np.ndarray, geo: Dict, landmarks):
        """ kneehandledrawknee_angle. """
        h, w = frame.shape[:2]

        # left_knee
        left_knee = landmarks[25] if len(landmarks) > 25 else None
        left_hip = landmarks[23] if len(landmarks) > 23 else None
        left_ankle = landmarks[27] if len(landmarks) > 27 else None
        if left_knee and left_hip and left_ankle:
            c = (int(left_knee.x * w), int(left_knee.y * h))
            p1 = (int(left_hip.x * w), int(left_hip.y * h))
            p2 = (int(left_ankle.x * w), int(left_ankle.y * h))
            angle = geo.get("left_knee_angle", 0)
            color = COLOR_CORRECT if angle > 100 else COLOR_WARNING
            self.draw_angle_arc(frame, c, p1, p2, angle, color)

        # right_knee
        right_knee = landmarks[26] if len(landmarks) > 26 else None
        right_hip = landmarks[24] if len(landmarks) > 24 else None
        right_ankle = landmarks[28] if len(landmarks) > 28 else None
        if right_knee and right_hip and right_ankle:
            c = (int(right_knee.x * w), int(right_knee.y * h))
            p1 = (int(right_hip.x * w), int(right_hip.y * h))
            p2 = (int(right_ankle.x * w), int(right_ankle.y * h))
            angle = geo.get("right_knee_angle", 0)
            color = COLOR_CORRECT if angle > 100 else COLOR_WARNING
            self.draw_angle_arc(frame, c, p1, p2, angle, color)

    def draw_status_panel(self, frame: np.ndarray, status: Dict):
        """
         画面leftupperangledrawstate面board. 
        """
        panel_x, panel_y = 10, 10
        line_height = 25
        panel_width = 280

        # back景
        lines = []
        state = status.get("state", "unknown")
        rep_count = status.get("rep_count", 0)
        knee_angle = status.get("knee_angle", 0)
        errors = status.get("errors", [])
        warnings = status.get("warnings", [])

        lines.append(f"state: {state.upper()}")
        lines.append(f"count: {rep_count}")
        lines.append(f"knee_angle: {knee_angle:.1f}")

        if errors:
            lines.append(f"error: {', '.join(errors[:2])}")
        if warnings:
            lines.append(f"provideshow: {', '.join(warnings[:2])}")

        panel_height = len(lines) * line_height + 10

        overlay = frame.copy()
        cv2.rectangle(overlay,
                      (panel_x, panel_y),
                      (panel_x + panel_width, panel_y + panel_height),
                      COLOR_BG, -1)
        cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)

        # textcharcolorbased_onstatechangeize
        text_color = COLOR_CORRECT
        if errors:
            text_color = COLOR_ERROR
        elif warnings:
            text_color = COLOR_WARNING

        for i, line in enumerate(lines):
            y = panel_y + 20 + i * line_height
            cv2.putText(frame, line, (panel_x + 10, y),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, text_color, 2)

    def draw_depth_bar(self, frame: np.ndarray, knee_angle: float):
        """
         画面right侧drawdown蹲depthrefshowitem. 
        """
        bar_x = self.frame_width - 40
        bar_top = 50
        bar_bottom = self.frame_height - 50
        bar_width = 20

        # back景item
        cv2.rectangle(frame,
                      (bar_x, bar_top),
                      (bar_x + bar_width, bar_bottom),
                      (50, 50, 50), -1)

        # angle映射toheight(180° top部, 80° bottom)
        min_angle, max_angle = 80, 180
        ratio = 1.0 - (knee_angle - min_angle) / (max_angle - min_angle)
        ratio = max(0, min(1, ratio))

        fill_height = int((bar_bottom - bar_top) * ratio)
        fill_y = bar_bottom - fill_height

        # color: based_ondepthchangeize
        if knee_angle <= 115:
            color = COLOR_CORRECT  # sufficientdeep
        elif knee_angle <= 130:
            color = COLOR_WARNING  # 偏shallow
        else:
            color = COLOR_ERROR    # tooshallow

        cv2.rectangle(frame,
                      (bar_x, fill_y),
                      (bar_x + bar_width, bar_bottom),
                      color, -1)

        # mark记mark准line(115°)
        std_ratio = 1.0 - (115 - min_angle) / (max_angle - min_angle)
        std_y = int(bar_bottom - (bar_bottom - bar_top) * std_ratio)
        cv2.line(frame, (bar_x - 5, std_y), (bar_x + bar_width + 5, std_y),
                 COLOR_TEXT, 2)

        # mark签
        cv2.putText(frame, "deep", (bar_x - 30, bar_bottom - 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, COLOR_TEXT, 1)
        cv2.putText(frame, "shallow", (bar_x - 30, bar_top + 15),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, COLOR_TEXT, 1)

    def render(self, frame: np.ndarray, landmarks, geo: Dict, status: Dict) -> np.ndarray:
        """
        mainrenderfunction, group合place draw元素.
        """
        h, w = frame.shape[:2]
        self.set_frame_size(w, h)

        # 先在原始frame上drawskeleton(anglemark注), 再镜像翻转
        # 这样landmark坐标与frame坐标系一致, 翻转后skeleton与人体位置匹配
        if landmarks and len(landmarks) > 0:
            self.draw_skeleton(frame, landmarks)
            self.draw_knee_angles(frame, geo, landmarks)

        self.draw_status_panel(frame, status)
        self.draw_depth_bar(frame, status.get("knee_angle", 180))

        # langaudiofeedback
        errors = status.get("errors", [])
        warnings = status.get("warnings", [])

        for err in errors:
            self.feedback.speak_async(err, key=f"err_{err}")

        for warn in warnings:
            self.feedback.speak_async(warn, key=f"warn_{warn}")

        # 最后镜像翻转(self拍视anglemoreself然)
        frame = cv2.flip(frame, 1)

        return frame

    def render_summary(self, frame: np.ndarray, summary: Dict) -> np.ndarray:
        """
        trainingendbeambackdisplaytotalend画面.
        """
        h, w = frame.shape[:2]
        # 镜像翻转背景video (text在翻转后draw, 保证可读)
        frame = cv2.flip(frame, 1)

        # half透明黑色back景
        overlay = np.zeros_like(frame)
        cv2.rectangle(overlay, (0, 0), (w, h), COLOR_BG, -1)
        cv2.addWeighted(overlay, 0.8, frame, 0.2, 0, frame)

        lines = [
            "=== trainingtotalend ===",
            "",
            f"totalcount: {summary.get('total_reps', 0)}",
            f"averagescore: {summary.get('avg_score', 0):.1f}",
            f"best: {summary.get('best_score', 0):.1f}",
            f"worst: {summary.get('worst_score', 0):.1f}",
            f"averageusewhen: {summary.get('avg_duration_ms', 0)/1000:.1f}s",
            "",
            "常见error:",
        ]

        error_summary = summary.get("error_summary", {})
        if error_summary:
            for err, count in error_summary.items():
                lines.append(f"  {err}: {count}rep")
        else:
            lines.append("  none")

        lines.append("")
        lines.append("按 Q exit")

        start_y = h // 2 - len(lines) * 15
        for i, line in enumerate(lines):
            y = start_y + i * 30
            x = w // 2 - 150
            cv2.putText(frame, line, (x, y),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, COLOR_TEXT, 2)

        return frame
