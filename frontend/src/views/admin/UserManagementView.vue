<template>
  <div class="user-management">
    <div class="header">
      <h1>用户管理</h1>
      <p>管理系统用户和权限</p>
    </div>

    <div class="actions">
      <el-button type="primary" icon="Plus" @click="addUser">添加用户</el-button>
      <el-button icon="Download" @click="exportUsers">导出用户</el-button>
      <el-button icon="Refresh" @click="refresh">刷新</el-button>
    </div>

    <div class="filters">
      <el-form :inline="true" :model="filters">
        <el-form-item label="用户名">
          <el-input v-model="filters.username" placeholder="搜索用户名" />
        </el-form-item>
        <el-form-item label="邮箱">
          <el-input v-model="filters.email" placeholder="搜索邮箱" />
        </el-form-item>
        <el-form-item label="角色">
          <el-select v-model="filters.role" placeholder="请选择">
            <el-option label="全部" value="" />
            <el-option label="管理员" value="admin" />
            <el-option label="运营" value="operator" />
            <el-option label="普通用户" value="user" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="filters.status" placeholder="请选择">
            <el-option label="全部" value="" />
            <el-option label="正常" value="active" />
            <el-option label="禁用" value="inactive" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="search">搜索</el-button>
          <el-button @click="resetFilters">重置</el-button>
        </el-form-item>
      </el-form>
    </div>

    <div class="user-table">
      <el-table :data="users" style="width: 100%">
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="username" label="用户名" width="120" />
        <el-table-column prop="email" label="邮箱" width="180" />
        <el-table-column prop="full_name" label="姓名" width="120" />
        <el-table-column prop="role" label="角色" width="100">
          <template #default="{ row }">
            <el-tag :type="getRoleType(row.role)">
              {{ row.role === 'admin' ? '管理员' : row.role === 'operator' ? '运营' : '普通用户' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="row.status === 'active' ? 'success' : 'danger'">
              {{ row.status === 'active' ? '正常' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="注册时间" width="180" />
        <el-table-column prop="last_login" label="最后登录" width="180" />
        <el-table-column label="操作" width="200">
          <template #default="{ row }">
            <el-button type="primary" size="small" @click="editUser(row)">编辑</el-button>
            <el-button
              :type="row.status === 'active' ? 'warning' : 'success'"
              size="small"
              @click="toggleUserStatus(row)"
            >
              {{ row.status === 'active' ? '禁用' : '启用' }}
            </el-button>
            <el-popconfirm
              title="确认删除此用户？"
              @confirm="deleteUser(row.id)"
            >
              <template #reference>
                <el-button type="danger" size="small">删除</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <div class="pagination">
      <el-pagination
        v-model:current-page="pagination.current"
        v-model:page-size="pagination.size"
        :total="pagination.total"
        :page-sizes="[10, 20, 50]"
        layout="total, sizes, prev, pager, next, jumper"
      />
    </div>

    <!-- 添加/编辑用户对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="dialogTitle"
      width="500px"
    >
      <el-form ref="userFormRef" :model="userForm" :rules="userRules" label-width="80px">
        <el-form-item label="用户名" prop="username">
          <el-input v-model="userForm.username" />
        </el-form-item>
        <el-form-item label="邮箱" prop="email">
          <el-input v-model="userForm.email" />
        </el-form-item>
        <el-form-item label="姓名" prop="full_name">
          <el-input v-model="userForm.full_name" />
        </el-form-item>
        <el-form-item label="角色" prop="role">
          <el-select v-model="userForm.role">
            <el-option label="管理员" value="admin" />
            <el-option label="运营" value="operator" />
            <el-option label="普通用户" value="user" />
          </el-select>
        </el-form-item>
        <el-form-item label="密码" prop="password" v-if="isAddMode">
          <el-input v-model="userForm.password" type="password" show-password />
        </el-form-item>
        <el-form-item label="确认密码" prop="confirm_password" v-if="isAddMode">
          <el-input v-model="userForm.confirm_password" type="password" show-password />
        </el-form-item>
        <el-form-item label="状态" prop="status">
          <el-switch
            v-model="userForm.status"
            active-value="active"
            inactive-value="inactive"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitUserForm">确认</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import type { FormInstance, FormRules } from 'element-plus'

const filters = ref({
  username: '',
  email: '',
  role: '',
  status: ''
})

const users = ref([
  {
    id: 1,
    username: 'admin',
    email: 'admin@example.com',
    full_name: '系统管理员',
    role: 'admin',
    status: 'active',
    created_at: '2026-01-01 10:00:00',
    last_login: '2026-04-11 14:30:25'
  },
  {
    id: 2,
    username: 'operator1',
    email: 'operator1@example.com',
    full_name: '运营人员1',
    role: 'operator',
    status: 'active',
    created_at: '2026-02-15 14:20:00',
    last_login: '2026-04-11 09:15:30'
  },
  {
    id: 3,
    username: 'user123',
    email: 'user123@example.com',
    full_name: '测试用户',
    role: 'user',
    status: 'active',
    created_at: '2026-03-20 16:45:00',
    last_login: '2026-04-10 18:20:15'
  }
])

const pagination = ref({
  current: 1,
  size: 10,
  total: 100
})

const dialogVisible = ref(false)
const isAddMode = ref(true)
const userFormRef = ref<FormInstance>()

const userForm = ref({
  id: 0,
  username: '',
  email: '',
  full_name: '',
  role: 'user',
  password: '',
  confirm_password: '',
  status: 'active'
})

const userRules: FormRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 20, message: '用户名长度3-20个字符', trigger: 'blur' }
  ],
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '请输入正确的邮箱地址', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码长度至少6位', trigger: 'blur' }
  ],
  confirm_password: [
    { required: true, message: '请确认密码', trigger: 'blur' },
    {
      validator: (rule, value, callback) => {
        if (value !== userForm.value.password) {
          callback(new Error('两次输入密码不一致'))
        } else {
          callback()
        }
      },
      trigger: 'blur'
    }
  ]
}

