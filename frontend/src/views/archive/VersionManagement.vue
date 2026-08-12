<template>
  <div>
    <div class="page-header" style="display: flex; justify-content: space-between; align-items: center">
      <h2>{{ domainName ? `${domainName} — 变更日志` : '变更日志' }}</h2>
      <a-space>
        <a-button v-if="batchFilter.archive" :loading="exporting" @click="exportExcel">导出 Excel</a-button>
      </a-space>
    </div>

    <!-- v18 汇总卡：近 7 天变更概况（业务视角看事件，不看版本） -->
    <a-row :gutter="12" style="margin-bottom: 16px">
      <a-col :span="6">
        <a-card size="small"><a-statistic title="近 7 天变更批次" :value="weekStats.batch_count" /></a-card>
      </a-col>
      <a-col :span="6">
        <a-card size="small"><a-statistic title="近 7 天新增记录" :value="weekStats.records_created" :value-style="{ color: '#52c41a' }" /></a-card>
      </a-col>
      <a-col :span="6">
        <a-card size="small"><a-statistic title="近 7 天修改记录" :value="weekStats.records_updated" :value-style="{ color: '#1890ff' }" /></a-card>
      </a-col>
      <a-col :span="6">
        <a-card size="small"><a-statistic title="近 7 天回滚恢复" :value="weekStats.records_rolled_back" :value-style="{ color: '#fa8c16' }" /></a-card>
      </a-col>
    </a-row>

    <a-card style="margin-bottom: 16px">
      <a-space wrap>
        <a-select
          v-model:value="batchFilter.archive"
          placeholder="选择档案（默认全部）"
          style="width: 220px"
          allow-clear
          @change="reloadBatches"
        >
          <a-select-option v-for="a in archives" :key="a.id" :value="a.id">{{ a.name }}</a-select-option>
        </a-select>
        <a-select v-model:value="batchFilter.change_source" style="width: 140px" placeholder="变更来源" allow-clear @change="reloadBatches">
          <a-select-option value="sync">源侧同步</a-select-option>
          <a-select-option value="manual">档案侧编辑</a-select-option>
          <a-select-option value="consistency">一致性处理</a-select-option>
        </a-select>
        <a-button @click="reloadBatches">查询</a-button>
      </a-space>
    </a-card>

    <!-- 批次视图（v18.1：仅按时间一层折叠）：同档案同日的所有批次合并为一个日期行，展开直出全部明细；批次降为明细行的字段 -->
    <a-table
      :dataSource="dayRows"
      :columns="dayColumns"
      :loading="batchLoading"
      rowKey="rowKey"
      childrenColumnName="details"
      size="small"
      :scroll="{ x: 1200 }"
      v-model:expandedRowKeys="expandedKeys"
      @expand="onExpandDay"
      :pagination="{ current: batchPage, pageSize: 20, total: dayRows.length, onChange: (p: number) => batchPage = p, showTotal: (t: number) => `共 ${t} 行` }"
    >
      <template #bodyCell="{ column, record: row }">
        <!-- 日期折叠行（一天 = 一行，展开看当天全部明细） -->
        <template v-if="row.isDayRow">
          <template v-if="column.key === 'time'">
            <b>{{ row.date }}</b>
            <a-tag color="default" style="margin-left: 8px">{{ row.batchIds.length }} 个批次</a-tag>
          </template>
          <template v-if="column.key === 'record_label'">{{ row.archive_name }}</template>
          <template v-if="column.key === 'field_changes'">
            <a-tag v-if="row.agg.created" color="green">新增 {{ row.agg.created }}</a-tag>
            <a-tag v-if="row.agg.updated" color="blue">修改 {{ row.agg.updated }}</a-tag>
            <a-tag v-if="row.agg.deactivated" color="red">停用 {{ row.agg.deactivated }}</a-tag>
            <a-tag v-if="row.agg.reactivated" color="purple">复活 {{ row.agg.reactivated }}</a-tag>
            <a-tag v-if="row.agg.rolled_back" color="orange">回滚 {{ row.agg.rolled_back }}</a-tag>
            <div v-if="daySummary(row)" style="color: #666; margin-top: 2px">{{ daySummary(row) }}</div>
          </template>
          <template v-if="column.key === 'd_action'">
            <a
              :class="{ 'disabled-link': !rollbackableBatches(row).length }"
              @click="rollbackableBatches(row).length && handleRollbackDay(row)"
            >撤销本日全部</a>
          </template>
        </template>
        <!-- 明细子行（批次号作为字段展示；占位行也走此分支） -->
        <template v-else-if="row.isDetailRow">
          <template v-if="column.key === 'time'">
            <template v-if="row.cd">
              <span style="color: #999">└ {{ formatTime(row.cd.created_at) }}</span>
              <a-tag color="default" style="margin-left: 6px">#{{ row.batchId }}</a-tag>
            </template>
            <span v-else style="color: #999">{{ row.note || '加载中…' }}</span>
          </template>
          <template v-if="row.cd && column.key === 'record_label'">
            <a-tooltip :title="row.cd.record_label || row.cd.record_key">
              <span>{{ row.cd.record_label || row.cd.record_key || '-' }}</span>
            </a-tooltip>
          </template>
          <template v-if="row.cd && column.key === 'change_type'">
            <a-tag :color="changeTypeColor(row.cd.change_type)">{{ row.cd.change_type_display }}</a-tag>
          </template>
          <template v-if="row.cd && column.key === 'operator'">{{ row.cd.operator }}</template>
          <template v-if="row.cd && column.key === 'field_changes'">
            <template v-if="row.cd.field_changes?.length">
              <div v-for="(fc, idx) in row.cd.field_changes.slice(0, 3)" :key="idx" style="line-height: 1.8">
                <span style="color: #1890ff">{{ fc.name || fc.field }}</span>
                <span style="color: #999">：</span>
                <span style="color: #ff4d4f">{{ fc.old ?? '-' }}</span>
                <span style="color: #999"> → </span>
                <span style="color: #52c41a">{{ fc.new ?? '-' }}</span>
              </div>
              <div v-if="row.cd.field_changes.length > 3" style="color: #999">…等 {{ row.cd.field_changes.length }} 项</div>
            </template>
            <span v-else style="color: #999">{{ ['created', 'deactivated'].includes(row.cd.change_type) ? '（记录级变更，无字段级变化）' : '-' }}</span>
          </template>
          <template v-if="row.cd && column.key === 'version'">
            <template v-if="row.cd.version_before != null">
              v{{ row.cd.version_before }} <span style="color: #999">→</span> v{{ row.cd.version_after }}
            </template>
            <span v-else style="color: #999">-</span>
          </template>
          <template v-if="row.cd && column.key === 'd_action'">
            <a-space :size="4">
              <template v-if="row.cd.record != null">
                <a @click="openRecordModal(row.cd)">详情</a>
                <a-divider type="vertical" />
                <a @click="openHistory(row.cd)">历史</a>
                <a-divider type="vertical" />
              </template>
              <a
                :class="{ 'disabled-link': !canRollbackDetail(row.cd) }"
                @click="canRollbackDetail(row.cd) && handleRollbackDetail(row.cd)"
              >回滚</a>
            </a-space>
          </template>
        </template>
      </template>
    </a-table>

    <!-- 记录详情弹窗（只读，套用档案页详情弹窗布局；编辑去档案页做） -->
    <a-modal
      v-model:open="recordModal"
      :title="`记录详情 — ${recordLabel}`"
      width="900px"
      :footer="null"
      :destroyOnClose="true"
      :bodyStyle="{ maxHeight: '70vh', overflowY: 'auto' }"
    >
      <div v-if="recordLoading" style="text-align: center; padding: 24px">
        <a-spin tip="加载记录详情..." />
      </div>
      <template v-else-if="recordDetail">
        <a-descriptions bordered :column="2" size="small" style="margin-bottom: 4px">
          <a-descriptions-item label="状态">
            <a-tag :color="recordDetail.status === 'active' ? 'green' : 'default'">
              {{ recordDetail.status === 'active' ? '启用' : '已停用' }}
            </a-tag>
          </a-descriptions-item>
          <a-descriptions-item label="当前版本">v{{ recordDetail.version }}</a-descriptions-item>
          <a-descriptions-item label="创建时间">{{ formatDateTime(recordDetail.created_at) }}</a-descriptions-item>
          <a-descriptions-item label="最近更新">{{ formatDateTime(recordDetail.updated_at) }}（{{ recordDetail.updated_by || '-' }}）</a-descriptions-item>
        </a-descriptions>
        <a-divider style="margin: 12px 0">业务数据</a-divider>
        <a-descriptions bordered :column="1" size="small">
          <a-descriptions-item v-for="field in recordSchema" :key="field.code">
            <template #label>
              {{ field.name }}
              <a-tag v-if="field.ownership !== 'source' && field.source !== 'computed'" color="orange" style="margin-left: 4px">档案维护</a-tag>
            </template>
            {{ formatFieldValue(recordDetail.data?.[field.code]) }}
          </a-descriptions-item>
        </a-descriptions>
        <div style="text-align: right; margin-top: 12px">
          <a-space>
            <a-button @click="openHistoryFromRecord">变更历史</a-button>
            <a-button @click="recordModal = false">关闭</a-button>
          </a-space>
        </div>
      </template>
    </a-modal>

    <!-- 变更历史抽屉（单条记录全部变更时间线，只读；回滚在列表明细行操作） | R-057：收敛为 ChangeHistoryDrawer 单组件 -->
    <ChangeHistoryDrawer
      v-model:open="historyOpen"
      :recordId="historyRecordId"
      :title="`变更历史 — ${historyLabel}`"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { message, Modal } from 'ant-design-vue'
