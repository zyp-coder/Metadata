<template>
  <div>
    <div class="page-header">
      <h2>域管理</h2>
      <a-button type="primary" @click="openCreate">新建域</a-button>
    </div>

    <a-table
      :dataSource="domains"
      :columns="columns"
      :loading="loading"
      :pagination="false"
      rowKey="id"
      :scroll="{ x: 1200 }"
    >
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'status'">
          <a-tag :color="record.status === 'active' ? 'green' : 'default'">
            {{ record.status === 'active' ? '启用' : '已废弃' }}
          </a-tag>
        </template>
        <template v-if="column.key === 'action'">
          <a-space>
            <a @click="goTables(record)" style="color: #1677ff; font-weight: 500">管理表</a>
            <a-divider type="vertical" />
            <a @click="goMappings(record)">关系管理</a>
            <a-divider type="vertical" />
            <a @click="goFields(record)">字段管理</a>
            <a-divider type="vertical" />
            <a @click="goEdit(record)">编辑</a>
            <a-divider type="vertical" />
            <a-popconfirm title="确定删除该域？" @confirm="doDelete(record.id)">
              <a style="color: #ff4d4f">删除</a>
            </a-popconfirm>
          </a-space>
        </template>
      </template>
    </a-table>

    <a-modal
      v-model:open="modalVisible"
      :title="editingId ? `编辑域 — ${formData.code}` : '新建域'"
      @ok="handleSubmit"
      :confirmLoading="saving"
    >
      <a-form :model="formData" layout="vertical">
        <a-form-item label="域名称" required>
          <a-input v-model:value="formData.name" placeholder="如：供应商主数据" />
        </a-form-item>
        <a-form-item label="域编码" required>
          <a-input v-model:value="formData.code" placeholder="如：SUPPLIER" :disabled="!!editingId" />
        </a-form-item>
        <a-form-item label="描述">
          <a-textarea v-model:value="formData.description" :rows="3" />
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { domainApi } from '@/api/modeling'
import type { Domain } from '@/types'
import { formatDateTime } from '@/utils/date'

const router = useRouter()
const domains = ref<Domain[]>([])
const loading = ref(false)
const modalVisible = ref(false)
const saving = ref(false)
const editingId = ref<number | null>(null)
const formData = ref({ name: '', code: '', description: '' })

const columns = [
  { title: '名称', dataIndex: 'name', key: 'name', width: 260 },
  { title: '编码', dataIndex: 'code', key: 'code', width: 200 },
  { title: '描述', dataIndex: 'description', key: 'description', ellipsis: true },
  { title: '状态', key: 'status', width: 100 },
  { title: '表数量', dataIndex: 'table_count', key: 'table_count', width: 80 },
  { title: '创建时间', dataIndex: 'created_at', key: 'created_at', width: 180,
    customRender: ({ text }: any) => formatDateTime(text) },
  { title: '操作', key: 'action', width: 380 },
]

async function loadData() {
  loading.value = true
  try {
    const res = await domainApi.list()
    domains.value = res.data.results
  } finally {
    loading.value = false
  }
}

function openCreate() {
  editingId.value = null
  formData.value = { name: '', code: '', description: '' }
  modalVisible.value = true
}

async function handleSubmit() {
  if (!formData.value.name || !formData.value.code) {
    message.warning('请填写名称和编码')
    return
  }
  saving.value = true
  try {
    if (editingId.value) {
      await domainApi.update(editingId.value, formData.value)
      message.success('更新成功')
    } else {
      await domainApi.create(formData.value)
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
    await domainApi.delete(id)
    message.success('删除成功')
    await loadData()
  } catch (e: any) {
    message.error(e.message || '删除失败')
  }
}

function goTables(record: Domain) {
  router.push(`/modeling/domains/${record.id}/tables`)
}

function goMappings(record: Domain) {
  router.push(`/modeling/domains/${record.id}/mappings`)
}

function goFields(record: Domain) {
  router.push(`/modeling/domains/${record.id}/fields`)
}

function goEdit(record: Domain) {
  editingId.value = record.id
  formData.value = { name: record.name, code: record.code, description: record.description }
  modalVisible.value = true
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
  font-size: 20px;
}
</style>
