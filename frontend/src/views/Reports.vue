<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { ElMessage } from 'element-plus';
import { Document, TrendCharts, Calendar, Trophy } from '@element-plus/icons-vue';
import WebShell from '@/components/WebShell.vue';
import { getWorkoutHistory, type WorkoutLog } from '@/api/workout';
import { getDashboardStats } from '@/api/dashboard';

const router = useRouter();

const loading = ref(false);
const workouts = ref<WorkoutLog[]>([]);
const stats = ref<any>(null);
const selectedReport = ref<WorkoutLog | null>(null);
const reportDialogVisible = ref(false);
const timeRange = ref('month');

const timeRangeOptions = [
  { label: '最近7天', value: 'week' },
  { label: '最近30天', value: 'month' },
  { label: '全部', value: 'all' },
];

// Error type to user-friendly description mapping
const errorDescriptionMap: Record<string, string> = {
  'trunk_forward_lean': '躯干前倾过大，建议加强核心训练，保持背部挺直',
  'knee_valgus': '膝盖内扣，注意膝盖对准脚尖方向，加强臀中肌训练',
  'insufficient_depth': '深蹲深度不足，建议增加髋关节灵活性训练',
  'hip_dominant': '臀部主导过多，注意膝盖弯曲配合',
  'knee_dominant': '膝盖主导过多，注意臀部后推',
  'heel_lift': '脚跟抬起，重心应放在脚后跟，可尝试穿举重鞋',
  'knee_asymmetry': '左右膝盖不对称，注意两侧均衡发力',
};

function getErrorCorrections(errors: string[] | undefined): string[] {
  if (!errors || errors.length === 0) return [];
  const unique = [...new Set(errors.map(e => e.split(':')[0].trim()))];
  return unique.map(e => errorDescriptionMap[e] || `${e}：需要注意纠正`).slice(0, 3);
}

function getHighlights(workout: WorkoutLog): string[] {
  const highlights: string[] = [];
  if (workout.rep_count && workout.rep_count >= 5) highlights.push(`完成 ${workout.rep_count} 次训练，训练量达标`);
  if (!workout.errors || workout.errors.length === 0) highlights.push('本次训练无明显错误，动作标准');
  else if (workout.errors.length <= 2) highlights.push('错误数量较少，动作质量良好');
  if (workout.duration_min && workout.duration_min >= 10) highlights.push(`训练时长 ${workout.duration_min} 分钟，持续性好`);
  return highlights.length > 0 ? highlights : ['完成本次训练'];
}

async function loadData() {
  loading.value = true;
  try {
    const [workoutRes, statsRes] = await Promise.all([
      getWorkoutHistory(20),
      getDashboardStats(),
    ]);
    workouts.value = workoutRes.data;
    stats.value = statsRes.data;
  } catch (error: any) {
    console.error('Failed to load reports:', error);
    ElMessage.error('加载数据失败');
  } finally {
    loading.value = false;
  }
}

function viewReportDetail(workout: WorkoutLog) {
  selectedReport.value = workout;
  reportDialogVisible.value = true;
}

function formatDate(dateStr: string): string {
  if (!dateStr) return '';
  const date = new Date(dateStr);
  return date.toLocaleDateString('zh-CN', {
    month: 'long',
    day: 'numeric',
    weekday: 'short',
  });
}

function getMovementIcon(type: string): string {
  const icons: Record<string, string> = {
    'squat': '🦵',
    'push-up': '💪',
    'plank': '📐',
    'lunge': '🚶',
    '深蹲': '🦵',
    '俯卧撑': '💪',
    '平板支撑': '📐',
    '弓步蹲': '🚶',
  };
  return icons[type] || '🏋️';
}

function calculateAccuracy(errors: string[] | undefined): number {
  if (!errors || errors.length === 0) return 100;
  return Math.max(0, 100 - errors.length * 10);
}

function getAccuracyColor(accuracy: number): string {
  if (accuracy >= 80) return 'text-mint';
  if (accuracy >= 60) return 'text-amber';
  return 'text-coral';
}

function exportReport(_workout: WorkoutLog) {
  ElMessage.success('报告导出功能开发中');
}

onMounted(() => {
  loadData();
});
</script>

