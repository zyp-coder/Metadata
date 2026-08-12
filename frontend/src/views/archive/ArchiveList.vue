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
      :scroll="{ x: 1220 }"
      :pagination="{ current: page, pageSize: 20, total, onChange: (p: number) => { page = p; loadData() } }"
    >
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'name'">
          <span style="font-weight: 500">{{ record.name }}</span>
        </template>
        <template v-if="column.key === 'status'">
          <a-tag :color="statusColor(record.status)">{{ statusLabel(record.status) }}</a-tag>
        </template>
        <template v-if="column.key === 'action'">
          <a-space :size="4" style="white-space: nowrap">
            <a @click="goDetail(record)">编辑</a>
            <a-divider type="vertical" />
            <a @click="goConsistency(record)">检查</a>
            <a-divider type="vertical" />
            <a @click="doRefreshPreview(record)">同步</a>
            <template v-if="isAdmin">
              <a-divider type="vertical" />
              <a @click="openPermissionOverview(record)">权限</a>
            </template>
            <a-divider type="vertical" />
            <a style="color: #ff4d4f" @click="confirmDelete(record)">删除</a>
          </a-space>
        </template>
      </template>
    </a-table>

    <!-- 刷新预检弹窗（schema 变化+数据试算+波及告警+warnings） | R-062：收敛为 RefreshPreviewModal 单组件，确认意图上抛父组件执行 -->
    <RefreshPreviewModal
      v-model:open="previewModal"
      :previewData="previewData"
      :archiveName="previewArchive?.name ?? ''"
      @confirm="confirmRefresh"
    />

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

    <!-- 权限全景抽屉（仅管理员，只读审计视图） -->
    <PermissionOverview
      v-model:open="permOverviewVisible"
      :archive-id="permOverviewArchive?.id ?? null"
      :archive-name="permOverviewArchive?.name ?? ''"
    />

  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { message, Modal, notification } from 'ant-design-vue'
import { domainApi } from '@/api/modeling'
import { archiveApi } from '@/api/archive'
import { getMeApi } from '@/api/auth'
import { formatDateTime } from '@/utils/date'
import { extractApiError } from '@/utils/apiError'
import PermissionOverview from './components/PermissionOverview.vue'
import RefreshPreviewModal from './components/RefreshPreviewModal.vue'
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

// 权限全景（仅管理员可见入口，后端另有 IsMdmAdmin 403 拦截）
const isAdmin = ref(false)
const permOverviewVisible = ref(false)
const permOverviewArchive = ref<Archive | null>(null)

function openPermissionOverview(record: Archive) {
  permOverviewArchive.value = record
  permOverviewVisible.value = true
}

const columns = [
  { title: '档案名称', key: 'name', width: 200, ellipsis: true },
  { title: '所属域', dataIndex: 'domain_name', key: 'domain_name', width: 120, ellipsis: true },
  { title: '状态', key: 'status', width: 80 },
  { title: 'Schema版本', dataIndex: 'schema_version', key: 'schema_version', width: 100 },
  { title: '记录数', dataIndex: 'record_count', key: 'record_count', width: 70 },
  { title: '创建人', dataIndex: 'created_by', key: 'created_by', width: 90, ellipsis: true },
  { title: '创建时间', dataIndex: 'created_at', key: 'created_at', width: 160,
    customRender: ({ text }: any) => formatDateTime(text) },
  { title: '操作', key: 'action', width: 320, fixed: 'right' },
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
      message.error(extractApiError(e) || '创建失败')
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
    message.error(extractApiError(e) || '预检失败')
  }
}

async function confirmRefresh() {
  if (!previewArchive.value) return
  previewModal.value = false
  const archiveId = previewArchive.value.id
  try {
    const res = previewData.value?.schema_changes?.has_changes
      ? await archiveApi.syncSchema(archiveId)
      : await archiveApi.refreshData(archiveId)
    const stats = res.data.sync_stats
    if (stats) {
      const parts: string[] = []
      if ((stats.tables_synced ?? 0) > 0) parts.push(`${previewData.value?.schema_changes?.has_changes ? '同步' : '刷新'}了 ${stats.tables_synced} 张表`)
      if (stats.records_created > 0) parts.push(`新增 ${stats.records_created} 条`)
      if (stats.records_updated > 0) parts.push(`更新 ${stats.records_updated} 条`)
      if ((stats.records_deactivated ?? 0) > 0) parts.push(`停用 ${stats.records_deactivated} 条`)
      if ((stats.records_reactivated ?? 0) > 0) parts.push(`源侧恢复，复活 ${stats.records_reactivated} 条`)
      if (parts.length === 0) parts.push('数据已是最新')
      if (stats.errors?.length > 0) {
        Modal.warning({ title: `完成，但有 ${stats.errors.length} 个错误`, content: stats.errors.slice(0, 10).join('\n') })
      } else if (stats.warnings && stats.warnings.length > 0) {
        message.success(parts.join('，'))
        Modal.warning({ title: `${stats.warnings.length} 条提醒`, content: stats.warnings.slice(0, 10).join('\n') })
      } else {
        message.success(parts.join('，'))
      }
      // 一致性检查告警（不阻断）
      const cc = stats?.consistency_check
      if (cc && cc.mismatch_count > 0) {
        notification.warning({
          message: `一致性提醒：${cc.mismatch_records} 条记录、${cc.mismatch_count} 处不一致`,
          description: '数据已以主字段为准写入，不一致项仅为提醒，可稍后到一致性检查页处理。',
          duration: 8,
          style: { width: 360 },
        })
      }
    } else {
      message.success('操作完成')
    }
    await loadData()
  } catch (e: any) {
    message.error(extractApiError(e) || '同步失败')
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
    title: '确认删除此档案？',
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
    message.error(extractApiError(e) || '删除失败')
  }
}

onMounted(async () => {
  await loadDomains()
  await loadData()
  // 当前用户是否管理员（决定「权限」入口可见性）
  try {
    const { data } = await getMeApi()
    isAdmin.value = !!data.user?.is_admin
  } catch { /* 判定失败按非管理员处理，不阻断页面 */ }
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
