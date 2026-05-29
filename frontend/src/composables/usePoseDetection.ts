import { onBeforeUnmount, ref, shallowRef } from 'vue';
import { FilesetResolver, PoseLandmarker } from '@mediapipe/tasks-vision';

export interface PosePoint {
  x: number;
  y: number;
  z: number;
  visibility?: number;
}

export interface PoseFramePayload {
  landmarks: PosePoint[];
  timestamp: number;
}

export interface UsePoseDetectionOptions {
  onFrame?: (payload: PoseFramePayload) => void;
  deviceId?: string;
}

const poseConnections = [
  [11, 12],
  [11, 13],
  [13, 15],
  [15, 17],
  [15, 19],
  [15, 21],
  [17, 19],
  [12, 14],
  [14, 16],
  [16, 18],
  [16, 20],
  [16, 22],
  [18, 20],
  [11, 23],
  [12, 24],
  [23, 24],
  [23, 25],
  [25, 27],
  [27, 29],
  [27, 31],
  [29, 31],
  [24, 26],
  [26, 28],
  [28, 30],
  [28, 32],
  [30, 32],
];

const POSE_INIT_TIMEOUT_MS = 12000;
const CAMERA_START_TIMEOUT_MS = 8000;
const VIDEO_PLAY_TIMEOUT_MS = 5000;

async function withTimeout<T>(promise: Promise<T>, ms: number, message: string): Promise<T> {
  let timeoutId: ReturnType<typeof setTimeout> | null = null;
  const timeout = new Promise<never>((_, reject) => {
    timeoutId = setTimeout(() => reject(new Error(message)), ms);
  });

  try {
    return await Promise.race([promise, timeout]);
  } finally {
    if (timeoutId) {
      clearTimeout(timeoutId);
    }
  }
}

