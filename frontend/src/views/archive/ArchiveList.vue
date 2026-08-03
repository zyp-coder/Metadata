<template>
  <div>
    <div class="page-header">
      <h2>档案管理</h2>
      <a-button type="primary" @click="openCreate">新建档案</a-button>
    </div>

    <a-table
      :dataSource="archives"
      :columns="columns"
      :loading="loading"
      rowKey="id"
      :scroll="{ x: 1180 }"
      :pagination="{ current: page, pageSize: 20, total, onChange: (p: number) => { page = p; loadData() } }"
    >
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'name'">
          {{ record.name }}
        </template>
        <template v-if="column.key === 'status'">
          <a-tag :color="statusColor(record.status)">{{ statusLabel(record.status) }}</a-tag>
        </template>
        <template v-if="column.key === 'action'">
          <a-space :size="4" style="white-space: nowrap">
            <a @click="goDetail(record)">管理记录</a>
            <a-divider type="vertical" />
            <a @click="goConsistency(record)">一致性检查</a>
            <a-divider type="vertical" />
            <a @click="doRefreshPreview(record)">从数据源同步</a>
            <a-divider type="vertical" />
            <a style="color: #ff4d4f" @click="confirmDelete(record)">删除</a>
          </a-space>
        </template>
      </template>
    </a-table>

    <!-- 刷新预检弹窗 -->
    <a-modal
      v-model:open="previewModal"
      :title="previewArchive ? `刷新预检 — ${previewArchive.name}` : '刷新预检：检测到以下变化'"
      width="760px"
      okText="确认更新"
      cancelText="取消"
      :bodyStyle="{ maxHeight: '65vh', overflowY: 'auto' }"
      @ok="confirmRefresh"
    >
      <template v-if="previewData">
        <template v-if="previewData.schema_changes?.has_changes">
          <a-alert type="warning" show-icon style="margin-bottom: 12px">
            <template #message>模型结构有变化，确认后将先同步结构再刷新数据（schema 版本 +1）</template>
          </a-alert>
          <div v-if="previewData.schema_changes.added?.length" style="margin-bottom: 8px">
            <b>新增字段：</b>
            <a-tag v-for="f in previewData.schema_changes.added" :key="f.code" color="green">{{ f.name }}</a-tag>
          </div>
          <div v-if="previewData.schema_changes.removed?.length" style="margin-bottom: 8px">
            <b>移除字段：</b>
            <a-tag v-for="f in previewData.schema_changes.removed" :key="f.code" color="red">{{ f.name }}</a-tag>
          </div>
          <div v-if="previewData.schema_changes.changed?.length" style="margin-bottom: 8px">
            <b>字段变更：</b>
            <div v-for="f in previewData.schema_changes.changed" :key="f.code" style="margin: 4px 0 0 12px">
              <span style="color: #1890ff">{{ f.name }}</span>
              <span v-for="(c, i) in f.changes" :key="i" style="margin-left: 8px; color: #666">
                {{ c.attr }}：<span style="color: #ff4d4f">{{ c.old ?? '-' }}</span> → <span style="color: #52c41a">{{ c.new ?? '-' }}</span>
              </span>
            </div>
          </div>
          <a-divider style="margin: 12px 0" />
        </template>
        <template v-if="previewData.data_changes?.has_changes">
          <div style="margin-bottom: 8px">
            <b>数据变化：</b>
            <a-tag v-if="previewData.data_changes.would_create" color="green">新增 {{ previewData.data_changes.would_create }} 条</a-tag>
            <a-tag v-if="previewData.data_changes.would_update" color="blue">更新 {{ previewData.data_changes.would_update }} 条</a-tag>
            <a-tag v-if="previewData.data_changes.would_deactivate" color="orange">源侧已删将停用 {{ previewData.data_changes.would_deactivate }} 条</a-tag>
          </div>
          <a-table
            v-if="previewData.data_changes.changes_sample?.length"
            :dataSource="previewData.data_changes.changes_sample"
            :columns="[{ title: '记录标识', dataIndex: 'record_key', key: 'record_key', width: 140 }, { title: '字段变化', key: 'fields' }]"
            :pagination="false"
            rowKey="record_key"
            size="small"
            :scroll="{ y: 240 }"
          >
            <template #bodyCell="{ column, record: s }">
              <template v-if="column.key === 'fields'">
                <div v-for="(cf, i) in s.changed_fields" :key="i" style="line-height: 1.8">
                  <span style="color: #1890ff">{{ cf.name }}</span>
                  <span style="color: #999">：</span>
                  <span style="color: #ff4d4f">{{ cf.old ?? '-' }}</span>
                  <span style="color: #999"> → </span>
                  <span style="color: #52c41a">{{ cf.new ?? '-' }}</span>
                </div>
              </template>
            </template>
          </a-table>
          <div v-if="(previewData.data_changes.would_update || 0) > (previewData.data_changes.changes_sample?.length || 0)" style="color: #999; margin-top: 4px">
            仅展示前 {{ previewData.data_changes.changes_sample?.length }} 条变化样本
          </div>
        </template>
        <a-alert v-if="previewData.data_changes?.errors?.length" type="error" show-icon style="margin-top: 8px">
          <template #message>试算遇到错误：{{ previewData.data_changes.errors.slice(0, 5).join('；') }}</template>
        </a-alert>
      </template>
    </a-modal>

    <a-modal
      v-model:open="createModal"
      title="新建档案"
      @ok="handleCreate"
      :confirmLoading="creating"
      width="500px"
    >
      <a-form layout="vertical">
        <a-form-item label="所属域" required>
          <a-select v-model:value="createForm.domain" placeholder="选择域（一个域只能创建一个档案）" @change="onDomainChange">
            <a-select-option v-for="d in availableDomains" :key="d.id" :value="d.id">{{ d.name }}</a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item label="档案名称" required>
          <a-input v-model:value="createForm.name" placeholder="档案名称" />
        </a-form-item>
        <a-form-item label="描述">
          <a-textarea v-model:value="createForm.description" placeholder="描述" :rows="3" />
        </a-form-item>
        <a-form-item label="创建人">
          <a-input v-model:value="createForm.created_by" placeholder="创建人" />
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { message, Modal } from 'ant-design-vue'
import { domainApi } from '@/api/modeling'
import { archiveApi } from '@/api/archive'
import { formatDateTime } from '@/utils/date'
import { extractApiError } from '@/utils/apiError'
import type { Domain, Archive } from '@/types'

