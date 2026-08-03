<template>
  <div>
    <div class="page-header">
      <a-space>
        <a-button @click="goBack">← 返回列表</a-button>
        <h2>{{ archive?.name || '档案详情' }}</h2>
        <a-tag v-if="archive" :color="statusColor(archive.status)">{{ statusLabel(archive.status) }}</a-tag>
      </a-space>
      <a-space>
        <a-button type="primary" :loading="previewLoading" @click="refreshData">立即刷新</a-button>
      </a-space>
    </div>

    <!-- 档案记录列表 -->
    <div>
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
        <div style="display: flex; gap: 12px; align-items: flex-start">
          <div class="field-nav">
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
              >{{ f.name }}</div>
            </template>
          </div>
          <div ref="recordTableWrap" style="flex: 1; min-width: 0">
        <a-table
          :dataSource="records"
          :columns="dynamicColumns"
          :loading="loading"
          rowKey="id"
          size="small"
          :scroll="{ x: dynamicColumnsTotalWidth }"
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
                <a @click="openHistoryModal(rec)">变更历史</a>
              </a-space>
            </template>
          </template>
        </a-table>
          </div>
        </div>
      </div>


    <!-- 记录详情弹窗（详情即编辑：档案维护字段直接可改，无变更不可保存） -->
    <a-modal
      v-model:open="detailModal"
      :title="detailModalTitle"
      width="1400px"
      :footer="null"
      :destroyOnClose="true"
      :bodyStyle="{ maxHeight: '70vh', overflowY: 'auto' }"
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
                          :disabled="field.ownership === 'source'"
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
                    :disabled="field.ownership === 'source'"
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
            <!-- 历史回滚时间线 -->
            <a-collapse v-model:activeKey="rollbackPanelKey" style="margin-bottom: 16px" :bordered="false">
              <a-collapse-panel key="rollback" header="🔄 历史回滚">
                <div v-if="rollbackLoading" style="text-align: center; padding: 16px">
                  <a-spin tip="加载变更历史..." />
                </div>
                <div v-else-if="rollbackHistory.length === 0" style="color: #999; padding: 8px">暂无可回滚的变更记录</div>
                <a-timeline v-else mode="left" style="max-height: 300px; overflow-y: auto; padding-top: 8px">
                  <a-timeline-item v-for="(item, index) in rollbackHistory" :key="item.id" :color="rollbackTimelineColor(item.change_type)">
                    <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 8px">
                      <div style="flex: 1; min-width: 0">
                        <div>
                          <a-tag :color="rollbackChangeTypeColor(item.change_type)" size="small">{{ item.change_type_display }}</a-tag>
                          <span style="color: #999; font-size: 12px">{{ formatDateTime(item.created_at) }}</span>
                          <span style="margin-left: 8px; color: #666; font-size: 12px">{{ item.operator }}</span>
                        </div>
                        <div v-if="item.field_changes?.length" style="margin-top: 4px; font-size: 12px; color: #666">
                          <span v-for="(fc, idx) in item.field_changes.slice(0, 3)" :key="idx">
                            {{ fc.name || fc.field }}<span v-if="idx < Math.min(item.field_changes.length, 3) - 1">、</span>
                          </span>
                          <span v-if="item.field_changes.length > 3">等{{ item.field_changes.length }}项</span>
                        </div>
                      </div>
                      <a-button
                        v-if="canRollbackToPoint(index)"
                        size="small"
                        danger
                        :loading="rollbackingId === item.id"
                        @click="handleRollbackToChange(item, detailRecord!)"
                      >回滚到此</a-button>
                    </div>
                  </a-timeline-item>
                </a-timeline>
              </a-collapse-panel>
            </a-collapse>

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
              <template #message>档案维护字段可直接修改，源系统维护字段只读；有修改后可保存</template>
            </a-alert>
            <div style="text-align: right">
              <a-space>
                <a-button @click="detailModal = false">关闭</a-button>
                <a-button type="primary" :loading="saving" :disabled="editChanges.length === 0" @click="handleSaveDrawer">保存</a-button>
              </a-space>
            </div>
          </div>
      </template>
    </a-modal>

    <!-- 变更历史弹窗（记录列表入口：单条记录全部变更 + 双粒度回滚） -->
    <a-modal
      v-model:open="historyModal"
      :title="historyModalTitle"
      width="860px"
      :footer="null"
      :bodyStyle="{ maxHeight: '70vh', overflowY: 'auto' }"
    >
      <div v-if="rollbackLoading" style="text-align: center; padding: 24px">
        <a-spin tip="加载变更历史..." />
      </div>
      <a-empty v-else-if="rollbackHistory.length === 0" description="该记录暂无变更历史" />
      <a-timeline v-else style="padding: 8px 4px 0">
        <a-timeline-item v-for="(item, index) in rollbackHistory" :key="item.id" :color="rollbackTimelineColor(item.change_type)">
          <div style="display: flex; justify-content: space-between; gap: 12px">
            <div style="flex: 1; min-width: 0">
              <div>
                <a-tag :color="rollbackChangeTypeColor(item.change_type)">{{ item.change_type_display }}</a-tag>
                <a-tag :color="historySourceColor(item.change_source)">{{ item.change_source_display }}</a-tag>
                <span style="color: #999; font-size: 12px">{{ formatDateTime(item.created_at) }}</span>
                <span style="margin-left: 8px; color: #666; font-size: 12px">{{ item.operator }}</span>
              </div>
              <div v-if="item.field_changes?.length" style="margin-top: 6px">
                <div v-for="(fc, fi) in item.field_changes" :key="fi" style="font-size: 12px; line-height: 1.9">
                  <span style="color: #1890ff">{{ fc.name || fc.field }}</span>
                  <span style="color: #999">：</span>
                  <span style="color: #ff4d4f">{{ fc.old ?? '-' }}</span>
                  <span style="color: #999"> → </span>
                  <span style="color: #52c41a">{{ fc.new ?? '-' }}</span>
                </div>
              </div>
            </div>
            <a-space direction="vertical" :size="4" style="flex-shrink: 0">
              <a-button v-if="canRollbackDetail(item)" size="small" @click="handleRollbackSingle(item)">回滚此条</a-button>
              <a-button
                v-if="canRollbackToPoint(index)"
                size="small"
                danger
                :loading="rollbackingId === item.id"
                @click="handleRollbackToChange(item, historyRecord!)"
              >回滚到此</a-button>
            </a-space>
          </div>
        </a-timeline-item>
      </a-timeline>
    </a-modal>

    <!-- 刷新预检弹窗：展示源与档案的 schema/数据变化，确认后执行更新 -->
    <a-modal
      v-model:open="previewModal"
      :title="archive ? `刷新预检 — ${archive.name}` : '刷新预检：检测到以下变化'"
      width="760px"
      okText="确认更新"
      cancelText="取消"
      :bodyStyle="{ maxHeight: '65vh', overflowY: 'auto' }"
      @ok="confirmRefresh"
    >
      <template v-if="previewData">
        <!-- 结构变化 -->
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
        <!-- 数据变化 -->
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
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, h } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { message, Modal } from 'ant-design-vue'
import { archiveApi, archiveRecordApi, changeLogApi } from '@/api/archive'
import { formatDateTime } from '@/utils/date'
import { extractApiError } from '@/utils/apiError'
import type { Archive, ArchiveRecord, ArchiveSchemaItem, ChangeDetail } from '@/types'

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

