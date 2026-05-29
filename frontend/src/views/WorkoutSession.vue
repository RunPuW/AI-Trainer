<script setup lang="ts">
import { ref, computed, onBeforeUnmount, onMounted, nextTick } from 'vue';
import { ElMessage } from 'element-plus';
import WebShell from '@/components/WebShell.vue';
import { usePoseDetection } from '@/composables/usePoseDetection';
import { useAuthStore } from '@/stores/auth';
import { generateReport, type ReportResponse } from '@/api/report';
import { saveWorkout } from '@/api/workout';

const authStore = useAuthStore();

// --- Session state ---
const sessionState = ref<'idle' | 'connecting' | 'running' | 'paused' | 'finished'>('idle');
const selectedMovement = ref('squat');
const sessionId = ref('');
const elapsedTime = ref(0);
let timerInterval: ReturnType<typeof setInterval> | null = null;
let preparationInterval: ReturnType<typeof setInterval> | null = null;
const PREPARATION_SECONDS = 5;
const preparationCountdown = ref(0);
const isSendingPoseFrames = ref(false);

// --- Stats from backend ---
const repCount = ref(0);
const status = ref('等待开始');
const depth = ref(0);
const depthSum = ref(0);
const depthCount = ref(0);
const viewMode = ref('正面');
const errors = ref<string[]>([]);
const warnings = ref<string[]>([]);
const sessionErrors = ref<string[]>([]);
const correction = ref('');
const safety = ref('');

// --- Error history (accumulated across session) ---
const errorHistory = ref<Record<string, number>>({});

// --- Session data for report ---
const sessionErrorsList = ref<string[]>([]);
const sessionStartTime = ref<number>(0);
const reportLoading = ref(false);
const reportResult = ref<ReportResponse | null>(null);
const showReportDialog = ref(false);
const capturedFrames = ref<Array<{ image: string; reason: string; state: string; timestamp: number }>>([]);
const videoAspectRatio = ref('16 / 9');
let lastCaptureAt = 0;
const countedIssueKeys = new Set<string>();

// --- Camera ---
const availableDevices = ref<MediaDeviceInfo[]>([]);
const selectedDeviceId = ref('');
const cameraLoading = ref(false);
const cameraError = ref('');

// --- WebSocket ---
let ws: WebSocket | null = null;

// --- Pose detection (deviceId set at start time, not init time) ---
let poseOptions = {
  onFrame(payload: any) {
    if (isSendingPoseFrames.value && ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({
        type: 'landmarks',
        landmarks: payload.landmarks,
        timestamp: payload.timestamp,
        view_mode_requested: 'front',
      }));
    }
  },
  deviceId: undefined as string | undefined,
};

const {
  videoRef,
  canvasRef,
  error: poseError,
  start: startPose,
  stop: stopPose,
} = usePoseDetection(poseOptions);

// --- Computed ---
const formattedTime = computed(() => {
  const m = Math.floor(elapsedTime.value / 60);
  const s = elapsedTime.value % 60;
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
});

const videoFrameStyle = computed(() => ({
  aspectRatio: videoAspectRatio.value,
}));

const avgDepth = computed(() => {
  return depthCount.value > 0 ? Math.round(depthSum.value / depthCount.value) : 0;
});

const depthLabel = computed(() => {
  if (depth.value >= 80) return '优秀';
  if (depth.value >= 60) return '良好';
  if (depth.value >= 40) return '一般';
  return '不足';
});

const depthColor = computed(() => {
  if (depth.value >= 80) return 'bg-mint';
  if (depth.value >= 60) return 'bg-ocean';
  if (depth.value >= 40) return 'bg-amber';
  return 'bg-coral';
});

const topErrors = computed(() => {
  return Object.entries(errorHistory.value)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 5);
});

const viewModeMap: Record<string, string> = {
  front: '正面',
  side: '侧面',
  back: '背面',
  'front-left': '左前',
  'front-right': '右前',
};

const stateMap: Record<string, string> = {
  idle: '等待中',
  ready: '准备就绪',
  exercising: '运动中',
  resting: '休息中',
  completed: '已完成',
  unknown: '等待识别',
  no_person: '未检测到人体',
  standing: '站立准备',
  descending: '下蹲',
  bottom: '底部',
  ascending: '起立',
};