import { archiveApi, archiveRecordApi, changeLogApi, downloadBlob } from '@/api/archive'
import { extractApiError } from '@/utils/apiError'
import type { Archive, ArchiveRecord, ChangeBatch, ChangeDetail } from '@/types'
import ChangeHistoryDrawer from './components/ChangeHistoryDrawer.vue'
import { formatDateTime, formatDate } from '@/utils/date'

const route = useRoute()
const archives = ref<Archive[]>([])
const domainName = ref('')
const exporting = ref(false)

// ===== 日期折叠视图（v18.1：仅按时间一层折叠，批次降为明细行字段） =====
interface DayRow {
  rowKey: string
  isDayRow: true
  date: string
  archive: number
  archive_name: string
  batchIds: number[]
  batches: ChangeBatch[]   // 当日全部批次（供「撤销本日全部」筛选可撤销批）
  details?: DetailRow[]    // 展开时按需加载；占位行使展开箭头可见
  agg: { created: number; updated: number; deactivated: number; reactivated: number; rolled_back: number }
}
interface DetailRow {
  rowKey: string
  isDetailRow: true
  batchId: number
  cd?: ChangeDetail
  note?: string          // 加载中 / 无明细 / 加载失败 的占位文案
}

const batches = ref<ChangeBatch[]>([])
const batchLoading = ref(false)
const batchPage = ref(1)
const batchFilter = ref<{ archive?: number; change_source?: string }>({})
const expandedKeys = ref<string[]>([])
// dayKey → 当日已加载的明细子行（响应式，展开日行时逐批拉取；刷新批次时清空）
const dayDetails = ref<Record<string, DetailRow[]>>({})