<template>
  <WebShell title="训练报告" subtitle="查看详细训练数据分析和进步轨迹">
    <div class="space-y-6">
      <!-- Summary Cards -->
      <div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div class="app-card flex items-center gap-4 p-5" v-loading="loading">
          <div class="grid h-12 w-12 shrink-0 place-items-center rounded-2xl bg-gradient-to-br from-orange to-coral text-xl text-white">
            <el-icon><Trophy /></el-icon>
          </div>
          <div>
            <p class="text-2xl font-black text-ink">{{ calculateAccuracy([]) }}</p>
            <p class="text-xs text-muted">平均动作标准度</p>
          </div>
        </div>
        
        <div class="app-card flex items-center gap-4 p-5" v-loading="loading">
          <div class="grid h-12 w-12 shrink-0 place-items-center rounded-2xl bg-gradient-to-br from-indigo to-ocean text-xl text-white">
            <el-icon><TrendCharts /></el-icon>
          </div>
          <div>
            <p class="text-2xl font-black text-ink">+12%</p>
            <p class="text-xs text-muted">本月进步幅度</p>
          </div>
        </div>
        
        <div class="app-card flex items-center gap-4 p-5" v-loading="loading">
          <div class="grid h-12 w-12 shrink-0 place-items-center rounded-2xl bg-gradient-to-br from-mint to-water text-xl text-white">
            <el-icon><Calendar /></el-icon>
          </div>
          <div>
            <p class="text-2xl font-black text-ink">{{ workouts.length }}</p>
            <p class="text-xs text-muted">总训练记录</p>
          </div>
        </div>
        
        <div class="app-card flex items-center gap-4 p-5" v-loading="loading">
          <div class="grid h-12 w-12 shrink-0 place-items-center rounded-2xl bg-gradient-to-br from-violet to-indigo text-xl text-white">
            <el-icon><Document /></el-icon>
          </div>
          <div>
            <p class="text-2xl font-black text-ink">{{ stats?.total_reps || 0 }}</p>
            <p class="text-xs text-muted">累计完成次数</p>
          </div>
        </div>
      </div>

      <!-- Report List -->
      <div class="app-card p-6" v-loading="loading">
        <div class="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <h3 class="text-lg font-bold text-ink">训练记录</h3>
          <el-radio-group v-model="timeRange" size="small">
            <el-radio-button v-for="opt in timeRangeOptions" :key="opt.value" :label="opt.value">
              {{ opt.label }}
            </el-radio-button>
          </el-radio-group>
        </div>
        
        <div v-if="workouts.length === 0" class="py-16 text-center">
          <p class="text-5xl">📊</p>
          <p class="mt-4 text-muted">还没有训练记录</p>
          <el-button 
            round 
            class="!mt-4 !bg-indigo !text-white !border-none"
            @click="router.push('/workout')"
          >
            开始第一次训练
          </el-button>
        </div>
        
        <div v-else class="space-y-3">
          <div
            v-for="workout in workouts"
            :key="workout.id"
            class="flex flex-col gap-3 rounded-2xl bg-canvas p-4 transition hover:bg-canvas/80 sm:flex-row sm:items-center"
          >
            <div class="flex items-center gap-4">
              <div class="grid h-12 w-12 shrink-0 place-items-center rounded-2xl bg-indigo/10 text-2xl">
                {{ getMovementIcon(workout.exercise_type) }}
              </div>
              <div>
                <p class="font-semibold text-ink">{{ workout.exercise_type || '深蹲' }} 训练</p>
                <p class="text-sm text-muted">{{ formatDate(workout.session_date) }}</p>
              </div>
            </div>
            
            <div class="flex flex-1 items-center justify-between gap-4 sm:justify-end">
              <div class="flex gap-6 text-sm">
                <div class="text-center">
                  <p class="font-bold text-indigo">{{ workout.rep_count }} 次</p>
                  <p class="text-xs text-muted">完成动作</p>
                </div>
                <div class="text-center">
                  <p class="font-bold text-ink">{{ workout.duration_min }} 分钟</p>
                  <p class="text-xs text-muted">训练时长</p>
                </div>
                <div class="text-center">
                  <p class="font-bold" :class="getAccuracyColor(calculateAccuracy(workout.errors))">
                    {{ calculateAccuracy(workout.errors) }}%
                  </p>
                  <p class="text-xs text-muted">动作标准度</p>
                </div>
              </div>
              
              <div class="flex gap-2">
                <el-button text size="small" class="!text-indigo" @click="viewReportDetail(workout)">
                  查看详情
                </el-button>
                <el-button text size="small" @click="exportReport(workout)">
                  导出
                </el-button>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Progress Chart Placeholder -->
      <div class="app-card p-6">
        <h3 class="mb-4 text-lg font-bold text-ink">进步趋势</h3>
        <div class="flex h-64 items-center justify-center rounded-2xl bg-canvas">
          <div class="text-center">
            <p class="text-4xl">📈</p>
            <p class="mt-2 text-sm text-muted">训练趋势图表开发中</p>
            <p class="text-xs text-muted">记录更多数据后将显示你的进步曲线</p>
          </div>
        </div>
      </div>
    </div>

    <!-- Report Detail Dialog -->
    <el-dialog
      v-model="reportDialogVisible"
      :title="selectedReport ? formatDate(selectedReport.session_date) + ' 训练报告' : '训练报告'"
      width="600px"
      class="!rounded-2xl"
    >
      <div v-if="selectedReport" class="space-y-6">
        <!-- Score Header -->
        <div class="flex items-center gap-4 rounded-2xl bg-gradient-to-r from-indigo/5 to-violet/5 p-4">
          <div class="grid h-16 w-16 place-items-center rounded-full bg-gradient-to-br from-indigo to-violet text-2xl font-black text-white">
            {{ calculateAccuracy(selectedReport.errors) }}
          </div>
          <div>
            <p class="font-bold text-ink">综合评分</p>
            <p class="text-sm text-muted">基于动作标准度、完成度和稳定性</p>
          </div>
        </div>

        <!-- Stats Grid -->
        <div class="grid grid-cols-3 gap-3">
          <div class="rounded-xl bg-canvas p-3 text-center">
            <p class="text-xl font-bold text-indigo">{{ selectedReport.rep_count }}</p>
            <p class="text-[10px] text-muted">完成次数</p>
          </div>
          <div class="rounded-xl bg-canvas p-3 text-center">
            <p class="text-xl font-bold text-orange">{{ selectedReport.duration_min }}</p>
            <p class="text-[10px] text-muted">训练分钟</p>
          </div>
          <div class="rounded-xl bg-canvas p-3 text-center">
            <p class="text-xl font-bold text-mint">{{ selectedReport.errors?.length || 0 }}</p>
            <p class="text-[10px] text-muted">检测到问题</p>
          </div>
        </div>

        <!-- AI Analysis -->
        <div class="space-y-4">
          <div v-if="getHighlights(selectedReport).length > 0">
            <h4 class="mb-2 flex items-center gap-2 text-sm font-bold text-mint">
              <span>✨</span> 训练亮点
            </h4>
            <ul class="space-y-1.5">
              <li v-for="(h, i) in getHighlights(selectedReport)" :key="i" class="flex items-start gap-2 text-sm text-ink">
                <span class="text-mint">•</span>{{ h }}
              </li>
            </ul>
          </div>

          <div v-if="getErrorCorrections(selectedReport.errors).length > 0">
            <h4 class="mb-2 flex items-center gap-2 text-sm font-bold text-coral">
              <span>💡</span> 改进建议
            </h4>
            <ul class="space-y-1.5">
              <li v-for="(c, i) in getErrorCorrections(selectedReport.errors)" :key="i" class="flex items-start gap-2 text-sm text-ink">
                <span class="text-coral">•</span>{{ c }}
              </li>
            </ul>
          </div>

          <div v-else>
            <h4 class="mb-2 flex items-center gap-2 text-sm font-bold text-mint">
              <span>✨</span> 表现优秀
            </h4>
            <p class="rounded-xl bg-mint/5 p-3 text-sm leading-relaxed text-ink">
              本次训练动作标准，继续保持！
            </p>
          </div>

          <div>
            <h4 class="mb-2 flex items-center gap-2 text-sm font-bold text-ocean">
              <span>🧘</span> 恢复建议
            </h4>
            <p class="rounded-xl bg-ocean/5 p-3 text-sm leading-relaxed text-ink">
              训练后建议进行全身拉伸，重点放松股四头肌、腘绳肌和臀部肌群。可使用泡沫轴辅助放松，每次 10-15 分钟。
            </p>
          </div>

          <div>
            <h4 class="mb-2 flex items-center gap-2 text-sm font-bold text-amber">
              <span>🎯</span> 下次目标
            </h4>
            <ol class="space-y-1.5">
              <li class="flex items-start gap-2 text-sm text-ink">
                <span class="font-bold text-amber">1.</span>保持动作质量，注意本次发现的问题
              </li>
              <li class="flex items-start gap-2 text-sm text-ink">
                <span class="font-bold text-amber">2.</span>尝试增加每组次数或适当增加负重
              </li>
              <li class="flex items-start gap-2 text-sm text-ink">
                <span class="font-bold text-amber">3.</span>控制动作节奏，下蹲 2 秒、站起 1 秒
              </li>
            </ol>
          </div>
        </div>
      </div>
    </el-dialog>
  </WebShell>
</template>