// 记录详情弹窗
const detailModal = ref(false)
const detailRecord = ref<ArchiveRecord | null>(null)
const drawerEditData = ref<Record<string, any>>({})
const drawerEditOperator = ref('')

// 历史回滚时间线（详情弹窗内可展开面板 + 独立变更历史弹窗共用数据源）
const rollbackPanelKey = ref<string[]>([])
const rollbackLoading = ref(false)
const rollbackHistory = ref<ChangeDetail[]>([])
const rollbackingId = ref<number | null>(null)

// 变更历史弹窗（记录列表入口）
const historyModal = ref(false)
const historyRecord = ref<ArchiveRecord | null>(null)

const historyModalTitle = computed(() => {
  if (!historyRecord.value || !archive.value?.schema) return '变更历史'
  const labelParts = archive.value.schema.slice(0, 3)
    .map(f => historyRecord.value!.data?.[f.code])
    .filter(v => v != null && v !== '')
  return labelParts.length ? `变更历史 — ${labelParts.join(' / ')}` : '变更历史'
})

// 弹窗标题动态标识业务对象
const detailModalTitle = computed(() => {
  if (!detailRecord.value || !archive.value?.schema) return '记录详情'
  const labelParts = archive.value.schema.slice(0, 3)
    .map(f => detailRecord.value!.data?.[f.code])
    .filter(v => v != null && v !== '')
  return labelParts.length ? `记录详情 — ${labelParts.join(' / ')}` : '记录详情'
})

