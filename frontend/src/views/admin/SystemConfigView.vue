<template>
  <div class="system-config">
    <div class="header">
      <h1>系统配置</h1>
      <p>参数调整、阈值配置、开关控制</p>
    </div>

    <div class="config-sections">
      <el-card class="config-section">
        <template #header>
          <h3>LLM API配置</h3>
        </template>
        <el-form :model="llmConfig" label-width="120px">
          <el-form-item label="AI提供商">
            <el-select v-model="llmConfig.provider" @change="onProviderChange(llmConfig.provider)" placeholder="请选择AI提供商">
              <el-option
                v-for="option in providerOptions"
                :key="option.value"
                :label="option.label"
                :value="option.value"
              />
            </el-select>
          </el-form-item>
          <el-form-item label="API密钥">
            <el-input v-model="llmConfig.api_key" type="password" show-password placeholder="输入API密钥" />
            <div class="help-text">密钥将加密存储</div>
          </el-form-item>
          <el-form-item label="基础URL">
            <el-input v-model="llmConfig.base_url" placeholder="API基础URL，可用于国内代理或自建服务" />
            <div class="help-text">{{ providerDefaultUrls[llmConfig.provider] }}（{{ llmConfig.provider }}默认）</div>
          </el-form-item>
          <el-form-item label="模型">
            <el-select v-model="llmConfig.default_model" filterable placeholder="请选择模型，可先测试连接获取模型列表">
              <el-option
                v-for="option in modelOptions"
                :key="option.value"
                :label="option.label"
                :value="option.value"
              />
              <el-option v-if="modelOptions.length === 0" label="无可用模型，请先测试连接" value="" disabled />
            </el-select>
            <el-button type="primary" :loading="testingConnection" @click="testConnection" style="margin-left: 10px;">
              测试连接
            </el-button>
          </el-form-item>
          <el-form-item label="温度">
            <el-slider v-model="llmConfig.temperature" :min="0" :max="2" :step="0.1" />
            <span class="slider-value">{{ llmConfig.temperature }}</span>
          </el-form-item>
          <el-form-item label="最大令牌数">
            <el-input-number v-model="llmConfig.max_tokens" :min="100" :max="16384" />
            <span class="help-text">范围：100 - 16384</span>
          </el-form-item>
          <el-form-item label="启用配置">
            <el-switch v-model="llmConfig.enabled" />
            <span class="help-text">启用此AI配置</span>
          </el-form-item>
        </el-form>
      </el-card>

      <el-card class="config-section">
        <template #header>
          <h3>爬虫配置</h3>
        </template>
        <el-form :model="crawlerConfig" label-width="120px">
          <el-form-item label="延迟范围(秒)">
            <div class="range-input">
              <el-input-number v-model="crawlerConfig.delay_min" :min="0.5" :max="10" :step="0.5" />
              <span class="separator">-</span>
              <el-input-number v-model="crawlerConfig.delay_max" :min="1" :max="30" :step="0.5" />
            </div>
          </el-form-item>
          <el-form-item label="最大重试次数">
            <el-input-number v-model="crawlerConfig.max_retries" :min="1" :max="10" />
          </el-form-item>
          <el-form-item label="超时时间(秒)">
            <el-input-number v-model="crawlerConfig.timeout" :min="10" :max="120" />
          </el-form-item>
          <el-form-item label="启用代理">
            <el-switch v-model="crawlerConfig.use_proxy" />
          </el-form-item>
          <el-form-item v-if="crawlerConfig.use_proxy" label="代理列表">
            <el-tag
              v-for="proxy in crawlerConfig.proxy_list"
              :key="proxy"
              closable
              @close="removeProxy(proxy)"
            >
              {{ proxy }}
            </el-tag>
            <el-input
              v-model="newProxy"
              placeholder="输入代理地址"
              style="width: 200px; margin-left: 10px;"
              @keyup.enter="addProxy"
            >
              <template #append>
                <el-button @click="addProxy">添加</el-button>
              </template>
            </el-input>
          </el-form-item>
        </el-form>
      </el-card>

      <el-card class="config-section">
        <template #header>
          <h3>评估阈值配置</h3>
        </template>
        <el-form :model="evaluationConfig" label-width="120px">
          <el-form-item label="通过分数">
            <el-input-number v-model="evaluationConfig.pass_score" :min="0" :max="100" />
            <span class="help-text">≥ 此分数为通过</span>
          </el-form-item>
          <el-form-item label="优秀分数">
            <el-input-number v-model="evaluationConfig.excellent_score" :min="0" :max="100" />
            <span class="help-text">≥ 此分数为优秀</span>
          </el-form-item>
          <el-form-item label="待提升分数">
            <el-input-number v-model="evaluationConfig.need_improvement_score" :min="0" :max="100" />
            <span class="help-text">≤ 此分数需要重点提升</span>
          </el-form-item>
          <el-form-item label="自动评估延迟">
            <el-input-number v-model="evaluationConfig.auto_evaluation_delay" :min="0" :max="60" />
            <span class="help-text">秒，0表示立即评估</span>
          </el-form-item>
          <el-form-item label="启用详细反馈">
            <el-switch v-model="evaluationConfig.detailed_feedback" />
          </el-form-item>
        </el-form>
      </el-card>

      <el-card class="config-section">
        <template #header>
          <h3>系统开关</h3>
        </template>
        <el-form label-width="120px">
          <el-form-item label="用户注册">
            <el-switch v-model="systemSwitches.user_registration" />
          </el-form-item>
          <el-form-item label="意向解析">
            <el-switch v-model="systemSwitches.intent_parsing" />
          </el-form-item>
          <el-form-item label="岗位搜索">
            <el-switch v-model="systemSwitches.job_search" />
          </el-form-item>
          <el-form-item label="面试练习">
            <el-switch v-model="systemSwitches.interview_practice" />
          </el-form-item>
          <el-form-item label="AI评估">
            <el-switch v-model="systemSwitches.ai_evaluation" />
          </el-form-item>
          <el-form-item label="维护模式">
            <el-switch v-model="systemSwitches.maintenance_mode" />
          </el-form-item>
        </el-form>
      </el-card>
    </div>

    <div class="actions">
      <el-button type="primary" @click="saveConfig" :loading="savingConfig">保存配置</el-button>
      <el-button @click="resetConfig">恢复默认</el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import type { AIProviderConfig, AIConfigResponse, TestConnectionRequest } from '@/services/api'