// --- Camera device enumeration ---
function getCameraLabel(device: MediaDeviceInfo, index: number) {
  return device.label || `摄像头 ${index + 1}`;
}

function handleCameraChange(deviceId: string) {
  selectedDeviceId.value = deviceId;
  if (deviceId) {
    localStorage.setItem('preferred_camera_id', deviceId);
  }
}

async function enumerateDevices(showMessage = false) {
  cameraLoading.value = true;
  cameraError.value = '';

  try {
    if (!navigator.mediaDevices?.enumerateDevices) {
      cameraError.value = '当前浏览器不支持摄像头设备枚举';
      return;
    }

    const devices = await navigator.mediaDevices.enumerateDevices();
    availableDevices.value = devices.filter((d) => d.kind === 'videoinput');

    const savedDeviceId = localStorage.getItem('preferred_camera_id');
    const currentStillExists = availableDevices.value.some((d) => d.deviceId === selectedDeviceId.value);
    const savedStillExists = savedDeviceId && availableDevices.value.some((d) => d.deviceId === savedDeviceId);

    if (savedStillExists) {
      selectedDeviceId.value = savedDeviceId;
    } else if (!currentStillExists && availableDevices.value.length > 0) {
      selectedDeviceId.value = availableDevices.value[0].deviceId;
    }

    if (showMessage) {
      if (availableDevices.value.length > 0) {
        ElMessage.success(`已检测到 ${availableDevices.value.length} 个摄像头`);
      } else {
        ElMessage.warning('未检测到摄像头，请确认设备已连接后再刷新');
      }
    }
  } catch (error: any) {
    cameraError.value = error?.message || '摄像头列表读取失败';
    if (showMessage) {
      ElMessage.error(cameraError.value);
    }
  } finally {
    cameraLoading.value = false;
  }
}

function handleDeviceListChanged() {
  enumerateDevices();
}

function abortSessionStart(message: string) {
  ElMessage.error(message);
  stopPose();
  clearPreparationTimer();
  if (timerInterval) {
    clearInterval(timerInterval);
    timerInterval = null;
  }
  if (ws) {
    ws.close();
    ws = null;
  }
  sessionState.value = 'idle';
}

function clearPreparationTimer() {
  if (preparationInterval) {
    clearInterval(preparationInterval);
    preparationInterval = null;
  }
  preparationCountdown.value = 0;
  isSendingPoseFrames.value = false;
}

function startElapsedTimer() {
  if (timerInterval) {
    clearInterval(timerInterval);
  }
  timerInterval = setInterval(() => {
    elapsedTime.value++;
  }, 1000);
}

function startPreparationCountdown() {
  clearPreparationTimer();
  preparationCountdown.value = PREPARATION_SECONDS;
  status.value = `准备中 ${preparationCountdown.value}`;

  preparationInterval = setInterval(() => {
    preparationCountdown.value -= 1;
    if (preparationCountdown.value <= 0) {
      clearPreparationTimer();
      isSendingPoseFrames.value = true;
      status.value = '运动中';
      startElapsedTimer();
      captureFrame('开始训练');
    } else {
      status.value = `准备中 ${preparationCountdown.value}`;
    }
  }, 1000);
}

function updateVideoAspectRatio() {
  const video = videoRef.value;
  if (!video?.videoWidth || !video?.videoHeight) {
    return;
  }
  videoAspectRatio.value = `${video.videoWidth} / ${video.videoHeight}`;
}

function captureFrame(reason: string) {
  const now = Date.now();
  if (capturedFrames.value.length >= 3 || now - lastCaptureAt < 1200) {
    return;
  }

  const video = videoRef.value;
  if (!video || !video.videoWidth || !video.videoHeight) {
    return;
  }

  const output = document.createElement('canvas');
  const maxWidth = 720;
  const scale = Math.min(1, maxWidth / video.videoWidth);
  output.width = Math.round(video.videoWidth * scale);
  output.height = Math.round(video.videoHeight * scale);

  const context = output.getContext('2d');
  if (!context) {
    return;
  }

  context.drawImage(video, 0, 0, output.width, output.height);
  if (canvasRef.value) {
    context.drawImage(canvasRef.value, 0, 0, output.width, output.height);
  }

  capturedFrames.value.push({
    image: output.toDataURL('image/jpeg', 0.82),
    reason,
    state: status.value,
    timestamp: now,
  });
  lastCaptureAt = now;
}

