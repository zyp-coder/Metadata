<template>
  <div>
    <div class="page-header">
      <a-space>
        <a-button @click="goBack">← 返回列表</a-button>
        <h2>{{ archive?.name || '档案详情' }}</h2>
        <a-tag v-if="archive" :color="statusColor(archive.status)">{{ statusLabel(archive.status) }}</a-tag>
      </a-space>
      <a-space>
        <!-- v18 攒批保存：有待存修改时点亮，保存=一个人工批次 -->
        <a-tooltip :title="pendingEdits.length ? '提交待存修改，合并为一个批次' : '先在记录详情里修改并暂存'">
          <a-button :disabled="!pendingEdits.length" :loading="batchSaving" @click="savePendingEdits">
            {{ pendingEdits.length ? `保存（${pendingEdits.length} 条待存）` : '保存' }}
          </a-button>
        </a-tooltip>
        <a-button type="primary" :loading="previewLoading" @click="refreshData">立即刷新</a-button>
      </a-space>
    </div>

    <div style="min-height: calc(100vh - 180px)">
        <a-alert v-if="archive" type="info" show-icon style="margin-bottom: 12px">
          <template #message>
            所属域：{{ archive.domain_name }} | Schema 版本：v{{ archive.schema_version }} | 字段数：{{ archive.schema?.length || 0 }} | 记录数：{{ recordTotal }}
          </template>
        </a-alert>

        <!-- 筛选器 + 查询（第八十七轮问题6） -->
        <a-space style="margin-bottom: 12px" wrap>
          <a-input
            v-model:value="recordSearch"
            placeholder="按数据内容搜索（主键/任意字段值）"
            style="width: 240px"
            allowClear
            @pressEnter="doSearchRecords"
          />
          <a-select v-model:value="recordSyncFilter" placeholder="同步状态" style="width: 130px" allowClear>
            <a-select-option value="unsynced">未同步</a-select-option>
            <a-select-option value="synced">已同步</a-select-option>
            <a-select-option value="partial">部分同步</a-select-option>
            <a-select-option value="error">同步失败</a-select-option>
            <a-select-option value="stale">源侧已删</a-select-option>
          </a-select>
          <a-select v-model:value="recordStatusFilter" placeholder="记录状态" style="width: 120px" allowClear>
            <a-select-option value="active">启用</a-select-option>
            <a-select-option value="deleted">已停用</a-select-option>
          </a-select>
          <a-button type="primary" @click="doSearchRecords">查询</a-button>
          <a-button @click="resetRecordFilters">重置</a-button>
        </a-space>

        <!-- 左侧字段导航 + 记录表格（第八十七轮问题7） -->
        <div style="display: flex; gap: 12px; align-items: stretch; min-height: calc(100vh - 280px)">
          <div class="field-nav" style="height: calc(100vh - 260px); overflow-y: auto">
            <div class="field-nav-title">字段导航</div>
            <template v-for="block in groupedSchemaBlocks" :key="block.key">
              <div v-if="block.name" class="field-nav-group" :style="{ paddingLeft: (block.level - 1) * 8 + 'px' }">{{ block.name }}</div>
              <div
                v-for="f in block.fields"
                :key="f.code"
                class="field-nav-item"
                :class="{ active: highlightFieldCode === f.code }"
                :style="{ paddingLeft: block.name ? (block.level * 8 + 6) + 'px' : '6px' }"
                :title="f.name"
                @click="scrollToFieldColumn(f.code)"
              >
                {{ f.name }}
                <span class="field-nav-dv" @click.stop="openFieldDistinctValues(f)">
                  <template v-if="dvCache[f.code]">{{ dvCache[f.code].distinct_count }}</template>
                  <template v-else>值</template>
                </span>
              </div>
            </template>
          </div>
          <div ref="recordTableWrap" style="flex: 1; min-width: 0">
        <a-table
          :dataSource="records"
          :columns="dynamicColumns"
          :loading="loading"
          rowKey="id"
          size="small"
          :scroll="{ x: dynamicColumnsTotalWidth, y: 'calc(100vh - 300px)' }"
          :pagination="{ current: recordPage, pageSize: 20, total: recordTotal, onChange: (p: number) => { recordPage = p; loadRecords() }, showTotal: (t: number) => `共 ${t} 条` }"
        >
          <template #bodyCell="{ column, record: rec, index }">
            <template v-if="column.key === 'rowIndex'">
              {{ (recordPage - 1) * 20 + index + 1 }}
            </template>
            <template v-if="column.dataIndex && column.dataIndex.startsWith('data.')">
              <a-tooltip v-if="rec.overrides?.[column.fieldCode]" :title="`人工修正值（档案维护）：${rec.overrides[column.fieldCode].protected_by}（${rec.overrides[column.fieldCode].protected_at}）`">
                <span style="cursor: default; margin-right: 2px">🔒</span>
              </a-tooltip>
              <span class="data-cell">{{ formatCellValue(rec.data[column.fieldCode], column.fieldType) }}</span>
            </template>
            <template v-if="column.key === 'updated_at'">{{ formatDateTime(rec.updated_at) }}</template>
            <template v-if="column.key === 'action'">
              <a-space :size="4" style="white-space: nowrap">
                <a-switch
                  :checked="rec.status === 'active'"
                  checked-children="启用"
                  un-checked-children="停用"
                  size="small"
                  @change="(checked: any) => doToggleStatus(rec, checked ? 'active' : 'deleted')"
                />
                <a-divider type="vertical" />
                <a @click="openDetailDrawer(rec)">详情</a>
                <a-divider type="vertical" />
                <a @click="openDetailRowsDrawer(rec)">明细</a>
                <a-divider type="vertical" />
                <a @click="openHistoryModal(rec)">变更历史</a>
              </a-space>
            </template>
          </template>
        </a-table>
          </div>
        </div>
      </div>


    <!-- 记录详情抽屉（详情即编辑：档案维护字段直接可改，无变更不可保存） | R-056：1400 modal → 1100 大抽屉，不遮记录列表可边看边改 -->
    <a-drawer
      v-model:open="detailModal"
      :title="detailModalTitle"
      width="1100px"
      :destroyOnClose="true"
      :bodyStyle="{ padding: '16px 24px' }"
    >
      <template v-if="detailRecord && archive">
        <a-descriptions bordered :column="1" size="small">
            <a-descriptions-item label="状态">
              <a-tag :color="detailRecord.status === 'active' ? 'green' : 'default'">
                {{ detailRecord.status === 'active' ? '启用' : '已停用' }}
              </a-tag>
            </a-descriptions-item>
            <a-descriptions-item label="同步状态">
              <a-tag :color="syncColor(detailRecord.sync_status)">{{ syncLabel(detailRecord.sync_status) }}</a-tag>
            </a-descriptions-item>
            <a-descriptions-item label="当前版本">v{{ detailRecord.version }}</a-descriptions-item>
            <a-descriptions-item label="创建人">{{ detailRecord.created_by || '-' }}</a-descriptions-item>
            <a-descriptions-item label="修改人">{{ detailRecord.updated_by || '-' }}</a-descriptions-item>
            <a-descriptions-item label="创建时间">{{ formatDateTime(detailRecord.created_at) }}</a-descriptions-item>
            <a-descriptions-item label="更新时间">{{ formatDateTime(detailRecord.updated_at) }}</a-descriptions-item>
          </a-descriptions>

        <a-divider>业务数据</a-divider>

          <div style="padding-right: 8px">
            <!-- 按分组层级展示（level1 分组分列，最多 3 列） -->
            <template v-if="hasSchemaGroups">
              <div :style="schemaGridStyle">
                <div v-for="(col, ci) in groupedSchemaColumns" :key="ci" style="min-width: 0">
                  <template v-for="block in col" :key="block.key">
                    <div v-if="block.name" :style="groupTitleStyle(block.level)">{{ block.name }}</div>
                    <a-descriptions v-if="block.fields.length" bordered :column="1" size="small" :style="groupBodyStyle(block.level)">
                      <a-descriptions-item
                        v-for="field in block.fields"
                        :key="field.code"
                        :labelStyle="highlightChangedCodes.includes(field.code) ? { background: '#fff7e6' } : undefined"
                        :contentStyle="highlightChangedCodes.includes(field.code) ? { background: '#fff7e6' } : undefined"
                      >
                        <template #label>
                          {{ field.name }}
                          <a-tag v-if="field.ownership !== 'source' && field.source !== 'computed'" color="orange" style="margin-left: 4px">档案维护</a-tag>
                          <a-tooltip v-if="detailRecord.lineage?.[field.code] && detailRecord.lineage[field.code].source !== 'sync'" :overlayInnerStyle="{ whiteSpace: 'pre-line' }" :title="lineageTooltip(detailRecord, field.code)">
                            <a-tag :color="lineageColor(detailRecord.lineage[field.code].source)" style="margin-left: 4px">{{ lineageText(detailRecord.lineage[field.code].source) }}</a-tag>
                          </a-tooltip>
                        </template>
                        <component
                          :is="getFieldComponent(field.type)"
                          v-model:value="drawerEditData[field.code]"
                          v-bind="getFieldProps(field)"
                          :disabled="field.ownership === 'source' || field.editable === false"
                          :placeholder="field.note || getPlaceholder(field)"
                          style="width: 100%"
                        />
                      </a-descriptions-item>
                    </a-descriptions>
                  </template>
                </div>
              </div>
            </template>
            <!-- 无分组时平铺 -->
            <template v-else>
              <a-descriptions bordered :column="1" size="small">
                <a-descriptions-item
                  v-for="field in archive.schema"
                  :key="field.code"
                  :labelStyle="highlightChangedCodes.includes(field.code) ? { background: '#fff7e6' } : undefined"
                  :contentStyle="highlightChangedCodes.includes(field.code) ? { background: '#fff7e6' } : undefined"
                >
                  <template #label>
                    {{ field.name }}
                    <a-tag v-if="field.ownership !== 'source' && field.source !== 'computed'" color="orange" style="margin-left: 4px">档案维护</a-tag>
                    <a-tooltip v-if="detailRecord.lineage?.[field.code] && detailRecord.lineage[field.code].source !== 'sync'" :overlayInnerStyle="{ whiteSpace: 'pre-line' }" :title="lineageTooltip(detailRecord, field.code)">
                      <a-tag :color="lineageColor(detailRecord.lineage[field.code].source)" style="margin-left: 4px">{{ lineageText(detailRecord.lineage[field.code].source) }}</a-tag>
                    </a-tooltip>
                  </template>
                  <component
                    :is="getFieldComponent(field.type)"
                    v-model:value="drawerEditData[field.code]"
                    v-bind="getFieldProps(field)"
                    :disabled="field.ownership === 'source' || field.editable === false"
                    :placeholder="field.note || getPlaceholder(field)"
                    style="width: 100%"
                  />
                </a-descriptions-item>
              </a-descriptions>
            </template>

            <a-descriptions bordered :column="1" size="small" style="margin-top: 16px">
              <a-descriptions-item label="修改人">
                <a-input v-model:value="drawerEditOperator" placeholder="操作人" style="width: 200px" />
              </a-descriptions-item>
            </a-descriptions>
          </div>

          <div style="margin-top: 16px">
            <!-- 变更预览 -->
            <template v-if="editChanges.length > 0">
              <a-alert type="info" show-icon style="margin-bottom: 12px">
                <template #message>共修改了 {{ editChanges.length }} 个字段</template>
              </a-alert>
              <a-table
                :dataSource="editChanges"
                :columns="[{ title: '字段', dataIndex: 'field', key: 'field', width: 150 }, { title: '原值', dataIndex: 'oldVal', key: 'oldVal' }, { title: '新值', dataIndex: 'newVal', key: 'newVal' }]"
                :pagination="false"
                rowKey="field"
                size="small"
                bordered
              >
                <template #bodyCell="{ column, record: c }">
                  <template v-if="column.key === 'oldVal'">
                    <span style="color: #ff4d4f">{{ c.oldVal }}</span>
                  </template>
                  <template v-if="column.key === 'newVal'">
                    <span style="color: #52c41a">{{ c.newVal }}</span>
                  </template>
                </template>
              </a-table>
            </template>
            <a-alert v-else type="info" show-icon style="margin-bottom: 12px">
              <template #message>档案维护字段可直接修改，源系统维护字段只读；修改后点「暂存修改」，再到页头「保存」统一提交为一批。如需回滚请查看「变更历史」</template>
            </a-alert>
          </div>
      </template>
      <template #footer>
        <div style="text-align: right">
          <a-space>
            <a-button @click="detailModal = false">关闭</a-button>
            <a-button type="primary" :disabled="editChanges.length === 0" @click="handleSaveDrawer">暂存修改</a-button>
          </a-space>
        </div>
      </template>
    </a-drawer>

    <!-- 变更历史抽屉（记录列表入口：单条记录全部变更 + 双粒度回滚） | R-057：收敛为 ChangeHistoryDrawer 单组件 -->
    <ChangeHistoryDrawer
      v-model:open="historyOpen"
      :recordId="historyRecordId"
      :title="historyTitle"
      enableRollback
      @rolled-back="onHistoryRolledBack"
    />

    <!-- 明细子表行抽屉（批3b：展示记录的全部明细子表行） -->
    <a-drawer
      v-model:open="detailRowsOpen"
      :title="detailRowsTitle"
      width="900px"
      :destroyOnClose="true"
      :bodyStyle="{ padding: '16px 24px' }"
    >
      <a-spin :spinning="detailRowsLoading">
        <template v-if="detailRows.length > 0">
          <div style="margin-bottom: 12px; color: #666; font-size: 13px">
            共 {{ detailRows.length }} 条明细行，按行键排序
          </div>
          <a-table
            :dataSource="detailRows"
            :columns="detailRowColumns"
            :pagination="false"
            rowKey="id"
            size="small"
            bordered
          >
            <template #bodyCell="{ column, record }">
              <template v-if="column.key === 'row_key'">
                <span style="font-weight: 500">{{ record.row_key || '-' }}</span>
              </template>
              <template v-if="column.key === 'status'">
                <a-tag :color="record.status === 'active' ? 'green' : 'default'">
                  {{ record.status === 'active' ? '启用' : '已停用' }}
                </a-tag>
              </template>
              <template v-if="column.key === 'data'">
                <div style="max-height: 200px; overflow-y: auto; font-size: 12px">
                  <div v-for="(v, k) in record.data" :key="k" style="line-height: 1.7">
                    <span style="color: #1890ff">{{ k }}</span>：<span>{{ formatCellValue(v, 'string') }}</span>
                  </div>
                </div>
              </template>
              <template v-if="column.key === 'updated_at'">
                {{ formatDateTime(record.updated_at) }}
              </template>
            </template>
          </a-table>
        </template>
        <a-empty v-else description="该记录暂无明细子表数据" />
      </a-spin>
      <template #footer>
        <div style="text-align: right">
          <a-button @click="detailRowsOpen = false">关闭</a-button>
        </div>
      </template>
    </a-drawer>

    <!-- 刷新预检弹窗（schema 变化+数据试算+波及告警+warnings） | R-062：收敛为 RefreshPreviewModal 单组件，确认意图上抛父组件执行 -->
    <RefreshPreviewModal
      v-model:open="previewModal"
      :previewData="previewData"
      :archiveName="archive?.name ?? ''"
      @confirm="confirmRefresh"
    />

    <!-- 字段去重值弹窗（字段导航入口） -->
    <a-modal
      v-model:open="dvModalOpen"
      :title="`去重值 — ${dvModalField?.name || ''}`"
      :footer="null"
      width="520px"
    >
      <a-spin :spinning="dvLoading">
        <template v-if="dvModalData">
          <div style="color: #666; margin-bottom: 8px">
            <span style="color: #999">{{ dvModalField?.code }}</span>
            <a-tag style="margin-left: 8px">{{ dvModalData.distinct_count }} 个不同值</a-tag>
            <span style="margin-left: 8px">共 {{ dvModalData.total_records }} 条记录</span>
          </div>
          <template v-if="dvModalData.values.length">
            <div style="display: flex; flex-wrap: wrap; gap: 4px; max-height: 400px; overflow-y: auto">
              <a-tooltip
                v-for="v in dvModalData.values"
                :key="v.value"
                :title="`${v.count} 条记录`"
              >
                <a-tag style="margin: 0; max-width: 220px; overflow: hidden; text-overflow: ellipsis">
                  {{ v.value }}<span style="color: #999; margin-left: 4px">({{ v.count }})</span>
                </a-tag>
              </a-tooltip>
            </div>
            <div v-if="dvModalData.distinct_count > dvModalData.values.length" style="color: #999; font-size: 12px; margin-top: 8px">
              …还有 {{ dvModalData.distinct_count - dvModalData.values.length }} 个值未显示
            </div>
          </template>
          <a-empty v-else description="该字段全部为空" :image-style="{ height: '40px' }" />
        </template>
      </a-spin>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { useRoute, useRouter, onBeforeRouteLeave } from 'vue-router'