const dayColumns = [
  { title: '日期 / 时间', key: 'time', width: 200 },
  { title: '记录 / 所属档案', key: 'record_label', width: 170, ellipsis: true },
  { title: '变更类型', key: 'change_type', width: 140 },
  { title: '操作人', dataIndex: 'operator', key: 'operator', width: 90 },
  { title: '变更概况 / 字段变化', key: 'field_changes', width: 320 },
  { title: '版本', key: 'version', width: 90 },
  { title: '操作', key: 'd_action', width: 150 },
]

// 同档案同日的所有批次合并为一个日期行（展示层折叠，数据层批次不合并）；
// 日期行预挂占位子行保证展开箭头可见，展开时才逐批拉取当日全部明细
const dayRows = computed<DayRow[]>(() => {
  const rows: DayRow[] = []
  const list = batches.value
  let i = 0
  while (i < list.length) {
    const b = list[i]
    const date = formatDate(b.created_at)
    const sameDay: ChangeBatch[] = [b]
    let j = i + 1
    while (j < list.length
      && list[j].archive === b.archive
      && formatDate(list[j].created_at) === date) {
      sameDay.push(list[j])
      j += 1
    }
    const rowKey = `day-${b.archive}-${date}`
    const agg = { created: 0, updated: 0, deactivated: 0, reactivated: 0, rolled_back: 0 }
    let detailTotal = 0
    for (const x of sameDay) {
      agg.created += x.stats?.records_created || 0
      agg.updated += x.stats?.records_updated || 0
      agg.deactivated += x.stats?.records_deactivated || 0
      agg.reactivated += x.stats?.records_reactivated || 0
      agg.rolled_back += x.stats?.records_rolled_back || 0
      detailTotal += x.detail_count || 0
    }
    rows.push({
      rowKey, isDayRow: true, date,
      archive: b.archive, archive_name: b.archive_name,
      batchIds: sameDay.map(x => x.id), batches: sameDay,
      details: dayDetails.value[rowKey]
        ?? (detailTotal > 0 ? [{ rowKey: `ph-${rowKey}`, isDetailRow: true, batchId: 0 }] : undefined),
      agg,
    })
    i = j
  }
  return rows
})

