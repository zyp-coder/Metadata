<template>
  <div>
    <a-page-header
      :title="`一致性检查：${archiveName || '...'}`"
      sub-title="多种检查类型打包展示（纯内部管理，不回写任何源表）"
      @back="router.push('/archive')"
    >
      <template #extra>
        <a-space>
          <a-button @click="showRulesDrawer = true">失效规则</a-button>
          <a-button type="primary" :loading="checking" @click="runCheck">重新检查</a-button>
        </a-space>
      </template>
    </a-page-header>

    <!-- 上次检查摘要 -->
    <a-card v-if="lastCheck" size="small" style="margin-bottom: 12px">
      <div style="font-size: 12px; color: #666; line-height: 1.8">
        上次检查：{{ formatDateTime(lastCheck.checked_at) }}，
        差异 {{ lastCheck.mismatch_count }} 处
        （新增 {{ lastCheck.new_issues }}、重现 {{ lastCheck.reopened_issues }}、消失 {{ lastCheck.resolved_issues }}）
        <span v-if="lastCheck.errors?.length" style="color: #ff4d4f">，{{ lastCheck.errors.length }} 个错误</span>
      </div>
    </a-card>

    <!-- 检查类型分组卡片 -->
    <a-row :gutter="12" style="margin-bottom: 16px">
      <a-col :span="6" v-for="ct in checkTypes" :key="ct.key">
        <a-card
          size="small"
          :style="expandedType === ct.key ? 'border-color:#1890ff;cursor:pointer' : 'cursor:pointer'"
          @click="toggleType(ct.key)"
        >
          <a-statistic :title="ct.label" :value="typeCounts[ct.key] || 0" :value-style="{ color: typeCounts[ct.key] ? ct.color : '#bfbfbf' }" />
          <div style="font-size: 11px; color: #999; margin-top: 4px">
            待审 {{ typeStatusCounts[ct.key]?.open || 0 }} /
            已审 {{ typeStatusCounts[ct.key]?.reviewed || 0 }} /
            忽略 {{ typeStatusCounts[ct.key]?.ignored || 0 }}
          </div>
        </a-card>
      </a-col>
    </a-row>

    <!-- 展开的检查类型详情 -->
    <template v-if="expandedType">
      <a-card size="small" :title="expandedTypeLabel" style="margin-bottom: 12px">
        <template #extra>
          <a-space>
            <a-select v-model:value="filterStatus" style="width: 120px" allow-clear placeholder="状态" size="small" @change="loadGroupedIssues">
              <a-select-option value="open">待审核</a-select-option>
              <a-select-option value="reviewed">已审核</a-select-option>
              <a-select-option value="ignored">已忽略</a-select-option>
              <a-select-option value="resolved">已消失</a-select-option>
            </a-select>
            <a-input-search v-model:value="filterKey" style="width: 180px" allow-clear placeholder="搜索记录标识" size="small" @search="loadGroupedIssues" />
          </a-space>
        </template>

        <a-spin :spinning="loading">
          <!-- 按日期分组 -->
          <a-empty v-if="!groupedIssues.length" description="暂无差异记录" />
          <div v-for="group in groupedIssues" :key="group.date" style="margin-bottom: 12px">
            <div
              style="display:flex;align-items:center;gap:8px;padding:6px 0;border-bottom:1px solid #f0f0f0;cursor:pointer"
              @click="toggleDateGroup(group.date)"
            >
              <span style="font-size:12px;color:#999">{{ expandedDates.has(group.date) ? '▾' : '▸' }}</span>
              <span style="font-weight:500">{{ group.date }}</span>
              <a-tag>{{ group.issues.length }} 条</a-tag>
              <span style="font-size:11px;color:#999">
                首次发现 {{ group.issues.filter(i => !i.last_checked_at || i.last_checked_at.startsWith(group.date)).length }} 条
              </span>
            </div>
            <a-table
              v-if="expandedDates.has(group.date)"
              :columns="issueColumns"
              :data-source="group.issues"
              rowKey="id"
              size="small"
              :pagination="false"
              style="margin-top: 4px"
              :row-selection="{ selectedRowKeys: selectedIds, onChange: (keys: any) => { selectedIds = keys } }"
            >
              <template #bodyCell="{ column, record }">
                <template v-if="column.key === 'field'">
                  <span>{{ record.field_name || record.field_code || '—' }}</span>
                  <div v-if="record.field_code" style="font-size:11px;color:#999">{{ record.field_code }}</div>
                </template>
                <template v-if="column.key === 'diff'">
                  <template v-if="record.check_type === 'composite_member'">
                    <span style="color:#1890ff">{{ record.primary_value ?? '空' }}</span>
                    <span style="color:#999;margin:0 4px">→</span>
                    <span style="color:#fa541c">{{ record.member_value ?? '空' }}</span>
                    <div style="font-size:11px;color:#bbb">{{ record.primary_source }} vs {{ record.member_source }}</div>
                  </template>
                  <template v-else-if="record.check_type === 'archive_source_diff'">
                    <span style="color:#722ed1">档案:{{ record.primary_value ?? '空' }}</span>
                    <span style="color:#999;margin:0 4px">vs</span>
                    <span style="color:#fa541c">源:{{ record.member_value ?? '空' }}</span>
                  </template>
                  <template v-else-if="record.check_type === 'orphan_source_record'">
                    <a-tag color="red">{{ record.member_source }}</a-tag>
                    <span style="font-size:11px">主键: {{ record.record_key }}</span>
                  </template>
                  <template v-else-if="record.check_type === 'schema_drift'">
                    <span style="color:#1890ff">{{ record.primary_value }}</span>
                    <span style="color:#999;margin:0 4px">→</span>
                    <span style="color:#fa541c">{{ record.member_value }}</span>
                    <div v-if="record.detail?.issue" style="font-size:11px;color:#999">
                      {{ record.detail.issue === 'field_removed' ? '字段已移除' : '类型已变更' }}
                    </div>
                  </template>
                </template>
                <template v-if="column.key === 'record_key'">
                  <span style="font-size:12px">{{ record.record_key || '—' }}</span>
                </template>
                <template v-if="column.key === 'status'">
                  <a-tag :color="statusColor(record.status)" style="font-size:11px">{{ record.status_display }}</a-tag>
                </template>
                <template v-if="column.key === 'action'">
                  <a-button type="link" size="small" danger @click="disableRuleForIssue(record)">失效</a-button>
                </template>
              </template>
            </a-table>
          </div>
        </a-spin>

        <!-- 批量操作 -->
        <div v-if="selectedIds.length" style="margin-top:12px;display:flex;gap:8px;align-items:center">
          <span style="color:#1890ff">已选 {{ selectedIds.length }} 条</span>
          <a-button size="small" @click="openReviewModal('reviewed')">标记已审</a-button>
          <a-button size="small" @click="openReviewModal('ignored')">标记忽略</a-button>
          <a-button size="small" @click="openReviewModal('reopen')">重新打开</a-button>
        </div>
      </a-card>
    </template>

    <!-- 批量标记弹窗 -->
    <a-modal v-model:open="reviewModal" :title="`${actionLabel[reviewAction]}（${selectedIds.length} 条）`" :confirmLoading="reviewing" @ok="doBatchReview">
      <a-form layout="vertical">
        <a-form-item label="备注"><a-textarea v-model:value="reviewNote" :rows="2" :maxlength="500" /></a-form-item>
        <a-form-item label="操作人"><a-input v-model:value="reviewOperator" /></a-form-item>
      </a-form>
    </a-modal>

    <!-- 失效规则弹窗 -->
    <a-modal v-model:open="disableRuleModal" title="失效检查规则" :confirmLoading="disablingRule" @ok="submitDisableRule">
      <a-alert type="warning" show-icon style="margin-bottom:12px">
        <template #message>失效后该规则不再产生新差异</template>
      </a-alert>
      <a-form layout="vertical">
        <a-form-item label="类型"><span>{{ disableRuleTypeLabel }}</span></a-form-item>
        <a-form-item label="字段"><span>{{ disableRuleField || '（全部）' }}</span></a-form-item>
        <a-form-item label="原因"><a-textarea v-model:value="disableRuleReason" :rows="2" /></a-form-item>
        <a-form-item label="操作人"><a-input v-model:value="disableRuleOperator" /></a-form-item>
      </a-form>
    </a-modal>

    <!-- 失效规则管理抽屉 -->
    <a-drawer v-model:open="showRulesDrawer" title="失效规则管理" width="50vw">
      <a-table :columns="ruleColumns" :data-source="disabledRules" :loading="rulesLoading" rowKey="id" size="small" :pagination="false">
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'r_type'"><a-tag :color="checkTypeColor[record.check_type]">{{ record.check_type_display }}</a-tag></template>
          <template v-if="column.key === 'r_field'">{{ record.field_code || '（全部）' }}</template>
          <template v-if="column.key === 'r_reason'">{{ record.disabled_reason || '—' }}</template>
          <template v-if="column.key === 'r_action'">
            <a-popconfirm title="确认恢复？" @confirm="enableRule(record)"><a-button type="link" size="small">恢复</a-button></a-popconfirm>
            <a @click="confirmDeleteRule(record)" style="color: #ff4d4f; font-size: 12px; margin-left: 8px">删除</a>
          </template>
        </template>
      </a-table>
    </a-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { message, Modal } from 'ant-design-vue'
