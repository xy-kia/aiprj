<template>
  <div class="practice">
    <div class="container">
      <div class="header">
        <h1>面试练习</h1>
        <p>回答以下问题，AI将评估您的回答并提供改进建议</p>
      </div>

      <div v-if="!currentSession.questions.length" class="setup-section">
        <el-card class="setup-card">
          <h3>选择练习模式</h3>
          <div class="mode-select">
            <el-radio-group v-model="practiceMode">
              <el-radio label="technical">技术面试</el-radio>
              <el-radio label="behavioral">行为面试</el-radio>
              <el-radio label="mixed">综合面试</el-radio>
            </el-radio-group>
          </div>
          <div class="question-count">
            <span>问题数量：</span>
            <el-input-number v-model="questionCount" :min="3" :max="20" />
          </div>
          <div class="actions">
            <el-button type="primary" @click="generateQuestions">开始练习</el-button>
            <el-button @click="goBack">返回</el-button>
          </div>
        </el-card>
      </div>

      <div v-else class="practice-section">
        <div class="progress">
          <div class="progress-info">
            <span>进度：{{ currentSession.answers.length }}/{{ currentSession.questions.length }}</span>
            <el-progress :percentage="progress" :show-text="false" style="flex: 1; margin: 0 20px;" />
            <span>{{ progress.toFixed(1) }}%</span>
          </div>
        </div>

        <div class="question-list">
          <el-card
            v-for="(question, index) in currentSession.questions"
            :key="question.id"
            class="question-card"
            :class="{ 'answered': isAnswered(question.id) }"
          >
            <div class="question-header">
              <div class="question-number">问题 {{ index + 1 }}</div>
              <el-tag :type="question.type === 'technical' ? 'success' : 'warning'">
                {{ question.type === 'technical' ? '技术问题' : '行为问题' }}
              </el-tag>
            </div>

            <div class="question-content">
              <h4>{{ question.question }}</h4>
              <div v-if="question.hint" class="hint">
                <el-icon><InfoFilled /></el-icon>
                <span>提示：{{ question.hint }}</span>
              </div>
            </div>

            <div class="answer-section">
              <el-input
                v-model="answers[question.id]"
                type="textarea"
                :rows="4"
                placeholder="请输入您的回答..."
                resize="none"
                @input="saveAnswer(question.id, $event)"
              />

              <div v-if="currentResults.find(r => r.question_id === question.id)" class="preview-result">
                <div class="score">
                  评分：<span class="score-value">{{ getQuestionScore(question.id) }}</span>
                </div>
                <el-button type="text" @click="viewDetails(question.id)">查看详细反馈</el-button>
              </div>
            </div>
          </el-card>
        </div>

        <div class="practice-actions">
          <el-button type="primary" :loading="isEvaluating" @click="submitEvaluation">
            提交评估
          </el-button>
          <el-button @click="clearSession">重新开始</el-button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { InfoFilled } from '@element-plus/icons-vue'
import { useEvaluationStore } from '@/stores/evaluationStore'

const router = useRouter()
const evaluationStore = useEvaluationStore()

const practiceMode = ref('mixed')
const questionCount = ref(5)
const answers = ref<Record<number, string>>({})

const currentSession = computed(() => evaluationStore.currentSession)
const currentResults = computed(() => evaluationStore.currentResults)
const isEvaluating = computed(() => evaluationStore.isEvaluating)
const progress = computed(() => evaluationStore.progress)
const isComplete = computed(() => evaluationStore.isComplete)

const isAnswered = (questionId: number) => {
  return answers.value[questionId] && answers.value[questionId].trim().length > 0
}

const getQuestionScore = (questionId: number) => {
  const result = currentResults.value.find(r => r.question_id === questionId)
  return result ? result.score.toFixed(1) : '未评估'
}

const generateQuestions = async () => {
  // 这里应该调用问题生成API
  // 模拟数据
  const questions = Array.from({ length: questionCount.value }, (_, i) => ({
    id: i + 1,
    type: i % 2 === 0 ? 'technical' : 'behavioral',
    question: `这是第${i + 1}个${i % 2 === 0 ? '技术' : '行为'}面试问题？`,
    hint: i % 2 === 0 ? '可以从多个角度思考这个问题' : '请结合具体事例说明'
  }))

  evaluationStore.startNewSession(1, questions)
}

const saveAnswer = (questionId: number, answer: string) => {
  evaluationStore.addAnswer(questionId, answer)
  answers.value[questionId] = answer
}

const submitEvaluation = async () => {
  if (!isComplete.value) {
    ElMessage.warning('请先回答所有问题')
    return
  }

  try {
    await evaluationStore.submitEvaluation()
    ElMessage.success('评估完成！')
    router.push('/evaluation')
  } catch (error: any) {
    ElMessage.error(error.message || '评估失败')
  }
}

const clearSession = () => {
  evaluationStore.clearCurrentSession()
  answers.value = {}
}

const viewDetails = (questionId: number) => {
  // 查看问题详细反馈
  console.log('View details for question:', questionId)
}

const goBack = () => {
  router.back()
}

onMounted(() => {
  evaluationStore.restoreFromStorage()
})
</script>

<style scoped>
.practice {
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

.setup-section {
  max-width: 600px;
  margin: 0 auto;
}

.setup-card {
  padding: 30px;
}

.setup-card h3 {
  text-align: center;
  margin-bottom: 30px;
  color: #333;
}

.mode-select {
  margin-bottom: 30px;
  text-align: center;
}

.question-count {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  margin-bottom: 30px;
}

.actions {
  display: flex;
  justify-content: center;
  gap: 20px;
}

.progress {
  margin-bottom: 30px;
}

.progress-info {
  display: flex;
  align-items: center;
  gap: 10px;
}

.question-list {
  margin-bottom: 30px;
}

.question-card {
  margin-bottom: 20px;
  transition: all 0.3s;
}

.question-card.answered {
  border-left: 4px solid #409eff;
}

.question-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
}

.question-number {
  font-weight: bold;
  color: #333;
}

.question-content h4 {
  margin-bottom: 10px;
  color: #333;
  line-height: 1.6;
}

.hint {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #f56c6c;
  font-size: 13px;
  margin-top: 10px;
}

.answer-section {
  margin-top: 15px;
}

.preview-result {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 10px;
}

.score {
  display: flex;
  align-items: center;
  gap: 5px;
}

.score-value {
  font-weight: bold;
  color: #f56c6c;
  font-size: 16px;
}

.practice-actions {
  display: flex;
  justify-content: center;
  gap: 20px;
}
</style>