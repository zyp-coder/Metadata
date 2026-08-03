<template>
  <div>
    <div class="page-header">
      <h2>系统设置 — 数据源管理</h2>
      <a-button type="primary" @click="openCreate">新建数据源</a-button>
    </div>

    <a-table
      :dataSource="dataSources"
      :columns="columns"
      :loading="loading"
      :pagination="false"
      rowKey="id"
    >
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'db_type'">
          {{ dbTypeLabels[record.db_type] || record.db_type }}
        </template>
        <template v-if="column.key === 'status'">
          <a-tag :color="record.status === 'active' ? 'green' : 'default'">
            {{ record.status === 'active' ? '正常' : '停用' }}
          </a-tag>
        </template>
        <template v-if="column.key === 'action'">
          <a-space>
            <a @click="openEdit(record)">编辑</a>
            <a-divider type="vertical" />
            <a-popconfirm title="确定删除此数据源？" @confirm="doDelete(record.id)">
              <a style="color: #ff4d4f">删除</a>
            </a-popconfirm>
          </a-space>
        </template>
      </template>
    </a-table>

    <a-modal
      v-model:open="modalVisible"
      :title="editingId ? '编辑数据源' : '新建数据源'"
      @ok="handleSubmit"
      :confirmLoading="saving"
      width="600px"
    >
      <template #footer>
        <a-space style="width: 100%; justify-content: space-between">
          <a-button :loading="testing" @click="handleTestConnection">
            {{ testResult?.success ? '✅ 重新测试' : '测试连接' }}
          </a-button>
          <a-space>
            <a-button @click="modalVisible = false">取消</a-button>
            <a-button type="primary" :loading="saving" @click="handleSubmit">确定</a-button>
          </a-space>
        </a-space>
      </template>
      <a-form :model="formData" layout="vertical">
        <a-form-item label="数据源名称" required>
          <a-input v-model:value="formData.name" placeholder="如：生产数据库" />
        </a-form-item>
        <a-form-item label="数据库类型" required>
          <a-select v-model:value="formData.db_type" @change="onDbTypeChange">
            <a-select-option value="postgresql">PostgreSQL</a-select-option>
            <a-select-option value="mysql">MySQL</a-select-option>
            <a-select-option value="sqlserver">SQL Server</a-select-option>
            <a-select-option value="oracle">Oracle</a-select-option>
          </a-select>
        </a-form-item>
        <a-row :gutter="16">
          <a-col :span="14">
            <a-form-item label="主机地址" required>
              <a-input v-model:value="formData.host" placeholder="如：192.168.1.100" />
            </a-form-item>
          </a-col>
          <a-col :span="10">
            <a-form-item label="端口">
              <a-input-number v-model:value="formData.port" :min="1" :max="65535" style="width: 100%" />
            </a-form-item>
          </a-col>
        </a-row>
        <a-form-item label="数据库名" required>
          <a-input v-model:value="formData.db_name" placeholder="如：mdm_prod" />
        </a-form-item>
        <a-row :gutter="16">
          <a-col :span="12">
            <a-form-item label="用户名">
              <a-input v-model:value="formData.username" placeholder="数据库用户名" />
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="密码">
              <a-input-password v-model:value="formData.password" placeholder="数据库密码" />
            </a-form-item>
          </a-col>
        </a-row>
        <a-alert v-if="testResult" :type="testResult.success ? 'success' : 'error'" show-icon style="margin-top: 8px">
          <template #message>
            {{ testResult.success ? testResult.message : testResult.error }}
          </template>
        </a-alert>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { message } from 'ant-design-vue'
import { dataSourceApi } from '@/api/modeling'
import type { DataSource } from '@/types'

const dataSources = ref<DataSource[]>([])
const loading = ref(false)
const modalVisible = ref(false)
const saving = ref(false)
const testing = ref(false)
const testResult = ref<{ success: boolean; message?: string; error?: string } | null>(null)
const editingId = ref<number | null>(null)
const formData = ref<any>({
  name: '', db_type: 'postgresql', host: '', port: 5432, db_name: '',
  username: '', password: '',
})

const dbTypeLabels: Record<string, string> = {
  postgresql: 'PostgreSQL', mysql: 'MySQL', sqlserver: 'SQL Server', oracle: 'Oracle',
}

const dbTypeDefaultPorts: Record<string, number> = {
  postgresql: 5432, mysql: 3306, sqlserver: 1433, oracle: 1521,
}

const columns = [
  { title: '名称', dataIndex: 'name', key: 'name' },
  { title: '类型', key: 'db_type', width: 100 },
  { title: '主机', dataIndex: 'host', key: 'host', width: 140 },
  { title: '端口', dataIndex: 'port', key: 'port', width: 80 },
  { title: '数据库', dataIndex: 'db_name', key: 'db_name', width: 120 },
  { title: '状态', key: 'status', width: 80 },
  { title: '操作', key: 'action', width: 160 },
]

async function loadData() {
  loading.value = true
  try {
    const res = await dataSourceApi.list()
    dataSources.value = res.data.results
  } finally {
    loading.value = false
  }
}

function openCreate() {
  editingId.value = null
  formData.value = { name: '', db_type: 'postgresql', host: '', port: 5432, db_name: '', username: '', password: '' }
  testResult.value = null
  modalVisible.value = true
}

function onDbTypeChange(type: string) {
  formData.value.port = dbTypeDefaultPorts[type] || 5432
}

function openEdit(record: DataSource) {
  editingId.value = record.id
  formData.value = {
    name: record.name, db_type: record.db_type, host: record.host,
    port: record.port, db_name: record.db_name,
    username: record.username, password: '',
  }
  testResult.value = null
  modalVisible.value = true
}

async function handleSubmit() {
  if (!formData.value.name || !formData.value.host || !formData.value.db_name) {
    message.warning('请填写必要信息')
    return
  }
  saving.value = true
  try {
    const payload = { ...formData.value }
    if (!payload.password) delete payload.password
    if (editingId.value) {
      await dataSourceApi.update(editingId.value, payload)
      message.success('更新成功')
    } else {
      await dataSourceApi.create(payload)
      message.success('创建成功')
    }
    modalVisible.value = false
    await loadData()
  } catch (e: any) {
    message.error(e.message || '操作失败')
  } finally {
    saving.value = false
  }
}

async function doDelete(id: number) {
  try {
    await dataSourceApi.delete(id)
    message.success('删除成功')
    await loadData()
  } catch (e: any) {
    message.error(e.message || '删除失败')
  }
}

async function handleTestConnection() {
  const data = formData.value
  if (!data.host || !data.db_name) {
    message.warning('请先填写主机地址和数据库名')
    return
  }
  testing.value = true
  testResult.value = null
  try {
    if (editingId.value) {
      const res = await dataSourceApi.testConnection(editingId.value)
      testResult.value = res.data
    } else {
      const res = await dataSourceApi.testConnectionParams(data)
      testResult.value = res.data
    }
  } catch (e: any) {
    testResult.value = { success: false, error: `测试失败: ${e.message || '网络错误'}` }
  } finally {
    testing.value = false
  }
}

onMounted(loadData)
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
  font-size: 18px;
}
</style>