import { archiveApi, consistencyApi, consistencyRuleApi } from '@/api/archive'
import { formatDateTime } from '@/utils/date'
import { extractApiError } from '@/utils/apiError'
import type { ConsistencyIssue, ConsistencyCheckRule, CheckType } from '@/types'

const route = useRoute()
const router = useRouter()
const archiveId = Number(route.params.id)

const archiveName = ref('')
const loading = ref(false)
const checking = ref(false)
const lastCheck = ref<any>(null)
const selectedIds = ref<number[]>([])

// 检查类型配置
const checkTypes = [
  { key: 'composite_member', label: '组合字段成员', color: '#1890ff' },
  { key: 'archive_source_diff', label: '档案vs源差异', color: '#722ed1' },
  { key: 'orphan_source_record', label: '源侧孤立记录', color: '#ff4d4f' },
  { key: 'schema_drift', label: 'Schema漂移', color: '#fa8c16' },
]
const checkTypeColor: Record<string, string> = { composite_member: 'blue', archive_source_diff: 'purple', orphan_source_record: 'red', schema_drift: 'orange' }

// 类型计数
const typeCounts = ref<Record<string, number>>({})
const typeStatusCounts = ref<Record<string, Record<string, number>>>({})

// 展开的类型和日期
const expandedType = ref<string | null>(null)
const expandedDates = ref(new Set<string>())