import { message, Modal, notification } from 'ant-design-vue'
import { archiveApi, archiveRecordApi, changeLogApi } from '@/api/archive'
import type { FieldDistinctValue } from '@/api/archive'
import { formatDateTime } from '@/utils/date'
import { extractApiError } from '@/utils/apiError'
import type { Archive, ArchiveRecord, ArchiveSchemaItem } from '@/types'
import ChangeHistoryDrawer from './components/ChangeHistoryDrawer.vue'
import RefreshPreviewModal from './components/RefreshPreviewModal.vue'

const route = useRoute()
const router = useRouter()
const archiveId = Number(route.params.id)

const archive = ref<Archive | null>(null)
const records = ref<ArchiveRecord[]>([])
const loading = ref(false)
const recordPage = ref(1)
const recordTotal = ref(0)

// 记录筛选（第八十七轮问题6）
const recordSearch = ref('')
const recordSyncFilter = ref<string | undefined>(undefined)
const recordStatusFilter = ref<string | undefined>(undefined)

// 字段导航 + 列定位高亮（第八十七轮问题7）
const recordTableWrap = ref<HTMLElement | null>(null)
const highlightFieldCode = ref('')
let highlightTimer: ReturnType<typeof setTimeout> | null = null

// 变更明细定位：详情弹窗中高亮本次变更字段（第八十七轮问题8）
const highlightChangedCodes = ref<string[]>([])

