import axios from 'axios'
import type { AxiosInstance, AxiosRequestConfig, AxiosResponse } from 'axios'
import { ElMessage } from 'element-plus'

// 创建axios实例
const apiClient: AxiosInstance = axios.create({
  baseURL: '/api',
  timeout: 300000,  // 增加到300秒（5分钟），适应AI生成问题的较长思考时间
  headers: {
    'Content-Type': 'application/json'
  }
})

// 请求拦截器
apiClient.interceptors.request.use(
  (config) => {
    // 可以在这里添加token等
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// 响应拦截器
apiClient.interceptors.response.use(
  (response: AxiosResponse) => {
    return response
  },
  (error) => {
    // 错误处理
    if (error.response) {
      const { status, data } = error.response

      switch (status) {
        case 400:
          ElMessage.error(data.message || '请求参数错误')
          break
        case 401:
          ElMessage.error('未授权，请重新登录')
          // 可以跳转到登录页
          break
        case 403:
          ElMessage.error('禁止访问')
          break
        case 404:
          ElMessage.error('资源不存在')
          break
        case 500:
          ElMessage.error('服务器内部错误')
          break
        default:
          ElMessage.error(data.message || '请求失败')
      }
    } else if (error.request) {
      ElMessage.error('网络错误，请检查网络连接')
    } else {
      ElMessage.error('请求配置错误')
    }

    return Promise.reject(error)
  }
)

// API接口定义

// 意向解析
export interface ParseIntentRequest {
  raw_input: string
}

export interface ParseIntentResponse {
  keywords: {
    skills: string[]
    job_types: string[]
    locations: string[]
    experiences: string[]
    educations: string[]
    related_skills?: string[]
  }
  confidence: number
}

export const parseIntent = (data: ParseIntentRequest) => {
  return apiClient.post<ParseIntentResponse>('/v1/parse-intent', data)
}

// 岗位搜索
export interface SearchJobsRequest {
  keywords: {
    skills: string[]
    job_types: string[]
    locations: string[]
    experiences: string[]
    educations: string[]
  }
  page?: number
  page_size?: number
}

export interface JobItem {
  id: number
  source: string
  title: string
  company: string
  location: string
  salary: string
  experience: string
  education: string
  job_type: string
  description: string
  skills: string[]
  url: string
}

export interface SearchJobsResponse {
  jobs: JobItem[]
  total: number
  page: number
  page_size: number
}

export const searchJobs = (data: SearchJobsRequest) => {
  return apiClient.post<SearchJobsResponse>('/v1/search-jobs', data)
}

// 问题生成
export interface GenerateQuestionsRequest {
  job_data: {
    title: string
    company: string
    description: string
    requirements?: string[]
    skills?: string[]
    candidate_profile?: string  // 求职者个人资料（简历文本）
  }
  question_type?: 'intern_general' | 'intern_advanced'  // 一般实习或高阶实习/校招
  num_questions?: number
  enable_llm_evaluation?: boolean
}

export interface QuestionItem {
  id: number
  type: string  // technical/behavioral/situational/general
  question_type?: string  // technical/behavioral/situational/general (后端返回字段)
  question: string
  hint?: string
  target_skill?: string
  jd_reference?: string
  resume_reference?: string
  suggested_time?: number
  difficulty?: string
  scoring_criteria?: string[]
}

export interface GenerateQuestionsResponse {
  questions: QuestionItem[]
  total_count: number
  question_type: string
}

export const generateQuestions = (data: GenerateQuestionsRequest) => {
  return apiClient.post<GenerateQuestionsResponse>('/v1/generate-questions', data)
}

// 回答评估
export interface EvaluateAnswerRequest {
  question_id: number
  user_answer: string
}

export interface EvaluationResult {
  score: number
  feedback: string
  strengths: string[]
  improvements: string[]
  suggested_answer?: string
}

export const evaluateAnswer = (data: EvaluateAnswerRequest) => {
  return apiClient.post<EvaluationResult>('/v1/evaluate-answer', data)
}

// 批量评估
export interface BatchEvaluateRequest {
  answers: Array<{
    question_id: number
    user_answer: string
  }>
}

export interface BatchEvaluateResponse {
  results: EvaluationResult[]
  overall_score: number
  summary: string
}

export const batchEvaluate = (data: BatchEvaluateRequest) => {
  return apiClient.post<BatchEvaluateResponse>('/v1/evaluation/batch-evaluate', data)
}

// 健康检查
export interface HealthCheckResponse {
  status: string
  service: string
  version: string
  database: string
  redis: string
}

export const healthCheck = () => {
  return apiClient.get<HealthCheckResponse>('/health')
}

// ==================== AI配置接口 ====================

export interface AIProviderConfig {
  /** AI提供商：openai, anthropic, azure, custom */
  provider: string
  /** API密钥 */
  api_key: string
  /** API基础URL，可用于国内代理或自建服务 */
  base_url: string
  /** 默认模型 */
  default_model: string
  /** 是否启用此配置 */
  enabled: boolean
  /** 温度参数 */
  temperature: number
  /** 最大token数 */
  max_tokens: number
}

export interface AIConfigResponse {
  id: number
  user_id: number
  provider: string
  base_url: string
  default_model: string
  enabled: boolean
  temperature: number
  max_tokens: number
  created_at?: string
  updated_at?: string
}

export interface TestConnectionRequest {
  provider: string
  api_key: string
  base_url: string
}

export interface TestConnectionResponse {
  success: boolean
  message: string
  models?: string[]
  provider?: string
}

/**
 * 获取用户的AI配置
 */
export const getAIConfig = () => {
  return apiClient.get<AIConfigResponse>('/v1/ai-config')
}

/**
 * 更新用户的AI配置
 */
export const updateAIConfig = (config: AIProviderConfig) => {
  return apiClient.post<AIConfigResponse>('/v1/ai-config', config)
}

/**
 * 测试AI API连接并获取可用模型列表
 */
export const testAIConnection = (request: TestConnectionRequest) => {
  return apiClient.post<TestConnectionResponse>('/v1/ai-config/test-connection', request)
}

// ==================== 简历解析接口 ====================

export interface ParseIntentWithResumeRequest {
  /** 求职意向文本 */
  raw_input?: string
  /** 简历文件（FormData） */
  resume_file?: File
}

export interface ParseIntentWithResumeResponse {
  analysis: Record<string, any>
  extracted_resume_text?: string
  keywords?: {
    skills: string[]
    job_types: string[]
    locations: string[]
    experiences: string[]
    educations: string[]
    related_skills?: string[]
  }
  confidence?: number
}

/**
 * 解析简历和求职意向，使用LLM进行分析
 */
export const parseIntentWithResume = (data: ParseIntentWithResumeRequest) => {
  const formData = new FormData()
  if (data.raw_input) {
    formData.append('raw_input', data.raw_input)
  }
  if (data.resume_file) {
    formData.append('resume_file', data.resume_file)
  }
  return apiClient.post<ParseIntentWithResumeResponse>('/v1/parse-intent-with-resume', formData, {
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  })
}

export default apiClient