<template>
  <div>
    <div class="page-header">
      <h2>用户管理</h2>
      <a-button type="primary" @click="openCreate">新建用户</a-button>
    </div>

    <a-table
      :dataSource="users"
      :columns="columns"
      :loading="loading"
      :pagination="{ current: page, pageSize: 20, total, onChange: (p: number) => { page = p; loadData() } }"
      rowKey="id"
      :scroll="{ x: 1000 }"
    >
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'roles'">
          <a-tag v-for="r in record.roles" :key="r.id" :color="r.is_builtin ? 'blue' : 'default'">
            {{ r.name }}
          </a-tag>
          <span v-if="!record.roles?.length" style="color: #999">无角色</span>
        </template>
        <template v-if="column.key === 'status'">
          <a-tag :color="record.is_active ? 'green' : 'red'">
            {{ record.is_active ? '启用' : '禁用' }}
          </a-tag>
        </template>
        <template v-if="column.key === 'last_login'">
          {{ record.last_login ? formatDateTime(record.last_login) : '—' }}
        </template>
        <template v-if="column.key === 'action'">
          <a-space :size="4" style="white-space: nowrap">
            <a @click="openEdit(record)">编辑</a>
            <a-divider type="vertical" />
            <a @click="openResetPassword(record)">重置密码</a>
            <a-divider type="vertical" />
            <a-popconfirm
              :title="record.is_active ? '确认禁用该用户？禁用后即时生效。' : '确认启用该用户？'"
              @confirm="toggleActive(record)"
            >
              <a :style="{ color: record.is_active ? '#ff4d4f' : '#52c41a' }">
                {{ record.is_active ? '禁用' : '启用' }}
              </a>
            </a-popconfirm>
          </a-space>
        </template>
      </template>
    </a-table>

    <!-- 新建/编辑用户 Modal (C640) -->
    <a-modal
      v-model:open="modalVisible"
      :title="editingId ? '编辑用户' : '新建用户'"
      @ok="handleSubmit"
      :confirmLoading="saving"
      width="640px"
    >
      <a-form :model="formData" layout="vertical">
        <a-form-item label="用户名" required v-if="!editingId">
          <a-input v-model:value="formData.username" placeholder="登录账号" :maxlength="64" />
        </a-form-item>
        <a-form-item label="用户名" v-if="editingId">
          <a-input :value="editingUsername" disabled />
        </a-form-item>
        <a-form-item label="显示名">
          <a-input v-model:value="formData.display_name" placeholder="业务显示名" :maxlength="64" />
        </a-form-item>
        <a-form-item label="密码" required v-if="!editingId">
          <a-input-password v-model:value="formData.password" placeholder="登录密码" />
        </a-form-item>
        <a-form-item label="角色">
          <a-select
            v-model:value="formData.role_ids"
            mode="multiple"
            placeholder="选择角色（可多选）"
            :options="roleOptions"
            allowClear
          />
        </a-form-item>
      </a-form>
    </a-modal>

    <!-- 重置密码 Modal (小480) -->
    <a-modal
      v-model:open="resetVisible"
      title="重置密码"
      @ok="handleResetPassword"
      :confirmLoading="resetting"
      width="480px"
    >
      <a-form :model="resetForm" layout="vertical">
        <a-form-item label="用户">
          <a-input :value="resetUsername" disabled />
        </a-form-item>
        <a-form-item label="新密码" required>
          <a-input-password v-model:value="resetForm.password" placeholder="输入新密码" />
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue'
import { message } from 'ant-design-vue'
import { getUsersApi, createUserApi, updateUserApi, resetPasswordApi, getRolesApi } from '@/api/auth'
import { formatDateTime } from '@/utils/date'
import { extractApiError } from '@/utils/apiError'
import type { MdmUser, AuthRole } from '@/types'

