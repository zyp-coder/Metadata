<template>
  <div>
    <div class="page-header">
      <a-space>
        <a-button @click="goBack">← 返回</a-button>
        <h2 v-if="tableName">表：{{ tableName }} — 字段属性配置</h2>
      </a-space>
      <a-button type="primary" :loading="saving" @click="handleSave">全部保存</a-button>
    </div>

    <div v-for="group in groupedFields" :key="group.name" style="margin-bottom: 24px">
      <h3 style="margin-bottom: 12px; color: #1677ff">{{ group.name }}</h3>
      <a-table
        :dataSource="group.fields"
        :columns="columns"
        :pagination="false"
        rowKey="id"
        size="small"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'field_type'">
            <a-select v-model:value="record.field_type" style="width: 120px" @change="(val: string) => onTypeChange(record, val)">
              <a-select-option value="string">字符串</a-select-option>
              <a-select-option value="number">数字</a-select-option>
              <a-select-option value="date">日期</a-select-option>
              <a-select-option value="boolean">布尔</a-select-option>
              <a-select-option value="enum">枚举</a-select-option>
            </a-select>
          </template>
          <template v-if="column.key === 'length'">
            <a-input-number v-model:value="record.length" :min="0" style="width: 80px" />
          </template>
          <template v-if="column.key === 'required'">
            <a-switch v-model:checked="record.required" />
          </template>
          <template v-if="column.key === 'default_value'">
            <a-input v-model:value="record.default_value" style="width: 120px" />
          </template>
          <template v-if="column.key === 'options' && record.field_type === 'enum'">
            <a-space>
              <a-input v-model:value="record._newOptionLabel" placeholder="显示名" size="small" style="width: 80px" />
              <a-input v-model:value="record._newOptionValue" placeholder="值" size="small" style="width: 80px" />
              <a-button size="small" type="link" @click="addOption(record)">添加</a-button>
            </a-space>
            <div v-if="record.options?.length">
              <a-tag v-for="opt in record.options" :key="opt.value" closable style="margin: 2px" @close="removeOption(record, opt)">
                {{ opt.label }}={{ opt.value }}
              </a-tag>
            </div>
          </template>
        </template>
      </a-table>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { tableApi, fieldApi } from '@/api/modeling'
import type { Field } from '@/types'

const route = useRoute()
const router = useRouter()
const tableId = Number(route.params.id)
const tableName = ref('')
const fields = ref<any[]>([])
const saving = ref(false)

const columns = [
  { title: '字段', dataIndex: 'name', key: 'name', width: 120 },
  { title: '编码', dataIndex: 'code', key: 'code', width: 120 },
  { title: '类型', key: 'field_type', width: 140 },
  { title: '长度', key: 'length', width: 90 },
  { title: '必填', key: 'required', width: 70 },
  { title: '默认值', key: 'default_value', width: 140 },
  { title: '枚举选项', key: 'options', width: 300 },
]

const groupedFields = computed(() => {
  const map: Record<string, any[]> = {}
  const uncategorized: any[] = []
  for (const f of fields.value) {
    if (f.group_name) {
      if (!map[f.group_name]) map[f.group_name] = []
      map[f.group_name].push(f)
    } else {
      uncategorized.push(f)
    }
  }
  const result: any[] = Object.entries(map).map(([name, items]) => ({ name, fields: items }))
  if (uncategorized.length > 0) result.push({ name: '未分类', fields: uncategorized })
  return result
})

async function loadData() {
  try {
    const res = await tableApi.get(tableId)
    tableName.value = res.data.name
    const fieldRes = await fieldApi.list({ table: tableId })
    fields.value = fieldRes.data.results.map((f: Field) => ({
      ...f,
      options: f.options || [],
    }))
  } catch (e: any) {
    message.error(e.message)
  }
}

function onTypeChange(record: any, val: string) {
  if (val !== 'enum') {
    record.options = []
  }
}

function addOption(record: any) {
  if (!record._newOptionLabel || !record._newOptionValue) {
    message.warning('请填写选项显示名和值')
    return
  }
  if (!record.options) record.options = []
  record.options.push({ label: record._newOptionLabel, value: record._newOptionValue })
  record._newOptionLabel = ''
  record._newOptionValue = ''
}

function removeOption(record: any, opt: any) {
  const idx = record.options.indexOf(opt)
  if (idx > -1) record.options.splice(idx, 1)
}

async function handleSave() {
  saving.value = true
  try {
    const updates = fields.value.map((f) => ({
      id: f.id,
      field_type: f.field_type,
      length: f.length,
      required: f.required,
      default_value: f.default_value,
      // 发送 options，枚举类型传实际选项，非枚举传空数组以清除旧选项
      options: f.field_type === 'enum' ? (f.options || []) : [],
    }))
    await fieldApi.batchUpdateAttributes(updates)
    message.success('全部保存成功')
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
