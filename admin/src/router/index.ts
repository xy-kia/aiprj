import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: () => import('@views/LoginView.vue')
    },
    {
      path: '/',
      redirect: '/dashboard',
      meta: { requiresAuth: true }
    },
    {
      path: '/dashboard',
      name: 'dashboard',
      component: () => import('@views/DashboardView.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/crawler-monitor',
      name: 'crawler-monitor',
      component: () => import('@views/CrawlerMonitorView.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/knowledge-management',
      name: 'knowledge-management',
      component: () => import('@views/KnowledgeManagementView.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/evaluation-check',
      name: 'evaluation-check',
      component: () => import('@views/EvaluationCheckView.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/system-config',
      name: 'system-config',
      component: () => import('@views/SystemConfigView.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/user-management',
      name: 'user-management',
      component: () => import('@views/UserManagementView.vue'),
      meta: { requiresAuth: true }
    },
    // 404页面
    {
      path: '/:pathMatch(.*)*',
      name: 'not-found',
      component: () => import('@views/NotFoundView.vue')
    }
  ]
})

// 导航守卫
router.beforeEach((to, from, next) => {
  // 检查是否需要认证
  if (to.meta.requiresAuth) {
    const token = localStorage.getItem('admin-token')
    if (!token) {
      next('/login')
      return
    }
  }
  next()
})

export default router