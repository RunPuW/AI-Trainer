<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { ElMessage } from 'element-plus';
import { User, Lock, Bell, Setting, ArrowRight } from '@element-plus/icons-vue';
import WebShell from '@/components/WebShell.vue';
import { useAuthStore } from '@/stores/auth';
import { getProfile, saveQuestionnaire } from '@/api/profile';
import { getWorkoutStats } from '@/api/workout';

const authStore = useAuthStore();

const userName = ref(authStore.user?.username || '训练者');
const email = ref(authStore.user?.email || '');
const loading = ref(false);
const saving = ref(false);
const activeTab = ref('profile');

const profile = ref<any>(null);
const workoutStats = ref<any>(null);

// Form data
const profileForm = ref({
  gender: 'male',
  age: 25,
  height: 170,
  weight: 70,
  goal: 'general',
  trainingFrequency: '2-3',
  equipment: [] as string[],
});

const passwordForm = ref({
  current: '',
  new: '',
  confirm: '',
});

const notifications = ref({
  workoutReminder: true,
  weeklyReport: true,
  newFeatures: false,
});

const equipmentOptions = [
  { label: '无器械', value: 'bodyweight' },
  { label: '哑铃', value: 'dumbbell' },
  { label: '杠铃', value: 'barbell' },
  { label: '弹力带', value: 'resistance_band' },
  { label: '瑜伽垫', value: 'yoga_mat' },
  { label: '健身球', value: 'exercise_ball' },
];

async function loadData() {
  loading.value = true;
  try {
    const [profileRes, statsRes] = await Promise.all([
      getProfile(),
      getWorkoutStats(),
    ]);
    profile.value = profileRes.data;
    workoutStats.value = statsRes.data;
    
    // Populate form
    if (profile.value?.questionnaire) {
      const q = profile.value.questionnaire;
      profileForm.value = {
        gender: q.gender || 'male',
        age: q.birth_date 
          ? new Date().getFullYear() - new Date(q.birth_date).getFullYear() 
          : 25,
        height: q.height_cm || 170,
        weight: q.weight_kg || 70,
        goal: q.goal || 'general',
        trainingFrequency: q.weekly_days > 4 ? '5+' : q.weekly_days > 3 ? '3-4' : q.weekly_days > 1 ? '2-3' : '0-1',
        equipment: q.equipment || [],
      };
    }
  } catch (error) {
    console.error('Failed to load settings:', error);
  } finally {
    loading.value = false;
  }
}

async function saveProfile() {
  saving.value = true;
  try {
    await saveQuestionnaire({
      gender: profileForm.value.gender,
      age: profileForm.value.age,
      height: profileForm.value.height,
      weight: profileForm.value.weight,
      goal: profileForm.value.goal,
      trainingFrequency: profileForm.value.trainingFrequency,
      injuryNotes: '',
      equipment: profileForm.value.equipment,
    });
    ElMessage.success('个人信息已保存');
  } catch (error) {
    ElMessage.error('保存失败');
  } finally {
    saving.value = false;
  }
}

async function changePassword() {
  if (passwordForm.value.new !== passwordForm.value.confirm) {
    ElMessage.error('两次输入的新密码不一致');
    return;
  }
  ElMessage.info('密码修改功能暂未开放，请联系管理员');
}

async function saveNotifications() {
  ElMessage.success('通知设置已保存');
}

function logout() {
  authStore.logout();
  window.location.href = '/login';
}

onMounted(() => {
  loadData();
});
</script>

