import { createRouter, createWebHistory } from 'vue-router'

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