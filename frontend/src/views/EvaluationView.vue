<template>
  <div class="evaluation">
    <div class="container">
      <div class="header">
        <h1>评估报告</h1>
        <p>AI对您回答的详细评估和改进建议</p>
      </div>

      <div v-if="!overallResult.overall_score" class="empty">
        <el-empty description="暂无评估记录" />
        <div class="actions">
          <el-button type="primary" @click="goToPractice">开始练习</el-button>
        </div>
      </div>

      <div v-else>
        <!-- 总体评估 -->
        <el-card class="overall-card">
          <div class="overall-header">
            <h2>总体表现</h2>
            <div class="overall-score">
              <div class="score-circle">
                <span class="score-value">{{ overallResult.overall_score.toFixed(1) }}</span>
                <span class="score-label">总分</span>
              </div>
              <div class="score-level">
                <h3>{{ getScoreLevel(overallResult.overall_score) }}</h3>
                <p>{{ overallResult.summary }}</p>
              </div>
            </div>
          </div>

          <div class="strengths-improvements">
            <div class="section">
              <h4><el-icon color="#67C23A"><SuccessFilled /></el-icon> 优势</h4>
              <ul>
                <li v-for="strength in overallResult.strengths" :key="strength">{{ strength }}</li>
              </ul>
            </div>
            <div class="section">
              <h4><el-icon color="#E6A23C"><WarningFilled /></el-icon> 改进建议</h4>
              <ul>
                <li v-for="improvement in overallResult.improvements" :key="improvement">{{ improvement }}</li>
              </ul>
            </div>
          </div>
        </el-card>

        <!-- 各问题详细评估 -->
        <div class="detailed-evaluation">
          <h3>各问题详细评估</h3>
          <el-card
            v-for="(result, index) in currentResults"
            :key="result.question_id"
            class="detail-card"
          >
            <div class="detail-header">
              <div class="question-info">
                <div class="question-number">问题 {{ index + 1 }}</div>
                <div class="question-score">
                  评分：<span class="score">{{ result.score.toFixed(1) }}</span>
                </div>
              </div>
              <el-tag :type="getScoreTagType(result.score)">
                {{ getScoreLevel(result.score) }}
              </el-tag>
            </div>

            <div class="feedback">
              <h4>反馈：</h4>
              <p>{{ result.feedback }}</p>
            </div>

            <div class="strengths-improvements">
              <div class="section">
                <h5>亮点：</h5>
                <ul>
                  <li v-for="strength in result.strengths" :key="strength">{{ strength }}</li>
                </ul>
              </div>
              <div class="section">
                <h5>改进建议：</h5>
                <ul>
                  <li v-for="improvement in result.improvements" :key="improvement">{{ improvement }}</li>
                </ul>
              </div>
            </div>

            <div v-if="result.suggested_answer" class="suggested-answer">
              <h5>参考答案：</h5>
              <p>{{ result.suggested_answer }}</p>
            </div>
          </el-card>
        </div>

        <!-- 历史记录 -->
        <div class="history-section">
          <h3>历史评估记录</h3>
          <el-table :data="evaluationHistory" style="width: 100%">
            <el-table-column prop="timestamp" label="时间" width="180">
              <template #default="{ row }">
                {{ formatDate(row.timestamp) }}
              </template>
            </el-table-column>
            <el-table-column prop="overall_score" label="总分" width="100">
              <template #default="{ row }">
                <span :class="getScoreClass(row.overall_score)">{{ row.overall_score.toFixed(1) }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="question_count" label="问题数量" width="100" />
            <el-table-column prop="answered_count" label="已回答" width="100" />
            <el-table-column label="操作" width="120">
              <template #default="{ row }">
                <el-button type="text" @click="viewHistoryDetail(row)">查看详情</el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>

        <div class="actions">
          <el-button type="primary" @click="goToPractice">继续练习</el-button>
          <el-button @click="goToJobs">查看其他岗位</el-button>
          <el-button @click="shareReport">分享报告</el-button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { SuccessFilled, WarningFilled } from '@element-plus/icons-vue'
import { useEvaluationStore } from '@/stores/evaluationStore'
import ChartRadar from '@/components/ChartRadar.vue'

const router = useRouter()
const evaluationStore = useEvaluationStore()

const overallResult = computed(() => evaluationStore.overallResult)
const currentResults = computed(() => evaluationStore.currentResults)
const evaluationHistory = computed(() => evaluationStore.evaluationHistory)

const getScoreLevel = (score: number) => {
  if (score >= 90) return '优秀'
  if (score >= 80) return '良好'
  if (score >= 70) return '中等'
  if (score >= 60) return '及格'
  return '待提升'
}

const getScoreTagType = (score: number) => {
  if (score >= 90) return 'success'
  if (score >= 80) return 'warning'
  if (score >= 70) return ''
  if (score >= 60) return 'info'
  return 'danger'
}

const getScoreClass = (score: number) => {
  if (score >= 90) return 'score-excellent'
  if (score >= 80) return 'score-good'
  if (score >= 70) return 'score-medium'
  if (score >= 60) return 'score-pass'
  return 'score-fail'
}

const formatDate = (timestamp: string) => {
  return new Date(timestamp).toLocaleString('zh-CN')
}

const goToPractice = () => {
  router.push('/practice')
}

const goToJobs = () => {
  router.push('/jobs')
}

const viewHistoryDetail = (record: any) => {
  // 查看历史记录详情
  console.log('View history detail:', record)
}

const shareReport = () => {
  ElMessage.success('分享功能开发中...')
}
</script>

<style scoped>
.evaluation {
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
}

.container {
  background: white;
  border-radius: 8px;
  padding: 30px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
}

.header {
  text-align: center;
  margin-bottom: 30px;
}

.header h1 {
  color: #409eff;
  margin-bottom: 10px;
}

.header p {
  color: #666;
}

.empty {
  padding: 60px 0;
  text-align: center;
}

.actions {
  margin-top: 30px;
  display: flex;
  justify-content: center;
  gap: 20px;
}

.overall-card {
  margin-bottom: 30px;
}

.overall-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 30px;
}