// 分组后的差异
const groupedIssues = ref<{ date: string; issues: ConsistencyIssue[] }[]>([])

// 筛选
const filterStatus = ref<string | undefined>(undefined)
const filterKey = ref('')

// 批量标记
const reviewModal = ref(false)
const reviewAction = ref<'reviewed' | 'ignored' | 'reopen'>('reviewed')
const reviewNote = ref('')
const reviewOperator = ref('')
const reviewing = ref(false)
const actionLabel: Record<string, string> = { reviewed: '标记已审核', ignored: '标记忽略', reopen: '重新打开' }

// 失效规则
const disableRuleModal = ref(false)
const disablingRule = ref(false)
const disableRuleType = ref('')
const disableRuleField = ref('')
const disableRuleMemberSource = ref('')
const disableRuleReason = ref('')
const disableRuleOperator = ref('')
const showRulesDrawer = ref(false)
const disabledRules = ref<ConsistencyCheckRule[]>([])
const rulesLoading = ref(false)

const expandedTypeLabel = computed(() => checkTypes.find(t => t.key === expandedType.value)?.label || '')
const disableRuleTypeLabel = computed(() => checkTypes.find(t => t.key === disableRuleType.value)?.label || '')

const issueColumns = [
  { title: '字段', key: 'field', width: 160 },
  { title: '差异', key: 'diff', width: 280 },
  { title: '记录标识', key: 'record_key', width: 140, ellipsis: true },
  { title: '状态', key: 'status', width: 80 },
  { title: '操作', key: 'action', width: 70 },
]