const saving = ref(false)

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
    message.error(extractApiError(e) || e.message || '预检失败')
  } finally {
    previewLoading.value = false
  }
}

// 确认更新：schema 有变走同步结构（含拉数），无变仅刷数据；两路径均生成变更日志
function confirmRefresh() {
  previewModal.value = false
  if (previewData.value?.schema_changes?.has_changes) {
    doSyncSchema()
  } else {
    doRefreshData()
  }
}

// 一致性检查告警（非主字段成员值与主字段不一致；告警不阻断，数据已以主字段为准）
function showConsistencyWarning(stats: any) {
  const cc = stats?.consistency_check
  if (!cc || !(cc.mismatch_count > 0)) return
  const lines = (cc.samples || []).slice(0, 10).map((s: any) =>
    `[${s.record_key}] ${s.name}：主字段 ${s.primary_source}=${s.primary_value ?? '空'}，成员 ${s.member_source}=${s.member_value ?? '空'}`)
  Modal.confirm({
    title: `一致性检查：${cc.mismatch_records} 条记录、${cc.mismatch_count} 处成员值与主字段不一致`,
    icon: undefined,
    content: h('div', { style: 'max-height:300px;overflow:auto;font-size:12px;white-space:pre-wrap' },
      lines.join('\n') + (cc.mismatch_count > lines.length ? `\n…仅展示前 ${lines.length} 条样本` : '')),
    width: 640,
    okText: '前往一致性检查',
    cancelText: '知道了',
    onOk: () => { router.push(`/archive/${archiveId}/consistency`) },
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
    message.error(extractApiError(e) || e.message || '刷新失败')
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
    message.error(extractApiError(e) || e.message || '同步失败')
  } finally {
    loading.value = false
  }
}

// ===== 记录详情 =====

// ===== 详情弹窗（详情即编辑：打开即初始化编辑数据，档案维护字段可直接修改） =====
function openDetailDrawer(rec: ArchiveRecord) {
  detailRecord.value = rec
  highlightChangedCodes.value = []
  drawerEditData.value = convertRecordData(rec)
  drawerEditOperator.value = ''
  rollbackPanelKey.value = []
  rollbackHistory.value = []
  detailModal.value = true
  loadRollbackHistory(rec.id)
}

async function loadRollbackHistory(recordId: number) {
  rollbackLoading.value = true
  try {
    const res = await changeLogApi.listDetails({ record: recordId, page_size: 50, ordering: '-id' })
    // 过滤掉 created 和 rollback 类型（不可回滚的也展示但无按钮）
    rollbackHistory.value = res.data.results
  } catch {
    rollbackHistory.value = []
  } finally {
    rollbackLoading.value = false
  }
}

function canRollbackDetail(item: ChangeDetail) {
  return !['created', 'rollback'].includes(item.change_type) && (item.field_changes?.length ?? 0) > 0
}

// 能否「回滚到此时点」：时间线按 id 降序（最新在前），需存在比当前节点更新且可撤销的变更（非 created/rollback），否则后端必然 400
function canRollbackToPoint(index: number) {
  return rollbackHistory.value.slice(0, index).some(c => !['created', 'rollback'].includes(c.change_type))
}

function historySourceColor(s: string) {
  return ({ sync: 'geekblue', manual: 'orange', consistency: 'cyan' } as Record<string, string>)[s] || 'orange'
}

// 记录列表「变更历史」入口
function openHistoryModal(rec: ArchiveRecord) {
  historyRecord.value = rec
  rollbackHistory.value = []
  historyModal.value = true
  loadRollbackHistory(rec.id)
}

// 单条变更回滚（只撤销这一条的字段变化）
function handleRollbackSingle(item: ChangeDetail) {
  const isSyncSource = item.change_source === 'sync'
  const warningText = isSyncSource ? '\n\n⚠️ 此变更来自源系统同步，回滚后下次刷新可能再次被覆盖。' : ''
  Modal.confirm({
    title: '确认回滚此条变更',
    content: `将把这条变更涉及的 ${item.field_changes?.length || 0} 个字段恢复到变更前的值（不影响其它变更）。${warningText}`,
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
          await refreshAfterRollback()
        }
      } catch (e: any) {
        message.error(extractApiError(e))
      } finally {
        rollbackingId.value = null
      }
    },
  })
}