function uniqueIssues(values: unknown): string[] {
  if (!Array.isArray(values)) {
    return [];
  }
  return [...new Set(values.map((value) => String(value).trim()).filter(Boolean))];
}

function shouldDisplayIssues(state?: string) {
  return isSendingPoseFrames.value
    && !['standing', 'unknown', 'no_person', 'ready', '站立准备', '等待识别', '未检测到人体', '准备就绪'].includes(state || '');
}

function recordIssue(issue: string, repNumber: number) {
  const normalized = issue.trim();
  const key = `${Math.max(repNumber, 1)}:${normalized}`;
  if (countedIssueKeys.has(key)) {
    return;
  }

  countedIssueKeys.add(key);
  errorHistory.value[normalized] = (errorHistory.value[normalized] || 0) + 1;
  if (!sessionErrorsList.value.includes(normalized)) {
    sessionErrorsList.value.push(normalized);
  }
}

function buildLocalReport(): ReportResponse {
  const issueCount = Object.values(errorHistory.value).reduce((sum, count) => sum + count, 0);
  const score = Math.max(45, Math.min(100, 88 - issueCount * 10 - (repCount.value === 0 ? 18 : 0)));
  const issueList = sessionErrorsList.value.length > 0
    ? sessionErrorsList.value.slice(0, 4)
    : ['本次未捕捉到明确错误，请参考截图复核动作轨迹'];

  return {
    overall_score: score,
    highlights: [
      repCount.value > 0 ? `完成 ${repCount.value} 次动作` : '本次动作未被稳定计入完整次数',
      capturedFrames.value.length > 0 ? `已保留 ${capturedFrames.value.length} 张训练反馈截图` : '本次未生成有效截图',
    ],
    corrections: issueList,
    recovery_plan: '休息 1-2 分钟后再进行下一组；复测时保持全身进入画面，并从站立姿态开始。',
    next_session_goals: [
      '先站稳等待 5 秒准备倒计时结束',
      '完成一次完整的下蹲和起立后再结束训练',
      '让膝盖、髋部和脚踝始终保持在画面内',
    ],
  };
}

// --- Session lifecycle ---
function generateSessionId() {
  return `session_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
}

async function startSession() {
  if (!navigator.mediaDevices?.getUserMedia) {
    ElMessage.error('当前浏览器不支持摄像头访问');
    return;
  }

  if (availableDevices.value.length === 0) {
    await enumerateDevices();
  }

  if (availableDevices.value.length > 0 && !selectedDeviceId.value) {
    selectedDeviceId.value = availableDevices.value[0].deviceId;
  }

  sessionState.value = 'connecting';
  sessionId.value = generateSessionId();
  repCount.value = 0;
  depth.value = 0;
  depthSum.value = 0;
  depthCount.value = 0;
  errors.value = [];
  warnings.value = [];
  sessionErrors.value = [];
  errorHistory.value = {};
  countedIssueKeys.clear();
  sessionErrorsList.value = [];
  capturedFrames.value = [];
  lastCaptureAt = 0;
  correction.value = '';
  safety.value = '';
  elapsedTime.value = 0;
  sessionStartTime.value = Date.now();
  reportResult.value = null;

  // Connect WebSocket
  const token = authStore.token || 'demo-token';
  const wsProtocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
  const wsUrl = `${wsProtocol}//${location.host}/ws/pose/${sessionId.value}?token=${token}`;

  ws = new WebSocket(wsUrl);

  ws.onopen = async () => {
    sessionState.value = 'running';
    status.value = '运动中';

    status.value = `准备中 ${PREPARATION_SECONDS}`;

    // Update pose options with selected device before starting
    poseOptions.deviceId = selectedDeviceId.value || undefined;
    if (selectedDeviceId.value) {
      localStorage.setItem('preferred_camera_id', selectedDeviceId.value);
    }

    // Start pose detection
    await nextTick();
    await startPose();
    await enumerateDevices();
    updateVideoAspectRatio();
    if (!poseError.value) {
      startPreparationCountdown();
    }
    if (poseError.value) {
      abortSessionStart(`摄像头启动失败：${poseError.value}。请选择其他摄像头后重试。`);
    }
  };

  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      handleBackendResponse(data);
    } catch {
      // Ignore parse errors
    }
  };

  ws.onerror = () => {
    ElMessage.error('WebSocket 连接错误');
    stopSession();
  };

  ws.onclose = () => {
    if (sessionState.value === 'running') {
      ElMessage.warning('连接已断开');
      stopSession();
    }
  };
}

