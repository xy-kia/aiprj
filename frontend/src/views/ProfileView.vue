<template>
  <div class="profile">
    <div class="container">
      <div class="header">
        <h1>个人中心</h1>
      </div>

      <div class="profile-content">
        <div class="sidebar">
          <el-menu
            :default-active="activeMenu"
            class="profile-menu"
            @select="handleMenuSelect"
          >
            <el-menu-item index="info">
              <el-icon><User /></el-icon>
              <span>个人信息</span>
            </el-menu-item>
            <el-menu-item index="history">
              <el-icon><Clock /></el-icon>
              <span>历史记录</span>
            </el-menu-item>
            <el-menu-item index="settings">
              <el-icon><Setting /></el-icon>
              <span>设置</span>
            </el-menu-item>
            <el-menu-item index="help">
              <el-icon><QuestionFilled /></el-icon>
              <span>帮助与反馈</span>
            </el-menu-item>
          </el-menu>
        </div>

        <div class="main-content">
          <!-- 个人信息 -->
          <div v-if="activeMenu === 'info'" class="info-section">
            <h2>个人信息</h2>
            <el-card class="info-card">
              <div class="avatar-section">
                <el-avatar :size="100" :src="userInfo.avatar" class="avatar" />
                <div class="avatar-actions">
                  <el-button type="primary" text @click="changeAvatar">更换头像</el-button>
                </div>
              </div>

              <el-form :model="userInfo" label-width="80px" class="info-form">
                <el-form-item label="用户名">
                  <el-input v-model="userInfo.username" />
                </el-form-item>
                <el-form-item label="邮箱">
                  <el-input v-model="userInfo.email" />
                </el-form-item>
                <el-form-item label="姓名">
                  <el-input v-model="userInfo.fullName" />
                </el-form-item>
                <el-form-item label="学校">
                  <el-input v-model="userInfo.school" />
                </el-form-item>
                <el-form-item label="专业">
                  <el-input v-model="userInfo.major" />
                </el-form-item>
                <el-form-item label="年级">
                  <el-select v-model="userInfo.grade" placeholder="请选择">
                    <el-option label="大一" value="freshman" />
                    <el-option label="大二" value="sophomore" />
                    <el-option label="大三" value="junior" />
                    <el-option label="大四" value="senior" />
                    <el-option label="研究生" value="graduate" />
                  </el-select>
                </el-form-item>
                <el-form-item label="技能标签">
                  <el-select
                    v-model="userInfo.skills"
                    multiple
                    placeholder="请选择您的技能"
                    style="width: 100%"
                  >
                    <el-option
                      v-for="skill in skillOptions"
                      :key="skill.value"
                      :label="skill.label"
                      :value="skill.value"
                    />
                  </el-select>
                </el-form-item>
                <el-form-item>
                  <el-button type="primary" @click="saveProfile">保存信息</el-button>
                  <el-button @click="resetProfile">重置</el-button>
                </el-form-item>
              </el-form>
            </el-card>
          </div>

          <!-- 历史记录 -->
          <div v-else-if="activeMenu === 'history'" class="history-section">
            <h2>历史记录</h2>
            <div class="tabs">
              <el-tabs v-model="historyTab">
                <el-tab-pane label="搜索历史" name="search">
                  <el-table :data="searchHistory" style="width: 100%">
                    <el-table-column prop="timestamp" label="时间" width="180">
                      <template #default="{ row }">
                        {{ formatDate(row.timestamp) }}
                      </template>
                    </el-table-column>
                    <el-table-column prop="keywords" label="关键词" width="200">
                      <template #default="{ row }">
                        <div class="keywords">
                          <el-tag
                            v-for="skill in row.keywords.skills.slice(0, 3)"
                            :key="skill"
                            size="small"
                          >
                            {{ skill }}
                          </el-tag>
                          <el-tag v-if="row.keywords.skills.length > 3" size="small">
                            +{{ row.keywords.skills.length - 3 }}
                          </el-tag>
                        </div>
                      </template>
                    </el-table-column>
                    <el-table-column prop="result_count" label="结果数" width="100" />
                    <el-table-column label="操作" width="120">
                      <template #default="{ row }">
                        <el-button type="text" @click="repeatSearch(row)">再次搜索</el-button>
                      </template>
                    </el-table-column>
                  </el-table>
                  <div class="clear-history">
                    <el-button @click="clearSearchHistory">清空搜索历史</el-button>
                  </div>
                </el-tab-pane>
                <el-tab-pane label="评估记录" name="evaluation">
                  <el-table :data="evaluationHistory" style="width: 100%">
                    <el-table-column prop="timestamp" label="时间" width="180">
                      <template #default="{ row }">
                        {{ formatDate(row.timestamp) }}
                      </template>
                    </el-table-column>
                    <el-table-column prop="overall_score" label="总分" width="100">
                      <template #default="{ row }">
                        <span :class="getScoreClass(row.overall_score)">
                          {{ row.overall_score.toFixed(1) }}
                        </span>
                      </template>
                    </el-table-column>
                    <el-table-column prop="question_count" label="问题数" width="100" />
                    <el-table-column prop="answered_count" label="已回答" width="100" />
                    <el-table-column label="操作" width="120">
                      <template #default="{ row }">
                        <el-button type="text" @click="viewEvaluationDetail(row)">查看详情</el-button>
                      </template>
                    </el-table-column>
                  </el-table>
                </el-tab-pane>
              </el-tabs>
            </div>
          </div>

          <!-- 设置 -->
          <div v-else-if="activeMenu === 'settings'" class="settings-section">
            <h2>设置</h2>

            <!-- AI配置 -->
            <el-card class="settings-card">
              <h3>AI配置</h3>
              <p class="settings-desc">配置大模型API密钥以使用AI功能（如面试评估、问题生成）</p>

              <el-form :model="aiConfig" label-width="120px" class="ai-config-form">
                <el-form-item label="AI提供商">
                  <el-select v-model="aiConfig.provider" @change="onProviderChange" placeholder="请选择AI提供商" style="width: 100%">
                    <el-option label="OpenAI" value="openai" />
                    <el-option label="Anthropic (Claude)" value="anthropic" />
                    <el-option label="Azure OpenAI" value="azure" />
                    <el-option label="DeepSeek (深度求索)" value="deepseek" />
                    <el-option label="Kimi (月之暗面)" value="kimi" />
                    <el-option label="通义千问 (阿里云)" value="qwen" />
                    <el-option label="自定义/反代" value="custom" />
                  </el-select>
                </el-form-item>

                <el-form-item label="API密钥">
                  <el-input
                    v-model="aiConfig.api_key"
                    type="password"
                    show-password
                    placeholder="输入API密钥"
                  />
                  <div class="help-text">密钥将安全存储，用于AI功能调用</div>
                </el-form-item>

                <el-form-item label="基础URL">
                  <el-input
                    v-model="aiConfig.base_url"
                    placeholder="API基础URL，可用于国内代理或自建服务"
                  />
                  <div class="help-text">默认: {{ providerDefaultUrls[aiConfig.provider] }}</div>
                </el-form-item>

                <el-form-item label="模型">
                  <el-select v-model="aiConfig.default_model" placeholder="请选择模型" style="width: 100%">
                    <el-option
                      v-for="model in availableModels"
                      :key="model"
                      :label="model"
                      :value="model"
                    />
                  </el-select>
                </el-form-item>

                <el-form-item label="温度">
                  <el-slider v-model="aiConfig.temperature" :min="0" :max="2" :step="0.1" />
                  <span class="slider-value">{{ aiConfig.temperature }}</span>
                </el-form-item>

                <el-form-item label="最大令牌数">
                  <el-input-number v-model="aiConfig.max_tokens" :min="100" :max="16384" />
                </el-form-item>

                <el-form-item label="启用AI功能">
                  <el-switch v-model="aiConfig.enabled" />
                </el-form-item>

                <el-form-item>
                  <el-button type="primary" :loading="testingConnection" @click="testConnection">
                    测试连接
                  </el-button>
                  <el-button type="success" :loading="savingAIConfig" @click="saveAIConfig">
                    保存配置
                  </el-button>
                </el-form-item>
              </el-form>
            </el-card>

            <el-card class="settings-card" style="margin-top: 20px;">
              <h3>通知设置</h3>
              <div class="setting-item">
                <span>邮件通知</span>
                <el-switch v-model="settings.emailNotifications" />
              </div>
              <div class="setting-item">
                <span>系统消息</span>
                <el-switch v-model="settings.systemMessages" />
              </div>

              <h3>隐私设置</h3>
              <div class="setting-item">
                <span>公开个人信息</span>
                <el-switch v-model="settings.publicProfile" />
              </div>
              <div class="setting-item">
                <span>允许数据用于改进服务</span>
                <el-switch v-model="settings.dataUsage" />
              </div>

              <h3>其他</h3>
              <div class="setting-item">
                <span>语言</span>
                <el-select v-model="settings.language" style="width: 120px">
                  <el-option label="简体中文" value="zh-CN" />
                  <el-option label="English" value="en" />
                </el-select>
              </div>
              <div class="setting-item">
                <span>主题</span>
                <el-select v-model="settings.theme" style="width: 120px">
                  <el-option label="浅色" value="light" />
                  <el-option label="深色" value="dark" />
                </el-select>
              </div>

              <div class="actions">
                <el-button type="primary" @click="saveSettings">保存设置</el-button>
                <el-button @click="resetSettings">恢复默认</el-button>
              </div>
            </el-card>
          </div>

          <!-- 帮助与反馈 -->
          <div v-else-if="activeMenu === 'help'" class="help-section">
            <h2>帮助与反馈</h2>
            <el-card class="help-card">
              <h3>常见问题</h3>
              <el-collapse>
                <el-collapse-item title="如何使用意向解析功能？" name="1">
                  <p>在首页输入您的求职意向，例如："我想找一份Python开发的实习工作，最好在北京"，系统会自动解析出关键词并搜索匹配岗位。</p>
                </el-collapse-item>
                <el-collapse-item title="如何提高面试评估分数？" name="2">
                  <p>1. 认真回答每个问题，尽量详细具体</p>
                  <p>2. 结合自身经历和项目经验</p>
                  <p>3. 注意回答的结构和逻辑性</p>
                  <p>4. 参考AI提供的改进建议</p>
                </el-collapse-item>
                <el-collapse-item title="数据安全吗？" name="3">
                  <p>我们非常重视用户数据安全，所有数据都经过加密处理，不会泄露给第三方。</p>
                </el-collapse-item>
              </el-collapse>

              <h3 style="margin-top: 30px;">问题反馈</h3>
              <el-form :model="feedback" label-width="80px">
                <el-form-item label="反馈类型">
                  <el-select v-model="feedback.type" placeholder="请选择">
                    <el-option label="功能建议" value="suggestion" />
                    <el-option label="问题反馈" value="problem" />
                    <el-option label="其他" value="other" />
                  </el-select>
                </el-form-item>
                <el-form-item label="反馈内容">
                  <el-input
                    v-model="feedback.content"
                    type="textarea"
                    :rows="4"
                    placeholder="请输入您的反馈内容..."
                  />
                </el-form-item>
                <el-form-item label="联系方式">
                  <el-input v-model="feedback.contact" placeholder="邮箱或手机号（选填）" />
                </el-form-item>
                <el-form-item>
                  <el-button type="primary" @click="submitFeedback">提交反馈</el-button>
                </el-form-item>
              </el-form>
            </el-card>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { User, Clock, Setting, QuestionFilled } from '@element-plus/icons-vue'
