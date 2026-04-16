<template>
  <div class="knowledge-management">
    <div class="header">
      <h1>知识库管理</h1>
      <p>岗位模板、技能库、问题库的增删改查（CRUD）</p>
    </div>

    <div class="tabs">
      <el-tabs v-model="activeTab">
        <el-tab-pane label="岗位模板" name="jobs">
          <JobTemplate />
        </el-tab-pane>
        <el-tab-pane label="技能库" name="skills">
          <SkillLibrary />
        </el-tab-pane>
        <el-tab-pane label="问题库" name="questions">
          <QuestionLibrary />
        </el-tab-pane>
      </el-tabs>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import JobTemplate from './knowledge/JobTemplate.vue'
import SkillLibrary from './knowledge/SkillLibrary.vue'
import QuestionLibrary from './knowledge/QuestionLibrary.vue'

const activeTab = ref('jobs')
</script>

<style scoped>
.knowledge-management {
  padding: 20px;
}

.header {
  margin-bottom: 30px;
}

.header h1 {
  color: #409eff;
  margin-bottom: 10px;
}

.header p {
  color: #666;
}
</style>