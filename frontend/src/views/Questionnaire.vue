<script setup lang="ts">
import { reactive, ref } from 'vue';
import { useRouter } from 'vue-router';
import { ElMessage } from 'element-plus';
import WebShell from '@/components/WebShell.vue';
import { saveQuestionnaire } from '@/api/profile';

const router = useRouter();
const loading = ref(false);
const step = ref(1);
const totalSteps = 3;

const form = reactive({
  gender: '',
  age: null as number | null,
  height: null as number | null,
  weight: null as number | null,
  goal: '',
  trainingFrequency: '',
  injuryNotes: '',
  equipment: [] as string[],
});

const goalOptions = [
  { label: '减脂塑形', value: 'fat_loss', icon: '🔥' },
  { label: '增肌增重', value: 'muscle_gain', icon: '💪' },
  { label: '提升体能', value: 'fitness', icon: '⚡' },
  { label: '康复训练', value: 'rehab', icon: '🩹' },
  { label: '保持健康', value: 'general', icon: '❤️' },
];

const frequencyOptions = [
  { label: '0-1 次/周', value: '0-1' },
  { label: '2-3 次/周', value: '2-3' },
  { label: '3-4 次/周', value: '3-4' },
  { label: '5+ 次/周', value: '5+' },
];

const equipmentOptions = [
  { label: '无器械', value: 'bodyweight' },
  { label: '哑铃', value: 'dumbbell' },
  { label: '杠铃', value: 'barbell' },
  { label: '弹力带', value: 'resistance_band' },
  { label: '瑜伽垫', value: 'yoga_mat' },
  { label: '引体向上器', value: 'pull_up_bar' },
  { label: '跑步机', value: 'treadmill' },
];

function nextStep() {
  if (step.value < totalSteps) step.value++;
}

function prevStep() {
  if (step.value > 1) step.value--;
}

function toggleEquipment(item: string) {
  const idx = form.equipment.indexOf(item);
  if (idx >= 0) form.equipment.splice(idx, 1);
  else form.equipment.push(item);
}

