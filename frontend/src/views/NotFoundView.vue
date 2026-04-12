<template>
  <div class="not-found">
    <div class="container">
      <div class="error-code">404</div>
      <h1>页面未找到</h1>
      <p class="error-message">抱歉，您访问的页面不存在或已被移除</p>
      <div class="actions">
        <el-button type="primary" @click="goHome">返回首页</el-button>
        <el-button @click="goBack">返回上一页</el-button>
      </div>
      <div class="suggestions">
        <h3>您可能想要访问：</h3>
        <div class="links">
          <router-link to="/">首页</router-link>
          <router-link to="/jobs">岗位搜索</router-link>
          <router-link to="/practice">面试练习</router-link>
          <router-link to="/evaluation">评估报告</router-link>
          <router-link to="/profile">个人中心</router-link>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'

const router = useRouter()

const goHome = () => {
  router.push('/')
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
  margin-bottom: 40px;
}

.suggestions h3 {
  margin-bottom: 20px;
  color: #333;
}

.links {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 15px;
}

.links a {
  color: #409eff;
  text-decoration: none;
  padding: 8px 16px;
  border: 1px solid #409eff;
  border-radius: 4px;
  transition: all 0.3s;
}

.links a:hover {
  background: #409eff;
  color: white;
}
</style>