// 刷新预检
const previewModal = ref(false)
const previewLoading = ref(false)
const previewData = ref<any>(null)

// 字段去重值弹窗（字段导航入口，按需加载+缓存）
const dvModalOpen = ref(false)
const dvModalField = ref<{ code: string; name: string } | null>(null)
const dvModalData = ref<{ distinct_count: number; values: { value: string; count: number }[]; total_records: number } | null>(null)
const dvLoading = ref(false)
const dvCache = ref<Record<string, FieldDistinctValue>>({})

async function openFieldDistinctValues(field: ArchiveSchemaItem) {
  dvModalField.value = { code: field.code, name: field.name }
  dvModalData.value = null
  dvModalOpen.value = true
  // 命中缓存直接展示
  if (dvCache.value[field.code]) {
    const cached = dvCache.value[field.code]
    dvModalData.value = { distinct_count: cached.distinct_count, values: cached.values, total_records: dvTotalRecords.value }
    return
  }
  // 首次加载：拉全量缓存
  dvLoading.value = true
  try {
    const { data } = await archiveApi.fieldDistinctValues(archiveId)
    dvTotalRecords.value = data.total_records
    for (const f of data.fields) {
      dvCache.value[f.code] = f
    }
    if (dvCache.value[field.code]) {
      const cached = dvCache.value[field.code]
      dvModalData.value = { distinct_count: cached.distinct_count, values: cached.values, total_records: data.total_records }
    } else {
      dvModalData.value = { distinct_count: 0, values: [], total_records: data.total_records }
    }
  } catch (e: any) {
    message.error(extractApiError(e) || '加载去重值失败')
  } finally {
    dvLoading.value = false
  }
}
const dvTotalRecords = ref(0)