const ruleColumns = [
  { title: '类型', key: 'r_type', width: 130 },
  { title: '字段', key: 'r_field', width: 140 },
  { title: '原因', key: 'r_reason' },
  { title: '操作', key: 'r_action', width: 120 },
]

function statusColor(s: string) {
  return ({ open: 'orange', reviewed: 'cyan', ignored: 'default', resolved: 'green' } as Record<string, string>)[s] || 'default'
}

async function loadArchive() {
  try {
    const res = await archiveApi.get(archiveId)
    archiveName.value = res.data.name
  } catch { /* 非关键 */ }
}

// 加载各类型的计数
async function loadTypeCounts() {
  for (const ct of checkTypes) {
    try {
      const [allRes, openRes, reviewedRes, ignoredRes] = await Promise.all([
        consistencyApi.list({ archive: archiveId, check_type: ct.key, page_size: 1 }),
        consistencyApi.list({ archive: archiveId, check_type: ct.key, status: 'open', page_size: 1 }),
        consistencyApi.list({ archive: archiveId, check_type: ct.key, status: 'reviewed', page_size: 1 }),
        consistencyApi.list({ archive: archiveId, check_type: ct.key, status: 'ignored', page_size: 1 }),
      ])
      typeCounts.value[ct.key] = allRes.data.count
      typeStatusCounts.value[ct.key] = {
        open: openRes.data.count,
        reviewed: reviewedRes.data.count,
        ignored: ignoredRes.data.count,
      }
    } catch { /* 非关键 */ }
  }
}

// 切换类型展开
function toggleType(ctKey: string) {
  if (expandedType.value === ctKey) {
    expandedType.value = null
    groupedIssues.value = []
  } else {
    expandedType.value = ctKey
    expandedDates.value = new Set()
    loadGroupedIssues()
  }
}

// 加载展开类型的分组数据
async function loadGroupedIssues() {
  if (!expandedType.value) return
  loading.value = true
  try {
    const params: any = { archive: archiveId, check_type: expandedType.value, page_size: 500 }
    if (filterStatus.value) params.status = filterStatus.value
    if (filterKey.value) params.record_key = filterKey.value
    const res = await consistencyApi.list(params)
    const issues = res.data.results

    // 按日期分组
    const dateMap = new Map<string, ConsistencyIssue[]>()
    for (const issue of issues) {
      const date = (issue.first_found_at || '').slice(0, 10) || '未知日期'
      if (!dateMap.has(date)) dateMap.set(date, [])
      dateMap.get(date)!.push(issue)
    }
    groupedIssues.value = [...dateMap.entries()]
      .sort(([a], [b]) => b.localeCompare(a))
      .map(([date, items]) => ({ date, issues: items }))
  } catch (e: any) {
    message.error(extractApiError(e) || '加载失败')
  } finally {
    loading.value = false
  }
}

function toggleDateGroup(date: string) {
  const s = new Set(expandedDates.value)
  if (s.has(date)) s.delete(date)
  else s.add(date)
  expandedDates.value = s
}