const loading = ref(false)
const saving = ref(false)
const resetting = ref(false)
const users = ref<MdmUser[]>([])
const page = ref(1)
const total = ref(0)
const allRoles = ref<AuthRole[]>([])

const columns = [
  { title: '用户名', dataIndex: 'username', key: 'username', width: 140 },
  { title: '显示名', dataIndex: 'display_name', key: 'display_name', width: 140 },
  { title: '角色', key: 'roles', width: 200 },
  { title: '状态', key: 'status', width: 80 },
  { title: '最近登录', key: 'last_login', width: 160 },
  { title: '操作', key: 'action', width: 200 },
]

const roleOptions = computed(() => allRoles.value.map(r => ({ label: r.name, value: r.id })))

// ===== 列表 =====
async function loadData() {
  loading.value = true
  try {
    const { data } = await getUsersApi({ page: page.value, page_size: 20 })
    users.value = data.results
    total.value = data.count
  } catch (e: any) {
    message.error(extractApiError(e) || '加载用户列表失败')
  } finally {
    loading.value = false
  }
}

async function loadRoles() {
  try {
    const { data } = await getRolesApi({ page_size: 1000 })
    allRoles.value = data.results
  } catch { /* 角色加载失败不阻断页面 */ }
}

// ===== 新建/编辑 =====
const modalVisible = ref(false)
const editingId = ref<number | null>(null)
const editingUsername = ref('')
const formData = reactive({
  username: '',
  display_name: '',
  password: '',
  role_ids: [] as number[],
})

function openCreate() {
  editingId.value = null
  editingUsername.value = ''
  formData.username = ''
  formData.display_name = ''
  formData.password = ''
  formData.role_ids = []
  modalVisible.value = true
}

function openEdit(record: MdmUser) {
  editingId.value = record.id
  editingUsername.value = record.username
  formData.username = record.username
  formData.display_name = record.display_name
  formData.password = ''
  formData.role_ids = record.roles.map(r => r.id)
  modalVisible.value = true
}

async function handleSubmit() {
  if (!editingId.value) {
    if (!formData.username || !formData.password) {
      message.warning('请填写用户名和密码')
      return
    }
  }
  saving.value = true
  try {
    if (editingId.value) {
      await updateUserApi(editingId.value, {
        display_name: formData.display_name,
        role_ids: formData.role_ids,
      })
      message.success('更新成功')
    } else {
      await createUserApi({
        username: formData.username,
        password: formData.password,
        display_name: formData.display_name,
        role_ids: formData.role_ids,
      })
      message.success('创建成功')
    }
    modalVisible.value = false
    loadData()
  } catch (e: any) {
    message.error(extractApiError(e) || '操作失败')
  } finally {
    saving.value = false
  }
}

// ===== 禁用/启用 =====
async function toggleActive(record: MdmUser) {
  try {
    await updateUserApi(record.id, { is_active: !record.is_active })
    message.success(record.is_active ? '已禁用' : '已启用')
    loadData()
  } catch (e: any) {
    message.error(extractApiError(e) || '操作失败')
  }
}

// ===== 重置密码 =====
const resetVisible = ref(false)
const resetUserId = ref(0)
const resetUsername = ref('')
const resetForm = reactive({ password: '' })

function openResetPassword(record: MdmUser) {
  resetUserId.value = record.id
  resetUsername.value = record.username
  resetForm.password = ''
  resetVisible.value = true
}

async function handleResetPassword() {
  if (!resetForm.password) {
    message.warning('请输入新密码')
    return
  }
  resetting.value = true
  try {
    await resetPasswordApi(resetUserId.value, { password: resetForm.password })
    message.success('密码已重置')
    resetVisible.value = false
  } catch (e: any) {
    message.error(extractApiError(e) || '重置密码失败')
  } finally {
    resetting.value = false
  }
}

onMounted(() => {
  loadData()
  loadRoles()
})
</script>

<style scoped>
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}
.page-header h2 {
  margin: 0;
  font-size: 20px;
}
</style>