// 明细子表行列定义
const detailRowColumns = [
  { title: '行键', key: 'row_key', width: 120 },
  { title: '数据', key: 'data' },
  { title: '状态', key: 'status', width: 80 },
  { title: '更新时间', key: 'updated_at', width: 170 },
]

// 记录详情弹窗
const detailModal = ref(false)
const detailRecord = ref<ArchiveRecord | null>(null)
const drawerEditData = ref<Record<string, any>>({})
const drawerEditOperator = ref('')

// 变更历史抽屉（记录列表入口） | R-057：渲染与回滚收敛进 ChangeHistoryDrawer 组件，父组件只管开关/标题/回滚后刷新
const historyOpen = ref(false)
const historyRecordId = ref<number | null>(null)
const historyTitle = ref('')

// 明细子表行抽屉（批3b）
const detailRowsOpen = ref(false)
const detailRows = ref<any[]>([])
const detailRowsLoading = ref(false)
const detailRowsRecordId = ref<number | null>(null)
const detailRowsTitle = ref('')

// 弹窗标题动态标识业务对象
const detailModalTitle = computed(() => {
  if (!detailRecord.value || !archive.value?.schema) return '记录详情'
  const labelParts = archive.value.schema.slice(0, 3)
    .map(f => detailRecord.value!.data?.[f.code])
    .filter(v => v != null && v !== '')
  return labelParts.length ? `记录详情 — ${labelParts.join(' / ')}` : '记录详情'
})

// v18 攒批保存：待存队列（草稿仅存浏览器，未保存前不落库）
interface PendingEdit { record: ArchiveRecord; data: Record<string, any>; operator: string }
const pendingEdits = ref<PendingEdit[]>([])
const batchSaving = ref(false)

// ===== 动态列计算 =====
const DATA_COLUMN_WIDTH = 160

interface SchemaGroupNode {
  name: string
  path: string[]
  key: string
  level: number
  fields: ArchiveSchemaItem[]
  children: SchemaGroupNode[]
}

// 按 group_path 构建嵌套分组树（保留 schema 顺序 = 建模 DFS 序）
const schemaGroupTree = computed<SchemaGroupNode[]>(() => {
  if (!archive.value?.schema) return []
  const roots: SchemaGroupNode[] = []
  const nodeMap = new Map<string, SchemaGroupNode>()
  const ensureNode = (path: string[]): SchemaGroupNode => {
    const key = path.join(' / ')
    let node = nodeMap.get(key)
    if (node) return node
    node = { name: path[path.length - 1] || '', path, key, level: path.length, fields: [], children: [] }
    nodeMap.set(key, node)
    if (path.length <= 1) roots.push(node)
    else ensureNode(path.slice(0, -1)).children.push(node)
    return node
  }
  for (const field of archive.value.schema) {
    const path = field.group_path?.length ? field.group_path : (field.group ? [field.group] : [''])
    ensureNode(path).fields.push(field)
  }
  return roots
})

interface SchemaGroupBlock {
  key: string
  name: string
  level: number
  fields: ArchiveSchemaItem[]
}

// 树展平为块序列（父标题在前、子组紧随），供抽屉嵌套标题渲染
const groupedSchemaBlocks = computed<SchemaGroupBlock[]>(() => {
  const blocks: SchemaGroupBlock[] = []
  const walk = (nodes: SchemaGroupNode[]) => {
    for (const n of nodes) {
      blocks.push({ key: n.key, name: n.name, level: n.level, fields: n.fields })
      walk(n.children)
    }
  }
  walk(schemaGroupTree.value)
  return blocks
})

// 按 level1 分组分列：每个根分组自成一列（含其子组块），供详情/编辑抽屉多列渲染
const groupedSchemaColumns = computed<SchemaGroupBlock[][]>(() => {
  return schemaGroupTree.value.map(root => {
    const blocks: SchemaGroupBlock[] = []
    const walk = (nodes: SchemaGroupNode[]) => {
      for (const n of nodes) {
        blocks.push({ key: n.key, name: n.name, level: n.level, fields: n.fields })
        walk(n.children)
      }
    }
    walk([root])
    return blocks
  })
})

// 最多 3 列的 grid 容器样式（分组数不足 3 按实际数量分列，超出自动换行）
const schemaGridStyle = computed<Record<string, string>>(() => ({
  display: 'grid',
  gridTemplateColumns: `repeat(${Math.min(3, Math.max(1, groupedSchemaColumns.value.length))}, minmax(0, 1fr))`,
  gap: '0 16px',
  alignItems: 'start',
}))

// 嵌套分组标题样式：层级越深缩进越大；各层级统一蓝色系突出分组标题（第八十七轮问题3）
function groupTitleStyle(level: number): Record<string, string> {
  const indent = `${(level - 1) * 16}px`
  if (level <= 1) {
    return { margin: '12px 0 8px', marginLeft: indent, color: '#1890ff', fontSize: '15px', fontWeight: '600', borderLeft: '3px solid #1890ff', paddingLeft: '8px' }
  }
  if (level === 2) {
    return { margin: '10px 0 6px', marginLeft: indent, color: '#1890ff', fontSize: '14px', fontWeight: '600', borderLeft: '3px solid #91caff', paddingLeft: '8px' }
  }
  return { margin: '8px 0 6px', marginLeft: indent, color: '#40a9ff', fontSize: '13px', fontWeight: '600', paddingLeft: '8px' }
}

