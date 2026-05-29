<script setup lang="ts">
import { reactive, ref } from 'vue';
import { useRouter } from 'vue-router';
import { ElMessage } from 'element-plus';
import { register, login, getMe } from '@/api/auth';
import { useAuthStore } from '@/stores/auth';

const router = useRouter();
const authStore = useAuthStore();

const form = reactive({
  username: '',
  email: '',
  password: '',
  confirmPassword: '',
});

const loading = ref(false);
const formRef = ref();

const rules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 2, max: 20, message: '用户名长度 2-20 个字符', trigger: 'blur' },
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码至少 6 个字符', trigger: 'blur' },
  ],
  confirmPassword: [
    { required: true, message: '请确认密码', trigger: 'blur' },
    {
      validator: (_rule: any, value: string, callback: Function) => {
        if (value !== form.password) {
          callback(new Error('两次输入的密码不一致'));
        } else {
          callback();
        }
      },
      trigger: 'blur',
    },
  ],
};

async function handleRegister() {
  try {
    await formRef.value?.validate();
  } catch {
    return;
  }

  loading.value = true;
  try {
    await register({
      username: form.username,
      password: form.password,
      email: form.email || undefined,
    });

    // Backend register doesn't return token, so login after register
    const { data } = await login({ username: form.username, password: form.password });
    authStore.setSession(data.access_token);

    try {
      const { data: user } = await getMe();
      authStore.updateUser({ id: user.id, username: user.username, email: user.email, avatar_url: user.avatar_url });
    } catch {
      authStore.updateUser({ id: '1', username: form.username });
    }

    ElMessage.success('注册成功');
    router.push('/questionnaire');
  } catch (err: any) {
    if (err?.code === 'ERR_NETWORK' || !err?.response) {
      authStore.setSession('demo-token');
      authStore.updateUser({ id: 'demo', username: form.username || '体验用户' });
      ElMessage.warning('后端未连接，已进入体验模式');
      router.push('/questionnaire');
    } else {
      ElMessage.error(err?.response?.data?.detail || '注册失败，请稍后重试');
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
        <h1 class="text-2xl font-black text-ink">创建账号</h1>
        <p class="mt-1 text-sm text-muted">开启你的 AI 训练之旅</p>
      </div>

      <el-form 
        ref="formRef" 
        :model="form" 
        :rules="rules" 
        label-position="top" 
        size="large"
        class="register-form"
      >
        <el-form-item label="用户名" prop="username" class="form-item">
          <el-input v-model="form.username" placeholder="请输入用户名" class="form-input" />
        </el-form-item>

        <el-form-item label="邮箱（可选）" prop="email" class="form-item">
          <el-input v-model="form.email" placeholder="请输入邮箱" class="form-input" />
        </el-form-item>

        <el-form-item label="密码" prop="password" class="form-item">
          <el-input v-model="form.password" type="password" placeholder="至少 6 个字符" show-password class="form-input" />
        </el-form-item>

        <el-form-item label="确认密码" prop="confirmPassword" class="form-item">
          <el-input v-model="form.confirmPassword" type="password" placeholder="再次输入密码" show-password class="form-input" />
        </el-form-item>

        <el-form-item class="form-item-button">
          <el-button
            class="brand-button w-full !rounded-xl !py-5 !text-base !font-bold"
            :loading="loading"
            @click="handleRegister"
          >
            注册
          </el-button>
        </el-form-item>
      </el-form>

      <p class="mt-6 text-center text-sm text-muted">
        已有账号？
        <RouterLink to="/login" class="font-semibold text-indigo hover:underline">立即登录</RouterLink>
      </p>
    </div>
  </div>
</template>

<style scoped>
.register-form :deep(.el-form-item) {
  margin-bottom: 16px;
}

.register-form :deep(.el-form-item__label) {
  padding-bottom: 4px;
  line-height: 1.5;
}

.register-form :deep(.el-input__wrapper) {
  border-radius: 12px;
  padding: 0 15px;
  height: 48px;
}

.register-form :deep(.el-input__inner) {
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