function handleBackendResponse(data: any) {
  if (data.state) {
    status.value = stateMap[data.state] || data.state;
  }
  if (data.rep_count !== undefined) {
    repCount.value = data.rep_count;
  }
  if (data.knee_angle !== undefined) {
    // Convert knee_angle to depth percentage: smaller angle = deeper squat
    const frameDepth = Math.max(0, Math.min(100, ((180 - data.knee_angle) / 100) * 100));
    depth.value = frameDepth;
    // Accumulate for average calculation
    depthSum.value += frameDepth;
    depthCount.value++;
  }
  if (data.view_mode) {
    viewMode.value = viewModeMap[data.view_mode] || data.view_mode;
  }

  const activeIssues = shouldDisplayIssues(data.state);
  const currentErrors = activeIssues ? uniqueIssues(data.errors) : [];
  const currentWarnings = activeIssues ? uniqueIssues(data.warnings) : [];
  errors.value = currentErrors;
  warnings.value = currentWarnings;

  if (activeIssues) {
    const repNumber = data.rep_count || repCount.value || 1;
    for (const issue of [...currentErrors, ...currentWarnings]) {
      recordIssue(issue, repNumber);
    }
    if (currentErrors.length || currentWarnings.length) {
      captureFrame(currentErrors[0] || currentWarnings[0]);
    }
  }

  if (Array.isArray(data.session_errors)) {
    sessionErrors.value = uniqueIssues(data.session_errors);
  }
  correction.value = activeIssues ? (data.correction || '') : '';
  safety.value = activeIssues ? (data.safety || '') : '';
}

function pauseSession() {
  if (sessionState.value === 'running') {
    sessionState.value = 'paused';
    clearPreparationTimer();
    stopPose();
    if (timerInterval) clearInterval(timerInterval);
  }
}

function resumeSession() {
  if (sessionState.value === 'paused') {
    sessionState.value = 'running';
    startPose();
    isSendingPoseFrames.value = true;
    startElapsedTimer();
  }
}

function stopSession() {
  const hadSession = Boolean(sessionId.value || elapsedTime.value > 0 || repCount.value > 0 || capturedFrames.value.length > 0);
  sessionState.value = 'finished';
  clearPreparationTimer();
  if (capturedFrames.value.length === 0) {
    captureFrame('训练结束');
  }
  stopPose();
  if (timerInterval) {
    clearInterval(timerInterval);
    timerInterval = null;
  }
  if (ws) {
    ws.close();
    ws = null;
  }

  // Fire-and-forget: API calls continue after component unmount
  if (hadSession) {
    generateTrainingReport();
  }
}

async function generateTrainingReport() {
  reportLoading.value = true;
  try {
    const { data } = await generateReport({
      session_data: {
        session_id: sessionId.value,
        movement: selectedMovement.value,
        duration_seconds: elapsedTime.value,
        rep_count: repCount.value,
        errors: sessionErrorsList.value,
        error_details: errorHistory.value,
        captured_frames: capturedFrames.value,
      }
    });
    reportResult.value = data;
  } catch (error: any) {
    console.error('Failed to generate report:', error);
    reportResult.value = buildLocalReport();
    ElMessage.warning('AI 报告生成失败，已生成本地训练反馈报告');
  } finally {
    reportLoading.value = false;
  }
  
  // Save workout to database
  await saveWorkoutLog();
}