function groupBodyStyle(level: number): Record<string, string> {
  return { marginBottom: '16px', marginLeft: `${(level - 1) * 16}px` }
}

// 兼容旧逻辑：是否存在分组
const hasSchemaGroups = computed(() => groupedSchemaBlocks.value.some(b => b.name))

// 取全部 schema 字段作为表格动态列
const displaySchemaFields = computed(() => {
  if (!archive.value?.schema) return []
  return archive.value.schema
})

// 递归构建多级表头列（父分组→子分组→字段）
function buildGroupColumns(nodes: SchemaGroupNode[]): any[] {
  const cols: any[] = []
  for (const n of nodes) {
    const fieldCols = n.fields.map(field => ({
      title: field.name,
      dataIndex: `data.${field.code}`,
      key: `data_${field.code}`,
      width: DATA_COLUMN_WIDTH,
      ellipsis: true,
      fieldCode: field.code,
      fieldType: field.type,
      customHeaderCell: () => ({ class: highlightFieldCode.value === field.code ? 'col-flash' : '' }),
      customCell: () => ({ class: highlightFieldCode.value === field.code ? 'col-flash' : '' }),
    }))
    const childCols = buildGroupColumns(n.children)
    if (!fieldCols.length && !childCols.length) continue
    if (n.name) {
      cols.push({ title: n.name, children: [...fieldCols, ...childCols] })
    } else {
      cols.push(...fieldCols, ...childCols)
    }
  }
  return cols
}

const dynamicColumns = computed(() => {
  const cols: any[] = [
    { title: '#', key: 'rowIndex', width: 50, align: 'center', fixed: 'left' as const },
  ]

  // 按分组树构建多级表头（支持父/子分组嵌套）
  if (schemaGroupTree.value.length > 0) {
    cols.push(...buildGroupColumns(schemaGroupTree.value))
  } else if (archive.value?.schema) {
    for (const field of archive.value.schema) {
      cols.push({
        title: field.name,
        dataIndex: `data.${field.code}`,
        key: `data_${field.code}`,
        width: DATA_COLUMN_WIDTH,
        ellipsis: true,
        fieldCode: field.code,
        fieldType: field.type,
        customHeaderCell: () => ({ class: highlightFieldCode.value === field.code ? 'col-flash' : '' }),
        customCell: () => ({ class: highlightFieldCode.value === field.code ? 'col-flash' : '' }),
      })
    }
  }

  cols.push(
    { title: '更新时间', dataIndex: 'updated_at', key: 'updated_at', width: 170 },
    { title: '操作', key: 'action', width: 340, fixed: 'right' as const },
  )
  return cols
})

const dynamicColumnsTotalWidth = computed(() => {
  // R-012: 递归累加叶子列宽（分组表头无自身 width，需下钻 children）
  function sumLeafWidths(cols: any[]): number {
    return cols.reduce((sum, col) => {
      if (col.children?.length) return sum + sumLeafWidths(col.children)
      return sum + (col.width || 100)
    }, 0)
  }
  return sumLeafWidths(dynamicColumns.value)
})


// ===== 编辑变更预览 =====
const editChanges = computed(() => {
  if (!detailRecord.value || !archive.value?.schema) return []
  const original = detailRecord.value.data || {}
  const changes: { field: string; oldVal: any; newVal: any }[] = []
  for (const field of archive.value.schema) {
    const oldV = formatCellValue(original[field.code], field.type)
    const newV = formatCellValue(drawerEditData.value[field.code], field.type)
    if (String(oldV) !== String(newV)) {
      changes.push({ field: field.name, oldVal: oldV, newVal: newV })
    }
  }
  return changes
})

// ===== 字段类型 → 组件映射 =====
function getFieldComponent(type: string) {
  const t = (type || '').toLowerCase()
  if (t === 'number' || t === 'integer' || t === 'decimal' || t === 'float') return 'a-input-number'
  if (t === 'boolean' || t === 'bool') return 'a-switch'
  if (t === 'date' || t === 'datetime') return 'a-date-picker'
  if (t === 'text' || t === 'longtext') return 'a-textarea'
  return 'a-input'
}

function getFieldProps(field: ArchiveSchemaItem) {
  const t = (field.type || '').toLowerCase()
  const props: Record<string, any> = {}
  if (t === 'number' || t === 'integer' || t === 'decimal' || t === 'float') {
    props.style = 'width: 100%'
    props.precision = t === 'integer' ? 0 : 2
  }
  if (t === 'text' || t === 'longtext') {
    props.rows = 3
  }
  if (t === 'date' || t === 'datetime') {
    props.style = 'width: 100%'
    props.showTime = t === 'datetime'
    props.format = t === 'datetime' ? 'YYYY-MM-DD HH:mm:ss' : 'YYYY-MM-DD'
    props.valueFormat = t === 'datetime' ? 'YYYY-MM-DD HH:mm:ss' : 'YYYY-MM-DD'
  }
  return props
}

function getPlaceholder(field: ArchiveSchemaItem) {
  const t = (field.type || '').toLowerCase()
  if (t === 'number' || t === 'integer' || t === 'decimal') return `请输入${field.name}`
  if (t === 'date' || t === 'datetime') return `请选择${field.name}`
  if (t === 'boolean') return ''
  return `请输入${field.name}`
}

function formatCellValue(value: any, type: string) {
  if (value === null || value === undefined || value === '') return '-'
  const t = (type || '').toLowerCase()
  if (t === 'boolean' || t === 'bool') return value ? '是' : '否'
  if (t === 'datetime') return formatDateTime(value)
  if (t === 'date') return formatDateTime(value)?.split(' ')[0] || '-'
  return String(value)
}

// ===== 工具函数 =====
function statusColor(s: string) { return { draft: 'default', active: 'green', archived: 'blue' }[s] || 'default' }
function statusLabel(s: string) { return { draft: '草稿', active: '已发布', archived: '已归档' }[s] || s }
function syncColor(s: string) { return { unsynced: 'default', synced: 'green', partial: 'orange', error: 'red', stale: 'orange' }[s] || 'default' }
function syncLabel(s: string) { return { unsynced: '未同步', synced: '已同步', partial: '部分同步', error: '同步失败', stale: '源侧已删' }[s] || s }

