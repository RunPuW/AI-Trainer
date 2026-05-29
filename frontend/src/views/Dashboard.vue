<script setup lang="ts">
import { ref, onMounted, computed } from 'vue';
import { useRouter } from 'vue-router';
import { Plus } from '@element-plus/icons-vue';
import WebShell from '@/components/WebShell.vue';
import { useAuthStore } from '@/stores/auth';
import { getDashboardStats, getRecentSessions, type DashboardStats, type RecentSession } from '@/api/dashboard';

const router = useRouter();
const authStore = useAuthStore();

const userName = ref(authStore.user?.username || '训练者');
const loading = ref(false);
const hasProfile = ref(true); // TODO: check if user has completed questionnaire

const stats = ref<DashboardStats | null>(null);
const recentSessions = ref<RecentSession[]>([]);

// Quick actions
const quickActions = [
  { label: '开始训练', icon: '🔥', path: '/workout', color: 'from-orange to-coral' },
  { label: '体能问卷', icon: '📝', path: '/questionnaire', color: 'from-indigo to-ocean' },
  { label: '动作库', icon: '📚', path: '/movements', color: 'from-mint to-water' },
];

// Computed stats for display
const displayStats = computed(() => [
  { 
    label: '训练次数', 
    value: stats.value?.total_sessions.toString() || '0', 
    trend: null,
    icon: '🔥', 
    color: 'from-orange to-coral' 
  },
  { 
    label: '累计时长', 
    value: stats.value ? formatDuration(stats.value.total_duration_min) : '0分', 
    trend: null,
    icon: '⏱️', 
    color: 'from-indigo to-ocean' 
  },
  { 
    label: '完成动作', 
    value: stats.value?.total_exercises.toString() || '0', 
    trend: null,
    icon: '💪', 
    color: 'from-mint to-water' 
  },
  { 
    label: '连续天数', 
    value: stats.value?.streak_days.toString() || '0', 
    trend: stats.value && stats.value.streak_days > 0 ? '🔥' : null,
    icon: '📅', 
    color: 'from-violet to-indigo' 
  },
]);

function formatDuration(minutes: number): string {
  if (!minutes || minutes === 0) return '0分';
  if (minutes < 60) {
    return `${minutes}分`;
  }
  const hours = Math.floor(minutes / 60);
  const mins = minutes % 60;
  return mins > 0 ? `${hours}时${mins}分` : `${hours}时`;
}

function formatDate(dateStr: string): string {
  if (!dateStr) return '';
  const date = new Date(dateStr);
  const now = new Date();
  const diff = now.getTime() - date.getTime();
  const days = Math.floor(diff / (1000 * 60 * 60 * 24));
  
  if (days === 0) return '今天';
  if (days === 1) return '昨天';
  if (days < 7) return `${days}天前`;
  
  return date.toLocaleDateString('zh-CN', {
    month: 'short',
    day: 'numeric'
  });
}

async function loadDashboardData() {
  loading.value = true;
  try {
    const [statsRes, sessionsRes] = await Promise.all([
      getDashboardStats(),
      getRecentSessions(5)
    ]);
    stats.value = statsRes.data;
    recentSessions.value = sessionsRes.data;
  } catch (error: any) {
    console.error('Failed to load dashboard data:', error);
  } finally {
    loading.value = false;
  }
}

function getMovementIcon(movement: string): string {
  const iconMap: Record<string, string> = {
    'squat': '🦵',
    '深蹲': '🦵',
    'push-up': '💪',
    '俯卧撑': '💪',
    'plank': '📐',
    '平板支撑': '📐',
    'lunge': '🚶',
    '弓步蹲': '🚶',
  };
  return iconMap[movement] || '🏋️';
}

function getAccuracyBg(accuracy: number): string {
  if (accuracy >= 80) return 'bg-mint';
  if (accuracy >= 60) return 'bg-amber';
  return 'bg-coral';
}