import { useUserStore } from '@/stores/userStore'
import { useSearchStore } from '@/stores/searchStore'
import { useEvaluationStore } from '@/stores/evaluationStore'
import { ElMessage } from 'element-plus'
import { getAIConfig, updateAIConfig, testAIConnection, type AIProviderConfig } from '@/services/api'

const userStore = useUserStore()
const searchStore = useSearchStore()
const evaluationStore = useEvaluationStore()

const activeMenu = ref('info')
const historyTab = ref('search')

const userInfo = ref({
  avatar: '',
  username: 'testuser',
  email: 'test@example.com',
  fullName: '测试用户',
  school: '某大学',
  major: '计算机科学',
  grade: 'junior',
  skills: ['Python', 'Vue.js', 'MySQL']
})

const settings = ref({
  emailNotifications: true,
  systemMessages: true,
  publicProfile: false,
  dataUsage: true,
  language: 'zh-CN',
  theme: 'light'
})

const feedback = ref({
  type: 'suggestion',
  content: '',
  contact: ''
})

const skillOptions = [
  { label: 'Python', value: 'Python' },
  { label: 'Java', value: 'Java' },
  { label: 'JavaScript', value: 'JavaScript' },
  { label: 'Vue.js', value: 'Vue.js' },
  { label: 'React', value: 'React' },
  { label: 'MySQL', value: 'MySQL' },
  { label: 'MongoDB', value: 'MongoDB' },
  { label: 'Docker', value: 'Docker' },
  { label: 'Linux', value: 'Linux' },
  { label: 'Git', value: 'Git' }
]

