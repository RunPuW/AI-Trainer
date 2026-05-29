"""
camera.py - Cyber Trainermain程序in口
use MediaPipe Pose Landmarker enterrowrealwhen姿态detection, 
end合geometryanalysis, FSM statemachine can视izefeedback, real现squatmovementknow别 assessment. 

runmethod:
    python camera.py

按键ctrlmake:
    Q - exit
    R - resetstatemachine
    S - savecurrentsessiondata
    D - 切换debuginfooutput
    L - generateAItrainingreport(needbacksideservicetask)
"""

import json
import os
import sys
import time
import asyncio
from datetime import datetime
from typing import Optional

import cv2
import numpy as np

# MediaPipe import
try:
    from mediapipe.tasks.python.vision import PoseLandmarker, PoseLandmarkerOptions
    from mediapipe.tasks.python import BaseOptions
    from mediapipe.tasks.python.vision import RunningMode
    _MEDIAPIPE_AVAILABLE = True
except ImportError:
    _MEDIAPIPE_AVAILABLE = False
    print("[error] not_installed mediapipe, pleaserun: pip install mediapipe")
    sys.exit(1)

# LLM bridgeimport
try:
    from camera_llm_bridge import LLMBridge
    _LLM_BRIDGE_AVAILABLE = True
except ImportError:
    _LLM_BRIDGE_AVAILABLE = False
    print("[warning] camera_llm_bridge not_installed, AIreport功can将 canuse")

from geometry import SquatGeometry
from fsm import SquatFSM, SquatState
from overlay import OverlayRenderer
from frame_capture import FrameCaptureManager
from view_classifier import ViewClassifier, get_enabled_metrics