const getRoleType = (role: string) => {
  switch (role) {
    case 'admin': return 'danger'
    case 'operator': return 'warning'
    default: return ''
  }
}

const dialogTitle = computed(() => {
  return isAddMode.value ? '添加用户' : '编辑用户'
})

const addUser = () => {
  isAddMode.value = true
  userForm.value = {
    id: 0,
    username: '',
    email: '',
    full_name: '',
    role: 'user',
    password: '',
    confirm_password: '',
    status: 'active'
  }
  dialogVisible.value = true
}

const editUser = (user: any) => {
  isAddMode.value = false
  userForm.value = {
    id: user.id,
    username: user.username,
    email: user.email,
    full_name: user.full_name,
    role: user.role,
    password: '',
    confirm_password: '',
    status: user.status
  }
  dialogVisible.value = true
}

const toggleUserStatus = (user: any) => {
  const newStatus = user.status === 'active' ? 'inactive' : 'active'
  ElMessage.success(`用户 ${user.username} 状态已${newStatus === 'active' ? '启用' : '禁用'}`)
  // 这里应该调用API更新用户状态
}

const deleteUser = (id: number) => {
  ElMessage.success(`用户 ${id} 已删除`)
  // 这里应该调用API删除用户
}

const submitUserForm = async () => {
  if (!userFormRef.value) return

  const valid = await userFormRef.value.validate()
  if (!valid) return

  if (isAddMode.value) {
    ElMessage.success('用户添加成功')
  } else {
    ElMessage.success('用户信息已更新')
  }

  dialogVisible.value = false
}

const search = () => {
  ElMessage.success('搜索完成')
}

const resetFilters = () => {
  filters.value = {
    username: '',
    email: '',
    role: '',
    status: ''
  }
}

const exportUsers = () => {
  ElMessage.info('导出功能开发中')
}

const refresh = () => {
  ElMessage.success('数据已刷新')
}
</script>

<style scoped>
.user-management {
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
}

.filters {
  margin-bottom: 20px;
  padding: 20px;
  background: #f8f9fa;
  border-radius: 8px;
}

.user-table {
  margin-bottom: 20px;
}

.pagination {
  display: flex;
  justify-content: center;
}
</style>