// AI配置
const aiConfig = ref<AIProviderConfig>({
  provider: 'openai',
  api_key: '',
  base_url: 'https://api.openai.com/v1',
  default_model: '',
  enabled: true,
  temperature: 0.7,
  max_tokens: 2000
})

const providerDefaultUrls: Record<string, string> = {
  openai: 'https://api.openai.com/v1',
  anthropic: 'https://api.anthropic.com',
  azure: 'https://{resource}.openai.azure.com',
  deepseek: 'https://api.deepseek.com/v1',
  kimi: 'https://api.moonshot.cn/v1',
  qwen: 'https://dashscope.aliyuncs.com/compatible-mode/v1',
  custom: 'https://api.example.com/v1'
}

const availableModels = ref<string[]>([])
const testingConnection = ref(false)
const savingAIConfig = ref(false)

const searchHistory = ref<any[]>([])
const evaluationHistory = ref<any[]>([])

const handleMenuSelect = (index: string) => {
  activeMenu.value = index
}

const changeAvatar = () => {
  ElMessage.info('头像上传功能开发中...')
}

const saveProfile = () => {
  ElMessage.success('个人信息已保存')
  userStore.updateUserInfo(userInfo.value)
}

const resetProfile = () => {
  // 重置为原始数据
  ElMessage.info('已重置')
}