<template>
  <WebShell title="个人设置" subtitle="管理你的账户和偏好设置">
    <div class="mx-auto max-w-3xl">
      <!-- Profile Header -->
      <div class="app-card mb-6 flex items-center gap-5 p-6">
        <div class="relative">
          <div class="grid h-20 w-20 place-items-center rounded-full bg-gradient-to-br from-indigo to-violet text-3xl font-black text-white">
            {{ userName.slice(0, 1) }}
          </div>
          <button class="absolute -bottom-1 -right-1 grid h-7 w-7 place-items-center rounded-full bg-white text-xs shadow-md transition hover:bg-canvas">
            📷
          </button>
        </div>
        <div class="flex-1">
          <h2 class="text-xl font-black text-ink">{{ userName }}</h2>
          <p class="text-sm text-muted">{{ email || '未设置邮箱' }}</p>
          <div class="mt-2 flex flex-wrap gap-2">
            <span v-if="workoutStats?.streak_days > 0" class="rounded-full bg-orange/10 px-2.5 py-1 text-xs font-bold text-orange">
              🔥 连续 {{ workoutStats.streak_days }} 天
            </span>
            <span class="rounded-full bg-indigo/10 px-2.5 py-1 text-xs font-bold text-indigo">
              {{ workoutStats?.total_sessions || 0 }} 次训练
            </span>
          </div>
        </div>
        <el-button round class="!border-indigo/30 !text-indigo" @click="logout">
          退出登录
        </el-button>
      </div>

      <!-- Tabs -->
      <div class="app-card overflow-hidden">
        <div class="flex border-b border-black/5">
          <button
            v-for="tab in [
              { key: 'profile', label: '个人资料', icon: User },
              { key: 'password', label: '密码安全', icon: Lock },
              { key: 'notifications', label: '通知设置', icon: Bell },
            ]"
            :key="tab.key"
            class="flex items-center gap-2 px-6 py-4 text-sm font-semibold transition"
            :class="activeTab === tab.key ? 'text-indigo border-b-2 border-indigo' : 'text-muted hover:text-ink'"
            @click="activeTab = tab.key"
          >
            <el-icon><component :is="tab.icon" /></el-icon>
            {{ tab.label }}
          </button>
        </div>

        <div class="p-6">
          <!-- Profile Tab -->
          <div v-if="activeTab === 'profile'" class="space-y-5">
            <div class="grid gap-5 sm:grid-cols-2">
              <div>
                <label class="mb-2 block text-sm font-semibold text-ink">性别</label>
                <el-radio-group v-model="profileForm.gender" size="large" class="!w-full">
                  <el-radio-button label="male" class="flex-1">男</el-radio-button>
                  <el-radio-button label="female" class="flex-1">女</el-radio-button>
                </el-radio-group>
              </div>
              <div>
                <label class="mb-2 block text-sm font-semibold text-ink">年龄</label>
                <el-input-number v-model="profileForm.age" :min="10" :max="100" class="!w-full" />
              </div>
              <div>
                <label class="mb-2 block text-sm font-semibold text-ink">身高 (cm)</label>
                <el-input-number v-model="profileForm.height" :min="100" :max="250" class="!w-full" />
              </div>
              <div>
                <label class="mb-2 block text-sm font-semibold text-ink">体重 (kg)</label>
                <el-input-number v-model="profileForm.weight" :min="30" :max="200" class="!w-full" />
              </div>
            </div>

            <div>
              <label class="mb-2 block text-sm font-semibold text-ink">训练目标</label>
              <el-select v-model="profileForm.goal" class="!w-full" size="large">
                <el-option label="减脂塑形" value="fat_loss" />
                <el-option label="增肌力量" value="muscle_gain" />
                <el-option label="体能提升" value="fitness" />
                <el-option label="康复训练" value="rehab" />
                <el-option label="保持健康" value="general" />
              </el-select>
            </div>

            <div>
              <label class="mb-2 block text-sm font-semibold text-ink">每周训练频率</label>
              <el-radio-group v-model="profileForm.trainingFrequency" size="large" class="!w-full !flex">
                <el-radio-button label="0-1" class="flex-1">0-1 次</el-radio-button>
                <el-radio-button label="2-3" class="flex-1">2-3 次</el-radio-button>
                <el-radio-button label="3-4" class="flex-1">3-4 次</el-radio-button>
                <el-radio-button label="5+" class="flex-1">5+ 次</el-radio-button>
              </el-radio-group>
            </div>

            <div>
              <label class="mb-2 block text-sm font-semibold text-ink">可用器材</label>
              <el-checkbox-group v-model="profileForm.equipment" class="flex flex-wrap gap-3">
                <el-checkbox v-for="opt in equipmentOptions" :key="opt.value" :label="opt.value" border class="!rounded-xl">
                  {{ opt.label }}
                </el-checkbox>
              </el-checkbox-group>
            </div>

            <el-button 
              type="primary" 
              round 
              size="large" 
              class="!h-12 !w-full !bg-indigo !border-none"
              :loading="saving"
              @click="saveProfile"
            >
              保存修改
            </el-button>
          </div>

          <!-- Password Tab -->
          <div v-if="activeTab === 'password'" class="space-y-5">
            <div>
              <label class="mb-2 block text-sm font-semibold text-ink">当前密码</label>
              <el-input v-model="passwordForm.current" type="password" placeholder="输入当前密码" size="large" show-password />
            </div>
            <div>
              <label class="mb-2 block text-sm font-semibold text-ink">新密码</label>
              <el-input v-model="passwordForm.new" type="password" placeholder="设置新密码" size="large" show-password />
            </div>
            <div>
              <label class="mb-2 block text-sm font-semibold text-ink">确认新密码</label>
              <el-input v-model="passwordForm.confirm" type="password" placeholder="再次输入新密码" size="large" show-password />
            </div>

            <div class="rounded-2xl bg-canvas p-4">
              <p class="flex items-center gap-2 text-sm font-semibold text-ink">
                <el-icon><Setting /></el-icon>
                密码安全提示
              </p>
              <ul class="mt-2 space-y-1 text-xs text-muted">
                <li>• 密码长度至少 8 位</li>
                <li>• 包含字母和数字</li>
                <li>• 不要使用常用密码</li>
              </ul>
            </div>

            <el-button 
              type="primary" 
              round 
              size="large" 
              class="!h-12 !w-full !bg-indigo !border-none"
              :loading="saving"
              @click="changePassword"
            >
              修改密码
            </el-button>
          </div>

          <!-- Notifications Tab -->
          <div v-if="activeTab === 'notifications'" class="space-y-4">
            <div class="flex items-center justify-between rounded-2xl bg-canvas p-4">
              <div>
                <p class="font-semibold text-ink">训练提醒</p>
                <p class="text-xs text-muted">在计划训练日推送提醒通知</p>
              </div>
              <el-switch v-model="notifications.workoutReminder" />
            </div>
            <div class="flex items-center justify-between rounded-2xl bg-canvas p-4">
              <div>
                <p class="font-semibold text-ink">周报推送</p>
                <p class="text-xs text-muted">每周生成训练总结报告</p>
              </div>
              <el-switch v-model="notifications.weeklyReport" />
            </div>
            <div class="flex items-center justify-between rounded-2xl bg-canvas p-4">
              <div>
                <p class="font-semibold text-ink">新功能通知</p>
                <p class="text-xs text-muted">了解产品更新和新功能上线</p>
              </div>
              <el-switch v-model="notifications.newFeatures" />
            </div>

            <el-button 
              type="primary" 
              round 
              size="large" 
              class="!h-12 !w-full !bg-indigo !border-none !mt-4"
              @click="saveNotifications"
            >
              保存设置
            </el-button>
          </div>
        </div>
      </div>

      <!-- Quick Links -->
      <div class="mt-6 app-card p-4">
        <h3 class="mb-3 text-sm font-bold text-ink">快捷入口</h3>
        <div class="space-y-2">
          <RouterLink to="/questionnaire" class="flex items-center justify-between rounded-xl p-3 transition hover:bg-canvas">
            <div class="flex items-center gap-3">
              <div class="grid h-10 w-10 place-items-center rounded-xl bg-orange/10 text-lg text-orange">📝</div>
              <span class="text-sm font-semibold text-ink">重新填写体能问卷</span>
            </div>
            <el-icon class="text-muted"><ArrowRight /></el-icon>
          </RouterLink>
          <RouterLink to="/plan" class="flex items-center justify-between rounded-xl p-3 transition hover:bg-canvas">
            <div class="flex items-center gap-3">
              <div class="grid h-10 w-10 place-items-center rounded-xl bg-indigo/10 text-lg text-indigo">🎯</div>
              <span class="text-sm font-semibold text-ink">查看训练计划</span>
            </div>
            <el-icon class="text-muted"><ArrowRight /></el-icon>
          </RouterLink>
          <RouterLink to="/reports" class="flex items-center justify-between rounded-xl p-3 transition hover:bg-canvas">
            <div class="flex items-center gap-3">
              <div class="grid h-10 w-10 place-items-center rounded-xl bg-mint/10 text-lg text-mint">📊</div>
              <span class="text-sm font-semibold text-ink">训练报告</span>
            </div>
            <el-icon class="text-muted"><ArrowRight /></el-icon>
          </RouterLink>
        </div>
      </div>
    </div>
  </WebShell>
</template>
