import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useUserStore = defineStore('user', () => {
  // 用户信息
  const userInfo = ref({
    id: null as number | null,
    username: '',
    email: '',
    fullName: '',
    isAdmin: false
  })

  // 登录状态
  const isLoggedIn = computed(() => !!userInfo.value.id)

  // 登录
  const login = async (username: string, password: string) => {
    // 这里应该调用登录API
    // 模拟登录
    userInfo.value = {
      id: 1,
      username,
      email: `${username}@example.com`,
      fullName: '测试用户',
      isAdmin: false
    }

    // 保存token到localStorage
    localStorage.setItem('token', 'mock-jwt-token')
    localStorage.setItem('user', JSON.stringify(userInfo.value))
  }

  // 登出
  const logout = () => {
    userInfo.value = {
      id: null,
      username: '',
      email: '',
      fullName: '',
      isAdmin: false
    }
    localStorage.removeItem('token')
    localStorage.removeItem('user')
  }

  // 从localStorage恢复用户信息
  const restoreUser = () => {
    const storedUser = localStorage.getItem('user')
    if (storedUser) {
      userInfo.value = JSON.parse(storedUser)
    }
  }

  // 更新用户信息
  const updateUserInfo = (info: Partial<typeof userInfo.value>) => {
    userInfo.value = { ...userInfo.value, ...info }
    localStorage.setItem('user', JSON.stringify(userInfo.value))
  }

  return {
    userInfo,
    isLoggedIn,
    login,
    logout,
    restoreUser,
    updateUserInfo
  }
})