const formatDate = (timestamp: string) => {
  return new Date(timestamp).toLocaleString('zh-CN')
}

const repeatSearch = (record: any) => {
  // 重复搜索
  searchStore.setCurrentKeywords(record.keywords)
  // 跳转到岗位搜索页面
  // router.push('/jobs')
  ElMessage.success('已应用搜索关键词')
}

const clearSearchHistory = () => {
  searchStore.clearSearchHistory()
  searchHistory.value = []
  ElMessage.success('搜索历史已清空')
}

const viewEvaluationDetail = (record: any) => {
  // 查看评估详情
  ElMessage.info('查看评估详情功能开发中...')
}

const getScoreClass = (score: number) => {
  if (score >= 90) return 'score-excellent'
  if (score >= 80) return 'score-good'
  if (score >= 70) return 'score-medium'
  if (score >= 60) return 'score-pass'
  return 'score-fail'
}

const saveSettings = () => {
  localStorage.setItem('userSettings', JSON.stringify(settings.value))
  ElMessage.success('设置已保存')
}

const resetSettings = () => {
  settings.value = {
    emailNotifications: true,
    systemMessages: true,
    publicProfile: false,
    dataUsage: true,
    language: 'zh-CN',
    theme: 'light'
  }
  ElMessage.success('已恢复默认设置')
}

// AI配置方法
const onProviderChange = (provider: string) => {
  aiConfig.value.base_url = providerDefaultUrls[provider] || providerDefaultUrls.openai
}

const testConnection = async () => {
  if (!aiConfig.value.api_key) {
    ElMessage.warning('请输入API密钥')
    return
  }

  testingConnection.value = true
  try {
    const response = await testAIConnection({
      provider: aiConfig.value.provider,
      api_key: aiConfig.value.api_key,
      base_url: aiConfig.value.base_url
    })

    if (response.data.success) {
      ElMessage.success(`连接成功: ${response.data.message}`)
      if (response.data.models && response.data.models.length > 0) {
        availableModels.value = response.data.models
        if (!aiConfig.value.default_model) {
          aiConfig.value.default_model = response.data.models[0]
        }
      }
    } else {
      ElMessage.error(`连接失败: ${response.data.message}`)
    }
  } catch (error) {
    ElMessage.error('测试连接时发生错误')
    console.error('测试连接错误:', error)
  } finally {
    testingConnection.value = false
  }
}

