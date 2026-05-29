<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue';
import WebShell from '@/components/WebShell.vue';
import { 
  getMovements, 
  getMovementCategories, 
  type Movement, 
  type MovementCategories 
} from '@/api/movement';

const movements = ref<Movement[]>([]);
const categoriesData = ref<MovementCategories>({ muscle_groups: [], categories: [], equipment: [] });
const loading = ref(false);
const searchQuery = ref('');
const selectedCategory = ref('');
const selectedMuscle = ref('');
const selectedDifficulty = ref('');
const selectedEquipment = ref('');

// Debounced search
let searchTimeout: ReturnType<typeof setTimeout> | null = null;

const fallbackMovements: Movement[] = [
  {
    id: 'squat',
    name: '深蹲',
    name_en: 'Squat',
    category: '下肢',
    muscle_group: '股四头肌,臀大肌',
    equipment: '无器械',
    difficulty: '初级',
    description: '双脚与肩同宽站立，屈髋屈膝下蹲至大腿平行地面，然后站起。',
    key_points: ['膝盖与脚尖方向一致', '背部保持挺直', '重心在脚掌中部'],
    common_mistakes: ['膝盖内扣', '弓背', '脚跟离地'],
  },
  {
    id: 'push-up',
    name: '俯卧撑',
    name_en: 'Push-up',
    category: '上肢',
    muscle_group: '胸大肌,肱三头肌',
    equipment: '无器械',
    difficulty: '初级',
    description: '双手撑地，身体保持一条直线，屈肘下降至胸部接近地面，然后推起。',
    key_points: ['身体保持一条直线', '手肘角度约 45°', '核心收紧'],
    common_mistakes: ['塌腰', '手肘过度外展', '头部前伸'],
  },
  {
    id: 'plank',
    name: '平板支撑',
    name_en: 'Plank',
    category: '核心',
    muscle_group: '腹直肌,腹横肌',
    equipment: '无器械',
    difficulty: '初级',
    description: '前臂撑地，身体保持一条直线，核心收紧维持姿势。',
    key_points: ['身体成一条直线', '不塌腰不翘臀', '均匀呼吸'],
    common_mistakes: ['臀部过高', '塌腰', '憋气'],
  },
  {
    id: 'lunge',
    name: '弓步蹲',
    name_en: 'Lunge',
    category: '下肢',
    muscle_group: '股四头肌,臀大肌',
    equipment: '无器械',
    difficulty: '中级',
    description: '一脚向前迈出一大步，双膝弯曲下蹲，然后蹬回起始位置。',
    key_points: ['前膝不超过脚尖', '后膝接近地面', '躯干保持直立'],
    common_mistakes: ['前膝内扣', '身体前倾过多', '步幅太小'],
  },
  {
    id: 'deadlift',
    name: '硬拉',
    name_en: 'Deadlift',
    category: '全身',
    muscle_group: '竖脊肌,臀大肌,股二头肌',
    equipment: '杠铃',
    difficulty: '高级',
    description: '双脚与髋同宽站立，屈髋握住杠铃，保持背部挺直站起。',
    key_points: ['背部全程挺直', '杠铃贴近身体', '髋关节主导'],
    common_mistakes: ['弓背', '杠铃离身体太远', '用腰部发力'],
  },
];

const categories = computed(() => {
  const cats = categoriesData.value.categories.length > 0 
    ? categoriesData.value.categories 
    : [...new Set(movements.value.map((m) => m.category).filter(Boolean))];
  return ['全部', ...cats];
});

const muscles = computed(() => {
  const groups = categoriesData.value.muscle_groups.length > 0
    ? categoriesData.value.muscle_groups
    : [...new Set(movements.value
        .flatMap((m) => (m.muscle_group || '').split(',').map((s) => s.trim()))
        .filter(Boolean))];
  return ['全部', ...groups];
});

const difficulties = computed(() => ['全部', '初级', '中级', '高级']);

const equipments = computed(() => {
  const eqs = categoriesData.value.equipment.length > 0
    ? categoriesData.value.equipment
    : [...new Set(movements.value.map((m) => m.equipment).filter(Boolean))];
  return ['全部', ...eqs];
});

const activeFiltersCount = computed(() => {
  let count = 0;
  if (searchQuery.value) count++;
  if (selectedCategory.value && selectedCategory.value !== '全部') count++;
  if (selectedMuscle.value && selectedMuscle.value !== '全部') count++;
  if (selectedDifficulty.value && selectedDifficulty.value !== '全部') count++;
  if (selectedEquipment.value && selectedEquipment.value !== '全部') count++;
  return count;
});

function clearFilters() {
  searchQuery.value = '';
  selectedCategory.value = '';
  selectedMuscle.value = '';
  selectedDifficulty.value = '';
  selectedEquipment.value = '';
}

