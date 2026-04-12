<template>
  <div class="crawler-monitor">
    <div class="header">
      <h1>爬虫监控</h1>
      <p>各平台爬虫健康状态监控</p>
    </div>

    <div class="actions">
      <el-button type="primary" icon="Refresh" @click="refreshStatus">刷新状态</el-button>
      <el-button icon="VideoPlay" @click="startAllCrawlers">启动所有爬虫</el-button>
      <el-button icon="VideoPause" @click="stopAllCrawlers">停止所有爬虫</el-button>
    </div>

    <div class="crawler-status">
      <el-table :data="crawlers" style="width: 100%">
        <el-table-column prop="platform" label="平台" width="120">
          <template #default="{ row }">
            <div class="platform-info">
              <el-avatar :size="32" :src="row.logo" />
              <span>{{ row.platform }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)">
              {{ row.status === 'running' ? '运行中' : row.status === 'stopped' ? '已停止' : '异常' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="success_rate" label="成功率" width="120">
          <template #default="{ row }">
            <el-progress :percentage="row.success_rate" :show-text="false" />
            <span>{{ row.success_rate }}%</span>
          </template>
        </el-table-column>
        <el-table-column prop="last_run" label="最近执行" width="180" />
        <el-table-column prop="total_jobs" label="累计抓取" width="120" />
        <el-table-column prop="error_count" label="错误数" width="100" />
        <el-table-column label="操作" width="200">
          <template #default="{ row }">
            <el-button
              v-if="row.status !== 'running'"
              type="success"
              size="small"
              @click="startCrawler(row.platform)"
            >
              启动
            </el-button>
            <el-button
              v-else
              type="warning"
              size="small"
              @click="stopCrawler(row.platform)"
            >
              停止
            </el-button>
            <el-button
              type="primary"
              size="small"
              @click="viewLogs(row.platform)"
            >
              查看日志
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <div class="charts">
      <el-row :gutter="20">
        <el-col :span="12">
          <el-card>
            <template #header>
              <h3>成功率趋势</h3>
            </template>
            <div class="chart-placeholder">
              <p>成功率趋势图表</p>
            </div>
          </el-card>
        </el-col>
        <el-col :span="12">
          <el-card>
            <template #header>
              <h3>抓取量统计</h3>
            </template>
            <div class="chart-placeholder">
              <p>抓取量统计图表</p>
            </div>
          </el-card>
        </el-col>
      </el-row>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const crawlers = ref([
  {
    platform: 'BOSS直聘',
    logo: '',
    status: 'running',
    success_rate: 95,
    last_run: '2026-04-11 14:30:25',
    total_jobs: 12560,
    error_count: 3
  },
  {
    platform: '智联招聘',
    logo: '',
    status: 'running',
    success_rate: 92,
    last_run: '2026-04-11 14:28:10',
    total_jobs: 9870,
    error_count: 8
  },
  {
    platform: '前程无忧',
    logo: '',
    status: 'stopped',
    success_rate: 88,
    last_run: '2026-04-10 23:15:45',
    total_jobs: 7540,
    error_count: 15
  },
  {
    platform: '猎聘',
    logo: '',
    status: 'error',
    success_rate: 65,
    last_run: '2026-04-10 20:45:30',
    total_jobs: 4320,
    error_count: 42
  }
])

const getStatusType = (status: string) => {
  switch (status) {
    case 'running': return 'success'
    case 'stopped': return 'info'
    default: return 'danger'
  }
}

const refreshStatus = () => {
  ElMessage.success('状态已刷新')
}

const startAllCrawlers = () => {
  ElMessage.info('启动所有爬虫功能开发中')
}

const stopAllCrawlers = () => {
  ElMessage.info('停止所有爬虫功能开发中')
}

const startCrawler = (platform: string) => {
  ElMessage.success(`启动 ${platform} 爬虫`)
}

const stopCrawler = (platform: string) => {
  ElMessage.success(`停止 ${platform} 爬虫`)
}

const viewLogs = (platform: string) => {
  ElMessage.info(`查看 ${platform} 日志`)
}
</script>

<style scoped>
.crawler-monitor {
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

.platform-info {
  display: flex;
  align-items: center;
  gap: 10px;
}

.charts {
  margin-top: 30px;
}

.chart-placeholder {
  height: 200px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #909399;
  background: #f5f7fa;
  border-radius: 4px;
}
</style>