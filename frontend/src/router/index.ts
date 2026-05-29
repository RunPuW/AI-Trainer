import { createRouter, createWebHistory } from 'vue-router';

const router = createRouter({
  history: createWebHistory(),
  scrollBehavior: () => ({ top: 0 }),
  routes: [
    {
      path: '/',
      name: 'landing',
      component: () => import('@/views/Landing.vue'),
    },
    {
      path: '/login',
      name: 'login',
      component: () => import('@/views/Login.vue'),
    },
    {
      path: '/register',
      name: 'register',
      component: () => import('@/views/Register.vue'),
    },
    {
      path: '/dashboard',
      name: 'dashboard',
      component: () => import('@/views/Dashboard.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/questionnaire',
      name: 'questionnaire',
      component: () => import('@/views/Questionnaire.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/movements',
      name: 'movements',
      component: () => import('@/views/MovementLibrary.vue'),
    },
    {
      path: '/workout',
      name: 'workout',
      component: () => import('@/views/WorkoutSession.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/plan',
      name: 'plan',
      component: () => import('@/views/TrainingPlan.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/assistant',
      name: 'assistant',
      component: () => import('@/views/AIAssistant.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/reports',
      name: 'reports',
      component: () => import('@/views/Reports.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/settings',
      name: 'settings',
      component: () => import('@/views/Settings.vue'),
      meta: { requiresAuth: true },
    },
  ],
});

router.beforeEach((to, _from, next) => {
  const token = localStorage.getItem('token');
  if (to.meta.requiresAuth && !token) {
    next({ path: '/login', query: { redirect: to.fullPath } });
  } else {
    next();
  }
});

export default router;