export function usePoseDetection(options: UsePoseDetectionOptions = {}) {
  const videoRef = ref<HTMLVideoElement | null>(null);
  const canvasRef = ref<HTMLCanvasElement | null>(null);
  const isReady = ref(false);
  const isRunning = ref(false);
  const error = ref<string | null>(null);
  const latestLandmarks = ref<PosePoint[]>([]);
  const poseLandmarker = shallowRef<PoseLandmarker | null>(null);
  const stream = shallowRef<MediaStream | null>(null);
  const rafId = ref<number | null>(null);

  async function createPoseLandmarker(delegate: 'GPU' | 'CPU') {
    const vision = await withTimeout(
      FilesetResolver.forVisionTasks(
        import.meta.env.VITE_MEDIAPIPE_WASM_BASE ||
          'https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.21/wasm',
      ),
      POSE_INIT_TIMEOUT_MS,
      '姿态模型 WASM 加载超时，请检查网络或刷新重试',
    );

    return withTimeout(PoseLandmarker.createFromOptions(vision, {
      baseOptions: {
          modelAssetPath:
            import.meta.env.VITE_POSE_MODEL_URL ||
            'https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_full/float16/latest/pose_landmarker_full.task',
        delegate,
      },
      runningMode: 'VIDEO',
      numPoses: 1,
      minPoseDetectionConfidence: 0.55,
      minPosePresenceConfidence: 0.55,
      minTrackingConfidence: 0.55,
    }), POSE_INIT_TIMEOUT_MS, '姿态模型初始化超时，请检查网络或刷新重试');
  }

  async function init() {
    if (poseLandmarker.value) {
      return;
    }

    try {
      poseLandmarker.value = await createPoseLandmarker('GPU');
    } catch (gpuError) {
      console.warn('GPU pose initialization failed, falling back to CPU:', gpuError);
      poseLandmarker.value = await createPoseLandmarker('CPU');
    }

    isReady.value = true;
  }

  async function requestCamera(videoConstraints: MediaTrackConstraints) {
    try {
      return await withTimeout(
        navigator.mediaDevices.getUserMedia({
          video: videoConstraints,
          audio: false,
        }),
        CAMERA_START_TIMEOUT_MS,
        '摄像头启动超时，请换一个摄像头或确认设备没有被占用',
      );
    } catch (cameraError) {
      if (!options.deviceId) {
        throw cameraError;
      }

      console.warn('Selected camera failed, falling back to any available camera:', cameraError);
      return withTimeout(
        navigator.mediaDevices.getUserMedia({
          video: { width: { ideal: 1280 }, height: { ideal: 720 } },
          audio: false,
        }),
        CAMERA_START_TIMEOUT_MS,
        '所选摄像头不可用，默认摄像头也启动超时，请重新选择设备',
      );
    }
  }

  async function start() {
    try {
      error.value = null;

      const videoConstraints: MediaTrackConstraints = options.deviceId
        ? { deviceId: { exact: options.deviceId }, width: { ideal: 1280 }, height: { ideal: 720 } }
        : { facingMode: 'user', width: { ideal: 1280 }, height: { ideal: 720 } };

      const mediaStream = await requestCamera(videoConstraints);

      stream.value = mediaStream;

      if (!videoRef.value) {
        throw new Error('视频元素尚未挂载');
      }

      videoRef.value.srcObject = mediaStream;
      await withTimeout(
        videoRef.value.play(),
        VIDEO_PLAY_TIMEOUT_MS,
        '摄像头画面播放超时，请重新选择摄像头',
      );

      isRunning.value = true;
      detectLoop();

      // Give the browser a chance to paint the camera view before MediaPipe WASM initialization.
      await new Promise<void>((resolve) => requestAnimationFrame(() => resolve()));
      await init();
    } catch (nextError) {
      error.value = nextError instanceof Error ? nextError.message : '摄像头或姿态模型启动失败';
      stop();
    }
  }

  function stop() {
    isRunning.value = false;

    if (rafId.value !== null) {
      cancelAnimationFrame(rafId.value);
      rafId.value = null;
    }

    stream.value?.getTracks().forEach((track) => track.stop());
    stream.value = null;

    if (videoRef.value) {
      videoRef.value.srcObject = null;
    }
  }

  function detectLoop() {
    const video = videoRef.value;
    const detector = poseLandmarker.value;

    if (!isRunning.value || !video || !detector || video.readyState < HTMLMediaElement.HAVE_CURRENT_DATA) {
      rafId.value = requestAnimationFrame(detectLoop);
      return;
    }

    const timestamp = performance.now();
    const result = detector.detectForVideo(video, timestamp);
    const landmarks = result.landmarks[0] ?? [];

    latestLandmarks.value = landmarks.map((point) => ({
      x: point.x,
      y: point.y,
      z: point.z,
      visibility: point.visibility,
    }));

    drawOverlay(latestLandmarks.value);

    if (latestLandmarks.value.length > 0) {
      options.onFrame?.({
        landmarks: latestLandmarks.value,
        timestamp: Date.now(),
      });
    }

    rafId.value = requestAnimationFrame(detectLoop);
  }

  function drawOverlay(points: PosePoint[]) {
    const canvas = canvasRef.value;
    const video = videoRef.value;

    if (!canvas || !video) {
      return;
    }

    const context = canvas.getContext('2d');
    if (!context) {
      return;
    }

    const width = video.videoWidth || canvas.clientWidth;
    const height = video.videoHeight || canvas.clientHeight;

    canvas.width = width;
    canvas.height = height;
    context.clearRect(0, 0, width, height);

    if (points.length === 0) {
      return;
    }

    context.lineCap = 'round';
    context.lineJoin = 'round';

    for (const [start, end] of poseConnections) {
      const pointA = points[start];
      const pointB = points[end];

      if (!pointA || !pointB || (pointA.visibility ?? 1) < 0.35 || (pointB.visibility ?? 1) < 0.35) {
        continue;
      }

      context.beginPath();
      context.moveTo(pointA.x * width, pointA.y * height);
      context.lineTo(pointB.x * width, pointB.y * height);
      context.strokeStyle = 'rgba(255, 255, 255, 0.92)';
      context.lineWidth = 5;
      context.stroke();
    }

    for (const point of points) {
      if ((point.visibility ?? 1) < 0.35) {
        continue;
      }

      context.beginPath();
      context.arc(point.x * width, point.y * height, 6, 0, Math.PI * 2);
      context.fillStyle = '#1f74ff';
      context.fill();
      context.strokeStyle = '#ffffff';
      context.lineWidth = 2;
      context.stroke();
    }
  }

  onBeforeUnmount(stop);

  return {
    videoRef,
    canvasRef,
    isReady,
    isRunning,
    error,
    latestLandmarks,
    init,
    start,
    stop,
  };
}