const router = useRouter()
const archives = ref<Archive[]>([])
const domains = ref<Domain[]>([])
const loading = ref(false)
const page = ref(1)
const total = ref(0)
const createModal = ref(false)
const creating = ref(false)
const createForm = ref<any>({ domain: null, name: '', description: '', created_by: '' })

// 刷新预检
const previewModal = ref(false)
const previewData = ref<any>(null)
const previewArchive = ref<Archive | null>(null)

const columns = [
  { title: '档案名称', key: 'name', width: 220, ellipsis: true },
  { title: '所属域', dataIndex: 'domain_name', key: 'domain_name', width: 120, ellipsis: true },
  { title: '状态', key: 'status', width: 80 },
  { title: 'Schema版本', dataIndex: 'schema_version', key: 'schema_version', width: 100 },
  { title: '记录数', dataIndex: 'record_count', key: 'record_count', width: 70 },
  { title: '创建人', dataIndex: 'created_by', key: 'created_by', width: 90, ellipsis: true },
  { title: '创建时间', dataIndex: 'created_at', key: 'created_at', width: 160,
    customRender: ({ text }: any) => formatDateTime(text) },
  { title: '操作', key: 'action', width: 340, fixed: 'right' },
]

function statusColor(s: string) {
  return { draft: 'default', active: 'green', archived: 'blue' }[s] || 'default'
}
function statusLabel(s: string) {
  return { draft: '草稿', active: '已发布', archived: '已归档' }[s] || s
}

// 可选域 = 还没有档案的域
const availableDomains = computed(() => {
  const archivedDomainIds = new Set(archives.value.map(a => a.domain))
  return domains.value.filter(d => !archivedDomainIds.has(d.id))
})

async function loadDomains() {
  const res = await domainApi.list()
  domains.value = res.data.results
}

async function loadData() {
  loading.value = true
  try {
    const res = await archiveApi.list({ page: page.value })
    archives.value = res.data.results
    total.value = res.data.count
  } finally {
    loading.value = false
  }
}