import { getAIConfig, updateAIConfig, testAIConnection } from '@/services/api'

// AI提供商选项
const providerOptions = [
  { label: 'OpenAI', value: 'openai' },
  { label: 'Anthropic', value: 'anthropic' },
  { label: 'Azure OpenAI', value: 'azure' },
  { label: 'Kimi (Moonshot)', value: 'kimi' },
  { label: 'DeepSeek', value: 'deepseek' },
  { label: '自定义/反代', value: 'custom' }
]

// 提供商默认基础URL映射
const providerDefaultUrls: Record<string, string> = {
  openai: 'https://api.openai.com/v1',
  anthropic: 'https://api.anthropic.com',
  azure: 'https://{resource}.openai.azure.com/openai/deployments/{deployment}',
  kimi: 'https://api.moonshot.cn/v1',
  deepseek: 'https://api.deepseek.com/v1',
  custom: 'https://api.example.com/v1'
}

// AI配置
const llmConfig = ref<AIProviderConfig>({
  provider: 'openai',
  api_key: '',
  base_url: 'https://api.openai.com/v1',
  default_model: '',
  enabled: true,
  temperature: 0.7,
  max_tokens: 2000
})

// 动态模型列表
const modelOptions = ref<Array<{ label: string, value: string }>>([])
// 测试连接加载状态
const testingConnection = ref(false)
// 保存配置加载状态
const savingConfig = ref(false)

// 其他配置（保持不变）
const crawlerConfig = ref({
  delay_min: 1.0,
  delay_max: 5.0,
  max_retries: 3,
  timeout: 30,
  use_proxy: false,
  proxy_list: ['http://proxy1.example.com', 'http://proxy2.example.com']
})

const evaluationConfig = ref({
  pass_score: 60,
  excellent_score: 80,
  need_improvement_score: 50,
  auto_evaluation_delay: 0,
  detailed_feedback: true
})

const systemSwitches = ref({
  user_registration: true,
  intent_parsing: true,
  job_search: true,
  interview_practice: true,
  ai_evaluation: true,
  maintenance_mode: false
})

const newProxy = ref('')

// 加载现有配置
const loadConfig = async () => {
  try {
    const response = await getAIConfig()
    const config = response.data
    llmConfig.value = {
      provider: config.provider,
      api_key: config.api_key ? '********' : '', // 不显示真实密钥，只显示占位符
      base_url: config.base_url,
      default_model: config.default_model,
      enabled: config.enabled,
      temperature: config.temperature,
      max_tokens: config.max_tokens
    }
    // 如果已有模型，可以尝试加载模型列表
    if (config.default_model) {
      // 可以添加一个静态选项
      modelOptions.value = [{ label: config.default_model, value: config.default_model }]
    }
  } catch (error) {
    console.error('加载配置失败:', error)
    // 使用默认配置
  }
}