.overall-header h2 {
  color: #333;
}

.overall-score {
  display: flex;
  align-items: center;
  gap: 40px;
}

.score-circle {
  width: 120px;
  height: 120px;
  border-radius: 50%;
  background: linear-gradient(135deg, #409eff, #66b1ff);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: white;
}

.score-value {
  font-size: 36px;
  font-weight: bold;
  line-height: 1;
}

.score-label {
  font-size: 14px;
  opacity: 0.9;
}

.score-level h3 {
  margin-bottom: 10px;
  color: #333;
}

.score-level p {
  color: #666;
  max-width: 300px;
}

.strengths-improvements {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 30px;
}

.section {
  background: #f8f9fa;
  border-radius: 8px;
  padding: 20px;
}

.section h4 {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 15px;
  color: #333;
}

.section ul {
  padding-left: 20px;
}

.section li {
  margin-bottom: 8px;
  color: #555;
  line-height: 1.6;
}

.detailed-evaluation {
  margin-top: 40px;
}

.detailed-evaluation h3 {
  margin-bottom: 20px;
  color: #333;
}

.detail-card {
  margin-bottom: 20px;
}

.detail-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
}

.question-info {
  display: flex;
  align-items: center;
  gap: 20px;
}

.question-number {
  font-weight: bold;
  color: #333;
}

.question-score {
  color: #666;
}

.question-score .score {
  font-weight: bold;
  color: #f56c6c;
  font-size: 18px;
}

.feedback {
  margin-bottom: 15px;
}

.feedback h4 {
  margin-bottom: 8px;
  color: #333;
}

.feedback p {
  color: #555;
  line-height: 1.6;
}

.strengths-improvements .section {
  background: transparent;
  padding: 0;
}

.strengths-improvements .section h5 {
  margin-bottom: 8px;
  color: #666;
}

.suggested-answer {
  margin-top: 15px;
  padding-top: 15px;
  border-top: 1px solid #eee;
}

.suggested-answer h5 {
  margin-bottom: 8px;
  color: #333;
}

.suggested-answer p {
  color: #555;
  line-height: 1.6;
  background: #f8f9fa;
  padding: 15px;
  border-radius: 4px;
}

.history-section {
  margin-top: 40px;
}

.history-section h3 {
  margin-bottom: 20px;
  color: #333;
}

.score-excellent { color: #67C23A; font-weight: bold; }
.score-good { color: #E6A23C; font-weight: bold; }
.score-medium { color: #409EFF; font-weight: bold; }
.score-pass { color: #909399; font-weight: bold; }
.score-fail { color: #F56C6C; font-weight: bold; }
</style>