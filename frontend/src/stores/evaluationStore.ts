import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useEvaluationStore = defineStore('evaluation', () => {
  // 当前评估会话
  const currentSession = ref({
    id: null as number | null,
    job_id: null as number | null,
    questions: [] as any[],
    answers: [] as any[],
    start_time: null as string | null,
    end_time: null as string | null
  })

  // 评估历史
  const evaluationHistory = ref<any[]>([])

  // 当前评估结果
  const currentResults = ref<any[]>([])

  // 总体评估结果
  const overallResult = ref({
    overall_score: 0,
    summary: '',
    strengths: [] as string[],
    improvements: [] as string[]
  })

  // 是否正在评估
  const isEvaluating = ref(false)

  // 开始新的评估会话
  const startNewSession = (jobId: number, questions: any[]) => {
    currentSession.value = {
      id: Date.now(),
      job_id: jobId,
      questions,
      answers: [],
      start_time: new Date().toISOString(),
      end_time: null
    }
  }

  // 添加答案
  const addAnswer = (questionId: number, answer: string) => {
    const existingIndex = currentSession.value.answers.findIndex(
      a => a.question_id === questionId
    )

    if (existingIndex >= 0) {
      currentSession.value.answers[existingIndex].user_answer = answer
    } else {
      currentSession.value.answers.push({
        question_id: questionId,
        user_answer: answer
      })
    }
  }

  // 提交评估
  const submitEvaluation = async () => {
    if (currentSession.value.answers.length === 0) {
      throw new Error('请先回答问题')
    }

    isEvaluating.value = true

    try {
      // 这里应该调用批量评估API
      // const response = await batchEvaluate({ answers: currentSession.value.answers })
      // currentResults.value = response.data.results
      // overallResult.value = {
      //   overall_score: response.data.overall_score,
      //   summary: response.data.summary,
      //   strengths: [],
      //   improvements: []
      // }

      // 模拟评估结果
      await new Promise(resolve => setTimeout(resolve, 1000))

      currentResults.value = currentSession.value.answers.map((answer, index) => ({
        question_id: answer.question_id,
        score: 70 + Math.random() * 30,
        feedback: `这是第${index + 1}个问题的反馈`,
        strengths: ['回答结构清晰', '相关知识点掌握较好'],
        improvements: ['可以更详细地举例说明', '注意专业术语的准确性']
      }))

      const totalScore = currentResults.value.reduce((sum, result) => sum + result.score, 0)
      const averageScore = totalScore / currentResults.value.length

      overallResult.value = {
        overall_score: averageScore,
        summary: averageScore >= 80 ? '表现优秀' : averageScore >= 60 ? '表现良好' : '需要更多练习',
        strengths: ['基础知识扎实', '表达清晰'],
        improvements: ['需要加强实践经验', '注意时间管理']
      }

      // 保存到历史记录
      const historyRecord = {
        id: currentSession.value.id,
        job_id: currentSession.value.job_id,
        timestamp: new Date().toISOString(),
        overall_score: overallResult.value.overall_score,
        question_count: currentSession.value.questions.length,
        answered_count: currentSession.value.answers.length
      }

      evaluationHistory.value.unshift(historyRecord)
      localStorage.setItem('evaluationHistory', JSON.stringify(evaluationHistory.value))

      // 结束会话
      currentSession.value.end_time = new Date().toISOString()

      return {
        results: currentResults.value,
        overall: overallResult.value
      }
    } finally {
      isEvaluating.value = false
    }
  }

  // 清除当前会话
  const clearCurrentSession = () => {
    currentSession.value = {
      id: null,
      job_id: null,
      questions: [],
      answers: [],
      start_time: null,
      end_time: null
    }
    currentResults.value = []
    overallResult.value = {
      overall_score: 0,
      summary: '',
      strengths: [],
      improvements: []
    }
  }

  // 从localStorage恢复历史记录
  const restoreFromStorage = () => {
    const storedHistory = localStorage.getItem('evaluationHistory')
    if (storedHistory) {
      evaluationHistory.value = JSON.parse(storedHistory)
    }
  }

  // 获取评估进度
  const progress = computed(() => {
    if (currentSession.value.questions.length === 0) return 0
    return (currentSession.value.answers.length / currentSession.value.questions.length) * 100
  })

  // 是否完成所有问题
  const isComplete = computed(() => {
    return currentSession.value.questions.length > 0 &&
           currentSession.value.answers.length === currentSession.value.questions.length
  })

  return {
    currentSession,
    evaluationHistory,
    currentResults,
    overallResult,
    isEvaluating,
    startNewSession,
    addAnswer,
    submitEvaluation,
    clearCurrentSession,
    restoreFromStorage,
    progress,
    isComplete
  }
})