async function saveWorkoutLog() {
  try {
    await saveWorkout({
      session_id: sessionId.value,
      exercise_type: selectedMovement.value,
      duration_min: Math.ceil(elapsedTime.value / 60),
      rep_count: repCount.value,
      errors: sessionErrorsList.value,
      error_details: errorHistory.value,
    });
    console.log('Workout saved successfully');
  } catch (error: any) {
    console.error('Failed to save workout:', error);
    // Don't show error to user, just log it
  }
}

function viewFullReport() {
  if (reportResult.value) {
    showReportDialog.value = true;
  }
}

function resetSession() {
  sessionState.value = 'idle';
  reportResult.value = null;
  capturedFrames.value = [];
  sessionId.value = '';
  elapsedTime.value = 0;
  errors.value = [];
  warnings.value = [];
  sessionErrors.value = [];
  sessionErrorsList.value = [];
  errorHistory.value = {};
  countedIssueKeys.clear();
}

onMounted(() => {
  // Read selected movement from localStorage (set by TrainingPlan page)
  const saved = localStorage.getItem('selected_movement');
  if (saved && movements.some(m => m.value === saved)) {
    selectedMovement.value = saved;
    localStorage.removeItem('selected_movement');
  }

  enumerateDevices();
  navigator.mediaDevices?.addEventListener?.('devicechange', handleDeviceListChanged);
});

onBeforeUnmount(() => {
  navigator.mediaDevices?.removeEventListener?.('devicechange', handleDeviceListChanged);
  if (sessionState.value !== 'idle' && sessionState.value !== 'finished') {
    stopSession();
  } else {
    clearPreparationTimer();
    stopPose();
  }
});

const movements = [
  { value: 'squat', label: '深蹲' },
  { value: 'push_up', label: '俯卧撑' },
  { value: 'plank', label: '平板支撑' },
  { value: 'lunge', label: '弓步蹲' },
];
</script>