// 提供商变化时更新基础URL
const onProviderChange = (provider: string) => {
  // 如果当前基础URL是默认的，则更新为新提供商的默认URL
  const currentUrl = llmConfig.value.base_url
  const defaultUrl = providerDefaultUrls[provider]
  // 如果当前URL是某个提供商的默认URL，则更新为新提供商的默认URL
  const isDefaultUrl = Object.values(providerDefaultUrls).includes(currentUrl)
  if (isDefaultUrl || !currentUrl || currentUrl === '') {
    llmConfig.value.base_url = defaultUrl
  }
}

// 测试连接
const testConnection = async () => {
  if (!llmConfig.value.api_key) {
    ElMessage.warning('请输入API密钥')
    return
  }

  testingConnection.value = true
  try {
    const request: TestConnectionRequest = {
      provider: llmConfig.value.provider,
      api_key: llmConfig.value.api_key === '********' ? '' : llmConfig.value.api_key, // 如果显示占位符，则发送空密钥
      base_url: llmConfig.value.base_url
    }

    // 如果API密钥是占位符，需要从后端获取真实密钥，这里简化处理：要求用户重新输入
    if (request.api_key === '') {
      ElMessage.warning('请重新输入API密钥进行测试')
      testingConnection.value = false
      return
    }

    const response = await testAIConnection(request)

    if (response.data.success) {
      ElMessage.success(`连接成功: ${response.data.message}`)
      // 更新模型列表
      if (response.data.models && response.data.models.length > 0) {
        modelOptions.value = response.data.models.map(model => ({
          label: model,
          value: model
        }))
        // 如果当前没有选择模型，则选择第一个
        if (!llmConfig.value.default_model) {
          llmConfig.value.default_model = response.data.models[0]
        }
      }
    } else {
      ElMessage.error(`连接失败: ${response.data.message}`)
      modelOptions.value = []
    }
  } catch (error) {
    ElMessage.error('测试连接时发生错误')
    console.error('测试连接错误:', error)
  } finally {
    testingConnection.value = false
  }
}

// 保存配置
const saveConfig = async () => {
  if (!llmConfig.value.api_key || llmConfig.value.api_key === '********') {
    ElMessage.warning('请输入API密钥')
    return
  }
  if (!llmConfig.value.default_model) {
    ElMessage.warning('请选择模型')
    return
  }

  savingConfig.value = true
  try {
    // 如果API密钥是占位符，表示用户未修改密钥，我们需要从后端获取原始密钥
    // 但为了简化，我们要求用户必须输入密钥
    // 在实际应用中，应该在后端处理密钥更新逻辑
    await updateAIConfig(llmConfig.value)
    ElMessage.success('AI配置已保存')
  } catch (error) {
    ElMessage.error('保存配置失败')
    console.error('保存配置错误:', error)
  } finally {
    savingConfig.value = false
  }
}

// 恢复默认配置
const resetConfig = () => {
  llmConfig.value = {
    provider: 'openai',
    api_key: '',
    base_url: providerDefaultUrls.openai,
    default_model: '',
    enabled: true,
    temperature: 0.7,
    max_tokens: 2000
  }
  modelOptions.value = []
  ElMessage.info('已恢复默认AI配置')
}

// 其他辅助函数
const addProxy = () => {
  if (newProxy.value.trim()) {
    crawlerConfig.value.proxy_list.push(newProxy.value.trim())
    newProxy.value = ''
  }
}

const removeProxy = (proxy: string) => {
  crawlerConfig.value.proxy_list = crawlerConfig.value.proxy_list.filter(p => p !== proxy)
}

// 组件挂载时加载配置
onMounted(() => {
  loadConfig()
})
</script>

<style scoped>
.system-config {
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

.config-sections {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(500px, 1fr));
  gap: 20px;
  margin-bottom: 30px;
}

.config-section h3 {
  margin: 0;
  color: #333;
}

.range-input {
  display: flex;
  align-items: center;
  gap: 10px;
}

.separator {
  color: #909399;
  margin: 0 8px;
}

.slider-value {
  display: inline-block;
  width: 40px;
  text-align: center;
  margin-left: 10px;
  font-weight: bold;
}

.help-text {
  margin-left: 10px;
  color: #909399;
  font-size: 12px;
}

.actions {
  display: flex;
  justify-content: center;
  gap: 20px;
}
</style>