import axios from 'axios'
import type { AxiosInstance, AxiosRequestConfig, AxiosResponse } from 'axios'
import { ElMessage } from 'element-plus'

// 创建axios实例
const apiClient: AxiosInstance = axios.create({
  baseURL: '/api',
  timeout: 10000,
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

// AI配置相关API接口

export interface AIProviderConfig {
  /** AI提供商：openai, anthropic, azure, custom */
  provider: string
  /** API密钥（前端传输时需加密，后端存储时加密） */
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

export interface ModelInfo {
  id: string
  object: string
  created?: number
  owned_by?: string
}

export interface ModelListResponse {
  models: ModelInfo[]
  provider: string
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

/**
 * 获取用户配置下可用的模型列表
 */
export const getAvailableModels = () => {
  return apiClient.get<ModelListResponse>('/v1/ai-config/models')
}

// 系统配置相关API（预留）
export interface SystemConfig {
  crawler_delay_min: number
  crawler_delay_max: number
  crawler_max_retries: number
  crawler_timeout: number
  crawler_use_proxy: boolean
  crawler_proxy_list: string[]
  evaluation_pass_score: number
  evaluation_excellent_score: number
  evaluation_need_improvement_score: number
  evaluation_auto_evaluation_delay: number
  evaluation_detailed_feedback: boolean
  system_user_registration: boolean
  system_intent_parsing: boolean
  system_job_search: boolean
  system_interview_practice: boolean
  system_ai_evaluation: boolean
  system_maintenance_mode: boolean
}

export const getSystemConfig = () => {
  return apiClient.get<SystemConfig>('/v1/system-config')
}

export const updateSystemConfig = (config: SystemConfig) => {
  return apiClient.post<SystemConfig>('/v1/system-config', config)
}

export default apiClient