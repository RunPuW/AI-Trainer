<script setup lang="ts">
import { reactive, ref } from 'vue';
import { useRouter, useRoute } from 'vue-router';
import { ElMessage } from 'element-plus';
import { login, getMe } from '@/api/auth';
import { useAuthStore } from '@/stores/auth';

const router = useRouter();
const route = useRoute();
const authStore = useAuthStore();

const form = reactive({
  username: '',
  password: '',
});

const loading = ref(false);

const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
};

const formRef = ref();

async function handleLogin() {
  try {
    await formRef.value?.validate();
  } catch {
    return;
  }

  loading.value = true;
  try {
    const { data } = await login({ username: form.username, password: form.password });
    authStore.setSession(data.access_token);

    try {
      const { data: user } = await getMe();
      authStore.updateUser({ id: user.id, username: user.username, email: user.email, avatar_url: user.avatar_url });
    } catch {
      authStore.updateUser({ id: '1', username: form.username });
    }

    ElMessage.success('登录成功');
    const redirect = (route.query.redirect as string) || '/dashboard';
    router.push(redirect);
  } catch (err: any) {
    if (err?.code === 'ERR_NETWORK' || !err?.response) {
      authStore.setSession('demo-token');
      authStore.updateUser({ id: 'demo', username: form.username || '体验用户' });
      ElMessage.warning('后端未连接，已进入体验模式');
      router.push('/dashboard');
    } else {
      ElMessage.error(err?.response?.data?.detail || '登录失败，请检查用户名和密码');
    }
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <div class="gradient-stage flex min-h-screen items-center justify-center px-5">
    <div class="glass-card w-full max-w-[420px] rounded-[28px] p-8 md:p-10">
      <div class="mb-8 text-center">
        <div class="mx-auto mb-4 grid h-14 w-14 place-items-center rounded-2xl bg-gradient-to-br from-orange to-coral text-2xl font-black text-white shadow-lg shadow-orange/25">
          智
        </div>
        <h1 class="text-2xl font-black text-ink">欢迎回来</h1>
        <p class="mt-1 text-sm text-muted">登录你的智训账号</p>
      </div>

      <el-form 
        ref="formRef" 
        :model="form" 
        :rules="rules" 
        label-position="top" 
        size="large"
        class="login-form"
      >
        <el-form-item label="用户名" prop="username" class="form-item">
          <el-input v-model="form.username" placeholder="请输入用户名" prefix-icon="User" class="form-input" />
        </el-form-item>

        <el-form-item label="密码" prop="password" class="form-item">
          <el-input v-model="form.password" type="password" placeholder="请输入密码" prefix-icon="Lock" show-password class="form-input" />
        </el-form-item>

        <el-form-item class="form-item-button">
          <el-button
            class="brand-button w-full !rounded-xl !py-5 !text-base !font-bold"
            :loading="loading"
            @click="handleLogin"
          >
            登录
          </el-button>
        </el-form-item>
      </el-form>

      <p class="mt-6 text-center text-sm text-muted">
        还没有账号？
        <RouterLink to="/register" class="font-semibold text-indigo hover:underline">立即注册</RouterLink>
      </p>
    </div>
  </div>
</template>

<style scoped>
.login-form :deep(.el-form-item) {
  margin-bottom: 16px;
}

.login-form :deep(.el-form-item__label) {
  padding-bottom: 4px;
  line-height: 1.5;
}

.login-form :deep(.el-input__wrapper) {
  border-radius: 12px;
  padding: 0 15px;
  height: 48px;
}

.login-form :deep(.el-input__inner) {
  height: 48px;
}

.form-item-button {
  margin-top: 8px;
  margin-bottom: 0 !important;
}

.form-item-button :deep(.el-form-item__content) {
  margin-left: 0 !important;
  width: 100%;
}
</style>
