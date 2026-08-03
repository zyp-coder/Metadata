<template>
  <div>
    <a-page-header
      :title="`一致性检查：${archiveName || '...'}`"
      sub-title="组合字段非主字段成员值与主字段值比对（纯内部管理，不回写任何源表）"
      @back="router.push('/archive')"
    >
      <template #extra>
        <a-button type="primary" :loading="checking" @click="runCheck">重新检查</a-button>
      </template>
    </a-page-header>

    <!-- 统计卡 -->
    <a-row :gutter="12" style="margin-bottom: 12px">
      <a-col :span="4"><a-card size="small"><a-statistic title="待审核" :value="statusCount.open" :value-style="{ color: '#fa8c16' }" /></a-card></a-col>
      <a-col :span="4"><a-card size="small"><a-statistic title="已审核" :value="statusCount.reviewed" :value-style="{ color: '#13c2c2' }" /></a-card></a-col>
      <a-col :span="4"><a-card size="small"><a-statistic title="已忽略" :value="statusCount.ignored" /></a-card></a-col>
      <a-col :span="4"><a-card size="small"><a-statistic title="已消失" :value="statusCount.resolved" :value-style="{ color: '#52c41a' }" /></a-card></a-col>
      <a-col :span="8">
        <a-card size="small" v-if="lastCheck">
          <div style="font-size: 12px; color: #888; line-height: 1.9">
            <div>上次检查：{{ formatDateTime(lastCheck.checked_at) }}，检查 {{ lastCheck.checked_fields }} 个组合字段、{{ lastCheck.tables_checked }} 张表</div>
            <div>
              发现差异 {{ lastCheck.mismatch_count }} 处（新增 {{ lastCheck.new_issues }}、重现 {{ lastCheck.reopened_issues }}、自动消失 {{ lastCheck.resolved_issues }}）
              <span v-if="lastCheck.errors?.length" style="color: #ff4d4f">，{{ lastCheck.errors.length }} 个错误</span>
            </div>
          </div>
        </a-card>
      </a-col>
    </a-row>

    <!-- 筛选 + 批量操作 -->
    <a-space style="margin-bottom: 12px" wrap>
      <a-select v-model:value="filterStatus" style="width: 130px" allow-clear placeholder="状态" @change="onFilterChange">
        <a-select-option value="open">待审核</a-select-option>
        <a-select-option value="reviewed">已审核</a-select-option>
        <a-select-option value="ignored">已忽略</a-select-option>
        <a-select-option value="resolved">已消失</a-select-option>
      </a-select>
      <a-select v-model:value="filterField" style="width: 200px" allow-clear placeholder="字段" @change="onFilterChange">
        <a-select-option v-for="f in fieldOptions" :key="f.code" :value="f.code">{{ f.name || f.code }}</a-select-option>
      </a-select>
      <a-input-search v-model:value="filterKey" style="width: 200px" allow-clear placeholder="记录标识" @search="onFilterChange" />
      <a-divider type="vertical" />
      <span v-if="selectedIds.length" style="color: #1890ff">已选 {{ selectedIds.length }} 条</span>
      <a-button :disabled="!selectedIds.length" @click="openReviewModal('reviewed')">标记已审核</a-button>
      <a-button :disabled="!selectedIds.length" @click="openReviewModal('ignored')">标记忽略</a-button>
      <a-button :disabled="!selectedIds.length" @click="openReviewModal('reopen')">重新打开</a-button>
    </a-space>

    <a-table
      :columns="columns"
      :data-source="issues"
      :loading="loading"
      rowKey="id"
      size="small"
      :row-selection="{ selectedRowKeys: selectedIds, onChange: (keys: any) => { selectedIds = keys } }"
      :pagination="{ current: page, pageSize: 20, total, onChange: (p: number) => { page = p; loadIssues() }, showTotal: (t: number) => `共 ${t} 条` }"
      :scroll="{ x: 1100 }"
      :expandedRowKeys="expandedKeys"
      @expand="onExpand"
    >
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'time'">
          <div style="font-size: 12px; font-weight: 500">{{ formatDateTime(record.first_found_at) }}</div>
          <div v-if="record.last_checked_at" style="font-size: 11px; color: #999">复检：{{ formatDateTime(record.last_checked_at) }}</div>
        </template>
        <template v-if="column.key === 'source_field'">
          <div>
            <a-tag color="blue" style="margin-right: 4px">{{ record.member_source }}</a-tag>
            <span style="font-weight: 500">{{ record.field_name || record.field_code }}</span>
          </div>
          <div style="font-size: 11px; color: #999">code: {{ record.field_code }}</div>
        </template>
        <template v-if="column.key === 'diff'">
          <div style="line-height: 2">
            <div><span style="color: #999; font-size: 11px">主({{ record.primary_source }})：</span><span style="color: #1890ff; font-weight: 500">{{ record.primary_value ?? '空' }}</span></div>
            <div><span style="color: #999; font-size: 11px">成员值：</span><span style="color: #fa541c; font-weight: 500">{{ record.member_value ?? '空' }}</span></div>
          </div>
        </template>
        <template v-if="column.key === 'record_key'">
          <span>{{ record.record_key }}</span>
        </template>
        <template v-if="column.key === 'status'">
          <a-tag :color="statusColor(record.status)">{{ record.status_display }}</a-tag>
        </template>
        <template v-if="column.key === 'review'">
          <template v-if="record.reviewed_at">
            <div style="font-size: 12px">{{ record.reviewed_by }} · {{ formatDateTime(record.reviewed_at) }}</div>
            <div v-if="record.review_note" style="font-size: 12px; color: #999">{{ record.review_note }}</div>
          </template>
          <span v-else style="color: #ccc">-</span>
        </template>
      </template>
      <!-- 展开行：历史差异值时间线 -->
      <template #expandedRowRender="{ record }">
        <div style="padding: 8px 0 8px 48px">
          <div style="font-weight: 600; margin-bottom: 6px; color: #555">差异值变化历史（{{ record.value_history?.length || 0 }} 条）</div>
          <a-table
            v-if="record.value_history?.length"
            :dataSource="record.value_history"
            :columns="historyColumns"
            :pagination="false"
            rowKey="id"
            size="small"
            :scroll="{ y: 200 }"
          >
            <template #bodyCell="{ column, record: h }">
              <template v-if="column.key === 'h_time'">{{ formatDateTime(h.checked_at) }}</template>
              <template v-if="column.key === 'h_primary'"><span style="color: #1890ff">{{ h.primary_value ?? '空' }}</span></template>
              <template v-if="column.key === 'h_member'"><span style="color: #fa541c">{{ h.member_value ?? '空' }}</span></template>
            </template>
          </a-table>
          <a-empty v-else description="暂无历史记录（首次发现）" :image="null" style="margin: 0; font-size: 12px; color: #999" />
        </div>
      </template>
    </a-table>

    <!-- 批量标记弹窗 -->
    <a-modal
      v-model:open="reviewModal"
      :title="`${actionLabel[reviewAction]}（${selectedIds.length} 条）`"
      :confirmLoading="reviewing"
      @ok="doBatchReview"
    >
      <a-alert
        v-if="reviewAction !== 'reopen'"
        type="info"
        show-icon
        style="margin-bottom: 12px"
        message="仅标记状态并写入变更日志批次，不修改档案数据，也不回写任何源表。"
      />
      <a-form layout="vertical">
        <a-form-item label="备注">
          <a-textarea v-model:value="reviewNote" :rows="3" :maxlength="500" placeholder="审核说明（可选）" />
        </a-form-item>
        <a-form-item label="操作人">
          <a-input v-model:value="reviewOperator" placeholder="操作人" />
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { archiveApi, consistencyApi } from '@/api/archive'
import { formatDateTime } from '@/utils/date'
import { extractApiError } from '@/utils/apiError'
import type { ConsistencyIssue } from '@/types'

