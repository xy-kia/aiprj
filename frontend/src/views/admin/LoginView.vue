<template>
  <div class="login">
    <div class="login-container">
      <div class="login-header">
        <h1>学生求职AI助手</h1>
        <p>管理后台登录</p>
      </div>

      <el-card class="login-card">
        <el-form
          ref="loginFormRef"
          :model="loginForm"
          :rules="loginRules"
          label-width="80px"
          @submit.prevent="handleLogin"
        >
          <el-form-item label="用户名" prop="username">
            <el-input
              v-model="loginForm.username"
              placeholder="请输入管理员用户名"
              prefix-icon="User"
              size="large"
            />
          </el-form-item>

          <el-form-item label="密码" prop="password">
            <el-input
              v-model="loginForm.password"
              type="password"
              placeholder="请输入密码"
              prefix-icon="Lock"
              size="large"
              show-password
            />
          </el-form-item>

          <el-form-item label="验证码" prop="captcha">
            <div class="captcha-input">
              <el-input
                v-model="loginForm.captcha"
                placeholder="请输入验证码"
                prefix-icon="Key"
                size="large"
                style="flex: 1"
              />
              <div class="captcha-image" @click="refreshCaptcha">
                <img :src="captchaImage" alt="验证码" v-if="captchaImage" />
                <div v-else class="captcha-placeholder">点击刷新</div>
              </div>
            </div>
          </el-form-item>

          <el-form-item>
            <el-button
              type="primary"
              size="large"
              :loading="loading"
              @click="handleLogin"
              style="width: 100%"
            >
              登录
            </el-button>
          </el-form-item>
        </el-form>

        <div class="login-footer">
          <p>提示：仅限管理员登录</p>
          <p>忘记密码？请联系系统管理员</p>
        </div>
      </el-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import type { FormInstance, FormRules } from 'element-plus'

const router = useRouter()

const loginFormRef = ref<FormInstance>()
const loading = ref(false)
const captchaImage = ref('')

const loginForm = reactive({
  username: '',
  password: '',
  captcha: ''
})

const loginRules: FormRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码长度至少6位', trigger: 'blur' }
  ],
  captcha: [
    { required: true, message: '请输入验证码', trigger: 'blur' },
    { len: 4, message: '验证码长度为4位', trigger: 'blur' }
  ]
}

const refreshCaptcha = () => {
  // 这里应该调用API获取验证码图片
  // 模拟验证码
  captchaImage.value = 'data:image/svg+xml;base64,' + btoa('<svg width="120" height="40" xmlns="http://www.w3.org/2000/svg"><rect width="120" height="40" fill="#f0f2f5"/><text x="60" y="25" font-family="Arial" font-size="20" text-anchor="middle" fill="#333">1234</text></svg>')
}

const handleLogin = async () => {
  if (!loginFormRef.value) return

  const valid = await loginFormRef.value.validate()
  if (!valid) return

  loading.value = true

  try {
    // 这里应该调用登录API
    // 模拟登录成功
    await new Promise(resolve => setTimeout(resolve, 1000))

    // 保存token
    localStorage.setItem('admin-token', 'mock-admin-jwt-token')
    localStorage.setItem('admin-user', JSON.stringify({
      username: loginForm.username,
      role: 'admin',
      permissions: ['all']
    }))

    ElMessage.success('登录成功')
    router.push('/dashboard')
  } catch (error) {
    ElMessage.error('登录失败，请检查用户名和密码')
  } finally {
    loading.value = false
  }
}

// 初始化时获取验证码
refreshCaptcha()
</script>

<style scoped>
.login {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.login-container {
  width: 100%;
  max-width: 420px;
  padding: 20px;
}

.login-header {
  text-align: center;
  margin-bottom: 30px;
  color: white;
}

.login-header h1 {
  font-size: 32px;
  margin-bottom: 10px;
}

.login-header p {
  font-size: 16px;
  opacity: 0.9;
}

.login-card {
  border-radius: 12px;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2);
}

.captcha-input {
  display: flex;
  gap: 10px;
  align-items: center;
}

.captcha-image {
  width: 120px;
  height: 40px;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  background: #f5f7fa;
}

.captcha-image img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.captcha-placeholder {
  color: #909399;
  font-size: 14px;
}

.login-footer {
  margin-top: 20px;
  text-align: center;
  color: #909399;
  font-size: 12px;
}

.login-footer p {
  margin: 5px 0;
}
</style>