<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { ElMessage } from 'element-plus';
import { Calendar, ArrowRight, Check, Clock, Trophy } from '@element-plus/icons-vue';
import WebShell from '@/components/WebShell.vue';
import { generateTrainingPlan, type PlanResponse, type PlanDay } from '@/api/plan';
import { getProfile } from '@/api/profile';

const router = useRouter();

const generating = ref(false);
const currentPlan = ref<PlanResponse | null>(null);
const selectedDay = ref<number | null>(null);
const hasProfile = ref(false);
const userProfile = ref<any>(null);

// Mock plan for demo
const mockPlan: PlanResponse = {
  plan_id: 'plan_demo',
  duration_weeks: 4,
  notes: '这是一个适合新手的全身训练计划，重点打好动作基础和建立训练习惯。',
  weekly_schedule: [
    {
      day: '周一',
      focus: '下肢力量',
      exercises: [
        { name: '深蹲', sets: 3, reps: '10-12', rest_seconds: 90, notes: '注意膝盖方向' },
        { name: '弓步蹲', sets: 3, reps: '每边10次', rest_seconds: 60 },
        { name: '臀桥', sets: 3, reps: '15', rest_seconds: 60 },
        { name: '小腿提踵', sets: 3, reps: '20', rest_seconds: 45 },
      ],
    },
    {
      day: '周二',
      focus: '上肢推力',
      exercises: [
        { name: '俯卧撑', sets: 3, reps: '8-12', rest_seconds: 90, notes: '可采用跪姿' },
        { name: '哑铃肩推', sets: 3, reps: '10', rest_seconds: 60 },
        { name: '三头肌屈伸', sets: 3, reps: '12', rest_seconds: 45 },
      ],
    },
    {
      day: '周三',
      focus: '休息日',
      exercises: [],
    },
    {
      day: '周四',
      focus: '上肢拉力+核心',
      exercises: [
        { name: '哑铃划船', sets: 3, reps: '每边12次', rest_seconds: 60 },
        { name: '超人式', sets: 3, reps: '15', rest_seconds: 45 },
        { name: '平板支撑', sets: 3, reps: '30秒', rest_seconds: 60 },
        { name: '死虫式', sets: 3, reps: '每边10次', rest_seconds: 45 },
      ],
    },
    {
      day: '周五',
      focus: '全身循环',
      exercises: [
        { name: '深蹲', sets: 2, reps: '15', rest_seconds: 30 },
        { name: '俯卧撑', sets: 2, reps: '10', rest_seconds: 30 },
        { name: '弓步蹲', sets: 2, reps: '每边8次', rest_seconds: 30 },
        { name: '平板支撑', sets: 2, reps: '20秒', rest_seconds: 30 },
      ],
    },
    {
      day: '周六',
      focus: '有氧/活动',
      exercises: [
        { name: '快走/慢跑', sets: 1, reps: '20-30分钟', rest_seconds: 0 },
        { name: '拉伸放松', sets: 1, reps: '10分钟', rest_seconds: 0 },
      ],
    },
    {
      day: '周日',
      focus: '完全休息',
      exercises: [],
    },
  ],
};

async function loadProfile() {
  try {
    const { data } = await getProfile();
    if (data.questionnaire) {
      hasProfile.value = true;
      userProfile.value = data.questionnaire;
    }
  } catch (error) {
    console.error('Failed to load profile:', error);
  }
}

async function generatePlan() {
  if (!hasProfile.value) {
    ElMessage.warning('请先在体能问卷中完善个人信息');
    return;
  }

  generating.value = true;
  try {
    // Transform profile to match API format
    const age = userProfile.value.birth_date 
      ? new Date().getFullYear() - new Date(userProfile.value.birth_date).getFullYear()
      : 25;
    
    const { data } = await generateTrainingPlan({
      gender: userProfile.value.gender,
      age,
      height_cm: userProfile.value.height_cm,
      weight_kg: userProfile.value.weight_kg,
      experience: userProfile.value.fitness_level,
      injuries: userProfile.value.injuries?.map((i: any) => i.area) || [],
      available_equipment: userProfile.value.equipment || ['bodyweight'],
      goal: userProfile.value.goal,
      sessions_per_week: userProfile.value.weekly_days,
    });
    currentPlan.value = data;
    ElMessage.success('训练计划已生成');
  } catch (error: any) {
    console.error('Failed to generate plan:', error);
    ElMessage.error('生成计划失败，使用默认演示计划');
    currentPlan.value = mockPlan;
  } finally {
    generating.value = false;
  }
}

function viewDayDetail(dayIndex: number) {
  selectedDay.value = selectedDay.value === dayIndex ? null : dayIndex;
}

