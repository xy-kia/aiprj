<template>
  <div class="home">
    <div class="container">
      <h1>学生求职AI助手</h1>
      <p class="subtitle">智能解析求职意向，推荐匹配岗位，提供面试练习</p>

      <div class="input-section">
        <el-input
          v-model="userInput"
          type="textarea"
          :rows="4"
          placeholder="请输入您的求职意向，例如：我想找一份Python开发的实习工作，最好在北京..."
          resize="none"
        />

        <!-- 简历上传 -->
        <div class="upload-section">
          <div class="upload-header">
            <span class="upload-label">上传简历（PDF格式）</span>
            <span class="upload-hint">可选，与求职意向一起分析</span>
          </div>
          <el-upload
            class="upload-demo"
            :auto-upload="false"
            :show-file-list="false"
            :on-change="handleFileUpload"
            accept=".pdf,application/pdf"
            :file-list="resumeFile ? [{ name: resumeFile.name, size: resumeFile.size }] : []"
          >
            <el-button type="primary" plain>
              <Upload class="el-icon--right" />
              选择文件
            </el-button>
            <template #tip>
              <div class="el-upload__tip">
                仅支持PDF文件，大小不超过10MB
              </div>
            </template>
          </el-upload>
          <div v-if="resumeFile" class="file-info">
            <div class="file-name">
              <Document style="width: 16px; height: 16px; margin-right: 8px;" />
              {{ resumeFile.name }}
              <span class="file-size">({{ (resumeFile.size / 1024 / 1024).toFixed(2) }} MB)</span>
            </div>
            <el-button type="danger" text @click="removeResumeFile">
              移除
            </el-button>
          </div>
        </div>

        <div class="actions">
          <el-button type="primary" size="large" :loading="loading" @click="parseUserIntent">
            智能解析
          </el-button>
          <el-button size="large" @click="clearInput">
            清空
          </el-button>
        </div>
      </div>

      <!-- 解析结果显示 -->
      <div v-if="parsedResult" class="result-section">
        <h3>解析结果</h3>
        <el-card class="result-card">
          <div class="result-grid">
            <div class="result-item">
              <span class="label">技能要求：</span>
              <div class="tags">
                <el-tag v-for="skill in parsedResult.keywords.skills" :key="skill" type="success">
                  {{ skill }}
                </el-tag>
              </div>
            </div>
            <div class="result-item">
              <span class="label">岗位类型：</span>
              <div class="tags">
                <el-tag v-for="type in parsedResult.keywords.job_types" :key="type">
                  {{ type }}
                </el-tag>
              </div>
            </div>
            <div class="result-item">
              <span class="label">工作地点：</span>
              <div class="tags">
                <el-tag v-for="location in parsedResult.keywords.locations" :key="location" type="info">
                  {{ location }}
                </el-tag>
              </div>
            </div>
            <div class="result-item">
              <span class="label">经验要求：</span>
              <div class="tags">
                <el-tag v-for="exp in parsedResult.keywords.experiences" :key="exp" type="warning">
                  {{ exp }}
                </el-tag>
              </div>
            </div>
            <div class="result-item">
              <span class="label">学历要求：</span>
              <div class="tags">
                <el-tag v-for="edu in parsedResult.keywords.educations" :key="edu" type="danger">
                  {{ edu }}
                </el-tag>
              </div>
            </div>
          </div>
          <div class="confidence">
            解析置信度：<el-progress :percentage="parsedResult.confidence * 100" :show-text="false" />
            <span class="confidence-value">{{ (parsedResult.confidence * 100).toFixed(1) }}%</span>
          </div>
          <div class="action-buttons">
            <el-button type="primary" @click="searchJobs">
              搜索匹配岗位
            </el-button>
          </div>
        </el-card>
      </div>

      <!-- 功能引导 -->
      <div class="features">
        <h3>核心功能</h3>
        <div class="feature-grid">
          <el-card class="feature-card">
            <div class="feature-icon">
              <Search style="width: 48px; height: 48px;" />
            </div>
            <h4>智能岗位搜索</h4>
            <p>基于您的意向，从各大招聘平台智能匹配适合的实习岗位</p>
          </el-card>
          <el-card class="feature-card">
            <div class="feature-icon">
              <ChatDotRound style="width: 48px; height: 48px;" />
            </div>
            <h4>面试问题生成</h4>
            <p>根据目标岗位，生成专业面试问题，帮助您提前准备</p>
          </el-card>
          <el-card class="feature-card">
            <div class="feature-icon">
              <Finished style="width: 48px; height: 48px;" />
            </div>
            <h4>回答智能评估</h4>
            <p>AI评估您的回答，提供改进建议，提升面试成功率</p>
          </el-card>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { Search, ChatDotRound, Finished, Upload, Document } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { parseIntent, parseIntentWithResume } from '@/services/api'

