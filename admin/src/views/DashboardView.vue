<template>
  <div class="dashboard">
    <div class="dashboard-header">
      <h1>数据看板</h1>
      <p>系统核心业务指标可视化</p>
    </div>

    <!-- 统计卡片 -->
    <div class="stats-cards">
      <el-card class="stat-card">
        <div class="stat-content">
          <div class="stat-icon" style="color: #409eff;">
            <el-icon size="24"><User /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">1,234</div>
            <div class="stat-label">日活跃用户</div>
          </div>
          <div class="stat-trend trend-up">+12.5%</div>
        </div>
      </el-card>

      <el-card class="stat-card">
        <div class="stat-content">
          <div class="stat-icon" style="color: #67c23a;">
            <el-icon size="24"><Search /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">5,678</div>
            <div class="stat-label">日搜索次数</div>
          </div>
          <div class="stat-trend trend-up">+8.3%</div>
        </div>
      </el-card>

      <el-card class="stat-card">
        <div class="stat-content">
          <div class="stat-icon" style="color: #e6a23c;">
            <el-icon size="24"><ChatDotRound /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">3,456</div>
            <div class="stat-label">日评估次数</div>
          </div>
          <div class="stat-trend trend-up">+15.2%</div>
        </div>
      </el-card>

      <el-card class="stat-card">
        <div class="stat-content">
          <div class="stat-icon" style="color: #f56c6c;">
            <el-icon size="24"><TrendCharts /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">89.5%</div>
            <div class="stat-label">用户满意度</div>
          </div>
          <div class="stat-trend trend-down">-2.1%</div>
        </div>
      </el-card>
    </div>

    <!-- 图表区域 -->
    <div class="charts-section">
      <el-row :gutter="20">
        <el-col :span="12">
          <el-card class="chart-card">
            <template #header>
              <h3>用户活跃趋势</h3>
            </template>
            <div ref="userChartRef" class="chart-container"></div>
          </el-card>
        </el-col>
        <el-col :span="12">
          <el-card class="chart-card">
            <template #header>
              <h3>热门岗位TOP10</h3>
            </template>
            <div ref="jobChartRef" class="chart-container"></div>
          </el-card>
        </el-col>
      </el-row>

      <el-row :gutter="20" style="margin-top: 20px;">
        <el-col :span="12">
          <el-card class="chart-card">
            <template #header>
              <h3>热门技能TOP10</h3>
            </template>
            <div ref="skillChartRef" class="chart-container"></div>
          </el-card>
        </el-col>
        <el-col :span="12">
          <el-card class="chart-card">
            <template #header>
              <h3>评估分数分布</h3>
            </template>
            <div ref="scoreChartRef" class="chart-container"></div>
          </el-card>
        </el-col>
      </el-row>
    </div>

    <!-- 最近活动 -->
    <div class="recent-activity">
      <el-card>
        <template #header>
          <h3>最近活动</h3>
        </template>
        <el-table :data="recentActivities" style="width: 100%">
          <el-table-column prop="time" label="时间" width="180" />
          <el-table-column prop="user" label="用户" width="120" />
          <el-table-column prop="action" label="操作" />
          <el-table-column prop="details" label="详情" />
        </el-table>
      </el-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import * as echarts from 'echarts'
import type { ECharts } from 'echarts'
import {
  User,
  Search,
  ChatDotRound,
  TrendCharts
} from '@element-plus/icons-vue'

// 图表引用
const userChartRef = ref<HTMLDivElement>()
const jobChartRef = ref<HTMLDivElement>()
const skillChartRef = ref<HTMLDivElement>()
const scoreChartRef = ref<HTMLDivElement>()

let userChart: ECharts | null = null
let jobChart: ECharts | null = null
let skillChart: ECharts | null = null
let scoreChart: ECharts | null = null

// 最近活动数据
const recentActivities = ref([
  {
    time: '2026-04-11 14:30',
    user: 'user123',
    action: '完成评估',
    details: 'Python开发实习生岗位评估，得分85.6'
  },
  {
    time: '2026-04-11 14:15',
    user: 'user456',
    action: '搜索岗位',
    details: '搜索关键词：前端开发、北京、实习'
  },
  {
    time: '2026-04-11 13:45',
    user: 'user789',
    action: '注册账号',
    details: '新用户注册，学校：清华大学'
  },
  {
    time: '2026-04-11 13:20',
    user: 'user101',
    action: '完成评估',
    details: '数据分析师岗位评估，得分78.2'
  },
  {
    time: '2026-04-11 12:55',
    user: 'user202',
    action: '修改个人信息',
    details: '更新技能标签：Python, SQL, PowerBI'
  }
])