function startExercise(exerciseName: string) {
  // Find matching movement ID
  const movementMap: Record<string, string> = {
    '深蹲': 'squat',
    '弓步蹲': 'lunge',
    '俯卧撑': 'push-up',
    '平板支撑': 'plank',
  };
  
  const movementId = movementMap[exerciseName];
  if (movementId) {
    localStorage.setItem('selected_movement', movementId);
    router.push('/workout');
  } else {
    router.push('/workout');
  }
}

function formatDuration(seconds: number): string {
  if (seconds < 60) return `${seconds}秒`;
  return `${Math.floor(seconds / 60)}分钟`;
}

function getDayStatus(day: PlanDay): 'completed' | 'today' | 'pending' {
  // Mock status logic - in real app would check against actual completed workouts
  const today = new Date().getDay();
  const dayMap: Record<string, number> = { '周一': 1, '周二': 2, '周三': 3, '周四': 4, '周五': 5, '周六': 6, '周日': 0 };
  const dayIndex = dayMap[day.day];
  
  if (dayIndex === today) return 'today';
  if (dayIndex < today) return 'completed';
  return 'pending';
}

onMounted(() => {
  loadProfile();
  // For demo, show mock plan initially
  currentPlan.value = mockPlan;
});
</script>

<template>
  <WebShell title="训练计划" subtitle="查看和管理你的个性化训练计划">
    <div class="space-y-6">
      <!-- Header Card -->
      <div class="app-card overflow-hidden">
        <div class="bg-gradient-to-r from-indigo to-violet p-6 text-white">
          <div class="flex items-center justify-between">
            <div>
              <h2 class="text-xl font-black">{{ currentPlan?.duration_weeks || 4 }} 周训练计划</h2>
              <p class="mt-1 text-sm text-white/70">{{ currentPlan?.notes || '根据你的体能水平定制的渐进式训练计划' }}</p>
            </div>
            <div class="hidden h-16 w-16 items-center justify-center rounded-2xl bg-white/20 text-3xl sm:flex">
              🎯
            </div>
          </div>
        </div>
        
        <div class="flex items-center justify-between p-4">
          <div class="flex items-center gap-4 text-sm text-muted">
            <span class="flex items-center gap-1">
              <el-icon><Calendar /></el-icon>
              第 1 / {{ currentPlan?.duration_weeks || 4 }} 周
            </span>
            <span class="flex items-center gap-1">
              <el-icon><Trophy /></el-icon>
              每周 {{ currentPlan?.weekly_schedule?.filter(d => d.exercises.length > 0).length || 4 }} 次训练
            </span>
          </div>
          <el-button 
            type="primary" 
            round
            :loading="generating"
            class="!bg-indigo !border-none"
            @click="generatePlan"
          >
            <template #icon>
              <span>✨</span>
            </template>
            {{ hasProfile ? '重新生成计划' : '去完善资料' }}
          </el-button>
        </div>
      </div>

      <div v-if="!currentPlan" class="app-card py-20 text-center">
        <p class="text-5xl">📝</p>
        <p class="mt-4 text-lg font-semibold text-ink">还没有训练计划</p>
        <p class="mt-1 text-sm text-muted">完善体能问卷后，AI 将为你生成个性化训练计划</p>
        <el-button 
          round 
          class="!mt-6 !bg-indigo !text-white !border-none"
          @click="hasProfile ? generatePlan() : router.push('/questionnaire')"
        >
          {{ hasProfile ? '立即生成' : '去完善资料' }}
        </el-button>
      </div>

      <div v-else class="grid gap-4 lg:grid-cols-[1fr_400px]">
        <!-- Weekly Schedule -->
        <div class="space-y-3">
          <div
            v-for="(day, index) in currentPlan.weekly_schedule"
            :key="index"
            class="app-card cursor-pointer overflow-hidden transition hover:shadow-lg"
            :class="selectedDay === index ? 'ring-2 ring-indigo' : ''"
            @click="viewDayDetail(index)"
          >
            <div class="flex items-center gap-4 p-4">
              <!-- Day Circle -->
              <div
                class="grid h-12 w-12 shrink-0 place-items-center rounded-full text-sm font-bold"
                :class="{
                  'bg-mint text-white': getDayStatus(day) === 'completed',
                  'bg-indigo text-white': getDayStatus(day) === 'today',
                  'bg-canvas text-muted': getDayStatus(day) === 'pending',
                }"
              >
                <el-icon v-if="getDayStatus(day) === 'completed'"><Check /></el-icon>
                <span v-else>{{ day.day.slice(0, 2) }}</span>
              </div>
              
              <!-- Day Info -->
              <div class="min-w-0 flex-1">
                <div class="flex items-center gap-2">
                  <span class="font-semibold text-ink">{{ day.day }}</span>
                  <span 
                    class="rounded-full px-2 py-0.5 text-[10px] font-bold"
                    :class="{
                      'bg-mint/10 text-mint': getDayStatus(day) === 'completed',
                      'bg-indigo/10 text-indigo': getDayStatus(day) === 'today',
                      'bg-amber/10 text-amber': day.focus === '休息日',
                      'bg-orange/10 text-orange': day.focus === '完全休息',
                    }"
                  >
                    {{ getDayStatus(day) === 'today' ? '今天' : getDayStatus(day) === 'completed' ? '已完成' : day.focus }}
                  </span>
                </div>
                <p v-if="day.exercises.length > 0" class="mt-0.5 text-sm text-muted truncate">
                  {{ day.exercises.map(e => e.name).join('、') }}
                </p>
                <p v-else class="mt-0.5 text-sm text-muted">适当休息，让身体恢复</p>
              </div>
              
              <!-- Arrow -->
              <el-icon 
                class="text-muted transition"
                :class="selectedDay === index ? 'rotate-90' : ''"
              >
                <ArrowRight />
              </el-icon>
            </div>
            
            <!-- Expanded Detail -->
            <div 
              v-if="selectedDay === index && day.exercises.length > 0"
              class="border-t border-black/5 bg-canvas/50 px-4 py-4"
            >
              <div class="space-y-3">
                <div
                  v-for="(exercise, exIndex) in day.exercises"
                  :key="exIndex"
                  class="flex items-center justify-between rounded-xl bg-white p-3"
                >
                  <div class="flex items-center gap-3">
                    <div class="grid h-8 w-8 place-items-center rounded-lg bg-indigo/10 text-sm font-bold text-indigo">
                      {{ exIndex + 1 }}
                    </div>
                    <div>
                      <p class="font-semibold text-ink">{{ exercise.name }}</p>
                      <p v-if="exercise.notes" class="text-xs text-muted">{{ exercise.notes }}</p>
                    </div>
                  </div>
                  <div class="text-right text-sm">
                    <p class="font-semibold text-ink">{{ exercise.sets }} 组 × {{ exercise.reps }}</p>
                    <p class="flex items-center justify-end gap-1 text-xs text-muted">
                      <el-icon class="text-[10px]"><Clock /></el-icon>
                      休息 {{ formatDuration(exercise.rest_seconds) }}
                    </p>
                  </div>
                </div>
              </div>
              
              <el-button 
                round
                class="!mt-4 !w-full !bg-indigo !text-white !border-none"
                @click.stop="startExercise(day.exercises[0]?.name || '深蹲')"
              >
                开始 {{ day.focus }} 训练
              </el-button>
            </div>
          </div>
        </div>

        <!-- Side Panel -->
        <div class="space-y-4">
          <!-- Progress Card -->
          <div class="app-card p-5">
            <h3 class="mb-4 flex items-center gap-2 text-sm font-bold text-ink">
              <span>📊</span> 本周进度
            </h3>
            <div class="mb-2 flex justify-between text-sm">
              <span class="text-muted">已完成 2 / {{ currentPlan.weekly_schedule.filter(d => d.exercises.length > 0).length }} 次</span>
              <span class="font-semibold text-indigo">50%</span>
            </div>
            <div class="h-2 overflow-hidden rounded-full bg-canvas">
              <div class="h-full rounded-full bg-gradient-to-r from-indigo to-violet transition-all" style="width: 50%" />
            </div>
          </div>

          <!-- Tips Card -->
          <div class="app-card p-5">
            <h3 class="mb-3 flex items-center gap-2 text-sm font-bold text-ink">
              <span>💡</span> 训练提示
            </h3>
            <ul class="space-y-2 text-xs leading-relaxed text-muted">
              <li class="flex gap-2">
                <span class="text-mint">•</span>
                <span>建议每次训练前进行 5-10 分钟热身</span>
              </li>
              <li class="flex gap-2">
                <span class="text-mint">•</span>
                <span>组间休息时间可根据个人感受调整</span>
              </li>
              <li class="flex gap-2">
                <span class="text-mint">•</span>
                <span>如果无法完成规定次数，可减少负重或次数</span>
              </li>
              <li class="flex gap-2">
                <span class="text-mint">•</span>
                <span>感觉身体不适时请立即停止训练</span>
              </li>
            </ul>
          </div>

          <!-- Quick Action -->
          <el-button 
            round
            class="!w-full !py-6 !text-base !font-bold !bg-gradient-to-r !from-orange !to-coral !border-none !text-white"
            @click="router.push('/workout')"
          >
            立即开始训练 🔥
          </el-button>
        </div>
      </div>
    </div>
  </WebShell>
</template>