async function runCheck() {
  checking.value = true
  try {
    const res = await archiveApi.consistencyCheck(archiveId)
    lastCheck.value = res.data
    const parts = [`差异 ${res.data.mismatch_count} 处`]
    if (res.data.new_issues) parts.push(`新增 ${res.data.new_issues}`)
    if (res.data.resolved_issues) parts.push(`消失 ${res.data.resolved_issues}`)
    message.success(`检查完成：${parts.join('，')}`)
    selectedIds.value = []
    await Promise.all([loadTypeCounts(), loadGroupedIssues()])
  } catch (e: any) {
    message.error(extractApiError(e) || '检查失败')
  } finally {
    checking.value = false
  }
}

// 批量标记
function openReviewModal(action: 'reviewed' | 'ignored' | 'reopen') {
  reviewAction.value = action
  reviewNote.value = ''
  reviewModal.value = true
}

async function doBatchReview() {
  reviewing.value = true
  try {
    const res = await consistencyApi.batchReview({
      ids: selectedIds.value, action: reviewAction.value,
      note: reviewNote.value, operated_by: reviewOperator.value,
    })
    message.success(`${actionLabel[reviewAction.value]}完成：更新 ${res.data.updated} 条`)
    reviewModal.value = false
    selectedIds.value = []
    await Promise.all([loadTypeCounts(), loadGroupedIssues()])
  } catch (e: any) {
    message.error(extractApiError(e) || '标记失败')
  } finally {
    reviewing.value = false
  }
}

// 失效规则
function disableRuleForIssue(issue: ConsistencyIssue) {
  disableRuleType.value = issue.check_type
  disableRuleField.value = issue.field_code || ''
  disableRuleMemberSource.value = issue.member_source || ''
  disableRuleReason.value = ''
  disableRuleOperator.value = ''
  disableRuleModal.value = true
}

async function submitDisableRule() {
  disablingRule.value = true
  try {
    await consistencyRuleApi.disable({
      archive: archiveId, check_type: disableRuleType.value,
      field_code: disableRuleField.value || undefined,
      member_source: disableRuleMemberSource.value || undefined,
      reason: disableRuleReason.value, operated_by: disableRuleOperator.value || 'system',
    })
    message.success('规则已失效')
    disableRuleModal.value = false
  } catch (e: any) {
    message.error(extractApiError(e) || '失效失败')
  } finally {
    disablingRule.value = false
  }
}

async function loadDisabledRules() {
  rulesLoading.value = true
  try {
    const res = await consistencyRuleApi.list({ archive: archiveId, disabled: 'true' })
    disabledRules.value = res.data.results
  } catch { /* 非关键 */ } finally { rulesLoading.value = false }
}

async function enableRule(rule: ConsistencyCheckRule) {
  try {
    await consistencyRuleApi.enable({ archive: archiveId, check_type: rule.check_type, field_code: rule.field_code || undefined, member_source: rule.member_source || undefined })
    message.success('规则已恢复')
    await loadDisabledRules()
  } catch (e: any) { message.error(extractApiError(e) || '恢复失败') }
}

async function deleteRule(rule: ConsistencyCheckRule) {
  try {
    await consistencyRuleApi.delete(rule.id)
    message.success('已删除')
    await loadDisabledRules()
  } catch (e: any) { message.error(extractApiError(e) || '删除失败') }
}

function confirmDeleteRule(rule: ConsistencyCheckRule) {
  Modal.confirm({
    title: '确认删除此失效规则？',
    content: `删除后该规则将永久移除，不可恢复。`,
    okType: 'danger',
    okText: '删除',
    cancelText: '取消',
    onOk: () => deleteRule(rule),
  })
}

watch(showRulesDrawer, (val) => { if (val) loadDisabledRules() })
watch(filterKey, (val) => { if (!val) loadGroupedIssues() })

onMounted(() => {
  loadArchive()
  loadTypeCounts()
})
</script>