onMounted(() => {
  loadDashboardData();
  // Check if user has profile
  const questionnaireCompleted = localStorage.getItem('questionnaire_completed');
  hasProfile.value = !!questionnaireCompleted;
});
</script>

<template>
  <WebShell title="训练面板" subtitle="欢迎回来，继续你的训练之旅">
    <!-- Welcome Card -->
    <div class="mb-6 rounded-[28px] bg-gradient-to-r from-indigo to-violet p-6 text-white md:p-8">
      <div class="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <h2 class="text-2xl font-black">你好，{{ userName }} 👋</h2>
          <p class="mt-2 text-white/70">今天也要元气满满地训练哦</p>
        </div>
        <el-button
          size="large"
          round
          class="!w-fit !bg-white !text-indigo !font-bold !border-none"
          @click="router.push('/workout')"
        >
          <template #icon>
            <el-icon><Plus /></el-icon>
          </template>
          开始训练
        </el-button>
      </div>
    </div>

    <!-- Quick Actions -->
    <div class="mb-6 flex gap-3 overflow-x-auto pb-2 md:hidden">
      <button
        v-for="action in quickActions"
        :key="action.path"
        class="flex shrink-0 items-center gap-2 rounded-2xl px-4 py-3 text-sm font-semibold transition active:scale-95"
        :class="`bg-gradient-to-r ${action.color} text-white shadow-lg`"
        @click="router.push(action.path)"
      >
        <span>{{ action.icon }}</span>
        {{ action.label }}
      </button>
    </div>

    <!-- Stats Grid -->
    <div class="mb-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
      <div
        v-for="stat in displayStats"
        :key="stat.label"
        class="app-card flex items-center gap-4 p-5"
        v-loading="loading"
      >
        <div
          class="grid h-12 w-12 shrink-0 place-items-center rounded-2xl bg-gradient-to-br text-xl text-white"
          :class="stat.color"
        >
          {{ stat.icon }}
        </div>
        <div class="min-w-0 flex-1">
          <div class="flex items-center gap-2">
            <p class="text-2xl font-black text-ink">{{ stat.value }}</p>
            <span v-if="stat.trend" class="text-sm">{{ stat.trend }}</span>
          </div>
          <p class="text-sm text-muted">{{ stat.label }}</p>
        </div>
      </div>
    </div>

    <!-- Main Content Grid -->
    <div class="grid gap-6 lg:grid-cols-[1fr_400px]">
      <!-- Recent Training Sessions -->
      <div class="app-card p-6" v-loading="loading">
        <div class="mb-4 flex items-center justify-between">
          <h3 class="text-lg font-bold text-ink">最近训练</h3>
          <el-button 
            v-if="recentSessions.length > 0"
            text
            size="small"
            class="!text-indigo"
            @click="router.push('/workout')"
          >
            开始训练 →
          </el-button>
        </div>
        
        <div v-if="recentSessions.length === 0" class="py-12 text-center">
          <p class="text-4xl">🏋️</p>
          <p class="mt-3 text-muted">还没有训练记录</p>
          <el-button 
            round 
            class="!mt-4 !border-indigo/30 !text-indigo"
            @click="router.push('/workout')"
          >
            开始第一次训练
          </el-button>
        </div>
        
        <div v-else class="space-y-3">
          <div
            v-for="session in recentSessions"
            :key="session.id"
            class="flex items-center gap-4 rounded-2xl bg-canvas p-4 transition hover:bg-canvas/80"
          >
            <div class="grid h-12 w-12 shrink-0 place-items-center rounded-2xl bg-indigo/10 text-2xl">
              {{ getMovementIcon(session.movement) }}
            </div>
            <div class="min-w-0 flex-1">
              <p class="font-semibold text-ink truncate">{{ session.movement }}</p>
              <p class="text-sm text-muted">{{ formatDate(session.date) }}</p>
            </div>
            <div class="shrink-0 text-right">
              <p class="font-bold text-indigo">{{ session.reps }} 次</p>
              <div class="mt-1 flex items-center justify-end gap-1.5">
                <div class="h-1.5 w-12 overflow-hidden rounded-full bg-black/10">
                  <div 
                    class="h-full rounded-full transition-all"
                    :class="getAccuracyBg(session.accuracy)"
                    :style="{ width: `${session.accuracy}%` }"
                  />
                </div>
                <span class="text-xs text-muted">{{ session.accuracy }}%</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Right Column -->
      <div class="space-y-6">
        <!-- Training Plan Card -->
        <div class="app-card overflow-hidden">
          <div class="p-6">
            <div class="mb-4 flex items-center justify-between">
              <h3 class="text-lg font-bold text-ink">训练计划</h3>
              <span class="rounded-full bg-amber/10 px-2.5 py-1 text-xs font-bold text-amber">
                AI 生成
              </span>
            </div>
            
            <div v-if="!hasProfile" class="rounded-2xl bg-canvas p-4 text-center">
              <p class="text-sm text-muted">完成体能问卷，获取专属训练计划</p>
              <el-button 
                round 
                size="small"
                class="!mt-3 !bg-indigo !text-white !border-none"
                @click="router.push('/questionnaire')"
              >
                去填写
              </el-button>
            </div>
            
            <div v-else class="rounded-2xl bg-gradient-to-r from-indigo/5 to-violet/5 p-4">
              <div class="flex items-center gap-3">
                <div class="grid h-10 w-10 place-items-center rounded-xl bg-indigo text-lg text-white">
                  🎯
                </div>
                <div>
                  <p class="font-semibold text-ink">12周增肌计划</p>
                  <p class="text-xs text-muted">每周 3 次 · 中级强度</p>
                </div>
              </div>
              <div class="mt-3 flex gap-2">
                <el-button 
                  round 
                  size="small"
                  class="flex-1 !bg-indigo !text-white !border-none"
                  @click="router.push('/workout')"
                >
                  开始第 1 天
                </el-button>
                <el-button 
                  round 
                  size="small"
                  class="flex-1 !border-indigo/30 !text-indigo"
                >
                  查看详情
                </el-button>
              </div>
            </div>
          </div>
          
          <!-- Weekly Schedule Mini -->
          <div class="border-t border-black/5 p-4">
            <p class="mb-3 text-xs font-semibold text-muted">本周安排</p>
            <div class="flex justify-between gap-1">
              <div 
                v-for="(day, i) in ['一', '二', '三', '四', '五', '六', '日']" 
                :key="i"
                class="flex flex-col items-center gap-1"
              >
                <span class="text-[10px] text-muted">{{ day }}</span>
                <div 
                  class="h-8 w-8 rounded-full"
                  :class="
                    i === 1 || i === 3 || i === 5 
                      ? 'bg-indigo text-white grid place-items-center text-xs font-bold' 
                      : 'bg-canvas'
                  "
                >
                  {{ i === 1 || i === 3 || i === 5 ? '✓' : '' }}
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Tips Card -->
        <div class="app-card p-5">
          <h4 class="mb-3 flex items-center gap-2 text-sm font-bold text-ink">
            <span class="text-lg">💡</span> 训练小贴士
          </h4>
          <div class="space-y-2">
            <p class="rounded-xl bg-mint/5 p-3 text-xs leading-relaxed text-ink">
              <span class="font-semibold text-mint">热身提醒：</span>
              训练前请进行 5-10 分钟热身，激活关节和肌肉
            </p>
            <p class="rounded-xl bg-ocean/5 p-3 text-xs leading-relaxed text-ink">
              <span class="font-semibold text-ocean">姿势纠正：</span>
              深蹲时注意膝盖与脚尖方向一致，核心收紧
            </p>
          </div>
        </div>
      </div>
    </div>
  </WebShell>
</template>