class CyberTrainer:
    """
    Cyber Trainermainctrlmakeer. 
    coordinatecamera, MediaPipe, geometryanalysis, statemachine can视ize. 
    """

    def __init__(self, rules_path: str = "configs/movement_rules.json"):
        print("=" * 50)
        print("  cyber_trainer - squatmovementknow别system统")
        print("=" * 50)

        # loadconfig
        if not os.path.exists(rules_path):
            raise FileNotFoundError(f"configfile store : {rules_path}")

        with open(rules_path, "r", encoding="utf-8") as f:
            self.config = json.load(f)

        self.rules = self.config["movements"]["squat"]
        self.debug_mode = self.config["debug"]["print_frame_data"]

        # init MediaPipe Pose Landmarker
        self._init_mediapipe()

        # initmodule
        self.geometry = SquatGeometry()
        self.fsm = SquatFSM(rules_path)
        self.view_classifier = ViewClassifier(self.config.get("view_classifier", {}))
        self.view_mode = "auto"  # "auto", "front", "side"
        self.detected_view = "unknown"
        self.renderer = OverlayRenderer(
            feedback_cooldown=self.rules["error_thresholds"]["cooldown_seconds"]
        )

        # initframecapturemanageer
        self.frame_capture = FrameCaptureManager(
            output_dir="captured_frames",
            cooldown_seconds=self.rules["error_thresholds"]["cooldown_seconds"],
            max_captures_per_error=5,
            max_total_captures=50,
        )

        # camera
        self.cap: Optional[cv2.VideoCapture] = None
        self.frame_width = 640
        self.frame_height = 480
        self.fps = 30

        # sessiondata
        self.session_data = []
        self.running = False
        self.frame_count = 0

        # settingcallback
        self.fsm.on_state_change = self._on_state_change
        self.fsm.on_rep_complete = self._on_rep_complete
        self.fsm.on_error_detected = self._on_error_detected
        self.fsm.on_error_with_data = self._on_error_with_data

        # init LLM bridge(if_available)
        self.llm_bridge = None
        self.ai_report = None  # store储AIgenerate report
        if _LLM_BRIDGE_AVAILABLE:
            try:
                self.llm_bridge = LLMBridge(
                    api_url=os.getenv("BACKEND_URL", "http://localhost:8000"),
                    enabled=True
                )
                print("[info] AIreport功canalready启use")
            except Exception as e:
                print(f"[warning] LLMbridgeinitfailed: {e}")

        # currentframe(used_forframecapture)
        self.current_frame: Optional[np.ndarray] = None

        # log
        self.log_dir = self.config["debug"]["log_dir"]
        os.makedirs(self.log_dir, exist_ok=True)

    def _init_mediapipe(self):
        """init MediaPipe Pose Landmarker. """
        # selfactiondown载modelfile
        model_path = "pose_landmarker_full.task"
        if not os.path.exists(model_path):
            print(f"[info] downloading MediaPipe model...")
            self._download_model(model_path)

        options = PoseLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=model_path),
            running_mode=RunningMode.VIDEO,
            num_poses=1,
            min_pose_detection_confidence=0.5,
            min_pose_presence_confidence=0.5,
            min_tracking_confidence=0.5,
        )
        self.landmarker = PoseLandmarker.create_from_options(options)
        print("[info] MediaPipe Pose Landmarker initcomplete")

    def _download_model(self, model_path: str):
        """down载 MediaPipe pose landmarker model. """
        import urllib.request
        url = "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_full/float16/latest/pose_landmarker_full.task"
        try:
            urllib.request.urlretrieve(url, model_path)
            print(f"[info] modelalreadydown载to {model_path}")
        except Exception as e:
            print(f"[error] modeldown载failed: {e}")
            print("please手actiondown载and放置tocurrentdirectory:")
            print(url)
            sys.exit(1)

    def _on_state_change(self, old_state: SquatState, new_state: SquatState):
        """statechangeizecallback. """
        if self.debug_mode:
            print(f"[FSM] {old_state.value} -> {new_state.value}")

    def _on_rep_complete(self, rep):
        """complete repredup callback. """
        print(f"[redup #{rep.rep_number}] score: {rep.overall_score:.1f} | "
              f"bottomknee_angle: {rep.bottom_knee_angle:.1f}° | "
              f"error: {rep.errors if rep.errors else 'none'}")

    def _on_error_detected(self, error: str):
        """detectiontoerror callback. """
        if self.debug_mode:
            print(f"[error] {error}")

    def _on_error_with_data(self, error_type: str, error_description: str, angles: dict):
        """detectiontoerrorwhencaptureframe(带detaildata). """
        if self.current_frame is None:
            return

        captured = self.frame_capture.capture_frame(
            frame=self.current_frame,
            error_type=error_type,
            error_description=error_description,
            rep_number=self.fsm.rep_count,
            angles=angles,
            state=self.fsm.state.value,
            draw_overlay=True,
        )

        if captured and self.debug_mode:
            print(f"[capture] {error_type}: {error_description}")

    def start_camera(self, camera_id: int = 0):
        """启actioncamera. """
        self.cap = cv2.VideoCapture(camera_id)
        if not self.cap.isOpened():
            raise RuntimeError(f"none法opencamera {camera_id}")

        # settingsplit辨率
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.frame_width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.frame_height)
        self.cap.set(cv2.CAP_PROP_FPS, self.fps)

        actual_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        actual_fps = self.cap.get(cv2.CAP_PROP_FPS)

        print(f"[info] cameraStarted: {actual_width}x{actual_height} @ {actual_fps:.0f}fps")
        self.renderer.set_frame_size(actual_width, actual_height)

    def process_frame(self, frame: np.ndarray, timestamp_ms: int) -> np.ndarray:
        """
        handlereasonsingleframeimage. 
        """
        # savecurrentframe(used_forframecapture)
        self.current_frame = frame.copy()

        # MediaPipe detection
        mp_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        # note: VIDEO mockstyledownneed传in numpy array
        from mediapipe import Image as MPImage, ImageFormat
        mp_frame = MPImage(image_format=ImageFormat.SRGB, data=mp_image)
        result = self.landmarker.detect_for_video(mp_frame, timestamp_ms)

        # defaultstate
        status = {
            "state": "no_person",
            "rep_count": self.fsm.rep_count,
            "knee_angle": 180,
            "hip_angle": 180,
            "knee_velocity": 0,
            "errors": [],
            "warnings": [],
            "current_rep": None,
        }

        geo = None
        landmarks = None

        if result.pose_landmarks and len(result.pose_landmarks) > 0:
            landmarks = result.pose_landmarks[0]

            # geometry analysis
            geo = self.geometry.analyze(landmarks)

            if geo:
                # View classification
                view_info = self.view_classifier.classify(landmarks)
                if self.view_mode == "auto":
                    detected = view_info["view_mode"]
                else:
                    detected = self.view_mode
                self.detected_view = detected

                # Get enabled metrics for this view
                enabled_metrics, disabled_metrics = get_enabled_metrics(
                    detected, self.fsm.camera_views_config
                )

                # FSM update (view-aware)
                status = self.fsm.update(geo, detected, enabled_metrics)

                # debugoutput
                if self.debug_mode and self.frame_count % 10 == 0:
                    self._print_debug_info(geo, status)

                # logsessiondata
                self.session_data.append({
                    "frame": self.frame_count,
                    "timestamp_ms": timestamp_ms,
                    "geo": {k: v for k, v in geo.items()
                            if isinstance(v, (int, float, str, bool, type(None)))},
                    "state": status["state"],
                })

        # render
        rendered = self.renderer.render(frame, landmarks, geo or {}, status)
        return rendered

    def _print_debug_info(self, geo: dict, status: dict):
        """Print debug info."""
        print(f"[frame {self.frame_count}] "
              f"view={self.detected_view} | "
              f"state={status['state']} | "
              f"knee_angle={geo['knee_angle']:.1f}° | "
              f"hip_angle={geo['hip_angle']:.1f}° | "
              f"trunk-tibia={geo['trunk_tibia_diff']:.1f}° | "
              f"forward_lean={geo['trunk_forward']:.1f}° | "
              f"knee_dev={geo.get('knee_deviation_avg', 'N/A')}")

    def save_session(self) -> str:
        """savesessiondatatofile. """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{self.log_dir}/session_{timestamp}.json"

        data = {
            "timestamp": timestamp,
            "total_frames": self.frame_count,
            "summary": self.fsm.get_session_summary(),
            "frames": self.session_data[-1000:],  # only保留last1000frameavoidfilepassbig
            "captured_frames": self.frame_capture.get_captures_for_report(),
            "error_summary": self.frame_capture.get_error_summary(),
        }

        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"[info] sessiondataalreadysave: {filename}")
        return filename

    def run(self):
        """main循ring. """
        self.start_camera()
        self.running = True

        print(f"\n[View mode: {self.view_mode}]")
        print("\n[Controls]")
        print("  Q - exit")
        print("  R - reset statemachine")
        print("  S - save session data")
        print("  D - toggle debug mode")
        print("  L - generate AI training report")
        print("\nPlease stand in front of camera and start squatting...\n")

        start_time = time.time()

        try:
            while self.running:
                ret, frame = self.cap.read()
                if not ret:
                    print("[warning] framereadfailed")
                    time.sleep(0.01)
                    continue

                # calculatetime戳(毫秒)
                elapsed_ms = int((time.time() - start_time) * 1000)
                self.frame_count += 1

                # handlereasonframe
                rendered = self.process_frame(frame, elapsed_ms)

                # display
                cv2.imshow("cyber_trainer - squatknow别", rendered)

                # 按键handlereason
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q') or key == ord('Q'):
                    self.running = False
                elif key == ord('r') or key == ord('R'):
                    self.fsm.reset()
                    print("[info] statemachinealreadyreset")
                elif key == ord('s') or key == ord('S'):
                    self.save_session()
                elif key == ord('l') or key == ord('L'):
                    asyncio.run(self._generate_ai_report())
                elif key == ord('d') or key == ord('D'):
                    self.debug_mode = not self.debug_mode
                    print(f"[info] debugmockstyle: {'open启' if self.debug_mode else 'close'}")

        except KeyboardInterrupt:
            print("\n[info] user 断")
        finally:
            self.shutdown()

    async def _generate_ai_report(self):
        """generateAItrainingreport(异步)"""
        if not self.llm_bridge:
            print("[warning] AIreport功can未启use, please确保backsideservicetaskStarted")
            return
        
        summary = self.fsm.get_session_summary()
        if summary.get("total_reps", 0) == 0:
            print("[info] 暂nonetrainingdata, none法generatereport")
            return
        
        print("[info] correct generateAItrainingreport...")
        try:
            report = await self.llm_bridge.submit_session(summary)
            if report:
                self.ai_report = report
                self._display_ai_report(report)
                # langaudio播报no itemhighlights
                if report.get("highlights"):
                    self.renderer.feedback.speak(report["highlights"][0])
        except Exception as e:
            print(f"[error] reportgeneratefailed: {e}")

    def _display_ai_report(self, report: dict):
        """displayAIgenerate report"""
        print("\n" + "=" * 60)
        print("  AI trainingreport")
        print("=" * 60)
        print(f"overallscore: {report.get('overall_score', 0):.1f}/100")
        print("\nhighlights:")
        for h in report.get('highlights', []):
            print(f"  ✓ {h}")
        print("\nimprovements:")
        for c in report.get('corrections', []):
            print(f"  • {c}")
        print(f"\n恢dupsquare案:")
        print(f"  {report.get('recovery_plan', 'none')}")
        print("\ndownreptarget:")
        for g in report.get('next_session_goals', []):
            print(f"  → {g}")
        print("=" * 60)

    def shutdown(self):
        """清reason资源. """
        self.running = False

        # savecapture errorframe
        if self.frame_capture.captures:
            saved_paths = self.frame_capture.save_captures()
            print(f"\n[info] alreadysave {len(saved_paths)} frameserrorframeto captured_frames/ directory")

        # displaytotalend
        summary = self.fsm.get_session_summary()
        if summary.get("total_reps", 0) > 0:
            print("\n" + "=" * 50)
            print("  trainingtotalend")
            print("=" * 50)
            print(f"  totalcount: {summary['total_reps']}")
            print(f"  averagescore: {summary['avg_score']:.1f}")
            print(f"  best: {summary['best_score']:.1f}")
            print(f"  worst: {summary['worst_score']:.1f}")
            print(f"  常见error: {summary.get('error_summary', {})}")
            print(f"  captureframenum: {len(self.frame_capture.captures)}")
            print("=" * 50)

            # selfactionsave
            self.save_session()
            
            # selfactiongenerateAIreport(if_available)
            if self.llm_bridge and _LLM_BRIDGE_AVAILABLE:
                print("\n[info] correct generateAIreport...")
                try:
                    asyncio.run(self._auto_generate_report())
                except Exception as e:
                    print(f"[warning] selfactionreportgeneratefailed: {e}")

        if self.cap:
            self.cap.release()
        cv2.destroyAllWindows()
        print("[info] system统alreadyclose")
    
    async def _auto_generate_report(self):
        """trainingendbeamwhenselfactiongeneratereport"""
        summary = self.fsm.get_session_summary()
        report = await self.llm_bridge.submit_session(summary)
        if report:
            self.ai_report = report
            self._display_ai_report(report)
            # saveAIreport
            self._save_ai_report(report)

    def _save_ai_report(self, report: dict):
        """saveAIreporttofile"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{self.log_dir}/ai_report_{timestamp}.json"
        
        data = {
            "timestamp": timestamp,
            "report": report,
            "session_summary": self.fsm.get_session_summary(),
        }
        
        try:
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"[info] AIreportalreadysave: {filename}")
        except Exception as e:
            print(f"[warning] reportsavefailed: {e}")


def main():
    """程序in口. """
    import argparse
    parser = argparse.ArgumentParser(description="CyberTrainer squat detection")
    parser.add_argument("--camera", type=int, default=0, help="Camera index (0, 1, 2, ...)")
    parser.add_argument("--view", choices=["front", "side", "auto"], default="auto",
                        help="Camera view mode: front (knee valgus/asymmetry), side (depth/trunk lean), auto (detect)")
    args = parser.parse_args()

    trainer = CyberTrainer()
    trainer.view_mode = args.view
    trainer.run()


if __name__ == "__main__":
    main()
