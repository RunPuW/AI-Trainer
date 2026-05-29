"""
frame_capture.py - errorframecapturemodule
 detectiontomovement mark准whencaptureframeimage, used_fortrainingreportdisplay. 
"""

import os
import time
import uuid
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, field

import cv2
import numpy as np


@dataclass
class CapturedFrame:
    """capture framedata"""
    frame_id: str
    timestamp: float
    error_type: str
    error_description: str
    rep_number: int
    frame_data: np.ndarray
    angles: Dict[str, float]
    state: str
    saved_path: Optional[str] = None

    def to_dict(self) -> Dict:
        """convertaschar典( containsimagedata)"""
        return {
            "frame_id": self.frame_id,
            "timestamp": self.timestamp,
            "error_type": self.error_type,
            "error_description": self.error_description,
            "rep_number": self.rep_number,
            "angles": self.angles,
            "state": self.state,
            "saved_path": self.saved_path,
        }


class FrameCaptureManager:
    """
    framecapturemanageer

    功can: 
    1. errorframeselfactioncapture
    2. sameerrorcooldown(avoidredupcapture)
    3. perreptraining maxcapturenumamount限make
    4. framestore储 manage
    """

    def __init__(
        self,
        output_dir: str = "captured_frames",
        cooldown_seconds: float = 3.0,
        max_captures_per_error: int = 5,
        max_total_captures: int = 50,
        image_quality: int = 85,
        max_width: int = 640,
    ):
        self.output_dir = output_dir
        self.cooldown_seconds = cooldown_seconds
        self.max_captures_per_error = max_captures_per_error
        self.max_total_captures = max_total_captures
        self.image_quality = image_quality
        self.max_width = max_width

        # capturelog
        self.captures: List[CapturedFrame] = []
        self.last_capture_time: Dict[str, float] = {}  # error_type -> timestamp
        self.error_count: Dict[str, int] = {}  # error_type -> count

        # createoutputdirectory
        os.makedirs(output_dir, exist_ok=True)

        # currenttrainingsessionID
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")

    def reset(self):
        """resetcapturemanageer(newtrainingsession)"""
        self.captures.clear()
        self.last_capture_time.clear()
        self.error_count.clear()
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")

    def should_capture(self, error_type: str) -> bool:
        """
        judgeYesNoshouldcapturecurrentframe

        Args:
            error_type: errortype

        Returns:
            YesNoshouldcapture
        """
        # checktotalnumamount限make
        if len(self.captures) >= self.max_total_captures:
            return False

        # checksingleclasserrornumamount限make
        if self.error_count.get(error_type, 0) >= self.max_captures_per_error:
            return False

        # checkcooldowntime
        last_time = self.last_capture_time.get(error_type, 0)
        if time.time() - last_time < self.cooldown_seconds:
            return False

        return True

    def capture_frame(
        self,
        frame: np.ndarray,
        error_type: str,
        error_description: str,
        rep_number: int,
        angles: Dict[str, float],
        state: str,
        draw_overlay: bool = True,
    ) -> Optional[CapturedFrame]:
        """
        capturecurrentframe

        Args:
            frame: 原始frameimage
            error_type: errortype
            error_description: error描述
            rep_number: currentredupcount
            angles: currentangledata
            state: currentstate
            draw_overlay: YesNo frameupperdrawinfo覆lidlayer

        Returns:
            CapturedFrame to象, if needcapturerulereturn None
        """
        if not self.should_capture(error_type):
            return None

        # Copyframe(avoidmodify原始data)
        capture_frame = frame.copy()

        # drawinfo覆lidlayer
        if draw_overlay:
            capture_frame = self._draw_overlay(
                capture_frame, error_type, error_description,
                rep_number, angles, state
            )

        # 调整size(ifneed)
        if capture_frame.shape[1] > self.max_width:
            ratio = self.max_width / capture_frame.shape[1]
            capture_frame = cv2.resize(capture_frame, None, fx=ratio, fy=ratio)

        # createcaptureto象
        captured = CapturedFrame(
            frame_id=str(uuid.uuid4())[:8],
            timestamp=time.time(),
            error_type=error_type,
            error_description=error_description,
            rep_number=rep_number,
            frame_data=capture_frame,
            angles=angles,
            state=state,
        )

        # updatelog
        self.captures.append(captured)
        self.last_capture_time[error_type] = time.time()
        self.error_count[error_type] = self.error_count.get(error_type, 0) + 1

        return captured

    def save_captures(self, session_id: Optional[str] = None) -> List[str]:
        """
        saveplace capture frametofile

        Args:
            session_id: sessionID, ifas None ruleusecurrentsessionID

        Returns:
            save filepathlist
        """
        sid = session_id or self.session_id
        session_dir = os.path.join(self.output_dir, sid)
        os.makedirs(session_dir, exist_ok=True)

        saved_paths = []
        for capture in self.captures:
            filename = f"{capture.frame_id}_{capture.error_type}.jpg"
            filepath = os.path.join(session_dir, filename)

            # saveimage
            cv2.imwrite(filepath, capture.frame_data,
                       [cv2.IMWRITE_JPEG_QUALITY, self.image_quality])

            capture.saved_path = filepath
            saved_paths.append(filepath)

        return saved_paths

    def get_captures_for_report(self) -> List[Dict]:
        """
        getgetused_forreport capturedata

        Returns:
            capturedatalist(packagecontainspath 元data)
        """
        return [capture.to_dict() for capture in self.captures]

    def get_capture_by_id(self, frame_id: str) -> Optional[CapturedFrame]:
        """based_onIDgetgetcapture frame"""
        for capture in self.captures:
            if capture.frame_id == frame_id:
                return capture
        return None

    def get_error_summary(self) -> Dict[str, int]:
        """getgeterrorstatistics"""
        return dict(self.error_count)

    def _draw_overlay(
        self,
        frame: np.ndarray,
        error_type: str,
        error_description: str,
        rep_number: int,
        angles: Dict[str, float],
        state: str,
    ) -> np.ndarray:
        """ frameupperdrawinfo覆lidlayer"""
        h, w = frame.shape[:2]

        # half透明back景item
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (w, 120), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)

        # errortype(红色bigchar)
        cv2.putText(frame, f"error: {error_type}", (10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)

        # error描述
        cv2.putText(frame, error_description, (10, 55),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

        # angleinfo
        angle_text = f"knee_angle: {angles.get('knee_angle', 0):.1f}° | hip_angle: {angles.get('hip_angle', 0):.1f}°"
        cv2.putText(frame, angle_text, (10, 80),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)

        # state count
        state_text = f"state: {state} | no {rep_number} rep"
        cv2.putText(frame, state_text, (10, 105),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)

        # time戳
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cv2.putText(frame, timestamp, (w - 200, h - 10),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (150, 150, 150), 1)

        return frame

    def create_mosaic(
        self,
        capture_ids: Optional[List[str]] = None,
        cols: int = 3,
        thumb_width: int = 300,
    ) -> Optional[np.ndarray]:
        """
        createcaptureframe mosaic(used_forreportdisplay)

        Args:
            capture_ids: needpackagecontains frameIDlist, Noneruleuseplace frame
            cols: perrowcolnum
            thumb_width: thumbnailwidth

        Returns:
            mosaicimage
        """
        captures = self.captures
        if capture_ids:
            captures = [c for c in captures if c.frame_id in capture_ids]

        if not captures:
            return None

        # calculatethumbnailsize
        images = []
        for capture in captures:
            img = capture.frame_data.copy()
            ratio = thumb_width / img.shape[1]
            thumb = cv2.resize(img, None, fx=ratio, fy=ratio)
            images.append(thumb)

        # calculate网格
        rows = (len(images) + cols - 1) // cols
        thumb_h, thumb_w = images[0].shape[:2]

        # create画布
        canvas = np.zeros((rows * thumb_h, cols * thumb_w, 3), dtype=np.uint8)

        # 填充image
        for i, img in enumerate(images):
            row = i // cols
            col = i % cols
            y = row * thumb_h
            x = col * thumb_w
            canvas[y:y+thumb_h, x:x+thumb_w] = img

        return canvas
