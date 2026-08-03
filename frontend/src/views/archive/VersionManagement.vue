<template>
  <div>
    <div class="page-header" style="display: flex; justify-content: space-between; align-items: center">
      <h2>{{ domainName ? `${domainName} — 变更日志` : '变更日志' }}</h2>
      <a-space>
        <a-button v-if="changeFilter.archive" :loading="exporting" @click="exportExcel">导出 Excel</a-button>
      </a-space>
    </div>

    <a-card style="margin-bottom: 16px">
      <a-space wrap>
        <a-select
          v-model:value="changeFilter.archive"
          placeholder="选择档案（默认全部）"
          style="width: 220px"
          allow-clear
          @change="reloadChanges"
        >
          <a-select-option v-for="a in archives" :key="a.id" :value="a.id">{{ a.name }}</a-select-option>
        </a-select>
        <a-select v-model:value="changeFilter.change_source" style="width: 140px" placeholder="变更来源" allow-clear @change="reloadChanges">
          <a-select-option value="sync">源侧同步</a-select-option>
          <a-select-option value="manual">档案侧编辑</a-select-option>
          <a-select-option value="consistency">一致性处理</a-select-option>
        </a-select>
        <a-select v-model:value="changeFilter.change_type" style="width: 120px" placeholder="变更类型" allow-clear @change="reloadChanges">
          <a-select-option value="created">新增</a-select-option>
          <a-select-option value="updated">修改</a-select-option>
          <a-select-option value="deactivated">停用</a-select-option>
          <a-select-option value="reactivated">复活</a-select-option>
        </a-select>
        <a-input-search v-model:value="changeFilter.record_key" style="width: 200px" placeholder="按记录标识搜索" allow-clear @search="reloadChanges" />
        <a-button @click="reloadChanges">查询</a-button>
      </a-space>
    </a-card>

    <a-table
      :dataSource="changeDetails"
      :columns="changeColumns"
      :loading="changeLoading"
      rowKey="id"
      size="small"
      :scroll="{ x: 1300 }"
      :pagination="{ current: changePage, pageSize: 20, total: changeTotal, onChange: (p: number) => { changePage = p; loadChangeDetails() }, showTotal: (t: number) => `共 ${t} 条` }"
    >
      <template #bodyCell="{ column, record: cd }">
        <template v-if="column.key === 'created_at'">{{ formatDateTime(cd.created_at) }}</template>
        <template v-if="column.key === 'record_label'">
          <a-tooltip :title="cd.record_label || cd.record_key">
            <span>{{ cd.record_label || cd.record_key || '-' }}</span>
          </a-tooltip>
        </template>
        <template v-if="column.key === 'change_source'">
          <a-tag :color="changeSourceColor(cd.change_source)">{{ cd.change_source_display }}</a-tag>
        </template>
        <template v-if="column.key === 'change_type'">
          <a-tag :color="changeTypeColor(cd.change_type)">{{ cd.change_type_display }}</a-tag>
        </template>
        <template v-if="column.key === 'field_changes'">
          <template v-if="cd.field_changes?.length">
            <div v-for="(fc, idx) in cd.field_changes.slice(0, 5)" :key="idx" style="line-height: 1.8">
              <span style="color: #1890ff">{{ fc.name || fc.field }}</span>
              <span style="color: #999">：</span>
              <span style="color: #ff4d4f">{{ fc.old ?? '-' }}</span>
              <span style="color: #999"> → </span>
              <span style="color: #52c41a">{{ fc.new ?? '-' }}</span>
            </div>
            <div v-if="cd.field_changes.length > 5" style="color: #999">…等 {{ cd.field_changes.length }} 项</div>
          </template>
          <span v-else style="color: #999">-</span>
        </template>
        <template v-if="column.key === 'cd_action'">
          <a-space :size="4">
            <a @click="gotoArchive(cd.archive)">进入档案</a>
            <a-divider type="vertical" />
            <a
              :class="{ 'disabled-link': !canRollback(cd) }"
              @click="canRollback(cd) && handleRollback(cd)"
            >回滚</a>
          </a-space>
        </template>
      </template>
    </a-table>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { message, Modal } from 'ant-design-vue'
import { archiveApi, changeLogApi, downloadBlob } from '@/api/archive'
import type { Archive, ChangeDetail } from '@/types'
import { formatDateTime } from '@/utils/date'

const route = useRoute()
const router = useRouter()
const archives = ref<Archive[]>([])
const domainName = ref('')
const exporting = ref(false)