async function loadMovements() {
  loading.value = true;
  try {
    const filters: Record<string, string> = {};
    if (searchQuery.value) filters.search = searchQuery.value;
    if (selectedCategory.value && selectedCategory.value !== '全部') filters.category = selectedCategory.value;
    if (selectedMuscle.value && selectedMuscle.value !== '全部') filters.muscle_group = selectedMuscle.value;
    if (selectedDifficulty.value && selectedDifficulty.value !== '全部') filters.difficulty = selectedDifficulty.value;
    if (selectedEquipment.value && selectedEquipment.value !== '全部') filters.equipment = selectedEquipment.value;
    
    const { data } = await getMovements(Object.keys(filters).length > 0 ? filters : undefined);
    movements.value = data.length > 0 ? data : fallbackMovements;
  } catch (error: any) {
    console.error('Failed to load movements:', error);
    if (movements.value.length === 0) {
      movements.value = fallbackMovements;
    }
  } finally {
    loading.value = false;
  }
}

async function loadCategories() {
  try {
    const { data } = await getMovementCategories();
    categoriesData.value = data;
  } catch (error) {
    console.error('Failed to load categories:', error);
  }
}

// Debounced search
watch(searchQuery, () => {
  if (searchTimeout) clearTimeout(searchTimeout);
  searchTimeout = setTimeout(() => {
    loadMovements();
  }, 300);
});

// Immediate filter changes
watch([selectedCategory, selectedMuscle, selectedDifficulty, selectedEquipment], () => {
  loadMovements();
});

const detailVisible = ref(false);
const detailMovement = ref<Movement | null>(null);

function showDetail(m: Movement) {
  detailMovement.value = m;
  detailVisible.value = true;
}

function startTraining(movement: Movement) {
  // Navigate to workout with pre-selected movement
  localStorage.setItem('selected_movement', movement.id);
  window.location.href = '/workout';
}

onMounted(() => {
  loadCategories();
  loadMovements();
});
</script>

