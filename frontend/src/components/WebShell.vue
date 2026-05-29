<script setup lang="ts">
import { computed, markRaw } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import {
  Aim,
  ChatDotRound,
  Collection,
  House,
  Setting,
  SwitchButton,
  VideoCamera,
} from '@element-plus/icons-vue';
import BrandLogo from './BrandLogo.vue';
import { useAuthStore } from '@/stores/auth';

defineProps<{
  title: string;
  subtitle?: string;
}>();

const route = useRoute();
const router = useRouter();
const authStore = useAuthStore();

const navItems = [
  { label: '首页', path: '/dashboard', icon: markRaw(House), primary: false },
  { label: '训练计划', path: '/plan', icon: markRaw(Aim), primary: false },
  { label: '动作库', path: '/movements', icon: markRaw(Collection), primary: false },
  { label: 'AI 助手', path: '/assistant', icon: markRaw(ChatDotRound), primary: false },
  { label: '开始训练', path: '/workout', icon: markRaw(VideoCamera), primary: true },
];

const footerItems = [
  { label: '设置', path: '/settings', icon: markRaw(Setting), primary: false },
];

const userName = computed(() => authStore.user?.username || '训练者');

function isActive(path: string) {
  return path.includes('#') ? route.fullPath === path : route.path === path;
}

function handleLogout() {
  authStore.logout();
  router.push('/login');
}
</script>

<template>
  <div class="min-h-screen bg-canvas">
    <aside
      class="fixed inset-y-0 left-0 z-30 hidden w-[264px] flex-col border-r border-white/70 bg-white/90 px-5 py-6 shadow-soft backdrop-blur-xl lg:flex"
    >
      <BrandLogo />

      <nav class="mt-10 flex flex-1 flex-col gap-2">
        <RouterLink
          v-for="item in navItems"
          :key="item.path"
          :class="[
            'flex items-center gap-3 rounded-2xl px-4 py-3 text-sm font-semibold transition',
            isActive(item.path)
              ? 'bg-gradient-to-r from-orange to-coral text-white shadow-lg shadow-orange/20'
              : item.primary
                ? 'border border-orange/30 bg-orange/10 text-orange hover:bg-orange/20'
                : 'text-ink hover:bg-indigo/10 hover:text-indigo',
          ]"
          :to="item.path"
        >
          <el-icon :size="20"><component :is="item.icon" /></el-icon>
          <span>{{ item.label }}</span>
        </RouterLink>
        
        <div class="my-2 h-px bg-black/5" />
        
        <RouterLink
          v-for="item in footerItems"
          :key="item.path"
          :class="[
            'flex items-center gap-3 rounded-2xl px-4 py-3 text-sm font-semibold transition',
            isActive(item.path)
              ? 'bg-indigo text-white'
              : 'text-ink hover:bg-indigo/10 hover:text-indigo',
          ]"
          :to="item.path"
        >
          <el-icon :size="20"><component :is="item.icon" /></el-icon>
          <span>{{ item.label }}</span>
        </RouterLink>
      </nav>

      <button
        class="flex items-center gap-3 rounded-2xl px-4 py-3 text-left text-sm font-semibold text-muted transition hover:bg-canvas hover:text-coral"
        type="button"
        @click="handleLogout"
      >
        <el-icon :size="20"><SwitchButton /></el-icon>
        退出登录
      </button>
    </aside>

    <main class="min-h-screen lg:pl-[264px]">
      <header
        class="sticky top-0 z-20 border-b border-white/70 bg-canvas/80 px-5 py-4 backdrop-blur-xl md:px-8"
      >
        <div class="mx-auto flex max-w-[1440px] items-center justify-between gap-5">
          <div class="lg:hidden">
            <BrandLogo />
          </div>

          <div class="hidden lg:block">
            <h1 class="text-2xl font-black text-ink">{{ title }}</h1>
            <p v-if="subtitle" class="mt-1 text-sm text-muted">{{ subtitle }}</p>
          </div>

          <div class="ml-auto flex items-center gap-3">
            <el-button class="!hidden md:!inline-flex" round @click="router.push('/questionnaire')">
              修改个人偏好
            </el-button>
            <div class="flex items-center gap-3 rounded-2xl bg-white px-3 py-2 shadow-sm">
              <span
                class="grid h-9 w-9 place-items-center rounded-full bg-gradient-to-br from-indigo to-ocean text-sm font-black text-white"
              >
                {{ userName.slice(0, 1) }}
              </span>
              <span class="hidden text-sm font-semibold text-ink sm:inline">{{ userName }}</span>
            </div>
          </div>
        </div>
      </header>

      <section class="mx-auto max-w-[1440px] px-5 py-6 md:px-8 md:py-8">
        <div class="mb-5 lg:hidden">
          <h1 class="text-2xl font-black text-ink">{{ title }}</h1>
          <p v-if="subtitle" class="mt-1 text-sm text-muted">{{ subtitle }}</p>
        </div>
        <slot />
      </section>

      <nav
        class="fixed inset-x-4 bottom-4 z-40 grid grid-cols-5 rounded-[28px] bg-white/95 p-2 shadow-soft backdrop-blur-xl lg:hidden"
      >
        <RouterLink
          v-for="item in [...navItems, footerItems[0]].slice(0, 5)"
          :key="`mobile-${item.path}`"
          :class="[
            'flex flex-col items-center justify-center gap-1 rounded-2xl py-2 text-[10px] font-semibold',
            isActive(item.path)
              ? 'bg-orange text-white'
              : item.primary
                ? 'text-orange'
                : 'text-ink',
          ]"
          :to="item.path"
        >
          <el-icon :size="18"><component :is="item.icon" /></el-icon>
          <span>{{ item.label.slice(0, 4) }}</span>
        </RouterLink>
      </nav>
    </main>
  </div>
</template>
