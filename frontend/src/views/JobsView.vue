<template>
  <div class="jobs">
    <div class="container">
      <div class="header">
        <h1>匹配岗位推荐</h1>
        <p>根据您的意向，为您推荐以下实习岗位</p>
      </div>

      <!-- 关键词展示区域 -->
      <div v-if="parsedIntent" class="keywords-display">
        <el-alert title="当前搜索关键词" type="info" :closable="false" class="keywords-alert">
          <div class="keywords-tags">
            <div v-if="parsedIntent.keywords.skills && parsedIntent.keywords.skills.length > 0" class="keyword-group">
              <span class="keyword-label">技能：</span>
              <el-tag v-for="skill in parsedIntent.keywords.skills" :key="skill" size="small" type="success">
                {{ skill }}
              </el-tag>
            </div>
            <div v-if="parsedIntent.keywords.job_types && parsedIntent.keywords.job_types.length > 0" class="keyword-group">
              <span class="keyword-label">岗位：</span>
              <el-tag v-for="type in parsedIntent.keywords.job_types" :key="type" size="small">
                {{ type }}
              </el-tag>
            </div>
            <div v-if="parsedIntent.keywords.locations && parsedIntent.keywords.locations.length > 0" class="keyword-group">
              <span class="keyword-label">地点：</span>
              <el-tag v-for="location in parsedIntent.keywords.locations" :key="location" size="small" type="info">
                {{ location }}
              </el-tag>
            </div>
            <div class="keyword-group">
              <el-button type="text" @click="parsedIntent = null; resetFilters()">使用自定义筛选</el-button>
            </div>
          </div>
        </el-alert>
      </div>

      <div class="filters">
        <el-row :gutter="20">
          <el-col :span="6">
            <el-input v-model="filters.keyword" :disabled="parsedIntent" placeholder="搜索岗位或公司" />
          </el-col>
          <el-col :span="6">
            <el-select v-model="filters.location" :disabled="parsedIntent" placeholder="选择地点" clearable>
              <el-option label="北京" value="北京" />
              <el-option label="上海" value="上海" />
              <el-option label="深圳" value="深圳" />
              <el-option label="广州" value="广州" />
              <el-option label="杭州" value="杭州" />
              <el-option label="成都" value="成都" />
            </el-select>
          </el-col>
          <el-col :span="6">
            <el-select v-model="filters.jobType" :disabled="parsedIntent" placeholder="岗位类型" clearable>
              <el-option label="实习" value="实习" />
              <el-option label="校招" value="校招" />
              <el-option label="全职" value="全职" />
              <el-option label="兼职" value="兼职" />
            </el-select>
          </el-col>
          <el-col :span="6">
            <el-button type="primary" @click="search">搜索</el-button>
            <el-button @click="resetFilters">重置</el-button>
          </el-col>
        </el-row>
      </div>

      <div class="job-list">
        <div v-if="loading" class="loading">
          <el-skeleton :rows="5" animated />
        </div>

        <div v-else-if="jobs.length === 0" class="empty">
          <el-empty description="暂无匹配的岗位" />
        </div>

        <div v-else>
          <el-card v-for="job in jobs" :key="job.id" class="job-card">
            <div class="job-header">
              <h3>{{ job.title }}</h3>
              <el-tag :type="job.source === 'boss' ? 'success' : 'info'">
                {{ job.source === 'boss' ? 'BOSS直聘' : '智联招聘' }}
              </el-tag>
            </div>

            <div class="job-info">
              <div class="info-item">
                <span class="label">公司：</span>
                <span class="value">{{ job.company }}</span>
              </div>
              <div class="info-item">
                <span class="label">地点：</span>
                <span class="value">{{ job.location }}</span>
              </div>
              <div class="info-item">
                <span class="label">薪资：</span>
                <span class="value salary">{{ job.salary }}</span>
              </div>
              <div class="info-item">
                <span class="label">经验：</span>
                <span class="value">{{ job.experience }}</span>
              </div>
              <div class="info-item">
                <span class="label">学历：</span>
                <span class="value">{{ job.education }}</span>
              </div>
            </div>

            <div class="job-skills">
              <span class="label">技能要求：</span>
              <div class="skills">
                <el-tag
                  v-for="skill in job.skills.slice(0, 5)"
                  :key="skill"
                  size="small"
                  type="info"
                >
                  {{ skill }}
                </el-tag>
                <el-tag v-if="job.skills.length > 5" size="small">+{{ job.skills.length - 5 }}</el-tag>
              </div>
            </div>

            <div class="job-actions">
              <el-button type="primary" @click="viewDetails(job)">查看详情</el-button>
              <el-button @click="practiceInterview(job)">面试练习</el-button>
              <el-button type="text" @click="openExternal(job.url)">原平台查看</el-button>
            </div>
          </el-card>

          <div class="pagination">
            <el-pagination
              v-model:current-page="pagination.current"
              v-model:page-size="pagination.size"
              :total="pagination.total"
              :page-sizes="[10, 20, 50]"
              layout="total, sizes, prev, pager, next, jumper"
              @size-change="handleSizeChange"
              @current-change="handleCurrentChange"
            />
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { searchJobs, type SearchJobsRequest } from '@/services/api'
import { ElMessage } from 'element-plus'

const router = useRouter()

// 从localStorage读取解析结果
const parsedIntent = ref<any>(null)