const saveAIConfig = async () => {
  if (!aiConfig.value.api_key) {
    ElMessage.warning('请输入API密钥')
    return
  }
  if (!aiConfig.value.default_model) {
    ElMessage.warning('请选择模型')
    return
  }

  savingAIConfig.value = true
  try {
    await updateAIConfig(aiConfig.value)
    ElMessage.success('AI配置已保存')
  } catch (error) {
    ElMessage.error('保存配置失败')
    console.error('保存配置错误:', error)
  } finally {
    savingAIConfig.value = false
  }
}

const loadAIConfig = async () => {
  try {
    const response = await getAIConfig()
    const config = response.data
    aiConfig.value.provider = config.provider
    aiConfig.value.base_url = config.base_url
    aiConfig.value.default_model = config.default_model
    aiConfig.value.enabled = config.enabled
    aiConfig.value.temperature = config.temperature
    aiConfig.value.max_tokens = config.max_tokens
    // api_key 出于安全原因后端不返回，保持为空
    if (config.default_model) {
      availableModels.value = [config.default_model]
    }
  } catch (error) {
    console.error('加载AI配置失败:', error)
  }
}

const submitFeedback = () => {
  if (!feedback.value.content.trim()) {
    ElMessage.warning('请输入反馈内容')
    return
  }

  // 这里应该调用API提交反馈
  console.log('Feedback submitted:', feedback.value)
  ElMessage.success('感谢您的反馈！')

  // 清空表单
  feedback.value = {
    type: 'suggestion',
    content: '',
    contact: ''
  }
}

onMounted(() => {
  // 从存储中恢复数据
  const storedSettings = localStorage.getItem('userSettings')
  if (storedSettings) {
    settings.value = JSON.parse(storedSettings)
  }

  searchHistory.value = searchStore.searchHistory
  evaluationHistory.value = evaluationStore.evaluationHistory

  // 加载AI配置
  loadAIConfig()
})
</script>

<style scoped>
.profile {
  padding: 20px;
  max-width: 1400px;
  margin: 0 auto;
}

.container {
  background: white;
  border-radius: 8px;
  padding: 30px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
}

.header {
  margin-bottom: 30px;
}

.header h1 {
  color: #409eff;
  text-align: center;
}

.profile-content {
  display: flex;
  gap: 30px;
}

.sidebar {
  width: 240px;
  flex-shrink: 0;
}

.profile-menu {
  border-right: none;
  border-radius: 8px;
  overflow: hidden;
}

.main-content {
  flex: 1;
  min-width: 0;
}

.info-section h2,
.history-section h2,
.settings-section h2,
.help-section h2 {
  margin-bottom: 20px;
  color: #333;
}

.info-card {
  padding: 30px;
}

.avatar-section {
  display: flex;
  align-items: center;
  gap: 20px;
  margin-bottom: 30px;
}

.avatar {
  border: 2px solid #409eff;
}

.info-form {
  max-width: 600px;
}

.keywords {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
}

.clear-history {
  margin-top: 20px;
  text-align: center;
}

.settings-card {
  padding: 30px;
  max-width: 600px;
}

.settings-card h3 {
  margin: 25px 0 15px 0;
  color: #333;
}

.settings-card h3:first-child {
  margin-top: 0;
}

.setting-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 15px 0;
  border-bottom: 1px solid #eee;
}

.setting-item:last-child {
  border-bottom: none;
}

.actions {
  margin-top: 30px;
}

.help-card {
  padding: 30px;
}

.help-card h3 {
  margin-bottom: 20px;
  color: #333;
}

.score-excellent { color: #67C23A; font-weight: bold; }
.score-good { color: #E6A23C; font-weight: bold; }
.score-medium { color: #409EFF; font-weight: bold; }
.score-pass { color: #909399; font-weight: bold; }
.score-fail { color: #F56C6C; font-weight: bold; }
</style>