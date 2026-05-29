<script setup lang="ts">
import { useRouter } from 'vue-router';
import BrandLogo from '@/components/BrandLogo.vue';

const router = useRouter();

const features = [
  { icon: '🎥', title: '实时姿态捕捉', desc: '摄像头驱动，毫秒级识别 33 个身体关键点' },
  { icon: '📐', title: '动作精度分析', desc: '计算关节角度、动作深度和躯干姿态，判断动作是否标准' },
  { icon: '🔢', title: '智能计数', desc: '自动识别深蹲阶段，精准记录每一次重复' },
  { icon: '⚠️', title: '即时纠错', desc: '发现膝内扣、浅蹲、前倾等问题时立刻提醒' },
  { icon: '📊', title: '训练报告', desc: '每次训练生成报告，追踪动作质量和进步轨迹' },
  { icon: '🎯', title: '个性化方案', desc: '根据体能问卷和训练记录生成专属训练计划' },
];
</script>

<template>
  <div class="landing-page">
    <header class="landing-header">
      <div class="landing-header-inner">
        <BrandLogo />
        <div class="landing-nav-actions">
          <el-button round @click="router.push('/login')">登录</el-button>
          <el-button type="primary" round class="landing-register-button" @click="router.push('/register')">
            免费注册
          </el-button>
        </div>
      </div>
    </header>

    <main>
      <section class="landing-hero">
        <div class="landing-hero-inner">
          <div class="landing-hero-copy">
            <p class="landing-eyebrow">AI Smart Fitness</p>
            <h1>智训赛博私教</h1>
            <p class="landing-lead">
              摄像头实时捕捉深蹲姿态，AI 分析膝角、躯干角度和动作节奏，帮你完成更安全、更标准的训练。
            </p>
            <div class="landing-hero-actions">
              <el-button size="large" round class="hero-primary-button" @click="router.push('/register')">
                开始训练
              </el-button>
              <el-button size="large" round plain class="hero-secondary-button" @click="router.push('/login')">
                已有账号，登录
              </el-button>
            </div>
          </div>

          <div class="camera-preview" aria-hidden="true">
            <div class="camera-topbar">
              <span class="camera-status"></span>
              <span>LIVE CAMERA</span>
              <strong>Squat</strong>
            </div>
            <div class="pose-stage">
              <span class="pose-joint joint-head"></span>
              <span class="pose-joint joint-shoulder"></span>
              <span class="pose-joint joint-hip"></span>
              <span class="pose-joint joint-knee-left"></span>
              <span class="pose-joint joint-knee-right"></span>
              <span class="pose-joint joint-foot-left"></span>
              <span class="pose-joint joint-foot-right"></span>
              <span class="pose-bone bone-neck"></span>
              <span class="pose-bone bone-spine"></span>
              <span class="pose-bone bone-thigh-left"></span>
              <span class="pose-bone bone-thigh-right"></span>
              <span class="pose-bone bone-shin-left"></span>
              <span class="pose-bone bone-shin-right"></span>
            </div>
            <div class="camera-metrics">
              <span>膝角 104°</span>
              <span>计数 08</span>
              <span>评分 92</span>
            </div>
          </div>
        </div>
      </section>

      <section class="landing-section">
        <div class="landing-section-heading">
          <h2>核心功能</h2>
          <p>结合计算机视觉与运动科学，为你的训练提供实时反馈。</p>
        </div>

        <div class="landing-feature-grid">
          <article v-for="feature in features" :key="feature.title" class="landing-feature-card">
            <span>{{ feature.icon }}</span>
            <h3>{{ feature.title }}</h3>
            <p>{{ feature.desc }}</p>
          </article>
        </div>
      </section>

      <section class="landing-cta">
        <div>
          <h2>准备好开始了吗？</h2>
          <p>注册即可体验 AI 私教，打开摄像头就能开始深蹲训练。</p>
        </div>
        <el-button size="large" round class="landing-cta-button" @click="router.push('/register')">
          立即注册
        </el-button>
      </section>
    </main>

    <footer class="landing-footer">
      <p>© 2026 智训 AI Smart Fitness · 训练更聪明</p>
    </footer>
  </div>
</template>
