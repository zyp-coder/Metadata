<template>
  <div>
    <div class="page-header">
      <a-space>
        <a-button @click="goBack">← 返回</a-button>
        <h2 v-if="tableName">表：{{ tableName }} — 字段映射</h2>
      </a-space>
      <a-button type="primary" :disabled="allTables.length < 2" @click="openCreate">新建映射</a-button>
    </div>

    <a-table
      :dataSource="mappings"
      :columns="columns"
      :loading="loading"
      :pagination="false"
      rowKey="id"
    >
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'action'">
          <a-popconfirm title="确定删除此映射？" @confirm="doDelete(record.id)">
            <a style="color: #ff4d4f">删除</a>
          </a-popconfirm>
        </template>
      </template>
    </a-table>

    <a-modal v-model:open="modalVisible" title="新建字段映射" @ok="handleSubmit" :confirmLoading="saving">
      <a-form layout="vertical">
        <a-form-item label="源表">
          <a-select v-model:value="form.source_table" style="width: 100%" show-search @change="loadSourceFields">
            <a-select-option v-for="t in allTables" :key="t.id" :value="t.id">{{ t.name }}</a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item label="源字段">
          <a-select v-model:value="form.source_field" style="width: 100%" show-search>
            <a-select-option v-for="f in sourceFields" :key="f.id" :value="f.id">{{ f.name }} ({{ f.code }})</a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item label="目标表">
          <a-select v-model:value="form.target_table" style="width: 100%" show-search @change="loadTargetFields">
            <a-select-option v-for="t in allTables" :key="t.id" :value="t.id">{{ t.name }}</a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item label="目标字段">
          <a-select v-model:value="form.target_field" style="width: 100%" show-search>
            <a-select-option v-for="f in targetFields" :key="f.id" :value="f.id">{{ f.name }} ({{ f.code }})</a-select-option>
          </a-select>
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { tableApi, fieldApi, fieldMappingApi } from '@/api/modeling'
import { formatDateTime } from '@/utils/date'
import type { Table, FieldMapping } from '@/types'

const route = useRoute()
const router = useRouter()
const tableId = Number(route.params.id)
const tableName = ref('')
const allTables = ref<Table[]>([])
const sourceFields = ref<any[]>([])
const targetFields = ref<any[]>([])
const mappings = ref<any[]>([])
const loading = ref(false)
const modalVisible = ref(false)
const saving = ref(false)
const form = ref<any>({ source_table: null, source_field: null, target_table: null, target_field: null })

const columns = [
  { title: '源表', dataIndex: 'source_table_name', key: 'source_table_name' },
  { title: '源字段', dataIndex: 'source_field_name', key: 'source_field_name' },
  { title: '→', key: 'arrow', width: 40 },
  { title: '目标表', dataIndex: 'target_table_name', key: 'target_table_name' },
  { title: '目标字段', dataIndex: 'target_field_name', key: 'target_field_name' },
  { title: '创建时间', dataIndex: 'created_at', key: 'created_at',
    customRender: ({ text }: any) => formatDateTime(text) },
  { title: '操作', key: 'action', width: 80 },
]

async function loadData() {
  loading.value = true
  try {
    const res = await tableApi.get(tableId)
    tableName.value = res.data.name
    const domainId = res.data.domain

    const tablesRes = await tableApi.list({ domain: domainId })
    allTables.value = tablesRes.data.results

    const mapRes = await fieldMappingApi.list({ table: tableId })
    mappings.value = mapRes.data.results
  } finally {
    loading.value = false
  }
}

async function loadSourceFields() {
  if (form.value.source_table) {
    const res = await fieldApi.list({ table: form.value.source_table })
    sourceFields.value = res.data.results
  }
}

async function loadTargetFields() {
  if (form.value.target_table) {
    const res = await fieldApi.list({ table: form.value.target_table })
    targetFields.value = res.data.results
  }
}

function openCreate() {
  form.value = { source_table: null, source_field: null, target_table: null, target_field: null }
  sourceFields.value = []
  targetFields.value = []
  modalVisible.value = true
}

async function handleSubmit() {
  if (!form.value.source_field || !form.value.target_field) {
    message.warning('请选择源字段和目标字段')
    return
  }
  saving.value = true
  try {
    await fieldMappingApi.create(form.value)
    message.success('映射创建成功')
    modalVisible.value = false
    await loadData()
  } catch (e: any) {
    message.error(e.message || '创建失败')
  } finally {
    saving.value = false
  }
}

async function doDelete(id: number) {
  try {
    await fieldMappingApi.delete(id)
    message.success('删除成功')
    await loadData()
  } catch (e: any) {
    message.error(e.message || '删除失败')
  }
}

function goBack() {
  router.back()
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
  display: inline;
}
</style>