const changeDetails = ref<ChangeDetail[]>([])
const changeLoading = ref(false)
const changePage = ref(1)
const changeTotal = ref(0)
const changeFilter = ref<{ archive?: number; change_source?: string; change_type?: string; record_key?: string }>({})

const changeColumns = [
  { title: '变更时间', key: 'created_at', width: 160 },
  { title: '所属档案', dataIndex: 'archive_name', key: 'archive_name', width: 150, ellipsis: true },
  { title: '记录信息', key: 'record_label', width: 220, ellipsis: true },
  { title: '来源', key: 'change_source', width: 100 },
  { title: '类型', key: 'change_type', width: 80 },
  { title: '字段变化', key: 'field_changes', width: 360 },
  { title: '操作人', dataIndex: 'operator', key: 'operator', width: 90 },
  { title: '操作', key: 'cd_action', width: 140 },
]

function changeTypeColor(t: string) {
  return ({ created: 'green', updated: 'blue', deactivated: 'red', reactivated: 'purple', reviewed: 'cyan', ignored: 'default', rollback: 'volcano' } as Record<string, string>)[t] || 'default'
}

function changeSourceColor(s: string) {
  return ({ sync: 'geekblue', manual: 'orange', consistency: 'cyan' } as Record<string, string>)[s] || 'orange'
}

async function loadChangeDetails() {
  changeLoading.value = true
  try {
    const params: Record<string, any> = { page: changePage.value }
    const f = changeFilter.value
    if (f.archive) params.archive = f.archive
    if (f.change_source) params.change_source = f.change_source
    if (f.change_type) params.change_type = f.change_type
    if (f.record_key) params.record_key = f.record_key
    const res = await changeLogApi.listDetails(params)
    changeDetails.value = res.data.results
    changeTotal.value = res.data.count
  } catch (e: any) {
    message.error(e.message || '加载变更日志失败')
  } finally {
    changeLoading.value = false
  }
}

function reloadChanges() {
  changePage.value = 1
  loadChangeDetails()
}

function gotoArchive(archiveId: number) {
  router.push(`/archive/${archiveId}`)
}

// ===== 回滚功能 =====
function canRollback(cd: ChangeDetail) {
  // created / rollback 类型不可回滚；无关联记录（已删）也不可
  return cd.record != null && !['created', 'rollback'].includes(cd.change_type) && (cd.field_changes?.length ?? 0) > 0
}

function handleRollback(cd: ChangeDetail) {
  const isSyncSource = cd.change_source === 'sync'
  const content = isSyncSource
    ? '⚠️ 此变更来自源系统同步，回滚后下次刷新可能再次被覆盖。\n\n确认要将该条变更涉及的字段恢复到变更前的值吗？'
    : `确认要回滚此条变更吗？涉及 ${cd.field_changes?.length || 0} 个字段将恢复到变更前的值。`
  Modal.confirm({
    title: '确认回滚',
    content,
    okText: '确认回滚',
    okType: 'danger',
    cancelText: '取消',
    async onOk() {
      try {
        const res = await changeLogApi.rollback(cd.id)
        const data = res.data
        if (data.rolled_back_fields === 0) {
          message.info(data.message || '所有字段已是目标值，无需回滚')
        } else {
          message.success(`已回滚 ${data.rolled_back_fields} 个字段`)
        }
        loadChangeDetails()
      } catch (e: any) {
        message.error(e.response?.data?.error || e.message || '回滚失败')
      }
    },
  })
}

async function exportExcel() {
  if (!changeFilter.value.archive) {
    message.info('请先选择一个档案后再导出')
    return
  }
  exporting.value = true
  try {
    const res = await changeLogApi.exportExcel(changeFilter.value.archive)
    const archiveName = archives.value.find(a => a.id === changeFilter.value.archive)?.name || ''
    downloadBlob(res, `变更日志_${archiveName}.xlsx`)
    message.success('导出成功')
  } catch (e: any) {
    message.error(e.message || '导出失败')
  } finally {
    exporting.value = false
  }
}

onMounted(async () => {
  const domainId = route.query.domain ? Number(route.query.domain) : undefined
  domainName.value = (route.query.domain_name as string) || ''
  try {
    const res = await archiveApi.list({ page_size: 1000 })
    archives.value = res.data.results
    if (domainId) {
      const domainArchives = archives.value.filter(a => a.domain === domainId)
      if (domainArchives.length === 1) {
        changeFilter.value.archive = domainArchives[0].id
      }
    }
  } catch { /* 忽略档案下拉加载失败 */ }
  loadChangeDetails()
})
</script>

<style scoped>
.disabled-link {
  color: #d9d9d9 !important;
  cursor: not-allowed;
  pointer-events: none;
}
</style>
