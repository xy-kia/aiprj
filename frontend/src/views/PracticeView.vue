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

              <!-- 个性化问题详细信息 -->
              <div v-if="question.target_skill || question.difficulty || question.suggested_time" class="question-details">
                <div class="detail-tags">
                  <el-tag v-if="question.target_skill" size="small" type="info">
                    <el-icon><Aim /></el-icon>
                    {{ question.target_skill }}
                  </el-tag>
                  <el-tag v-if="question.difficulty" size="small" :type="getDifficultyTagType(question.difficulty)">
                    <el-icon><Flag /></el-icon>
                    {{ getDifficultyText(question.difficulty) }}
                  </el-tag>
                  <el-tag v-if="question.suggested_time" size="small" type="warning">
                    <el-icon><Clock /></el-icon>
                    建议 {{ question.suggested_time }} 秒
                  </el-tag>
                </div>
              </div>

              <!-- 问题来源参考 -->
              <div v-if="question.jd_reference || question.resume_reference" class="question-references">
                <div v-if="question.jd_reference" class="reference-item">
                  <span class="reference-label">岗位要求参考：</span>
                  <span class="reference-content">{{ question.jd_reference }}</span>
                </div>
                <div v-if="question.resume_reference" class="reference-item">
                  <span class="reference-label">个人经历参考：</span>
                  <span class="reference-content">{{ question.resume_reference }}</span>
                </div>
              </div>

              <!-- 评分标准（如果有） -->
              <div v-if="question.scoring_criteria && question.scoring_criteria.length > 0" class="scoring-criteria">
                <div class="criteria-title">评分标准：</div>
                <ul class="criteria-list">
                  <li v-for="(criteria, idx) in question.scoring_criteria" :key="idx">{{ criteria }}</li>
                </ul>
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
import { InfoFilled, Aim, Flag, Clock } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { useEvaluationStore } from '@/stores/evaluationStore'
import { generateQuestions as generateQuestionsAPI, type GenerateQuestionsRequest } from '@/services/api'

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

const getDifficultyTagType = (difficulty: string) => {
  switch (difficulty.toLowerCase()) {
    case 'easy': return 'success'
    case 'medium': return 'warning'
    case 'hard': return 'danger'
    default: return 'info'
  }
}

const getDifficultyText = (difficulty: string) => {
  switch (difficulty.toLowerCase()) {
    case 'easy': return '简单'
    case 'medium': return '中等'
    case 'hard': return '困难'
    default: return difficulty
  }
}

const generateQuestions = async () => {
  // 获取选中的岗位信息
  const selectedJobStr = localStorage.getItem('selectedJob')
  if (!selectedJobStr) {
    ElMessage.warning('请先选择岗位进行面试练习')
    return
  }

  try {
    const selectedJob = JSON.parse(selectedJobStr)

    // 获取用户个人信息（从localStorage或默认值）
    const userInfoStr = localStorage.getItem('userInfo')
    let candidateProfile = ''

    if (userInfoStr) {
      const userInfo = JSON.parse(userInfoStr)
      candidateProfile = `个人信息：
- 姓名：${userInfo.fullName || '未填写'}
- 学校：${userInfo.school || '未填写'}
- 专业：${userInfo.major || '未填写'}
- 年级：${userInfo.grade || '未填写'}
- 技能：${userInfo.skills ? userInfo.skills.join('、') : '未填写'}`
    } else {
      candidateProfile = '求职者未提供详细的个人资料信息，请根据岗位要求生成通用面试问题。'
    }

    // 构建请求数据
    const requestData: GenerateQuestionsRequest = {
      job_data: {
        title: selectedJob.title || '',
        company: selectedJob.company || '',
        description: selectedJob.description || `岗位：${selectedJob.title}，公司：${selectedJob.company}`,
        requirements: selectedJob.requirements || [],
        skills: selectedJob.skills || [],
        candidate_profile: candidateProfile
      },
      question_type: 'intern_general', // 默认使用一般实习版问题
      num_questions: questionCount.value,
      enable_llm_evaluation: true
    }

    ElMessage.info('正在使用AI生成个性化面试问题...')

    // 调用API生成问题
    const response = await generateQuestionsAPI(requestData)

    // 转换响应格式以适应现有界面
    const questions = response.data.questions.map((q, index) => ({
      id: index + 1,
      type: q.question_type || q.type || 'general',  // 优先使用后端返回的question_type
      question: q.question,
      hint: q.target_skill ? `考察点：${q.target_skill}` :
             (q.difficulty ? `难度：${q.difficulty}` : ''),
      target_skill: q.target_skill,
      jd_reference: q.jd_reference,
      resume_reference: q.resume_reference,
      suggested_time: q.suggested_time,
      difficulty: q.difficulty,
      scoring_criteria: q.scoring_criteria,
      question_type: q.question_type  // 保留原始question_type字段
    }))

    evaluationStore.startNewSession(1, questions)
    ElMessage.success(`已生成${questions.length}个个性化面试问题`)

  } catch (error: any) {
    console.error('生成问题失败:', error)

    // 如果API调用失败，使用备用方案
    if (error.response) {
      ElMessage.error(`API错误: ${error.response.data?.detail || '生成问题失败'}`)
    } else {
      ElMessage.error('网络错误，使用默认问题')
    }

    // 使用默认问题作为后备
    const fallbackQuestions = Array.from({ length: questionCount.value }, (_, i) => ({
      id: i + 1,
      type: i % 2 === 0 ? 'technical' : 'behavioral',
      question: `这是第${i + 1}个${i % 2 === 0 ? '技术' : '行为'}面试问题？`,
      hint: i % 2 === 0 ? '可以从多个角度思考这个问题' : '请结合具体事例说明'
    }))

    evaluationStore.startNewSession(1, fallbackQuestions)
  }
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

/* 个性化问题详细信息样式 */
.question-details {
  margin: 15px 0;
  padding: 12px;
  background: #f8f9fa;
  border-radius: 6px;
  border-left: 4px solid #409eff;
}

.detail-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.detail-tags .el-tag {
  display: flex;
  align-items: center;
  gap: 4px;
}

/* 问题来源参考样式 */
.question-references {
  margin: 12px 0;
  padding: 12px;
  background: #fff8e6;
  border-radius: 6px;
  border: 1px solid #ffe7ba;
}

.reference-item {
  margin-bottom: 8px;
}

.reference-item:last-child {
  margin-bottom: 0;
}

.reference-label {
  font-weight: bold;
  color: #666;
  font-size: 13px;
  margin-right: 6px;
}

.reference-content {
  color: #555;
  font-size: 13px;
  line-height: 1.5;
}

/* 评分标准样式 */
.scoring-criteria {
  margin: 12px 0;
  padding: 12px;
  background: #f0f9ff;
  border-radius: 6px;
  border: 1px solid #91caff;
}

.criteria-title {
  font-weight: bold;
  color: #409eff;
  margin-bottom: 8px;
  font-size: 13px;
}

.criteria-list {
  padding-left: 20px;
  margin: 0;
}

.criteria-list li {
  color: #555;
  font-size: 13px;
  line-height: 1.5;
  margin-bottom: 4px;
}

.criteria-list li:last-child {
  margin-bottom: 0;
}
</style>