<template>
  <WebShell title="动作库" subtitle="所有训练动作的标准示范与要点">
    <!-- Search and Filters -->
    <div class="mb-6 space-y-4">
      <div class="flex flex-col gap-4 sm:flex-row sm:items-center">
        <el-input
          v-model="searchQuery"
          placeholder="搜索动作名称..."
          class="sm:max-w-xs"
          clearable
          :prefix-icon="'Search'"
        />
        <div class="flex flex-wrap gap-2">
          <el-select v-model="selectedCategory" placeholder="分类" clearable class="!w-28">
            <el-option v-for="c in categories" :key="c" :label="c" :value="c" />
          </el-select>
          <el-select v-model="selectedMuscle" placeholder="肌群" clearable class="!w-28">
            <el-option v-for="m in muscles" :key="m" :label="m" :value="m" />
          </el-select>
          <el-select v-model="selectedDifficulty" placeholder="难度" clearable class="!w-28">
            <el-option v-for="d in difficulties" :key="d" :label="d" :value="d" />
          </el-select>
          <el-select v-model="selectedEquipment" placeholder="器材" clearable class="!w-28">
            <el-option v-for="e in equipments" :key="e" :label="e" :value="e" />
          </el-select>
        </div>
        <el-button 
          v-if="activeFiltersCount > 0"
          text
          size="small"
          @click="clearFilters"
          class="!text-muted"
        >
          清除筛选 ({{ activeFiltersCount }})
        </el-button>
      </div>
      
      <!-- Results count -->
      <div v-if="!loading" class="text-sm text-muted">
        共 {{ movements.length }} 个动作
        <span v-if="activeFiltersCount > 0">（筛选后 {{ movements.length }} 个）</span>
      </div>
    </div>

    <div v-if="loading" class="py-20 text-center text-muted">加载中...</div>

    <div v-else class="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
      <div
        v-for="m in movements"
        :key="m.id"
        class="app-card group cursor-pointer p-5 transition hover:shadow-lg"
        @click="showDetail(m)"
      >
        <div class="mb-3 flex items-center justify-between">
          <span class="rounded-full bg-indigo/10 px-3 py-1 text-xs font-bold text-indigo">
            {{ m.category || '未分类' }}
          </span>
          <span 
            class="rounded-full px-3 py-1 text-xs font-bold"
            :class="m.difficulty === '初级' ? 'bg-mint/10 text-mint' : m.difficulty === '中级' ? 'bg-amber/10 text-amber' : 'bg-coral/10 text-coral'"
          >
            {{ m.difficulty || '--' }}
          </span>
        </div>
        <h3 class="text-lg font-bold text-ink group-hover:text-indigo transition">{{ m.name }}</h3>
        <p v-if="m.name_en" class="text-sm text-muted">{{ m.name_en }}</p>
        <div class="mt-3 flex flex-wrap gap-1.5">
          <span
            v-for="muscle in (m.muscle_group || '').split(',').filter(Boolean).slice(0, 3)"
            :key="muscle"
            class="rounded-full bg-orange/10 px-2.5 py-0.5 text-xs font-semibold text-orange"
          >
            {{ muscle.trim() }}
          </span>
          <span v-if="(m.muscle_group || '').split(',').filter(Boolean).length > 3" class="text-xs text-muted">
            +{{ (m.muscle_group || '').split(',').filter(Boolean).length - 3 }}
          </span>
        </div>
        <p class="mt-3 line-clamp-2 text-sm text-muted">{{ m.description }}</p>
        <div class="mt-4 flex items-center justify-between">
          <span class="text-xs text-muted">器材: {{ m.equipment || '无' }}</span>
          <el-button 
            size="small" 
            text
            class="!text-indigo !opacity-0 group-hover:!opacity-100 transition"
            @click.stop="startTraining(m)"
          >
            开始训练 →
          </el-button>
        </div>
      </div>
    </div>

    <div v-if="!loading && movements.length === 0" class="py-20 text-center">
      <p class="text-4xl">🔍</p>
      <p class="mt-3 text-muted">没有找到匹配的动作</p>
      <el-button class="!mt-4" text @click="clearFilters">清除筛选条件</el-button>
    </div>

    <!-- Detail Dialog -->
    <el-dialog v-model="detailVisible" :title="detailMovement?.name" width="560px" class="!rounded-2xl">
      <div v-if="detailMovement" class="space-y-5">
        <!-- Header info -->
        <div class="flex flex-wrap gap-2">
          <span 
            v-if="detailMovement.category"
            class="rounded-full bg-indigo/10 px-3 py-1 text-xs font-bold text-indigo"
          >
            {{ detailMovement.category }}
          </span>
          <span 
            v-if="detailMovement.difficulty"
            class="rounded-full px-3 py-1 text-xs font-bold"
            :class="detailMovement.difficulty === '初级' ? 'bg-mint/10 text-mint' : detailMovement.difficulty === '中级' ? 'bg-amber/10 text-amber' : 'bg-coral/10 text-coral'"
          >
            {{ detailMovement.difficulty }}
          </span>
        </div>

        <div v-if="detailMovement.description">
          <h4 class="mb-2 text-sm font-bold text-ink">动作说明</h4>
          <p class="text-sm leading-relaxed text-muted">{{ detailMovement.description }}</p>
        </div>

        <div class="flex flex-wrap gap-3">
          <div v-if="detailMovement.muscle_group" class="rounded-xl bg-canvas px-3 py-2 text-xs font-semibold text-ink">
            肌群：{{ detailMovement.muscle_group }}
          </div>
          <div v-if="detailMovement.equipment" class="rounded-xl bg-canvas px-3 py-2 text-xs font-semibold text-ink">
            器材：{{ detailMovement.equipment }}
          </div>
        </div>

        <div v-if="detailMovement.key_points?.length">
          <h4 class="mb-2 text-sm font-bold text-mint">动作要点</h4>
          <ul class="space-y-1.5">
            <li v-for="(p, i) in detailMovement.key_points" :key="i" class="flex items-start gap-2 text-sm text-ink">
              <span class="mt-0.5 text-mint">✓</span>{{ p }}
            </li>
          </ul>
        </div>

        <div v-if="detailMovement.common_mistakes?.length">
          <h4 class="mb-2 text-sm font-bold text-coral">常见错误</h4>
          <ul class="space-y-1.5">
            <li v-for="(p, i) in detailMovement.common_mistakes" :key="i" class="flex items-start gap-2 text-sm text-ink">
              <span class="mt-0.5 text-coral">✗</span>{{ p }}
            </li>
          </ul>
        </div>

        <div v-if="detailMovement.instructions?.length">
          <h4 class="mb-2 text-sm font-bold text-ink">训练步骤</h4>
          <ol class="space-y-1.5">
            <li v-for="(p, i) in detailMovement.instructions" :key="i" class="flex items-start gap-2 text-sm text-ink">
              <span class="font-bold text-indigo">{{ i + 1 }}.</span>{{ p }}
            </li>
          </ol>
        </div>

        <div v-if="detailMovement.contraindications?.length">
          <h4 class="mb-2 text-sm font-bold text-amber">禁忌症</h4>
          <ul class="space-y-1.5">
            <li v-for="(p, i) in detailMovement.contraindications" :key="i" class="flex items-start gap-2 text-sm text-ink">
              <span class="mt-0.5 text-amber">⚠</span>{{ p }}
            </li>
          </ul>
        </div>

        <!-- Action button -->
        <div class="border-t border-black/5 pt-4">
          <el-button 
            type="primary" 
            round 
            class="w-full !bg-indigo !border-indigo"
            @click="startTraining(detailMovement); detailVisible = false"
          >
            开始训练
          </el-button>
        </div>
      </div>
    </el-dialog>
  </WebShell>
</template>