<template>
  <WebShell title="开始训练" subtitle="AI 实时姿态分析">
    <!-- Pre-session: movement selection -->
    <div v-if="sessionState === 'idle'" class="mx-auto max-w-xl">
      <div class="app-card p-6 md:p-8">
        <h3 class="mb-6 text-lg font-bold text-ink">选择训练动作</h3>

        <div class="mb-6 grid grid-cols-2 gap-3">
          <button
            v-for="m in movements"
            :key="m.value"
            class="rounded-2xl border-2 py-4 text-sm font-bold transition"
            :class="selectedMovement === m.value ? 'border-indigo bg-indigo/10 text-indigo' : 'border-white/70 text-muted hover:border-indigo/30'"
            @click="selectedMovement = m.value"
          >
            {{ m.label }}
          </button>
        </div>

        <div class="mb-6 rounded-2xl bg-canvas p-4">
          <div class="mb-3 flex items-center justify-between gap-3">
            <label class="block text-sm font-semibold text-ink">选择摄像头</label>
            <el-button text size="small" :loading="cameraLoading" class="!text-indigo" @click="enumerateDevices(true)">
              刷新
            </el-button>
          </div>

          <el-select
            v-if="availableDevices.length > 0"
            v-model="selectedDeviceId"
            class="w-full"
            placeholder="请选择要使用的摄像头"
            :disabled="cameraLoading"
            @change="handleCameraChange"
          >
            <el-option
              v-for="(d, index) in availableDevices"
              :key="d.deviceId"
              :label="getCameraLabel(d, index)"
              :value="d.deviceId"
            />
          </el-select>
          <p v-else class="text-sm leading-relaxed text-muted">
            暂未检测到摄像头。请插入或启用设备后点击刷新；如果浏览器询问权限，请允许访问摄像头。
          </p>

          <p v-if="cameraError" class="mt-2 text-xs text-coral">{{ cameraError }}</p>
          <p v-else class="mt-2 text-xs text-muted">
            默认摄像头不可用时，请先在这里切换到其他摄像头，再点击开始训练。
          </p>
        </div>

        <el-button
          class="brand-button w-full !rounded-xl !py-5 !text-base !font-bold"
          @click="startSession"
        >
          开始训练
        </el-button>
      </div>
    </div>

    <!-- Active session -->
    <div v-else>
      <div class="grid gap-5 lg:grid-cols-[1fr_360px]">
        <!-- Video area -->
        <div class="relative overflow-hidden rounded-[28px] bg-black" :style="videoFrameStyle">
          <video
            ref="videoRef"
            class="h-full w-full object-contain"
            autoplay
            muted
            playsinline
            @loadedmetadata="updateVideoAspectRatio"
          />
          <canvas
            ref="canvasRef"
            class="pointer-events-none absolute inset-0 h-full w-full"
          />

          <!-- Status overlay -->
          <div class="absolute left-4 top-4 flex flex-col gap-2">
            <span class="rounded-full bg-black/60 px-3 py-1 text-xs font-bold text-white backdrop-blur">
              {{ status }}
            </span>
            <span class="rounded-full bg-black/60 px-3 py-1 text-xs font-bold text-white backdrop-blur">
              视角：{{ viewMode }}
            </span>
          </div>

          <!-- Timer overlay -->
          <div class="absolute right-4 top-4 rounded-full bg-black/60 px-4 py-2 text-lg font-black text-white backdrop-blur">
            {{ formattedTime }}
          </div>

          <div
            v-if="preparationCountdown > 0"
            class="absolute inset-0 grid place-items-center bg-black/45 text-center text-white backdrop-blur-sm"
          >
            <div>
              <p class="text-sm font-semibold text-white/80">准备开始</p>
              <p class="mt-2 text-6xl font-black">{{ preparationCountdown }}</p>
              <p class="mt-2 text-sm text-white/75">站稳入镜，倒计时结束后再下蹲</p>
            </div>
          </div>

          <!-- Pose error overlay -->
          <div v-if="poseError" class="absolute inset-x-4 bottom-4 rounded-2xl bg-coral/90 px-4 py-3 text-sm font-semibold text-white">
            {{ poseError }}
          </div>
        </div>

        <!-- Stats panel -->
        <div class="flex flex-col gap-4">
          <!-- Rep count -->
          <div class="app-card flex items-center justify-between p-5">
            <div>
              <p class="text-sm text-muted">完成次数</p>
              <p class="text-4xl font-black text-ink">{{ repCount }}</p>
            </div>
            <div class="grid h-16 w-16 place-items-center rounded-2xl bg-gradient-to-br from-orange to-coral text-2xl text-white">
              🔥
            </div>
          </div>

          <!-- Depth bar -->
          <div class="app-card p-5">
            <div class="mb-2 flex items-center justify-between">
              <p class="text-sm text-muted">动作深度</p>
              <span class="text-sm font-bold" :class="depth >= 60 ? 'text-mint' : 'text-coral'">{{ depthLabel }}</span>
            </div>
            <div class="h-3 overflow-hidden rounded-full bg-canvas">
              <div
                class="h-full rounded-full transition-all duration-300"
                :class="depthColor"
                :style="{ width: `${depth}%` }"
              />
            </div>
            <p class="mt-1 text-right text-xs text-muted">{{ Math.round(depth) }}%</p>
          </div>

          <!-- Current errors -->
          <div v-if="errors.length || warnings.length" class="app-card p-5">
            <h4 class="mb-2 text-sm font-bold text-coral">实时提示</h4>
            <ul class="space-y-1">
              <li v-for="err in errors" :key="err" class="flex items-start gap-2 text-sm text-coral">
                <span>⚠</span>{{ err }}
              </li>
              <li v-for="warn in warnings" :key="warn" class="flex items-start gap-2 text-sm text-amber">
                <span>💡</span>{{ warn }}
              </li>
            </ul>
          </div>

          <!-- Correction -->
          <div v-if="correction" class="app-card border-l-4 border-indigo p-5">
            <h4 class="mb-1 text-sm font-bold text-indigo">纠正建议</h4>
            <p class="text-sm text-ink">{{ correction }}</p>
          </div>

          <!-- Safety warning -->
          <div v-if="safety" class="app-card border-l-4 border-coral p-5">
            <h4 class="mb-1 text-sm font-bold text-coral">安全提醒</h4>
            <p class="text-sm text-ink">{{ safety }}</p>
          </div>

          <!-- Session errors -->
          <div v-if="sessionErrors.length" class="app-card p-5">
            <h4 class="mb-2 text-sm font-bold text-amber">累计问题</h4>
            <ul class="space-y-1">
              <li v-for="(err, i) in sessionErrors" :key="i" class="text-sm text-muted">{{ err }}</li>
            </ul>
          </div>

          <!-- Error history -->
          <div v-if="topErrors.length" class="app-card p-5">
            <h4 class="mb-2 text-sm font-bold text-ink">错误频率统计</h4>
            <div
              v-for="[errName, count] in topErrors"
              :key="errName"
              class="mb-2 flex items-center justify-between"
            >
              <span class="text-sm text-ink">{{ errName }}</span>
              <span class="rounded-full bg-coral/10 px-2 py-0.5 text-xs font-bold text-coral">{{ count }} 次</span>
            </div>
          </div>

          <!-- Control buttons -->
          <div class="flex gap-3">
            <el-button
              v-if="sessionState === 'running'"
              round
              size="large"
              class="flex-1 !h-12 !border-amber/30 !text-amber"
              @click="pauseSession"
            >
              暂停
            </el-button>
            <el-button
              v-if="sessionState === 'paused'"
              round
              size="large"
              class="flex-1 !h-12 !border-mint/30 !text-mint"
              @click="resumeSession"
            >
              继续
            </el-button>
            <el-button
              round
              size="large"
              class="flex-1 !h-12 !border-coral/30 !text-coral"
              @click="stopSession"
            >
              结束训练
            </el-button>
          </div>
        </div>
      </div>
    </div>

    <!-- Post-session summary -->
    <div v-if="sessionState === 'finished'" class="mx-auto mt-6 max-w-xl">
      <div class="app-card p-6 text-center md:p-8">
        <p class="text-5xl">🎉</p>
        <h3 class="mt-4 text-xl font-black text-ink">训练完成！</h3>
        
        <!-- AI Report Summary -->
        <div v-if="reportLoading" class="mt-4 rounded-2xl bg-canvas p-4">
          <el-skeleton :rows="2" animated />
        </div>
        
        <div v-else-if="reportResult" class="mt-4 rounded-2xl bg-gradient-to-r from-indigo/5 to-violet/5 p-4 text-left">
          <div class="flex items-center justify-between">
            <h4 class="text-sm font-bold text-indigo">AI 训练分析</h4>
            <span class="text-2xl font-black text-indigo">{{ Math.round(reportResult.overall_score) }}分</span>
          </div>
          <div v-if="reportResult.highlights.length > 0" class="mt-2">
            <p class="text-xs text-muted">亮点：</p>
            <p class="text-sm text-ink">{{ reportResult.highlights[0] }}</p>
          </div>
          <el-button 
            v-if="reportResult" 
            text 
            size="small" 
            class="!mt-2 !text-indigo"
            @click="viewFullReport"
          >
            查看完整报告 →
          </el-button>
        </div>

        <div v-if="capturedFrames.length" class="mt-4 rounded-2xl bg-canvas p-4 text-left">
          <h4 class="mb-3 text-sm font-bold text-ink">动作反馈截图</h4>
          <div class="grid gap-3 sm:grid-cols-3">
            <figure v-for="frame in capturedFrames" :key="frame.timestamp" class="overflow-hidden rounded-xl bg-white">
              <img :src="frame.image" :alt="frame.reason" class="aspect-video w-full object-cover" />
              <figcaption class="px-2 py-1.5 text-xs text-muted">{{ frame.reason }}</figcaption>
            </figure>
          </div>
        </div>

        <div class="mt-6 grid grid-cols-3 gap-4">
          <div>
            <p class="text-3xl font-black text-indigo">{{ repCount }}</p>
            <p class="text-sm text-muted">完成次数</p>
          </div>
          <div>
            <p class="text-3xl font-black text-orange">{{ formattedTime }}</p>
            <p class="text-sm text-muted">训练时长</p>
          </div>
          <div>
            <p class="text-3xl font-black text-mint">{{ avgDepth }}%</p>
            <p class="text-sm text-muted">平均深度</p>
          </div>
        </div>

        <div v-if="topErrors.length" class="mt-6 rounded-2xl bg-canvas p-4 text-left">
          <h4 class="mb-2 text-sm font-bold text-ink">本次错误统计</h4>
          <div
            v-for="[errName, count] in topErrors"
            :key="errName"
            class="flex items-center justify-between py-1"
          >
            <span class="text-sm text-ink">{{ errName }}</span>
            <span class="text-sm font-bold text-coral">{{ count }} 次</span>
          </div>
        </div>

        <div class="mt-6 flex gap-3">
          <el-button round size="large" class="flex-1 !h-12" @click="resetSession">
            再来一次
          </el-button>
          <el-button round size="large" class="flex-1 !h-12 !bg-gradient-to-r !from-orange !to-coral !border-none !text-white" @click="$router.push('/dashboard')">
            返回面板
          </el-button>
        </div>
      </div>
    </div>
    
    <!-- Full Report Dialog -->
    <el-dialog
      v-model="showReportDialog"
      title="训练报告"
      width="600px"
      class="!rounded-2xl"
    >
      <div v-if="reportResult" class="space-y-6">
        <!-- Score -->
        <div class="text-center">
          <div class="inline-flex h-24 w-24 items-center justify-center rounded-full bg-gradient-to-br from-indigo to-violet text-white">
            <span class="text-3xl font-black">{{ Math.round(reportResult.overall_score) }}</span>
          </div>
          <p class="mt-2 text-sm text-muted">综合评分</p>
        </div>

        <div v-if="capturedFrames.length">
          <h4 class="mb-2 text-sm font-bold text-ink">动作截图</h4>
          <div class="grid gap-3 sm:grid-cols-3">
            <figure v-for="frame in capturedFrames" :key="frame.timestamp" class="overflow-hidden rounded-xl bg-canvas">
              <img :src="frame.image" :alt="frame.reason" class="aspect-video w-full object-cover" />
              <figcaption class="px-2 py-1.5 text-xs text-muted">{{ frame.reason }}</figcaption>
            </figure>
          </div>
        </div>

        <!-- Highlights -->
        <div v-if="reportResult.highlights.length > 0">
          <h4 class="mb-2 flex items-center gap-2 text-sm font-bold text-mint">
            <span>✨</span> 训练亮点
          </h4>
          <ul class="space-y-2">
            <li v-for="(h, i) in reportResult.highlights" :key="i" class="rounded-xl bg-mint/5 p-3 text-sm text-ink">
              {{ h }}
            </li>
          </ul>
        </div>

        <!-- Corrections -->
        <div v-if="reportResult.corrections.length > 0">
          <h4 class="mb-2 flex items-center gap-2 text-sm font-bold text-coral">
            <span>💡</span> 改进建议
          </h4>
          <ul class="space-y-2">
            <li v-for="(c, i) in reportResult.corrections" :key="i" class="rounded-xl bg-coral/5 p-3 text-sm text-ink">
              {{ c }}
            </li>
          </ul>
        </div>

        <!-- Recovery Plan -->
        <div>
          <h4 class="mb-2 flex items-center gap-2 text-sm font-bold text-ocean">
            <span>🧘</span> 恢复计划
          </h4>
          <div class="rounded-xl bg-ocean/5 p-3 text-sm text-ink">
            {{ reportResult.recovery_plan }}
          </div>
        </div>

        <!-- Next Session Goals -->
        <div v-if="reportResult.next_session_goals.length > 0">
          <h4 class="mb-2 flex items-center gap-2 text-sm font-bold text-amber">
            <span>🎯</span> 下次训练目标
          </h4>
          <ol class="space-y-2">
            <li v-for="(g, i) in reportResult.next_session_goals" :key="i" class="flex items-start gap-2 text-sm text-ink">
              <span class="font-bold text-amber">{{ i + 1 }}.</span>{{ g }}
            </li>
          </ol>
        </div>
      </div>
    </el-dialog>
  </WebShell>
</template>