const filters = ref({
  keyword: '',
  location: '',
  jobType: ''
})

const jobs = ref<any[]>([])
const loading = ref(false)

const pagination = ref({
  current: 1,
  size: 10,
  total: 0
})

const search = async () => {
  loading.value = true
  try {
    // 构建搜索请求参数
    let searchParams: SearchJobsRequest = {
      keywords: {
        skills: [],
        job_types: [],
        locations: [],
        experiences: [],
        educations: []
      }
    }

    // 如果有解析结果，使用解析结果
    if (parsedIntent.value && parsedIntent.value.keywords) {
      const keywords = parsedIntent.value.keywords
      searchParams.keywords = {
        skills: keywords.skills || [],
        job_types: keywords.job_types || [],
        locations: keywords.locations || [],
        experiences: keywords.experiences || [],
        educations: keywords.educations || []
      }

      // 设置筛选器显示
      if (keywords.locations && keywords.locations.length > 0) {
        filters.value.location = keywords.locations[0]
      }
      if (keywords.job_types && keywords.job_types.length > 0) {
        filters.value.jobType = keywords.job_types[0]
      }
      if (keywords.skills && keywords.skills.length > 0) {
        filters.value.keyword = keywords.skills.join(' ')
      }
    } else {
      // 如果没有解析结果，使用手动输入的筛选条件
      searchParams.keywords = {
        skills: filters.value.keyword ? [filters.value.keyword] : [],
        job_types: filters.value.jobType ? [filters.value.jobType] : [],
        locations: filters.value.location ? [filters.value.location] : [],
        experiences: [],
        educations: []
      }
    }

    // 添加分页参数
    searchParams.page = pagination.value.current
    searchParams.page_size = pagination.value.size

    console.log('搜索参数:', searchParams)

    // 调用真实API
    const response = await searchJobs(searchParams)
    jobs.value = response.data.jobs
    pagination.value.total = response.data.total

    ElMessage.success(`找到 ${response.data.total} 个匹配岗位`)
  } catch (error: any) {
    console.error('搜索失败:', error)

    // 如果API调用失败，使用模拟数据作为后备
    ElMessage.warning('API调用失败，使用模拟数据')
    jobs.value = [
      {
        id: 1,
        source: 'boss',
        title: 'Python开发实习生',
        company: '某科技公司',
        location: '北京',
        salary: '4-6K',
        experience: '无经验',
        education: '本科',
        skills: ['Python', 'Django', 'MySQL', 'Linux'],
        url: 'https://www.zhipin.com/job/1'
      },
      {
        id: 2,
        source: 'zhaopin',
        title: '前端开发实习生',
        company: '某互联网公司',
        location: '上海',
        salary: '5-7K',
        experience: '1年以下',
        education: '本科',
        skills: ['Vue.js', 'JavaScript', 'HTML5', 'CSS3'],
        url: 'https://www.zhaopin.com/job/2'
      }
    ]
    pagination.value.total = 2
  } finally {
    loading.value = false
  }
}

const resetFilters = () => {
  filters.value = {
    keyword: '',
    location: '',
    jobType: ''
  }
  parsedIntent.value = null
  localStorage.removeItem('parsedIntent')
  search()
}

const viewDetails = (job: any) => {
  // 查看岗位详情
  console.log('View details:', job)
}

const practiceInterview = (job: any) => {
  // 进入面试练习页面
  localStorage.setItem('selectedJob', JSON.stringify(job))
  router.push('/practice')
}

const openExternal = (url: string) => {
  window.open(url, '_blank')
}

const handleSizeChange = (size: number) => {
  pagination.value.size = size
  search()
}

const handleCurrentChange = (page: number) => {
  pagination.value.current = page
  search()
}

// 读取解析结果
const loadParsedIntent = () => {
  try {
    const stored = localStorage.getItem('parsedIntent')
    if (stored) {
      parsedIntent.value = JSON.parse(stored)
      console.log('加载解析结果:', parsedIntent.value)
    }
  } catch (error) {
    console.error('读取解析结果失败:', error)
  }
}

onMounted(() => {
  loadParsedIntent()
  search()
})
</script>

<style scoped>
.jobs {
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

.keywords-display {
  margin-bottom: 20px;
}

.keywords-alert {
  margin-bottom: 0;
}

.keywords-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
}

.keyword-group {
  display: flex;
  align-items: center;
  gap: 5px;
  flex-wrap: wrap;
}

.keyword-label {
  font-weight: bold;
  color: #606266;
  font-size: 13px;
}

.filters {
  margin-bottom: 30px;
}

.job-list {
  min-height: 500px;
}

.loading {
  padding: 40px 0;
}

.empty {
  padding: 60px 0;
}

.job-card {
  margin-bottom: 20px;
  transition: transform 0.3s;
}

.job-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
}

.job-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
}

.job-header h3 {
  margin: 0;
  color: #333;
}

.job-info {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 10px;
  margin-bottom: 15px;
}

.info-item {
  display: flex;
  align-items: center;
}

.label {
  font-weight: bold;
  color: #666;
  min-width: 60px;
}

.value {
  color: #333;
}

.salary {
  color: #f56c6c;
  font-weight: bold;
}

.job-skills {
  margin-bottom: 15px;
}

.skills {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 5px;
}

.job-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

.pagination {
  display: flex;
  justify-content: center;
  margin-top: 30px;
}
</style>