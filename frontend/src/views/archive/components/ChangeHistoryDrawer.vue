<template>
  <!-- 变更历史抽屉（R-057 收敛单组件：ArchiveDetail 带回滚 / VersionManagement 只读，两处引用防分叉） -->
  <a-drawer
    :open="open"
    :title="title || '变更历史'"
    width="900px"
    :destroyOnClose="true"
    @close="emit('update:open', false)"
  >
    <div v-if="loading" style="text-align: center; padding: 24px">
      <a-spin tip="加载变更历史..." />
    </div>
    <a-empty v-else-if="historyList.length === 0" description="该记录暂无变更历史" />
    <a-timeline v-else style="padding: 8px 4px 0">
      <a-timeline-item v-for="(item, index) in historyList" :key="item.id" :color="timelineColor(item.change_type)">
        <div style="display: flex; justify-content: space-between; gap: 12px">
          <div style="flex: 1; min-width: 0">
            <div>
              <a-tag :color="changeTypeColor(item.change_type)">{{ item.change_type_display }}</a-tag>
              <a-tag :color="sourceColor(item.change_source)">{{ item.change_source_display }}</a-tag>
              <span style="color: #999; font-size: 12px">{{ formatDateTime(item.created_at) }}</span>
              <span style="margin-left: 8px; color: #666; font-size: 12px">{{ item.operator }}</span>
              <span v-if="item.version_before != null" style="margin-left: 8px; color: #999; font-size: 12px">v{{ item.version_before }} → v{{ item.version_after }}</span>
            </div>
            <div v-if="item.change_type === 'detail_sync' && item.field_changes?.length" style="margin-top: 6px">
              <template v-for="(fc, fi) in item.field_changes" :key="fi">
                <div v-if="fc.detail_stats" style="font-size: 12px; color: #666; line-height: 1.8">
                  <span>明细行变更：</span>
                  <span v-if="fc.detail_stats.created > 0" style="color: #52c41a">新增 {{ fc.detail_stats.created }} 行</span>
                  <span v-if="fc.detail_stats.created > 0 && (fc.detail_stats.updated > 0 || fc.detail_stats.deactivated > 0)" style="margin: 0 4px">·</span>
                  <span v-if="fc.detail_stats.updated > 0" style="color: #1890ff">更新 {{ fc.detail_stats.updated }} 行</span>
                  <span v-if="fc.detail_stats.updated > 0 && fc.detail_stats.deactivated > 0" style="margin: 0 4px">·</span>
                  <span v-if="fc.detail_stats.deactivated > 0" style="color: #ff4d4f">移除 {{ fc.detail_stats.deactivated }} 行</span>
                </div>
              </template>
            </div>
            <div v-else-if="item.field_changes?.length" style="margin-top: 6px">
              <div v-for="(fc, fi) in item.field_changes" :key="fi" style="font-size: 12px; line-height: 1.9">
                <span style="color: #1890ff">{{ fc.name || fc.field }}</span>
                <span style="color: #999">：</span>
                <span style="color: #ff4d4f">{{ fc.old ?? '-' }}</span>
                <span style="color: #999"> → </span>
                <span style="color: #52c41a">{{ fc.new ?? '-' }}</span>
              </div>
            </div>
            <div v-else-if="['created', 'deactivated'].includes(item.change_type)" style="color: #999; font-size: 12px; margin-top: 4px">
              （记录级变更，无字段级变化）
            </div>
            <div v-else-if="item.detail_group != null" style="margin-top: 4px; font-size: 12px; color: #999">
              关联明细行：{{ item.detail_row_key || '-' }}
            </div>
          </div>
          <a-dropdown v-if="enableRollback && (canRollbackDetail(item) || canRollbackToPoint(index))" :trigger="['click']">
            <a-button size="small" :loading="rollbackingId === item.id">回滚 ▾</a-button>
            <template #overlay>
              <a-menu>
                <a-menu-item v-if="canRollbackDetail(item)" @click="handleRollbackSingle(item)">回滚此条</a-menu-item>
                <a-menu-item v-if="canRollbackToPoint(index)" danger @click="handleRollbackToChange(item)">回滚到此</a-menu-item>
              </a-menu>
            </template>
          </a-dropdown>
        </div>
      </a-timeline-item>
    </a-timeline>
  </a-drawer>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { message, Modal } from 'ant-design-vue'
import { archiveRecordApi, changeLogApi } from '@/api/archive'
import { extractApiError } from '@/utils/apiError'
import type { ChangeDetail } from '@/types'
import { formatDateTime } from '@/utils/date'

const props = withDefaults(defineProps<{
  open: boolean
  recordId: number | null
  title?: string
  enableRollback?: boolean
}>(), {
  title: '',
  enableRollback: false,
})

const emit = defineEmits<{
  (e: 'update:open', open: boolean): void
  (e: 'rolled-back', recordId: number): void
}>()

const loading = ref(false)
const historyList = ref<ChangeDetail[]>([])
const rollbackingId = ref<number | null>(null)