const router = useRouter()

const userInput = ref('')
const resumeFile = ref<File | null>(null)
const loading = ref(false)
const parsedResult = ref<any>(null)

const clearInput = () => {
  userInput.value = ''
  resumeFile.value = null
  parsedResult.value = null
}

const handleFileUpload = (uploadFile: any) => {
  const file = uploadFile.raw
  if (file.type !== 'application/pdf') {
    ElMessage.error('仅支持PDF格式')
    return false
  }
  if (file.size > 10 * 1024 * 1024) { // 10MB
    ElMessage.error('文件大小不能超过10MB')
    return false
  }
  resumeFile.value = file
  return true
}

const removeResumeFile = () => {
  resumeFile.value = null
}

const parseUserIntent = async () => {
  if (!userInput.value.trim() && !resumeFile.value) {
    ElMessage.warning('请输入求职意向或上传简历文件')
    return
  }

  loading.value = true
  try {
    let response
    if (resumeFile.value) {
      // 使用新的简历解析API
      response = await parseIntentWithResume({
        raw_input: userInput.value.trim() || undefined,
        resume_file: resumeFile.value
      })
    } else {
      // 使用原有的意向解析API
      response = await parseIntent({ raw_input: userInput.value })
    }
    parsedResult.value = response.data
    ElMessage.success('解析成功')
  } catch (error) {
    ElMessage.error('解析失败，请重试')
    console.error(error)
  } finally {
    loading.value = false
  }
}

const searchJobs = () => {
  if (parsedResult.value) {
    // 存储解析结果到状态管理或本地存储
    localStorage.setItem('parsedIntent', JSON.stringify(parsedResult.value))
    router.push('/jobs')
  }
}
</script>

<style scoped>
.home {
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
}

.container {
  background: white;
  border-radius: 8px;
  padding: 40px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
}

h1 {
  text-align: center;
  color: #409eff;
  margin-bottom: 10px;
}

.subtitle {
  text-align: center;
  color: #666;
  margin-bottom: 40px;
  font-size: 18px;
}

.input-section {
  margin-bottom: 40px;
}

.actions {
  margin-top: 20px;
  display: flex;
  justify-content: center;
  gap: 20px;
}

.result-section {
  margin-top: 40px;
}

.result-card {
  margin-top: 20px;
}

.result-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 20px;
  margin-bottom: 20px;
}

.result-item {
  display: flex;
  flex-direction: column;
}

.label {
  font-weight: bold;
  margin-bottom: 8px;
  color: #333;
}

.tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.confidence {
  margin: 20px 0;
  display: flex;
  align-items: center;
  gap: 10px;
}

.confidence-value {
  font-weight: bold;
  color: #409eff;
}

.action-buttons {
  text-align: center;
}

.features {
  margin-top: 60px;
}

.feature-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 30px;
  margin-top: 30px;
}

.feature-card {
  text-align: center;
  padding: 30px 20px;
}

.feature-icon {
  color: #409eff;
  margin-bottom: 20px;
}

.feature-card h4 {
  margin-bottom: 15px;
  color: #333;
}

.feature-card p {
  color: #666;
  line-height: 1.6;
}

/* 上传区域样式 */
.upload-section {
  margin-top: 20px;
  padding: 16px;
  border: 1px dashed #dcdfe6;
  border-radius: 4px;
  background-color: #fafafa;
}

.upload-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.upload-label {
  font-weight: bold;
  color: #333;
}

.upload-hint {
  font-size: 12px;
  color: #999;
}

.upload-demo {
  margin-bottom: 12px;
}

.file-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px;
  background-color: white;
  border: 1px solid #e4e7ed;
  border-radius: 4px;
}

.file-name {
  display: flex;
  align-items: center;
  color: #333;
}

.file-size {
  margin-left: 8px;
  color: #999;
  font-size: 12px;
}
</style>