function onDomainChange() {
  // 自动填充名称
  const d = domains.value.find((x) => x.id === createForm.value.domain)
  if (d && !createForm.value.name) {
    createForm.value.name = `${d.name} 主数据档案`
  }
}

function openCreate() {
  createForm.value = { domain: null, name: '', description: '', created_by: '' }
  if (availableDomains.value.length === 0) {
    message.warning('所有域都已创建档案，无法再新建')
    return
  }
  createModal.value = true
}

async function handleCreate() {
  if (!createForm.value.domain || !createForm.value.name) {
    message.warning('请选择域并填写档案名称')
    return
  }
  creating.value = true
  try {
    const res = await archiveApi.create({
      domain: createForm.value.domain,
      name: createForm.value.name,
      description: createForm.value.description,
      created_by: createForm.value.created_by,
    })
    message.success('创建成功，已自动从域的标准模型生成 Schema')
    createModal.value = false
    await loadData()
  } catch (e: any) {
    const err = e.response?.data
    if (err?.domain && (err.domain[0]?.code === 'unique' || err.domain[0]?.code === 'unique_together')) {
      message.error('该域已有档案，一个域只能创建一个档案')
    } else {
      message.error(e.message || '创建失败')
    }
  } finally {
    creating.value = false
  }
}

// 刷新预检工作流：先预检源与档案差异，有变化弹窗确认后再执行
async function doRefreshPreview(archive: Archive) {
  previewArchive.value = archive
  try {
    const res = await archiveApi.refreshPreview(archive.id)
    previewData.value = res.data
    const schemaChanged = !!res.data?.schema_changes?.has_changes
    const dataChanged = !!res.data?.data_changes?.has_changes
    const errors: string[] = res.data?.data_changes?.errors || []
    if (!schemaChanged && !dataChanged) {
      if (errors.length > 0) {
        Modal.warning({ title: '预检未能完成', content: errors.slice(0, 10).join('\n') })
      } else {
        message.success('检查完成：源与档案无变化，数据已是最新')
      }
      return
    }
    previewModal.value = true
  } catch (e: any) {
    message.error(extractApiError(e) || e.message || '预检失败')
  }
}

async function confirmRefresh() {
  if (!previewArchive.value) return
  previewModal.value = false
  const archiveId = previewArchive.value.id
  try {
    if (previewData.value?.schema_changes?.has_changes) {
      const res = await archiveApi.syncSchema(archiveId)
      const stats = res.data.sync_stats
      const parts: string[] = []
      if (stats) {
        if ((stats.tables_synced ?? 0) > 0) parts.push(`同步了 ${stats.tables_synced} 张表`)
        if (stats.records_created > 0) parts.push(`新增 ${stats.records_created} 条记录`)
        if (stats.records_updated > 0) parts.push(`更新 ${stats.records_updated} 条记录`)
      }
      message.success(`同步完成：${parts.length ? parts.join('，') : 'Schema 已更新'}`)
    } else {
      const res = await archiveApi.refreshData(archiveId)
      const stats = res.data.sync_stats
      const parts: string[] = []
      if (stats) {
        if (stats.records_created > 0) parts.push(`新增 ${stats.records_created} 条`)
        if (stats.records_updated > 0) parts.push(`更新 ${stats.records_updated} 条`)
        if ((stats.records_deactivated ?? 0) > 0) parts.push(`停用 ${stats.records_deactivated} 条`)
      }
      message.success(`刷新完成：${parts.length ? parts.join('，') : '数据已是最新'}`)
    }
    await loadData()
  } catch (e: any) {
    message.error(extractApiError(e) || e.message || '同步失败')
  }
}

function goDetail(archive: Archive) {
  router.push(`/archive/${archive.id}`)
}

function goConsistency(archive: Archive) {
  router.push(`/archive/${archive.id}/consistency`)
}

function confirmDelete(record: Archive) {
  Modal.confirm({
    title: '确定删除此档案？',
    content: `档案「${record.name}」将被删除，此操作不可恢复。`,
    okType: 'danger',
    okText: '删除',
    cancelText: '取消',
    onOk: () => doDelete(record.id),
  })
}

async function doDelete(id: number) {
  try {
    await archiveApi.delete(id)
    message.success('删除成功')
    await loadData()
  } catch (e: any) {
    message.error(e.message || '删除失败')
  }
}

onMounted(async () => {
  await loadDomains()
  await loadData()
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