// 打开时全量分页加载（原 ArchiveDetail 侧仅单页 50 条，收敛后统一全量口径）
watch(() => props.open, (v) => {
  if (v && props.recordId != null) loadHistory(props.recordId)
})

async function loadHistory(recordId: number) {
  loading.value = true
  historyList.value = []
  try {
    const all: ChangeDetail[] = []
    let page = 1
    for (;;) {
      const res = await changeLogApi.listDetails({ record: recordId, page, page_size: 200, ordering: '-id' })
      all.push(...(res.data.results as ChangeDetail[]))
      if (all.length >= res.data.count || !res.data.results.length) break
      page++
    }
    historyList.value = all
  } catch {
    historyList.value = []
  } finally {
    loading.value = false
  }
}

// a-timeline 节点色（完整版映射，统一两处口径）
function timelineColor(changeType: string) {
  return ({ updated: 'blue', deactivated: 'red', reactivated: 'green', reviewed: 'gray', ignored: 'gray', rollback: 'orange', detail_sync: 'cyan' } as Record<string, string>)[changeType] || 'blue'
}

function changeTypeColor(changeType: string) {
  return ({ created: 'green', updated: 'blue', deactivated: 'red', reactivated: 'purple', reviewed: 'cyan', ignored: 'default', rollback: 'volcano', detail_sync: 'geekblue' } as Record<string, string>)[changeType] || 'default'
}

function sourceColor(s: string) {
  return ({ sync: 'geekblue', manual: 'orange', consistency: 'cyan' } as Record<string, string>)[s] || 'orange'
}

// ===== 双粒度回滚（仅 enableRollback 时启用；v18 语义：恢复到本条变更之前，之后变更一并撤销） =====

function canRollbackDetail(item: ChangeDetail) {
  if (['created', 'rollback', 'detail_sync'].includes(item.change_type)) return false
  // v18：有版本映射可按快照恢复；存量明细降级字段级，需有变更字段
  return item.version_before != null || (item.field_changes?.length ?? 0) > 0
}

// 能否「回滚到此时点」：时间线按 id 降序（最新在前），需存在比当前节点更新且可撤销的变更，否则后端必然 400
function canRollbackToPoint(index: number) {
  return historyList.value.slice(0, index).some(c => !['created', 'rollback'].includes(c.change_type))
}

function handleRollbackSingle(item: ChangeDetail) {
  const isSyncSource = item.change_source === 'sync'
  const warningText = isSyncSource ? '\n\n⚠️ 此变更来自源系统同步，回滚后下次刷新可能再次被覆盖。' : ''
  const content = item.version_before != null
    ? `将把这条记录恢复到本条变更之前的状态（v${item.version_before}），本条之后的变更会一并撤销。${warningText}`
    : `将把这条变更涉及的 ${item.field_changes?.length || 0} 个字段恢复到变更前的值（早期历史明细，逐字段恢复，不影响其它变更）。${warningText}`
  Modal.confirm({
    title: '确认回滚这条变更',
    content,
    okText: '确认回滚',
    okType: 'danger',
    cancelText: '取消',
    async onOk() {
      rollbackingId.value = item.id
      try {
        const res = await changeLogApi.rollback(item.id)
        const data = res.data
        if (data.rolled_back_fields === 0) {
          message.info(data.message || '所有字段已是目标值，无需回滚')
        } else {
          message.success(`已回滚 ${data.rolled_back_fields} 个字段`)
          afterRollback()
        }
      } catch (e: any) {
        message.error(extractApiError(e))
      } finally {
        rollbackingId.value = null
      }
    },
  })
}

function handleRollbackToChange(item: ChangeDetail) {
  if (props.recordId == null) return
  const isSyncSource = item.change_source === 'sync'
  const warningText = isSyncSource ? '\n\n⚠️ 此变更来自源系统同步，回滚后下次刷新可能再次被覆盖。' : ''
  Modal.confirm({
    title: '确认回滚到此时点',
    content: `将撤销此条变更之后的所有修改，恢复到该时点的状态。${warningText}`,
    okText: '确认回滚',
    okType: 'danger',
    cancelText: '取消',
    async onOk() {
      rollbackingId.value = item.id
      try {
        const res = await archiveRecordApi.rollbackToChange(props.recordId!, item.id)
        const data = res.data
        if (data.rolled_back_fields === 0) {
          message.info(data.message || '所有字段已是目标值，无需回滚')
        } else {
          message.success(`已回滚 ${data.rolled_back_fields} 个字段到该时点`)
          afterRollback()
        }
      } catch (e: any) {
        message.error(extractApiError(e))
      } finally {
        rollbackingId.value = null
      }
    },
  })
}

// 回滚成功：组件内重载时间线 + 通知父组件刷新列表/详情上下文
function afterRollback() {
  if (props.recordId != null) {
    emit('rolled-back', props.recordId)
    loadHistory(props.recordId)
  }
}
</script>