// 近 7 天汇总卡（基于已加载批次）
const weekStats = computed(() => {
  const cut = Date.now() - 7 * 86400000
  const s = { batch_count: 0, records_created: 0, records_updated: 0, records_rolled_back: 0 }
  for (const b of batches.value) {
    if (new Date(b.created_at).getTime() < cut) continue
    s.batch_count += 1
    s.records_created += b.stats?.records_created || 0
    s.records_updated += b.stats?.records_updated || 0
    s.records_rolled_back += b.stats?.records_rolled_back || 0
  }
  return s
})

// 明细行时间列只显示时分（日期已在日期行）
function formatTime(s: string) {
  const t = formatDateTime(s)
  return t.includes(' ') ? t.split(' ')[1] : t
}

function changeTypeColor(t: string) {
  return ({ created: 'green', updated: 'blue', deactivated: 'red', reactivated: 'purple', reviewed: 'cyan', ignored: 'default', rollback: 'volcano' } as Record<string, string>)[t] || 'default'
}

// 日行当日 top 字段变化摘要（展开加载完明细后显示）
function daySummary(row: DayRow): string {
  const list = dayDetails.value[row.rowKey]
  if (!list) return ''
  const counter: Record<string, number> = {}
  for (const d of list) {
    for (const fc of d.cd?.field_changes || []) {
      const name = fc.name || fc.field
      if (name) counter[name] = (counter[name] || 0) + 1
    }
  }
  const top = Object.entries(counter).sort((a, b) => b[1] - a[1]).slice(0, 3)
  return top.length ? `主要变化：${top.map(([n, c]) => `${n}×${c}`).join('，')}` : ''
}

// ===== 撤销本日全部（逐批串行撤销） =====
function rollbackableBatches(row: DayRow): ChangeBatch[] {
  // 可撤销 = 含正向数据变更（新增/修改/停用/复活）且非整批回滚产物；
  // 纯回滚批次（含明细级回滚自建批，stats 只有 records_rolled_back）不可再撤
  return row.batches.filter(b => {
    const s = b.stats || {}
    const hasForward = !!(s.records_created || s.records_updated
      || s.records_deactivated || s.records_reactivated)
    return hasForward && !s.source_batch_id
  })
}