const route = useRoute()
const router = useRouter()
const archiveId = Number(route.params.id)

const archiveName = ref('')
const issues = ref<ConsistencyIssue[]>([])
const loading = ref(false)
const checking = ref(false)
const page = ref(1)
const total = ref(0)
const selectedIds = ref<number[]>([])
const expandedKeys = ref<number[]>([])
const statusCount = ref<Record<string, number>>({ open: 0, reviewed: 0, ignored: 0, resolved: 0 })
const fieldOptions = ref<{ code: string; name: string }[]>([])
const lastCheck = ref<any>(null)

const filterStatus = ref<string | undefined>('open')
const filterField = ref<string | undefined>(undefined)
const filterKey = ref('')

const reviewModal = ref(false)
const reviewAction = ref<'reviewed' | 'ignored' | 'reopen'>('reviewed')
const reviewNote = ref('')
const reviewOperator = ref('admin')
const reviewing = ref(false)
const actionLabel: Record<string, string> = { reviewed: '标记已审核', ignored: '标记忽略', reopen: '重新打开' }

// 主表列：强调 发现时间→成员表.字段→差异对比→记录标识→状态→审核
const columns = [
  { title: '发现时间', key: 'time', width: 150 },
  { title: '成员表 · 字段', key: 'source_field', width: 200 },
  { title: '差异对比', key: 'diff', width: 240 },
  { title: '记录标识', key: 'record_key', width: 140, ellipsis: true },
  { title: '状态', key: 'status', width: 90 },
  { title: '审核信息', key: 'review', width: 200 },
]