// ===== 数据加载 =====
async function loadArchive() {
  try {
    const res = await archiveApi.get(archiveId)
    archive.value = res.data
  } catch (e: any) {
    message.error('加载档案失败')
  }
}

async function loadRecords() {
  loading.value = true
  try {
    const params: Record<string, any> = { archive: archiveId, page: recordPage.value }
    if (recordSearch.value.trim()) params.search = recordSearch.value.trim()
    if (recordSyncFilter.value) params.sync_status = recordSyncFilter.value
    if (recordStatusFilter.value) params.status = recordStatusFilter.value
    const res = await archiveRecordApi.list(params)
    records.value = res.data.results
    recordTotal.value = res.data.count
  } finally {
    loading.value = false
  }
}

function doSearchRecords() {
  recordPage.value = 1
  loadRecords()
}

function resetRecordFilters() {
  recordSearch.value = ''
  recordSyncFilter.value = undefined
  recordStatusFilter.value = undefined
  recordPage.value = 1
  loadRecords()
}

// 点击左侧字段导航：横向滚动表格定位到对应列并短暂高亮
function scrollToFieldColumn(code: string) {
  const leafCodes = groupedSchemaBlocks.value.flatMap(b => b.fields.map(f => f.code))
  const idx = leafCodes.indexOf(code)
  if (idx < 0) return
  // 固定左列「#」宽 50，其后每个数据列宽 DATA_COLUMN_WIDTH
  const offset = Math.max(0, idx * DATA_COLUMN_WIDTH - 80)
  const scroller = recordTableWrap.value?.querySelector('.ant-table-content, .ant-table-body') as HTMLElement | null
  if (scroller) scroller.scrollTo({ left: offset, behavior: 'smooth' })
  highlightFieldCode.value = code
  if (highlightTimer) clearTimeout(highlightTimer)
  highlightTimer = setTimeout(() => { highlightFieldCode.value = '' }, 2600)
}

function refreshData() {
  if (!archive.value) {
    message.warning('档案信息未加载完成，请稍候')
    return
  }
  doRefreshPreview()
}

// 刷新工作流第一步：预检源与档案的 schema/数据变化，有变化弹窗确认
async function doRefreshPreview() {
  previewLoading.value = true
  try {
    const res = await archiveApi.refreshPreview(archiveId)
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
  } finally {
    previewLoading.value = false
  }
}

// 确认更新：schema 有变走同步结构（含拉数），无变仅刷数据；两路径均生成变更日志
async function confirmRefresh() {
  previewModal.value = false
  loading.value = true
  try {
    const res = previewData.value?.schema_changes?.has_changes
      ? await archiveApi.syncSchema(archiveId)
      : await archiveApi.refreshData(archiveId)
    const stats = res.data.sync_stats
    if (stats) {
      const parts: string[] = []
      if ((stats.tables_synced ?? 0) > 0) parts.push(`${previewData.value?.schema_changes?.has_changes ? '同步' : '刷新'}了 ${stats.tables_synced} 张表`)
      if (stats.records_created > 0) parts.push(`新增 ${stats.records_created} 条记录`)
      if (stats.records_updated > 0) parts.push(`更新 ${stats.records_updated} 条记录`)
      if ((stats.records_deactivated ?? 0) > 0) parts.push(`源侧已删，停用 ${stats.records_deactivated} 条记录`)
      if ((stats.records_reactivated ?? 0) > 0) parts.push(`源侧恢复，复活 ${stats.records_reactivated} 条记录`)
      if (parts.length === 0) parts.push('数据已是最新，无变更')
      if (stats.errors?.length > 0) {
        Modal.warning({ title: `完成，但有 ${stats.errors.length} 个错误`, content: stats.errors.slice(0, 10).join('\n') })
      } else if (stats.warnings && stats.warnings.length > 0) {
        message.success(parts.join('，'))
        Modal.warning({ title: `${stats.warnings.length} 条提醒`, content: stats.warnings.slice(0, 10).join('\n') })
      } else {
        message.success(parts.join('，'))
      }
      showConsistencyWarning(stats)
    } else {
      message.success('操作完成')
    }
    await loadArchive()
    await loadRecords()
  } catch (e: any) {
    message.error(extractApiError(e) || '操作失败')
  } finally {
    loading.value = false
  }
}

// 一致性检查告警（非主字段成员值与主字段不一致；告警不阻断，数据已以主字段为准）
function showConsistencyWarning(stats: any) {
  const cc = stats?.consistency_check
  if (!cc || !(cc.mismatch_count > 0)) return
  notification.warning({
    message: `一致性提醒：${cc.mismatch_records} 条记录、${cc.mismatch_count} 处不一致`,
    description: '数据已以主字段为准写入，不一致项仅为提醒，可稍后到一致性检查页处理。',
    duration: 8,
    style: { width: 360 },
  })
}

async function doRefreshData() {
  loading.value = true
  try {
    const res = await archiveApi.refreshData(archiveId)
    const stats = res.data.sync_stats
    if (stats) {
      const parts: string[] = []
      if ((stats.tables_synced ?? 0) > 0) parts.push(`刷新了 ${stats.tables_synced} 张表`)
      if (stats.records_created > 0) parts.push(`新增 ${stats.records_created} 条记录`)
      if (stats.records_updated > 0) parts.push(`更新 ${stats.records_updated} 条记录`)
      if ((stats.records_deactivated ?? 0) > 0) parts.push(`源侧已删，停用 ${stats.records_deactivated} 条记录`)
      if ((stats.records_reactivated ?? 0) > 0) parts.push(`源侧恢复，复活 ${stats.records_reactivated} 条记录`)
      if (parts.length === 0) parts.push('数据已是最新，无变更')
      if (stats.errors?.length > 0) {
        Modal.warning({
          title: `刷新完成，但有 ${stats.errors.length} 个错误`,
          content: stats.errors.slice(0, 10).join('\n'),
        })
      } else if (stats.warnings && stats.warnings.length > 0) {
        message.success(`刷新完成：${parts.join('，')}`)
        Modal.warning({
          title: `${stats.warnings.length} 条提醒`,
          content: stats.warnings.slice(0, 10).join('\n'),
        })
      } else {
        message.success(`刷新完成：${parts.join('，')}`)
      }
      showConsistencyWarning(stats)
    } else {
      message.success('数据刷新完成')
    }
    await loadArchive()
    await loadRecords()
  } catch (e: any) {
    message.error(extractApiError(e) || '刷新失败')
  } finally {
    loading.value = false
  }
}