function handleRollbackDay(row: DayRow) {
  const targets = rollbackableBatches(row)
  const unroll = row.batches.length - targets.length
  Modal.confirm({
    title: `确认撤销 ${row.date} 当日全部变更`,
    content: `将逐批撤销 ${targets.map(b => `#${b.id}`).join('、')}，把受影响记录逐条恢复到各批之前的状态。`
      + (unroll ? `\n（当日另有 ${unroll} 个批次不可撤销：回滚产生或无明细）` : '')
      + '\n批次之后又被编辑过的记录会被跳过并列出，不会静默覆盖后续修改。',
    okText: '确认撤销',
    okType: 'danger',
    cancelText: '取消',
    async onOk() {
      let rolled = 0
      const issues: string[] = []
      for (const b of targets) {
        try {
          const d = (await changeLogApi.rollbackBatch(b.id)).data
          rolled += d.rolled_back_records
          if (d.skipped_edited?.length) {
            issues.push(`批次 #${b.id} 后续又编辑过（已跳过）：${d.skipped_edited.map(s => s.record_label || s.record_key).join('、')}`)
          }
          if (d.skipped_deleted) issues.push(`批次 #${b.id} 记录已删除：${d.skipped_deleted} 条`)
          if (d.skipped_legacy) issues.push(`批次 #${b.id} 早期历史无版本映射：${d.skipped_legacy} 条`)
        } catch (e: any) {
          issues.push(`批次 #${b.id} 撤销失败：${extractApiError(e) || '未知错误'}`)
        }
      }
      if (issues.length) {
        Modal.warning({ title: `已撤销 ${rolled} 条记录，部分跳过/失败`, content: issues.join('\n') })
      } else {
        message.success(`已撤销 ${rolled} 条记录`)
      }
      // 回滚会生成新批次 → 日期行与已加载明细一起刷新
      expandedKeys.value = []
      dayDetails.value = {}
      loadBatches()
    },
  })
}

// ===== 日行展开：逐批拉取当日全部明细 =====
function onExpandDay(expanded: boolean, row: DayRow) {
  if (!expanded || !row.isDayRow) return
  if (dayDetails.value[row.rowKey]) return
  loadDayDetails(row)
}

async function loadDayDetails(row: DayRow) {
  const key = row.rowKey
  dayDetails.value[key] = [{ rowKey: `ph-${key}`, isDetailRow: true, batchId: 0, note: '加载中…' }]
  try {
    const all: DetailRow[] = []
    for (const b of row.batches) {
      if (!((b.detail_count || 0) > 0)) continue
      let page = 1
      let fetched = 0
      // 翻页拉全（单批可能超 500 条）
      for (;;) {
        const res = await changeLogApi.listDetails({ batch: b.id, page, page_size: 500 })
        const results = res.data.results as ChangeDetail[]
        for (const cd of results) {
          all.push({ rowKey: `d-${cd.id}`, isDetailRow: true, batchId: b.id, cd })
        }
        fetched += results.length
        if (fetched >= res.data.count || !results.length) break
        page += 1
      }
    }
    dayDetails.value[key] = all.length
      ? all
      : [{ rowKey: `ph-${key}`, isDetailRow: true, batchId: 0, note: '当日无变更明细' }]
  } catch (e: any) {
    dayDetails.value[key] = [{ rowKey: `ph-${key}`, isDetailRow: true, batchId: 0, note: `加载失败：${extractApiError(e) || '未知错误'}` }]
  }
}

async function loadBatches() {
  batchLoading.value = true
  try {
    const params: Record<string, any> = { page: 1, page_size: 500 }
    if (batchFilter.value.archive) params.archive = batchFilter.value.archive
    if (batchFilter.value.change_source) params.change_source = batchFilter.value.change_source
    const res = await changeLogApi.listBatches(params)
    batches.value = res.data.results
  } catch (e: any) {
    message.error(extractApiError(e) || '加载变更批次失败')
  } finally {
    batchLoading.value = false
  }
}

function reloadBatches() {
  batchPage.value = 1
  expandedKeys.value = []
  dayDetails.value = {}
  loadBatches()
}

