<template>
  <div class="evaluation-check">
    <div class="header">
      <h1>评估抽检</h1>
      <p>随机抽样、人工复核、标注功能</p>
    </div>

    <div class="actions">
      <el-button type="primary" icon="Refresh" @click="refresh">刷新</el-button>
      <el-button icon="Download" @click="exportData">导出数据</el-button>
      <el-button icon="Setting" @click="openSettings">抽检设置</el-button>
    </div>

    <div class="filters">
      <el-form :inline="true" :model="filters">
        <el-form-item label="时间范围">
          <el-date-picker
            v-model="filters.dateRange"
            type="daterange"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
          />
        </el-form-item>
        <el-form-item label="分数范围">
          <el-input-number v-model="filters.minScore" :min="0" :max="100" placeholder="最低分" />
          <span class="separator">-</span>
          <el-input-number v-model="filters.maxScore" :min="0" :max="100" placeholder="最高分" />
        </el-form-item>
        <el-form-item label="岗位类型">
          <el-select v-model="filters.jobType" placeholder="请选择">
            <el-option label="全部" value="" />
            <el-option label="实习" value="intern" />
            <el-option label="全职" value="fulltime" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="search">搜索</el-button>
          <el-button @click="resetFilters">重置</el-button>
        </el-form-item>
      </el-form>
    </div>

    <div class="sample-list">
      <el-table :data="samples" style="width: 100%">
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="user" label="用户" width="120" />
        <el-table-column prop="job_title" label="岗位" width="180" />
        <el-table-column prop="ai_score" label="AI评分" width="100">
          <template #default="{ row }">
            <span :class="getScoreClass(row.ai_score)">{{ row.ai_score }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="human_score" label="人工评分" width="100">
          <template #default="{ row }">
            <span v-if="row.human_score" :class="getScoreClass(row.human_score)">
              {{ row.human_score }}
            </span>
            <span v-else class="unscored">未评分</span>
          </template>
        </el-table-column>
        <el-table-column prop="difference" label="差异" width="100">
          <template #default="{ row }">
            <span v-if="row.human_score" :class="getDiffClass(row.difference)">
              {{ row.difference > 0 ? '+' : '' }}{{ row.difference }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)">
              {{ row.status === 'pending' ? '待复核' : row.status === 'reviewed' ? '已复核' : '已标注' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="reviewer" label="复核人" width="120" />
        <el-table-column prop="review_time" label="复核时间" width="180" />
        <el-table-column label="操作" width="200">
          <template #default="{ row }">
            <el-button type="primary" size="small" @click="reviewSample(row)">
              复核
            </el-button>
            <el-button size="small" @click="viewDetails(row)">详情</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <div class="pagination">
      <el-pagination
        v-model:current-page="pagination.current"
        v-model:page-size="pagination.size"
        :total="pagination.total"
        :page-sizes="[10, 20, 50]"
        layout="total, sizes, prev, pager, next, jumper"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const filters = ref({
  dateRange: [],
  minScore: 0,
  maxScore: 100,
  jobType: ''
})

const samples = ref([
  {
    id: 1001,
    user: 'user123',
    job_title: 'Python开发实习生',
    ai_score: 85.6,
    human_score: 82.0,
    difference: -3.6,
    status: 'reviewed',
    reviewer: 'admin001',
    review_time: '2026-04-11 10:30:25'
  },
  {
    id: 1002,
    user: 'user456',
    job_title: '前端开发实习生',
    ai_score: 78.2,
    human_score: null,
    difference: null,
    status: 'pending',
    reviewer: null,
    review_time: null
  },
  {
    id: 1003,
    user: 'user789',
    job_title: '数据分析师',
    ai_score: 92.1,
    human_score: 90.5,
    difference: -1.6,
    status: 'labeled',
    reviewer: 'admin002',
    review_time: '2026-04-10 15:20:10'
  }
])

const pagination = ref({
  current: 1,
  size: 10,
  total: 50
})

const getScoreClass = (score: number) => {
  if (score >= 90) return 'score-excellent'
  if (score >= 80) return 'score-good'
  if (score >= 70) return 'score-medium'
  if (score >= 60) return 'score-pass'
  return 'score-fail'
}

const getDiffClass = (diff: number) => {
  if (Math.abs(diff) <= 2) return 'diff-small'
  if (Math.abs(diff) <= 5) return 'diff-medium'
  return 'diff-large'
}

const getStatusType = (status: string) => {
  switch (status) {
    case 'pending': return 'warning'
    case 'reviewed': return 'success'
    case 'labeled': return 'info'
    default: return ''
  }
}

const refresh = () => {
  ElMessage.success('数据已刷新')
}

const exportData = () => {
  ElMessage.info('导出功能开发中')
}

const openSettings = () => {
  ElMessage.info('设置功能开发中')
}

const search = () => {
  ElMessage.success('搜索完成')
}

const resetFilters = () => {
  filters.value = {
    dateRange: [],
    minScore: 0,
    maxScore: 100,
    jobType: ''
  }
}

const reviewSample = (sample: any) => {
  ElMessage.info(`复核样本 ${sample.id}`)
}

const viewDetails = (sample: any) => {
  ElMessage.info(`查看样本 ${sample.id} 详情`)
}
</script>

<style scoped>
.evaluation-check {
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

.actions {
  margin-bottom: 20px;
}

.filters {
  margin-bottom: 20px;
  padding: 20px;
  background: #f8f9fa;
  border-radius: 8px;
}

.separator {
  margin: 0 8px;
  color: #909399;
}

.sample-list {
  margin-bottom: 20px;
}

.unscored {
  color: #909399;
}

.score-excellent { color: #67C23A; font-weight: bold; }
.score-good { color: #E6A23C; font-weight: bold; }
.score-medium { color: #409EFF; font-weight: bold; }
.score-pass { color: #909399; font-weight: bold; }
.score-fail { color: #F56C6C; font-weight: bold; }

.diff-small { color: #67C23A; }
.diff-medium { color: #E6A23C; }
.diff-large { color: #F56C6C; }

.pagination {
  display: flex;
  justify-content: center;
}
</style>