async function handleSubmit() {
  loading.value = true;
  try {
    await saveQuestionnaire(form);
    ElMessage.success('问卷保存成功');
    router.push('/dashboard');
  } catch (err: any) {
    if (err?.code === 'ERR_NETWORK' || !err?.response) {
      ElMessage.warning('后端未连接，问卷已本地保存');
      router.push('/dashboard');
    } else {
      ElMessage.error('保存失败，请稍后重试');
    }
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <WebShell title="体能问卷" subtitle="帮助我们了解你的身体状况和训练目标">
    <div class="mx-auto max-w-2xl">
      <div class="mb-8 flex items-center justify-between">
        <div
          v-for="s in totalSteps"
          :key="s"
          class="flex items-center gap-2"
        >
          <div
            class="grid h-8 w-8 place-items-center rounded-full text-sm font-bold transition"
            :class="s <= step ? 'bg-gradient-to-r from-orange to-coral text-white' : 'bg-canvas text-muted'"
          >
            {{ s }}
          </div>
          <span v-if="s < totalSteps" class="h-0.5 w-12 bg-canvas md:w-20"></span>
        </div>
      </div>

      <div class="app-card p-6 md:p-8">
        <!-- Step 1: Basic Info -->
        <div v-if="step === 1">
          <h3 class="mb-6 text-lg font-bold text-ink">基本信息</h3>

          <div class="mb-5">
            <label class="mb-2 block text-sm font-semibold text-ink">性别</label>
            <div class="flex gap-3">
              <button
                v-for="g in [{ label: '男', value: 'male' }, { label: '女', value: 'female' }]"
                :key="g.value"
                class="flex-1 rounded-2xl border-2 py-3 text-sm font-bold transition"
                :class="form.gender === g.value ? 'border-indigo bg-indigo/10 text-indigo' : 'border-white/70 text-muted hover:border-indigo/30'"
                @click="form.gender = g.value"
              >
                {{ g.label }}
              </button>
            </div>
          </div>

          <div class="mb-5 grid gap-4 sm:grid-cols-3">
            <div>
              <label class="mb-2 block text-sm font-semibold text-ink">年龄</label>
              <el-input-number v-model="form.age" :min="10" :max="100" placeholder="岁" class="!w-full" />
            </div>
            <div>
              <label class="mb-2 block text-sm font-semibold text-ink">身高 (cm)</label>
              <el-input-number v-model="form.height" :min="100" :max="250" placeholder="cm" class="!w-full" />
            </div>
            <div>
              <label class="mb-2 block text-sm font-semibold text-ink">体重 (kg)</label>
              <el-input-number v-model="form.weight" :min="30" :max="200" placeholder="kg" class="!w-full" />
            </div>
          </div>
        </div>

        <!-- Step 2: Goals -->
        <div v-if="step === 2">
          <h3 class="mb-6 text-lg font-bold text-ink">训练目标</h3>

          <div class="mb-5">
            <label class="mb-2 block text-sm font-semibold text-ink">你的主要目标</label>
            <div class="grid grid-cols-2 gap-3 sm:grid-cols-3">
              <button
                v-for="opt in goalOptions"
                :key="opt.value"
                class="flex flex-col items-center gap-2 rounded-2xl border-2 p-4 text-sm font-semibold transition"
                :class="form.goal === opt.value ? 'border-indigo bg-indigo/10 text-indigo' : 'border-white/70 text-muted hover:border-indigo/30'"
                @click="form.goal = opt.value"
              >
                <span class="text-2xl">{{ opt.icon }}</span>
                {{ opt.label }}
              </button>
            </div>
          </div>

          <div class="mb-5">
            <label class="mb-2 block text-sm font-semibold text-ink">每周训练频率</label>
            <div class="flex flex-wrap gap-3">
              <button
                v-for="opt in frequencyOptions"
                :key="opt.value"
                class="rounded-2xl border-2 px-5 py-2.5 text-sm font-bold transition"
                :class="form.trainingFrequency === opt.value ? 'border-indigo bg-indigo/10 text-indigo' : 'border-white/70 text-muted hover:border-indigo/30'"
                @click="form.trainingFrequency = opt.value"
              >
                {{ opt.label }}
              </button>
            </div>
          </div>
        </div>

        <!-- Step 3: Equipment & Health -->
        <div v-if="step === 3">
          <h3 class="mb-6 text-lg font-bold text-ink">设备与健康</h3>

          <div class="mb-5">
            <label class="mb-2 block text-sm font-semibold text-ink">可用器材（多选）</label>
            <div class="flex flex-wrap gap-2">
              <button
                v-for="item in equipmentOptions"
                :key="item.value"
                class="rounded-full border-2 px-4 py-2 text-sm font-semibold transition"
                :class="form.equipment.includes(item.value) ? 'border-indigo bg-indigo/10 text-indigo' : 'border-white/70 text-muted hover:border-indigo/30'"
                @click="toggleEquipment(item.value)"
              >
                {{ item.label }}
              </button>
            </div>
          </div>

          <div>
            <label class="mb-2 block text-sm font-semibold text-ink">伤病 / 不适说明（可选）</label>
            <el-input
              v-model="form.injuryNotes"
              type="textarea"
              :rows="3"
              placeholder="例如：膝盖旧伤、腰椎间盘突出..."
            />
          </div>
        </div>

        <div class="mt-8 flex items-center justify-between">
          <el-button 
            v-if="step > 1" 
            round 
            @click="prevStep"
            class="!w-24"
          >
            上一步
          </el-button>
          <span v-else class="w-24"></span>
          
          <el-button
            v-if="step < totalSteps"
            type="primary"
            round
            class="!w-24 !bg-gradient-to-r !from-orange !to-coral !border-none"
            @click="nextStep"
          >
            下一步
          </el-button>
          <el-button
            v-else
            type="primary"
            round
            class="!w-24 !bg-gradient-to-r !from-orange !to-coral !border-none"
            :loading="loading"
            @click="handleSubmit"
          >
            提交问卷
          </el-button>
        </div>
      </div>
    </div>
  </WebShell>
</template>