// 展开行内嵌历史表列
const historyColumns = [
  { title: '检查时间', key: 'h_time', width: 160 },
  { title: '主字段值', key: 'h_primary', width: 200 },
  { title: '成员值', key: 'h_member', width: 200 },
]

function statusColor(s: string) {
  return ({ open: 'orange', reviewed: 'cyan', ignored: 'default', resolved: 'green' } as Record<string, string>)[s] || 'default'
}

function onExpand(expanded: boolean, record: ConsistencyIssue) {
  if (expanded) {
    expandedKeys.value = [...expandedKeys.value, record.id]
  } else {
    expandedKeys.value = expandedKeys.value.filter(k => k !== record.id)
  }
}

async function loadArchive() {
  try {
    const res = await archiveApi.get(archiveId)
    archiveName.value = res.data.name
  } catch { /* 非关键 */ }
}

async function loadIssues() {
  loading.value = true
  try {
    const params: any = { archive: archiveId, page: page.value }
    if (filterStatus.value) params.status = filterStatus.value
    if (filterField.value) params.field_code = filterField.value
    if (filterKey.value) params.record_key = filterKey.value
    const res = await consistencyApi.list(params)
    issues.value = res.data.results
    total.value = res.data.count
  } catch (e: any) {
    message.error(extractApiError(e) || '加载差异清单失败')
  } finally {
    loading.value = false
  }
}

// 各状态计数 + 字段筛选项
async function loadStats() {
  try {
    const reqs = ['open', 'reviewed', 'ignored', 'resolved'].map(s =>
      consistencyApi.list({ archive: archiveId, status: s, page_size: 1 }))
    const results = await Promise.all(reqs)
    statusCount.value = {
      open: results[0].data.count,
      reviewed: results[1].data.count,
      ignored: results[2].data.count,
      resolved: results[3].data.count,
    }
  } catch { /* 非关键 */ }
  try {
    const res = await consistencyApi.list({ archive: archiveId, page_size: 200 })
    const seen = new Map<string, string>()
    res.data.results.forEach(i => { if (!seen.has(i.field_code)) seen.set(i.field_code, i.field_name) })
    fieldOptions.value = [...seen.entries()].map(([code, name]) => ({ code, name }))
  } catch { /* 非关键 */ }
}

async function runCheck() {
  checking.value = true
  try {
    const res = await archiveApi.consistencyCheck(archiveId)
    const stats = res.data
    lastCheck.value = stats
    if (stats.message) {
      message.info(stats.message)
    } else {
      const parts = [`发现差异 ${stats.mismatch_count} 处`]
      if (stats.new_issues) parts.push(`新增 ${stats.new_issues}`)
      if (stats.reopened_issues) parts.push(`重现 ${stats.reopened_issues}`)
      if (stats.resolved_issues) parts.push(`自动消失 ${stats.resolved_issues}`)
      if (stats.errors?.length) parts.push(`${stats.errors.length} 个错误`)
      message.success(`检查完成：${parts.join('，')}`)
    }
    page.value = 1
    selectedIds.value = []
    expandedKeys.value = []
    await Promise.all([loadIssues(), loadStats()])
  } catch (e: any) {
    message.error(extractApiError(e) || '一致性检查失败')
  } finally {
    checking.value = false
  }
}

function onFilterChange() {
  page.value = 1
  selectedIds.value = []
  expandedKeys.value = []
  loadIssues()
}

// R-030: allow-clear 清空后自动重查
watch(filterKey, (val) => {
  if (!val) onFilterChange()
})

function openReviewModal(action: 'reviewed' | 'ignored' | 'reopen') {
  reviewAction.value = action
  reviewNote.value = ''
  reviewModal.value = true
}

async function doBatchReview() {
  reviewing.value = true
  try {
    const res = await consistencyApi.batchReview({
      ids: selectedIds.value,
      action: reviewAction.value,
      note: reviewNote.value,
      operated_by: reviewOperator.value || 'admin',
    })
    const d = res.data
    message.success(`${actionLabel[reviewAction.value]}完成：更新 ${d.updated} 条，跳过 ${d.skipped} 条（已写入变更日志批次）`)
    reviewModal.value = false
    selectedIds.value = []
    await Promise.all([loadIssues(), loadStats()])
  } catch (e: any) {
    message.error(extractApiError(e) || '批量标记失败')
  } finally {
    reviewing.value = false
  }
}

onMounted(() => {
  loadArchive()
  loadIssues()
  loadStats()
})
</script>