// 回滚后统一刷新：列表 + 当前打开的弹窗上下文（以弹窗打开状态为准，避免已关弹窗的残留记录干扰）
async function refreshAfterRollback() {
  const targetId = historyModal.value ? historyRecord.value?.id : detailRecord.value?.id
  if (targetId) {
    try {
      const fresh = await archiveRecordApi.get(targetId)
      if (historyModal.value && historyRecord.value?.id === targetId) historyRecord.value = fresh.data
      if (detailModal.value && detailRecord.value?.id === targetId) {
        detailRecord.value = fresh.data
        drawerEditData.value = convertRecordData(fresh.data)
      }
    } catch { /* 刷新失败不阻断 */ }
    loadRollbackHistory(targetId)
  }
  loadRecords()
}

function rollbackTimelineColor(changeType: string) {
  return ({ updated: 'blue', deactivated: 'red', reactivated: 'green', reviewed: 'gray', ignored: 'gray', rollback: 'orange' } as Record<string, string>)[changeType] || 'blue'
}

function rollbackChangeTypeColor(changeType: string) {
  return ({ created: 'green', updated: 'blue', deactivated: 'red', reactivated: 'purple', reviewed: 'cyan', ignored: 'default', rollback: 'volcano' } as Record<string, string>)[changeType] || 'default'
}

async function handleRollbackToChange(item: ChangeDetail, targetRecord: ArchiveRecord) {
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
        const res = await archiveRecordApi.rollbackToChange(targetRecord.id, item.id)
        const data = res.data
        if (data.rolled_back_fields === 0) {
          message.info(data.message || '所有字段已是目标值，无需回滚')
        } else {
          message.success(`已回滚 ${data.rolled_back_fields} 个字段到该时点`)
          await refreshAfterRollback()
        }
      } catch (e: any) {
        message.error(extractApiError(e))
      } finally {
        rollbackingId.value = null
      }
    },
  })
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

async function handleSaveDrawer() {
  if (!detailRecord.value) return
  saving.value = true
  try {
    await archiveRecordApi.update(detailRecord.value.id, {
      data: drawerEditData.value,
      updated_by: drawerEditOperator.value || '管理员',
    })
    message.success('更新成功')
    // 保存后关闭弹窗退出
    detailModal.value = false
    await loadRecords()
  } catch (e: any) {
    message.error(e.message || '保存失败')
  } finally {
    saving.value = false
  }
}

// ===== 启用/停用 =====
async function doToggleStatus(rec: ArchiveRecord, newStatus: 'active' | 'deleted') {
  try {
    await archiveRecordApi.update(rec.id, {
      status: newStatus,
      updated_by: '管理员',
    })
    message.success(newStatus === 'active' ? '已启用' : '已停用')
    await loadRecords()
  } catch (e: any) {
    message.error(e.message || '操作失败')
  }
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
:deep(.col-flash) {
  background-color: #fff7e6 !important;
}
</style>