// ===== 记录详情弹窗（只读，套用档案页详情弹窗布局） =====
const recordModal = ref(false)
const recordLoading = ref(false)
const recordDetail = ref<ArchiveRecord | null>(null)
const recordSchema = ref<any[]>([])
const recordLabel = ref('')
const historyRecordId = ref<number | null>(null)   // 详情弹窗内转变更历史用

async function openRecordModal(cd: ChangeDetail) {
  if (cd.record == null) return
  recordModal.value = true
  recordLoading.value = true
  recordDetail.value = null
  recordSchema.value = []
  recordLabel.value = cd.record_label || cd.record_key
  historyRecordId.value = cd.record
  try {
    const [recRes, arcRes] = await Promise.all([
      archiveRecordApi.get(cd.record),
      archiveApi.get(cd.archive),
    ])
    recordDetail.value = recRes.data
    recordSchema.value = arcRes.data.schema || []
  } catch (e: any) {
    message.error(extractApiError(e) || '加载记录详情失败')
    recordModal.value = false
  } finally {
    recordLoading.value = false
  }
}

function formatFieldValue(v: any): string {
  if (v == null || v === '') return '-'
  if (typeof v === 'object') return JSON.stringify(v)
  return String(v)
}

// ===== 变更历史抽屉（单条记录全部变更时间线，只读） | R-057：渲染收敛进 ChangeHistoryDrawer 组件 =====
const historyOpen = ref(false)
const historyLabel = ref('')

function openHistory(cd: ChangeDetail) {
  if (cd.record == null) return
  historyLabel.value = cd.record_label || cd.record_key
  historyRecordId.value = cd.record
  historyOpen.value = true
}

function openHistoryFromRecord() {
  if (historyRecordId.value == null) return
  if (!historyLabel.value) historyLabel.value = recordLabel.value
  recordModal.value = false
  historyOpen.value = true
}


// 单条明细回滚（v18 语义：恢复到本条变更之前的状态；存量明细降级字段级）
function canRollbackDetail(cd: ChangeDetail) {
  if (cd.record == null || ['created', 'rollback'].includes(cd.change_type)) return false
  return cd.version_before != null || (cd.field_changes?.length ?? 0) > 0
}

function handleRollbackDetail(cd: ChangeDetail) {
  const isSyncSource = cd.change_source === 'sync'
  const warningText = isSyncSource ? '\n\n⚠️ 此变更来自源系统同步，回滚后下次刷新可能再次被覆盖。' : ''
  const content = cd.version_before != null
    ? `将把这条记录恢复到本条变更之前的状态（v${cd.version_before}），本条之后的变更会一并撤销。${warningText}`
    : `将把这条变更涉及的 ${cd.field_changes?.length || 0} 个字段恢复到变更前的值（早期历史明细，逐字段恢复，不影响其它变更）。${warningText}`
  Modal.confirm({
    title: '确认回滚这条变更',
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
        // 回滚会生成新批次 → 日期行与已加载明细一起刷新
        expandedKeys.value = []
        dayDetails.value = {}
        await loadBatches()
      } catch (e: any) {
        message.error(extractApiError(e) || '回滚失败')
      }
    },
  })
}

// ===== 导出 =====
async function exportExcel() {
  if (!batchFilter.value.archive) {
    message.info('请先选择一个档案后再导出')
    return
  }
  exporting.value = true
  try {
    const res = await changeLogApi.exportExcel(batchFilter.value.archive)
    const archiveName = archives.value.find(a => a.id === batchFilter.value.archive)?.name || ''
    downloadBlob(res, `变更日志_${archiveName}.xlsx`)
    message.success('导出成功')
  } catch (e: any) {
    message.error(extractApiError(e) || '导出失败')
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
        batchFilter.value.archive = domainArchives[0].id
      }
    }
  } catch { /* 忽略档案下拉加载失败 */ }
  loadBatches()
})
</script>

<style scoped>
.disabled-link {
  color: #d9d9d9 !important;
  cursor: not-allowed;
  pointer-events: none;
}
</style>
