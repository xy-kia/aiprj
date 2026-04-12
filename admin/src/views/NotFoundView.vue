<template>
  <div class="not-found">
    <div class="container">
      <div class="error-code">404</div>
      <h1>页面未找到</h1>
      <p class="error-message">抱歉，您访问的管理后台页面不存在</p>
      <div class="actions">
        <el-button type="primary" @click="goDashboard">返回仪表盘</el-button>
        <el-button @click="goBack">返回上一页</el-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'

const router = useRouter()

const goDashboard = () => {
  router.push('/dashboard')
}

const goBack = () => {
  router.back()
}
</script>

<style scoped>
.not-found {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 70vh;
  padding: 20px;
}

.container {
  text-align: center;
  max-width: 600px;
  padding: 40px;
  background: white;
  border-radius: 12px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
}

.error-code {
  font-size: 120px;
  font-weight: bold;
  color: #409eff;
  line-height: 1;
  margin-bottom: 20px;
}

h1 {
  font-size: 32px;
  margin-bottom: 16px;
  color: #333;
}

.error-message {
  font-size: 18px;
  color: #666;
  margin-bottom: 30px;
}

.actions {
  display: flex;
  justify-content: center;
  gap: 20px;
}
</style>