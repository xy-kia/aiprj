import { createRouter, createWebHistory, type NavigationGuardNext } from 'vue-router'
import type { RouteLocationNormalized } from 'vue-router'

const requireAdmin = (to: RouteLocationNormalized, from: RouteLocationNormalized, next: NavigationGuardNext) => {
  const token = localStorage.getItem('admin-token')
  if (!token) {
    next('/admin/login')
    return
  }
  next()
}

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'home',
      component: () => import('@views/HomeView.vue')
    },
    {
      path: '/jobs',
      name: 'jobs',
      component: () => import('@views/JobsView.vue')
    },
    {
      path: '/practice',
      name: 'practice',
      component: () => import('@views/PracticeView.vue')
    },
    {
      path: '/evaluation',
      name: 'evaluation',
      component: () => import('@views/EvaluationView.vue')
    },
    {
      path: '/profile',
      name: 'profile',
      component: () => import('@views/ProfileView.vue')
    },
    // Admin routes
    {
      path: '/admin/login',
      name: 'admin-login',
      component: () => import('@views/admin/LoginView.vue'),
      meta: { hideNav: true }
    },
    {
      path: '/admin',
      redirect: '/admin/dashboard'
    },
    {
      path: '/admin/dashboard',
      name: 'admin-dashboard',
      component: () => import('@views/admin/DashboardView.vue'),
      beforeEnter: requireAdmin,
      meta: { hideNav: true }
    },
    {
      path: '/admin/crawler-monitor',
      name: 'admin-crawler-monitor',
      component: () => import('@views/admin/CrawlerMonitorView.vue'),
      beforeEnter: requireAdmin,
      meta: { hideNav: true }
    },
    {
      path: '/admin/knowledge-management',
      name: 'admin-knowledge-management',
      component: () => import('@views/admin/KnowledgeManagementView.vue'),
      beforeEnter: requireAdmin,
      meta: { hideNav: true }
    },
    {
      path: '/admin/evaluation-check',
      name: 'admin-evaluation-check',
      component: () => import('@views/admin/EvaluationCheckView.vue'),
      beforeEnter: requireAdmin,
      meta: { hideNav: true }
    },
    {
      path: '/admin/system-config',
      name: 'admin-system-config',
      component: () => import('@views/admin/SystemConfigView.vue'),
      beforeEnter: requireAdmin,
      meta: { hideNav: true }
    },
    {
      path: '/admin/user-management',
      name: 'admin-user-management',
      component: () => import('@views/admin/UserManagementView.vue'),
      beforeEnter: requireAdmin,
      meta: { hideNav: true }
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
  // 可以在这里添加权限检查、登录验证等
  next()
})

export default router