async function doSyncSchema() {
  loading.value = true
  try {
    const res = await archiveApi.syncSchema(archiveId)
    const stats = res.data.sync_stats
    if (stats) {
      const parts: string[] = []
      if ((stats.tables_synced ?? 0) > 0) parts.push(`同步了 ${stats.tables_synced} 张表`)
      if (stats.records_created > 0) parts.push(`新增 ${stats.records_created} 条记录`)
      if (stats.records_updated > 0) parts.push(`更新 ${stats.records_updated} 条记录`)
      if ((stats.records_deactivated ?? 0) > 0) parts.push(`源侧已删，停用 ${stats.records_deactivated} 条记录`)
      if ((stats.records_reactivated ?? 0) > 0) parts.push(`源侧恢复，复活 ${stats.records_reactivated} 条记录`)
      if (parts.length === 0) parts.push('Schema 已更新，暂无数据可同步')
      if (stats.errors?.length > 0) {
        Modal.warning({
          title: `同步完成，但有 ${stats.errors.length} 个错误`,
          content: stats.errors.slice(0, 10).join('\n'),
        })
      } else if (stats.warnings && stats.warnings.length > 0) {
        message.success(`同步完成：${parts.join('，')}`)
        Modal.warning({
          title: `${stats.warnings.length} 条提醒`,
          content: stats.warnings.slice(0, 10).join('\n'),
        })
      } else {
        message.success(`同步完成：${parts.join('，')}`)
      }
      showConsistencyWarning(stats)
    } else {
      message.success('模型同步成功')
    }
    await loadArchive()
    await loadRecords()
  } catch (e: any) {
    message.error(extractApiError(e) || '同步失败')
  } finally {
    loading.value = false
  }
}

// ===== 记录详情 =====

// ===== 详情弹窗（详情即编辑：打开即初始化编辑数据，档案维护字段可直接修改） =====
function openDetailDrawer(rec: ArchiveRecord) {
  detailRecord.value = rec
  highlightChangedCodes.value = []
  // 已有待存修改的记录重新打开时，载入暂存值继续编辑
  const pending = pendingEdits.value.find(p => p.record.id === rec.id)
  drawerEditData.value = pending ? { ...pending.data } : convertRecordData(rec)
  drawerEditOperator.value = pending?.operator || ''
  detailModal.value = true
}

// 记录列表「变更历史」入口（R-057：打开抽屉，标题仍取 schema 前 3 字段拼接）
function openHistoryModal(rec: ArchiveRecord) {
  historyRecordId.value = rec.id
  const labelParts = archive.value?.schema?.slice(0, 3).map(f => rec.data?.[f.code]).filter(v => v != null && v !== '') ?? []
  historyTitle.value = labelParts.length ? `变更历史 — ${labelParts.join(' / ')}` : '变更历史'
  historyOpen.value = true
}

// 明细子表行抽屉
async function openDetailRowsDrawer(rec: ArchiveRecord) {
  detailRowsRecordId.value = rec.id
  const labelParts = archive.value?.schema?.slice(0, 3).map(f => rec.data?.[f.code]).filter(v => v != null && v !== '') ?? []
  detailRowsTitle.value = labelParts.length ? `明细子表 — ${labelParts.join(' / ')}` : '明细子表'
  detailRowsOpen.value = true
  await loadDetailRows()
}

async function loadDetailRows() {
  if (!detailRowsRecordId.value) return
  detailRowsLoading.value = true
  detailRows.value = []
  try {
    const res = await archiveRecordApi.listDetails(detailRowsRecordId.value)
    detailRows.value = res.data
  } catch (e: any) {
    message.error(extractApiError(e) || '加载明细行失败')
  } finally {
    detailRowsLoading.value = false
  }
}

// 回滚后刷新（R-057：时间线由组件自行重载，父组件刷记录列表 + 详情抽屉上下文）
async function onHistoryRolledBack(recordId: number) {
  try {
    const fresh = await archiveRecordApi.get(recordId)
    if (detailModal.value && detailRecord.value?.id === recordId) {
      detailRecord.value = fresh.data
      drawerEditData.value = convertRecordData(fresh.data)
    }
  } catch { /* 刷新失败不阻断 */ }
  loadRecords()
}

function convertRecordData(rec: ArchiveRecord): Record<string, any> {
  const data: Record<string, any> = { ...rec.data }
  if (archive.value?.schema) {
    for (const field of archive.value.schema) {
      const ft = (field.type || '').toLowerCase()
      if ((ft === 'date' || ft === 'datetime') && data[field.code]) {
        const d = new Date(data[field.code])
        if (!isNaN(d.getTime())) {
          const pad = (n: number) => String(n).padStart(2, '0')
          const base = `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
          data[field.code] = ft === 'datetime' ? `${base} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}` : base
        }
      }
    }
  }
  return data
}

function handleSaveDrawer() {
  // v18 攒批保存：不立即落库，加入待存队列（同一记录重复暂存以最新一次为准）
  if (!detailRecord.value) return
  const rec = detailRecord.value
  const item: PendingEdit = {
    record: rec,
    data: { ...drawerEditData.value },
    operator: drawerEditOperator.value || '管理员',
  }
  const idx = pendingEdits.value.findIndex(p => p.record.id === rec.id)
  if (idx >= 0) pendingEdits.value[idx] = item
  else pendingEdits.value.push(item)
  message.success('已暂存，点页头「保存」统一提交为一批')
  detailModal.value = false
}

// 页头「保存」：开启人工批次 → 逐条 PUT 攒入本批（保存即批次封口）
async function savePendingEdits(): Promise<boolean> {
  if (!pendingEdits.value.length || !archive.value) return true
  batchSaving.value = true
  try {
    const batchRes = await changeLogApi.startManualBatch(archive.value.id)
    const batchId = batchRes.data.id
    const failed: PendingEdit[] = []
    let ok = 0
    for (const p of pendingEdits.value) {
      try {
        await archiveRecordApi.update(p.record.id, {
          data: p.data, updated_by: p.operator, change_batch_id: batchId,
        })
        ok += 1
      } catch (e: any) {
        failed.push(p)
        message.error(`记录 #${p.record.id} 保存失败：${extractApiError(e)}`)
      }
    }
    pendingEdits.value = failed
    if (failed.length) {
      message.warning(`成功 ${ok} 条，${failed.length} 条失败已保留在待存队列`)
    } else {
      message.success(`已保存 ${ok} 条修改（批次 #${batchId}）`)
    }
    await loadRecords()
    return failed.length === 0
  } catch (e: any) {
    message.error(extractApiError(e) || '保存失败')
    return false
  } finally {
    batchSaving.value = false
  }
}

