<template>
  <div id="app">
    <nav v-if="!isAdminRoute" class="navbar">
      <div class="nav-brand">
        <router-link to="/" class="brand-link">学生求职AI助手</router-link>
      </div>
      <div class="nav-links">
        <router-link to="/" class="nav-link" exact-active-class="active">首页</router-link>
        <router-link to="/jobs" class="nav-link" active-class="active">岗位搜索</router-link>
        <router-link to="/practice" class="nav-link" active-class="active">面试练习</router-link>
        <router-link to="/evaluation" class="nav-link" active-class="active">面试评估</router-link>
        <router-link to="/profile" class="nav-link" active-class="active">个人中心</router-link>
      </div>
    </nav>
    <router-view />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const isAdminRoute = computed(() => route.path.startsWith('/admin'))
</script>

<style>
#app {
  font-family: Avenir, Helvetica, Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  color: #2c3e50;
  min-height: 100vh;
  background-color: #f5f7fa;
}

.navbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 40px;
  height: 60px;
  background-color: #fff;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  position: sticky;
  top: 0;
  z-index: 100;
}

.nav-brand {
  font-size: 20px;
  font-weight: bold;
}

.brand-link {
  color: #409eff;
  text-decoration: none;
}

.nav-links {
  display: flex;
  gap: 30px;
}

.nav-link {
  color: #606266;
  text-decoration: none;
  font-size: 15px;
  padding: 8px 12px;
  border-radius: 4px;
  transition: all 0.3s;
}

.nav-link:hover {
  color: #409eff;
  background-color: #ecf5ff;
}

.nav-link.active {
  color: #409eff;
  background-color: #ecf5ff;
  font-weight: 500;
}
</style>