// 初始化用户活跃趋势图表
const initUserChart = () => {
  if (!userChartRef.value) return

  userChart = echarts.init(userChartRef.value)

  const option = {
    tooltip: {
      trigger: 'axis'
    },
    xAxis: {
      type: 'category',
      data: ['04-05', '04-06', '04-07', '04-08', '04-09', '04-10', '04-11']
    },
    yAxis: {
      type: 'value',
      name: '用户数'
    },
    series: [
      {
        name: '活跃用户',
        type: 'line',
        data: [820, 932, 901, 934, 1290, 1330, 1320],
        smooth: true,
        lineStyle: {
          color: '#409eff',
          width: 3
        },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(64, 158, 255, 0.3)' },
              { offset: 1, color: 'rgba(64, 158, 255, 0.05)' }
            ]
          }
        }
      }
    ]
  }

  userChart.setOption(option)
}

// 初始化热门岗位图表
const initJobChart = () => {
  if (!jobChartRef.value) return

  jobChart = echarts.init(jobChartRef.value)

  const option = {
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'shadow'
      }
    },
    xAxis: {
      type: 'value',
      name: '搜索次数'
    },
    yAxis: {
      type: 'category',
      data: ['Python开发', '前端开发', '数据分析', 'Java开发', '产品经理', 'UI设计', '测试开发', '运维开发', '移动开发', 'AI工程师']
    },
    series: [
      {
        name: '搜索次数',
        type: 'bar',
        data: [1560, 1420, 1280, 1150, 980, 870, 760, 690, 580, 520],
        itemStyle: {
          color: '#67c23a'
        }
      }
    ]
  }

  jobChart.setOption(option)
}

// 初始化热门技能图表
const initSkillChart = () => {
  if (!skillChartRef.value) return

  skillChart = echarts.init(skillChartRef.value)

  const option = {
    tooltip: {
      trigger: 'item'
    },
    series: [
      {
        name: '技能热度',
        type: 'pie',
        radius: ['40%', '70%'],
        data: [
          { value: 1560, name: 'Python' },
          { value: 1420, name: 'JavaScript' },
          { value: 1280, name: 'Java' },
          { value: 980, name: 'SQL' },
          { value: 870, name: 'Vue.js' },
          { value: 760, name: 'React' },
          { value: 690, name: 'Docker' },
          { value: 580, name: 'Linux' },
          { value: 520, name: 'Git' },
          { value: 480, name: 'Redis' }
        ],
        emphasis: {
          itemStyle: {
            shadowBlur: 10,
            shadowOffsetX: 0,
            shadowColor: 'rgba(0, 0, 0, 0.5)'
          }
        }
      }
    ]
  }

  skillChart.setOption(option)
}

// 初始化评估分数分布图表
const initScoreChart = () => {
  if (!scoreChartRef.value) return

  scoreChart = echarts.init(scoreChartRef.value)

  const option = {
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'cross'
      }
    },
    xAxis: {
      type: 'category',
      data: ['0-20', '20-40', '40-60', '60-70', '70-80', '80-90', '90-100']
    },
    yAxis: {
      type: 'value',
      name: '人数'
    },
    series: [
      {
        name: '分数分布',
        type: 'bar',
        data: [50, 120, 240, 360, 450, 280, 100],
        itemStyle: {
          color: '#e6a23c'
        }
      }
    ]
  }

  scoreChart.setOption(option)
}

// 初始化所有图表
const initCharts = () => {
  initUserChart()
  initJobChart()
  initSkillChart()
  initScoreChart()
}

// 响应式调整图表大小
const resizeCharts = () => {
  userChart?.resize()
  jobChart?.resize()
  skillChart?.resize()
  scoreChart?.resize()
}

onMounted(() => {
  initCharts()
  window.addEventListener('resize', resizeCharts)
})

onUnmounted(() => {
  userChart?.dispose()
  jobChart?.dispose()
  skillChart?.dispose()
  scoreChart?.dispose()
  window.removeEventListener('resize', resizeCharts)
})
</script>

<style scoped>
.dashboard {
  padding: 20px;
}

.dashboard-header {
  margin-bottom: 30px;
}

.dashboard-header h1 {
  color: #409eff;
  margin-bottom: 10px;
}

.dashboard-header p {
  color: #666;
}

.stats-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 20px;
  margin-bottom: 30px;
}

.stat-card {
  transition: transform 0.3s;
}

.stat-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
}

.stat-content {
  display: flex;
  align-items: center;
  gap: 15px;
}

.stat-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 48px;
  height: 48px;
  border-radius: 8px;
  background: rgba(64, 158, 255, 0.1);
}

.stat-info {
  flex: 1;
}

.stat-value {
  font-size: 24px;
  font-weight: bold;
  color: #333;
  line-height: 1;
  margin-bottom: 4px;
}

.stat-label {
  font-size: 14px;
  color: #666;
}

.stat-trend {
  font-size: 14px;
  font-weight: bold;
}

.trend-up {
  color: #67c23a;
}

.trend-down {
  color: #f56c6c;
}

.charts-section {
  margin-bottom: 30px;
}

.chart-card {
  height: 300px;
}

.chart-card h3 {
  margin: 0;
  color: #333;
}

.chart-container {
  width: 100%;
  height: 240px;
}

.recent-activity {
  margin-top: 20px;
}
</style>