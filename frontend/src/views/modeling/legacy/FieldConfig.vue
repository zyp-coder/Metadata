<template>
  <div>
    <div class="page-header">
      <a-space>
        <a-button @click="goBack">← 返回表列表</a-button>
        <h2 v-if="tableName">表：{{ tableName }} — 字段名称配置</h2>
      </a-space>
      <a-space>
        <a-button @click="addRow">添加一行</a-button>
        <a-button type="primary" :loading="saving" @click="handleSave">保存字段</a-button>
      </a-space>
    </div>

    <a-alert
      message="在此页面批量配置字段的名称和编码，配置完成后进入AI字段分类步骤。"
      type="info"
      show-icon
      style="margin-bottom: 16px"
    />

    <a-table
      :dataSource="fieldList"
      :columns="columns"
      :pagination="false"
      rowKey="key"
    >
      <template #bodyCell="{ column, record, index }">
        <template v-if="column.key === 'index'">
          {{ index + 1 }}
        </template>
        <template v-if="column.key === 'name'">
          <a-input v-model:value="record.name" placeholder="字段名称" />
        </template>
        <template v-if="column.key === 'code'">
          <a-input v-model:value="record.code" placeholder="字段编码" />
        </template>
        <template v-if="column.key === 'action'">
          <a-popconfirm title="确定删除该字段？" @confirm="fieldList.splice(index, 1)">
            <a style="color: #ff4d4f">删除</a>
          </a-popconfirm>
        </template>
      </template>
    </a-table>

    <div v-if="fieldList.length === 0" style="text-align: center; padding: 40px; color: #999">
      暂无字段，点击「添加一行」开始配置
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { tableApi, fieldApi } from '@/api/modeling'

const route = useRoute()
const router = useRouter()
const tableId = Number(route.params.id)
const tableName = ref('')
const fieldList = ref<any[]>([])
const saving = ref(false)
let keyCounter = 0

const columns = [
  { title: '#', key: 'index', width: 50 },
  { title: '字段名称', key: 'name' },
  { title: '字段编码', key: 'code' },
  { title: '操作', key: 'action', width: 80 },
]

async function loadData() {
  try {
    const res = await tableApi.get(tableId)
    tableName.value = res.data.name
    const fieldRes = await fieldApi.list({ table: tableId })
    const existing = fieldRes.data.results
    if (existing.length > 0) {
      fieldList.value = existing.map((f: any) => ({
        key: ++keyCounter,
        id: f.id,
        name: f.name,
        code: f.code,
      }))
    }
  } catch (e: any) {
    message.error(e.message)
  }
}

function addRow() {
  fieldList.value.push({ key: ++keyCounter, name: '', code: '' })
}

async function handleSave() {
  const validFields = fieldList.value.filter((f: any) => f.name.trim())
  if (validFields.length === 0) {
    message.warning('请至少添加一个字段')
    return
  }
  saving.value = true
  try {
    await fieldApi.batchSave(tableId, validFields.map((f: any) => ({
      name: f.name, code: f.code || f.name, sort_order: 0,
    })))
    message.success('保存成功，可继续添加或修改')
    await loadData()
  } catch (e: any) {
    message.error(e.message || '保存失败')
  } finally {
    saving.value = false
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
