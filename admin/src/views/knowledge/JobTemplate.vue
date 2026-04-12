<template>
  <div class="job-template">
    <div class="header">
      <h1>岗位模板管理</h1>
      <p>创建和管理岗位模板，用于智能匹配和问题生成</p>
    </div>

    <div class="actions">
      <el-button type="primary" icon="Plus" @click="createTemplate">新建模板</el-button>
      <el-button icon="Refresh" @click="refreshTemplates">刷新</el-button>
      <el-input
        v-model="searchQuery"
        placeholder="搜索模板..."
        style="width: 300px; margin-left: 10px"
        clearable
      >
        <template #prefix>
          <el-icon><Search /></el-icon>
        </template>
      </el-input>
    </div>

    <div class="template-list">
      <el-table :data="filteredTemplates" style="width: 100%" v-loading="loading">
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="title" label="岗位名称" width="200">
          <template #default="{ row }">
            <el-tag type="primary">{{ row.title }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="category" label="类别" width="120" />
        <el-table-column prop="skills" label="核心技能" min-width="250">
          <template #default="{ row }">
            <div class="skill-tags">
              <el-tag
                v-for="skill in row.skills.slice(0, 5)"
                :key="skill"
                size="small"
                class="skill-tag"
              >
                {{ skill }}
              </el-tag>
              <el-tag v-if="row.skills.length > 5" size="small">+{{ row.skills.length - 5 }}</el-tag>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="question_count" label="关联问题" width="100" />
        <el-table-column prop="created_at" label="创建时间" width="180" />
        <el-table-column prop="updated_at" label="更新时间" width="180" />
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" size="small" @click="editTemplate(row)">编辑</el-button>
            <el-button type="warning" size="small" @click="viewQuestions(row)">问题库</el-button>
            <el-button type="danger" size="small" @click="deleteTemplate(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <el-dialog
      v-model="dialogVisible"
      :title="dialogTitle"
      width="600px"
      @closed="resetForm"
    >
      <el-form :model="form" label-width="100px">
        <el-form-item label="岗位名称" required>
          <el-input v-model="form.title" placeholder="例如：Java后端开发工程师" />
        </el-form-item>
        <el-form-item label="岗位类别" required>
          <el-select v-model="form.category" placeholder="请选择类别">
            <el-option label="后端开发" value="backend" />
            <el-option label="前端开发" value="frontend" />
            <el-option label="移动开发" value="mobile" />
            <el-option label="数据科学" value="data" />
            <el-option label="人工智能" value="ai" />
            <el-option label="产品经理" value="product" />
            <el-option label="设计" value="design" />
            <el-option label="测试" value="qa" />
            <el-option label="运维" value="devops" />
          </el-select>
        </el-form-item>
        <el-form-item label="核心技能" required>
          <el-select
            v-model="form.skills"
            multiple
            filterable
            allow-create
            placeholder="输入或选择技能"
            style="width: 100%"
          >
            <el-option
              v-for="skill in availableSkills"
              :key="skill"
              :label="skill"
              :value="skill"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="岗位描述">
          <el-input
            v-model="form.description"
            type="textarea"
            :rows="3"
            placeholder="详细描述岗位职责和要求"
          />
        </el-form-item>
        <el-form-item label="匹配权重">
          <el-slider v-model="form.weight" :min="1" :max="10" show-input />
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="dialogVisible = false">取消</el-button>
          <el-button type="primary" @click="saveTemplate">保存</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'

interface Template {
  id: number
  title: string
  category: string
  skills: string[]
  question_count: number
  created_at: string
  updated_at: string
}

const loading = ref(false)
const searchQuery = ref('')
const dialogVisible = ref(false)
const dialogTitle = ref('新建岗位模板')
const isEditing = ref(false)
const currentTemplateId = ref<number | null>(null)

const templates = ref<Template[]>([
  {
    id: 1,
    title: 'Java后端开发工程师',
    category: 'backend',
    skills: ['Java', 'Spring Boot', 'MySQL', 'Redis', 'Linux'],
    question_count: 12,
    created_at: '2026-04-10 14:30:25',
    updated_at: '2026-04-12 09:15:33'
  },
  {
    id: 2,
    title: '前端开发工程师',
    category: 'frontend',
    skills: ['Vue.js', 'React', 'TypeScript', 'JavaScript', 'HTML/CSS'],
    question_count: 8,
    created_at: '2026-04-09 10:20:15',
    updated_at: '2026-04-11 16:45:22'
  },
  {
    id: 3,
    title: '数据科学家',
    category: 'data',
    skills: ['Python', 'Pandas', 'NumPy', '机器学习', 'SQL'],
    question_count: 15,
    created_at: '2026-04-08 09:15:40',
    updated_at: '2026-04-10 14:30:10'
  }
])

const form = ref({
  title: '',
  category: '',
  skills: [] as string[],
  description: '',
  weight: 5
})

const availableSkills = ref([
  'Java', 'Python', 'JavaScript', 'TypeScript', 'Go',
  'Spring Boot', 'Vue.js', 'React', 'Node.js', 'MySQL',
  'Redis', 'MongoDB', 'PostgreSQL', 'Docker', 'Kubernetes',
  'Linux', 'Git', 'CI/CD', 'AWS', 'Azure', 'GCP',
  '机器学习', '深度学习', '数据分析', '数据可视化'
])

const filteredTemplates = computed(() => {
  if (!searchQuery.value) return templates.value
  const query = searchQuery.value.toLowerCase()
  return templates.value.filter(template =>
    template.title.toLowerCase().includes(query) ||
    template.category.toLowerCase().includes(query) ||
    template.skills.some(skill => skill.toLowerCase().includes(query))
  )
})

const refreshTemplates = async () => {
  loading.value = true
  // 模拟API调用
  setTimeout(() => {
    ElMessage.success('模板列表已刷新')
    loading.value = false
  }, 1000)
}

const createTemplate = () => {
  dialogTitle.value = '新建岗位模板'
  isEditing.value = false
  currentTemplateId.value = null
  dialogVisible.value = true
}

const editTemplate = (template: Template) => {
  dialogTitle.value = '编辑岗位模板'
  isEditing.value = true
  currentTemplateId.value = template.id
  form.value = {
    title: template.title,
    category: template.category,
    skills: [...template.skills],
    description: '',
    weight: 5
  }
  dialogVisible.value = true
}

const viewQuestions = (template: Template) => {
  ElMessage.info(`查看 ${template.title} 的关联问题`)
}

const deleteTemplate = async (template: Template) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除岗位模板 "${template.title}" 吗？此操作不可恢复。`,
      '确认删除',
      {
        type: 'warning',
        confirmButtonText: '确定删除',
        cancelButtonText: '取消'
      }
    )

    const index = templates.value.findIndex(t => t.id === template.id)
    if (index !== -1) {
      templates.value.splice(index, 1)
      ElMessage.success('模板删除成功')
    }
  } catch {
    // 用户取消
  }
}

const saveTemplate = () => {
  if (!form.value.title.trim()) {
    ElMessage.error('请输入岗位名称')
    return
  }

  if (!form.value.category) {
    ElMessage.error('请选择岗位类别')
    return
  }

  if (form.value.skills.length === 0) {
    ElMessage.error('请至少添加一个核心技能')
    return
  }

  if (isEditing.value && currentTemplateId.value) {
    // 编辑现有模板
    const index = templates.value.findIndex(t => t.id === currentTemplateId.value)
    if (index !== -1) {
      templates.value[index] = {
        ...templates.value[index],
        title: form.value.title,
        category: form.value.category,
        skills: form.value.skills,
        updated_at: new Date().toLocaleString()
      }
    }
    ElMessage.success('模板更新成功')
  } else {
    // 创建新模板
    const newTemplate: Template = {
      id: templates.value.length + 1,
      title: form.value.title,
      category: form.value.category,
      skills: form.value.skills,
      question_count: 0,
      created_at: new Date().toLocaleString(),
      updated_at: new Date().toLocaleString()
    }
    templates.value.push(newTemplate)
    ElMessage.success('模板创建成功')
  }

  dialogVisible.value = false
}

const resetForm = () => {
  form.value = {
    title: '',
    category: '',
    skills: [],
    description: '',
    weight: 5
  }
  currentTemplateId.value = null
  isEditing.value = false
}

onMounted(() => {
  refreshTemplates()
})
</script>

<style scoped>
.job-template {
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

.actions {
  margin-bottom: 20px;
  display: flex;
  align-items: center;
}

.skill-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
}

.skill-tag {
  margin-right: 5px;
  margin-bottom: 5px;
}
</style>