// 离开拦截：列出待存内容，保存并离开 / 放弃并离开 / 留下
onBeforeRouteLeave(() => {
  if (!pendingEdits.value.length) return true
  return new Promise<boolean>((resolve) => {
    const lines = pendingEdits.value.map(p => {
      const orig = p.record.data || {}
      const n = Object.keys(p.data).filter(k => String(p.data[k] ?? '') !== String(orig[k] ?? '')).length
      return `・记录 #${p.record.id}（${n} 个字段）`
    })
    Modal.confirm({
      title: `有 ${pendingEdits.value.length} 条记录的修改未保存`,
      content: lines.join('\n') + '\n\n保存后这些修改将合并为一个批次。',
      okText: '保存并离开',
      cancelText: '不保存',
      async onOk() {
        resolve(await savePendingEdits())
      },
      onCancel() {
        Modal.confirm({
          title: '确认放弃未保存的修改？',
          content: '离开后这些修改将丢失，不可恢复。',
          okText: '放弃并离开',
          okType: 'danger',
          cancelText: '返回继续编辑',
          onOk() { pendingEdits.value = []; resolve(true) },
          onCancel() { resolve(false) },
        })
      },
    })
  })
})

// 浏览器关闭/刷新拦截（草稿仅存浏览器）
function beforeUnloadGuard(e: BeforeUnloadEvent) {
  if (pendingEdits.value.length) {
    e.preventDefault()
    e.returnValue = ''
  }
}
onMounted(() => window.addEventListener('beforeunload', beforeUnloadGuard))
onBeforeUnmount(() => window.removeEventListener('beforeunload', beforeUnloadGuard))

// ===== 启用/停用（R-055：危险操作补二次确认，开关为受控绑定取消后自动回弹） =====
function doToggleStatus(rec: ArchiveRecord, newStatus: 'active' | 'deleted') {
  const isDisable = newStatus === 'deleted'
  Modal.confirm({
    title: isDisable ? '确认停用这条记录' : '确认启用这条记录',
    content: isDisable
      ? '停用后该记录退出有效状态（标记为停用），随时可以再次启用。'
      : '启用后该记录恢复为有效状态。',
    okText: isDisable ? '确认停用' : '确认启用',
    okType: isDisable ? 'danger' : 'primary',
    cancelText: '取消',
    async onOk() {
      try {
        await archiveRecordApi.update(rec.id, {
          status: newStatus,
          updated_by: '管理员',
        })
        message.success(newStatus === 'active' ? '已启用' : '已停用')
        await loadRecords()
      } catch (e: any) {
        message.error(extractApiError(e) || '操作失败')
      }
    },
  })
}

// ===== 字段血缘展示 =====
function lineageColor(source: string) {
  return { manual: 'orange', sync: 'blue', resolve: 'purple' }[source] || 'default'
}
function lineageText(source: string) {
  return { manual: '人工', sync: '同步', resolve: '裁决' }[source] || source
}
function lineageTooltip(rec: ArchiveRecord, code: string): string {
  const lin = rec.lineage?.[code]
  if (!lin) return ''
  const lines: string[] = []
  if (lin.source_table) lines.push(`来源表：${lin.source_table}`)
  if (lin.updated_at) lines.push(`更新时间：${lin.updated_at}`)
  const ov = rec.overrides?.[code]
  if (ov) lines.push(`保护人：${ov.protected_by}（${ov.protected_at}）`)
  return lines.join('\n') || lineageText(lin.source)
}

function goBack() {
  router.push('/archive')
}

onMounted(async () => {
  await loadArchive()
  await loadRecords()
  // 后台预加载去重值数据（不阻塞页面）
  preloadDistinctValues()
})

async function preloadDistinctValues() {
  try {
    const { data } = await archiveApi.fieldDistinctValues(archiveId)
    dvTotalRecords.value = data.total_records
    for (const f of data.fields) {
      dvCache.value[f.code] = f
    }
  } catch { /* 预加载失败不阻断，点击时再重试 */ }
}
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
}
:deep(.ant-table-thead > tr > th.ant-table-cell-group) {
  background-color: #e6f7ff !important;
  font-weight: 600;
  border-bottom: 2px solid #1890ff !important;
}
.data-cell {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 120px;
  display: inline-block;
  vertical-align: middle;
}
.field-nav {
  width: 240px;
  flex-shrink: 0;
  border: 1px solid #f0f0f0;
  border-radius: 6px;
  background: #fff;
  padding: 8px 6px;
  max-height: calc(100vh - 260px);
  overflow-y: auto;
}
.field-nav-title {
  font-weight: 600;
  color: #1890ff;
  padding: 2px 6px 8px;
  border-bottom: 1px solid #f0f0f0;
  margin-bottom: 6px;
}
.field-nav-group {
  color: #1890ff;
  font-weight: 600;
  font-size: 12px;
  padding: 6px 6px 2px;
}
.field-nav-item {
  padding: 3px 6px;
  font-size: 12px;
  color: #555;
  cursor: pointer;
  border-radius: 4px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.field-nav-item:hover {
  background: #e6f7ff;
  color: #1890ff;
}
.field-nav-item.active {
  background: #fff7e6;
  color: #fa8c16;
  font-weight: 600;
}
.field-nav-dv {
  float: right;
  font-size: 10px;
  color: #1890ff;
  cursor: pointer;
  opacity: 0.6;
  padding: 0 3px;
  border-radius: 3px;
  background: #e6f7ff;
  line-height: 16px;
}
.field-nav-dv:hover {
  opacity: 1;
  background: #bae7ff;
}
:deep(.col-flash) {
  background-color: #fff7e6 !important;
}
</style>
