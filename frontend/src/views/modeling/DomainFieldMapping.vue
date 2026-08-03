<template>
  <div>
    <DomainStageNav :domain-name="domainName" stage="mappings" />

    <div class="page-header">
      <h3 style="margin: 0">关系管理</h3>
      <a-space :size="16">
        <div v-if="pkStatusData" style="display: flex; align-items: center; gap: 8px">
          <a-progress
            :percent="Math.round((pkStatusData.configured_count / pkStatusData.total) * 100)"
            :show-info="false"
            size="small"
            style="width: 120px"
            :status="pkStatusData.all_configured ? 'success' : 'active'"
          />
          <span style="color: #666; font-size: 13px; white-space: nowrap">
            {{ pkStatusData.configured_count }}/{{ pkStatusData.total }} 表已配置
          </span>
        </div>
        <a-tag v-if="pkStatusData?.all_configured" color="success" style="margin: 0">✓ 全部完成</a-tag>
        <a-button type="primary" @click="openCreate()">+ 新建映射</a-button>
        <a-button :type="erFullScreen ? 'primary' : 'default'" @click="toggleErFullScreen">
          {{ erFullScreen ? '返回列表' : 'ER图全屏' }}
        </a-button>
      </a-space>
    </div>

    <!-- 映射列表（全屏ER图模式下隐藏） -->
    <a-card v-show="!erFullScreen" :loading="loading" :bordered="false">
      <a-table
        :dataSource="mappingRows"
        :columns="mappingColumns"
        :pagination="false"
        rowKey="id"
        size="middle"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'source_table'">
            <span style="font-weight: 500">{{ record.source_table_name }}</span>
          </template>
          <template v-if="column.key === 'source_field'">
            <span :style="record.is_source_pk ? 'color: #faad14; font-weight: 500' : ''">
              <span v-if="record.is_source_pk" style="margin-right: 2px">⚿</span>{{ record.source_field_name }}
            </span>
          </template>
          <template v-if="column.key === 'target_table'">
            <span style="font-weight: 500">{{ record.target_table_name }}</span>
          </template>
          <template v-if="column.key === 'target_field'">
            <span :style="record.is_target_pk ? 'color: #faad14; font-weight: 500' : ''">
              <span v-if="record.is_target_pk" style="margin-right: 2px">⚿</span>{{ record.target_field_name }}
            </span>
          </template>
          <template v-if="column.key === 'action'">
            <a-space>
              <a @click="openEdit(record)" style="color: #1677ff">编辑</a>
              <a-popconfirm title="确定删除此映射？" @confirm="doDelete(record)">
                <a style="color: #ff4d4f">删除</a>
              </a-popconfirm>
            </a-space>
          </template>
        </template>
      </a-table>
      <a-empty v-if="!loading && mappingRows.length === 0" description="暂无关系映射，请点击「新建映射」创建" />
    </a-card>

    <a-card title="ER 关系图" :style="erFullScreen ? 'margin-top: 0' : 'margin-top: 16px'">
      <template #extra>
        <div style="display: flex; align-items: center; gap: 12px; width: 100%">
          <span style="color: #999; font-size: 12px">节点展示表与字段，连线标注具体字段映射关系（可拖动节点调整布局）</span>
          <a-button size="small" @click="resetErLayout" :loading="resettingEr" style="margin-left: auto">重置布局</a-button>
        </div>
      </template>
      <div v-show="mappings.length > 0" ref="erContainer" :class="erFullScreen ? 'er-container er-container--full' : 'er-container'"></div>
      <a-empty v-if="mappings.length === 0" description="暂无关系可展示" />
    </a-card>

    <a-modal v-model:open="modalVisible" :title="modalTitle" @ok="handleSubmit" :confirmLoading="saving" width="640px">
      <a-form layout="vertical">
        <a-form-item label="源表" required>
          <a-select v-model:value="form.source_table" style="width: 100%" show-search @change="loadSourceFields" :disabled="!!editingMappingId">
            <a-select-option v-for="t in domainTables" :key="t.id" :value="t.id">{{ t.name }} ({{ t.code }})</a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item label="源字段" required>
          <a-select v-model:value="form.source_field" style="width: 100%" show-search allowClear placeholder="请选择源字段">
            <a-select-option v-if="hasCompositeSourceKey" :value="'composite'" :title="compositeKeyLabel">
              <span style="color: #faad14; margin-right: 4px">⚿</span>
              <span style="font-weight: 600">{{ compositeKeyLabel }}</span>
              <span style="color: #888; font-size: 11px; margin-left: 4px">(联合主键)</span>
            </a-select-option>
            <a-select-option v-for="f in sourceFields" :key="f.id" :value="f.id">
              <span v-if="f.is_primary_key" style="color: #faad14; margin-right: 4px">⚿</span>{{ f.name }} ({{ f.code }})
            </a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item label="目标表" required>
          <a-select v-model:value="form.target_table" style="width: 100%" show-search @change="loadTargetFields">
            <a-select-option v-for="t in targetTableOptions" :key="t.id" :value="t.id">{{ t.name }} ({{ t.code }})</a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item label="目标字段" required>
          <a-select v-model:value="form.target_field" style="width: 100%" show-search allowClear placeholder="请选择目标字段">
            <a-select-option v-if="hasCompositeTargetKey" :value="'composite'" :title="targetCompositeKeyLabel">
              <span style="color: #faad14; margin-right: 4px">⚿</span>
              <span style="font-weight: 600">{{ targetCompositeKeyLabel }}</span>
              <span style="color: #888; font-size: 11px; margin-left: 4px">(联合主键)</span>
            </a-select-option>
            <a-select-option v-for="f in targetFields" :key="f.id" :value="f.id">
              <span v-if="f.is_primary_key" style="color: #faad14; margin-right: 4px">⚿</span>{{ f.name }} ({{ f.code }})
            </a-select-option>
          </a-select>
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import { message } from 'ant-design-vue'
import { extractApiError } from '@/utils/apiError'
import { Graph, Shape } from '@antv/x6'
import { domainApi, tableApi, fieldApi, fieldMappingApi } from '@/api/modeling'
import type { Table } from '@/types'
import DomainStageNav from './components/DomainStageNav.vue'

const route = useRoute()
const domainId = Number(route.params.id)
const domainName = ref('')
const domainTables = ref<Table[]>([])
const sourceFields = ref<any[]>([])
const targetFields = ref<any[]>([])
const mappings = ref<any[]>([])
const loading = ref(false)
const modalVisible = ref(false)
const saving = ref(false)
const form = ref<any>({ source_table: null, source_field: null, target_table: null, target_field: null })

const editingMappingId = ref<number | null>(null)
// 编辑模式下存储的映射 IDs（联合主键时可能有多个）
const editingMappingIds = ref<number[]>([])

// 主键配置状态
const pkStatusData = ref<any>(null)

// 映射列表列定义
const mappingColumns = [
  { title: '源表', key: 'source_table', width: 180 },
  { title: '源字段', key: 'source_field', width: 200 },
  { title: '目标表', key: 'target_table', width: 180 },
  { title: '目标字段', key: 'target_field', width: 200 },
  { title: '操作', key: 'action', width: 120 },
]

// 映射列表数据：同一对表的映射合并为一行（联合字段=一行，独立关系=一行）
const mappingRows = computed(() => {
  // 构建 PK 字段 ID 集合（用于判断字段是否为主键）
  const pkFieldIdsByTable: Record<number, Set<number>> = {}
  if (pkStatusData.value) {
    for (const t of pkStatusData.value.tables) {
      pkFieldIdsByTable[t.table_id] = new Set(t.pk_fields.map((f: any) => f.id))
    }
  }

  // 第一遍：按 (source_table, target_table) 分组
  const groups: Record<string, any> = {}
  const groupOrder: string[] = []
  for (const m of mappings.value) {
    const key = `${m.source_table}-${m.target_table}`
    if (!groups[key]) {
      groups[key] = {
        key,
        source_table: m.source_table,
        source_table_name: m.source_table_name,
        target_table: m.target_table,
        target_table_name: m.target_table_name,
        mapping_ids: [] as number[],
        _srcNames: [] as string[],
        _tgtNames: [] as string[],
        _srcFields: [] as number[],
        _tgtFields: [] as number[],
      }
      groupOrder.push(key)
    }
    groups[key].mapping_ids.push(m.id)
    groups[key]._srcNames.push(m.source_field_name)
    groups[key]._tgtNames.push(m.target_field_name)
    groups[key]._srcFields.push(m.source_field)
    groups[key]._tgtFields.push(m.target_field)
  }

  // 第二遍：判断每组是否涉及联合字段，生成行
  return groupOrder.map((key) => {
    const g = groups[key]
    const srcUnique = new Set(g._srcFields).size
    const tgtUnique = new Set(g._tgtFields).size
    // 联合字段：源端或目标端使用了多个不同字段
    const isComposite = g.mapping_ids.length > 1 && (srcUnique > 1 || tgtUnique > 1)

    // 判断主键标识
    const srcPkSet = pkFieldIdsByTable[g.source_table]
    const tgtPkSet = pkFieldIdsByTable[g.target_table]

    if (isComposite) {
      return {
        id: `composite-${key}`,
        is_composite: true,
        source_table: g.source_table,
        source_table_name: g.source_table_name,
        target_table: g.target_table,
        target_table_name: g.target_table_name,
        source_field: g._srcFields[0],
        target_field: g._tgtFields[0],
        source_field_name: [...new Set(g._srcNames)].join(' + '),
        target_field_name: [...new Set(g._tgtNames)].join(' + '),
        mapping_ids: g.mapping_ids,
        is_source_pk: g._srcFields.some((f: number) => srcPkSet?.has(f)),
        is_target_pk: g._tgtFields.some((f: number) => tgtPkSet?.has(f)),
      }
    } else {
      // 单条映射（普通映射 或 多对一/一对多但不跨多字段）
      const m = mappings.value.find((mm) => mm.source_table === g.source_table && mm.target_table === g.target_table)!
      return {
        ...m,
        is_composite: false,
        mapping_ids: [m.id],
        is_source_pk: srcPkSet?.has(m.source_field) ?? false,
        is_target_pk: tgtPkSet?.has(m.target_field) ?? false,
      }
    }
  })
})

// 联合主键检测（源表）
const hasCompositeSourceKey = computed(() => {
  const pkFields = sourceFields.value.filter((f: any) => f.is_primary_key)
  return pkFields.length >= 2
})
const compositeKeyLabel = computed(() => {
  const pkFields = sourceFields.value.filter((f: any) => f.is_primary_key)
  return pkFields.map((f: any) => f.code).join(' + ')
})

// 联合主键检测（目标表）
const hasCompositeTargetKey = computed(() => {
  const pkFields = targetFields.value.filter((f: any) => f.is_primary_key)
  return pkFields.length >= 2
})
const targetCompositeKeyLabel = computed(() => {
  const pkFields = targetFields.value.filter((f: any) => f.is_primary_key)
  return pkFields.map((f: any) => f.code).join(' + ')
})

// 目标表选项：排除源表
const targetTableOptions = computed(() => {
  if (!form.value.source_table) return domainTables.value
  return domainTables.value.filter((t) => t.id !== form.value.source_table)
})

// 弹窗标题：编辑时标识具体表对
const modalTitle = computed(() => {
  if (editingMappingId.value && form.value.source_table && form.value.target_table) {
    const src = domainTables.value.find((t) => t.id === form.value.source_table)
    const tgt = domainTables.value.find((t) => t.id === form.value.target_table)
    if (src && tgt) return `编辑字段映射 - ${src.name} → ${tgt.name}`
  }
  return editingMappingId.value ? '编辑字段映射' : '新建字段映射'
})

const erFullScreen = ref(false)
const erContainer = ref<HTMLElement | null>(null)
let graph: Graph | null = null
const resettingEr = ref(false)
const erNodeMap: Record<number, { node: any; tableId: number; tableRef: any }> = {}

// ER 图常量
const ER_HEADER_HEIGHT = 40
const ER_ROW_HEIGHT = 32

async function saveErNodePosition(tid: number, node: any, t: any) {
  const pos = node.getPosition()
  const x = Math.round(pos.x)
  const y = Math.round(pos.y)
  try {
    await tableApi.saveErPosition(tid, x, y)
    if (t) { t.er_node_x = x; t.er_node_y = y }
  } catch { /* 静默失败 */ }
}

async function loadData() {
  loading.value = true
  try {
    const domainRes = await domainApi.get(domainId)
    domainName.value = domainRes.data.name

    const tablesRes = await tableApi.list({ domain: domainId })
    domainTables.value = tablesRes.data.results

    const mapRes = await fieldMappingApi.list({ domain: domainId })
    mappings.value = mapRes.data.results

    // 加载主键配置状态
    const pkRes = await domainApi.pkStatus(domainId)
    pkStatusData.value = pkRes.data
  } finally {
    loading.value = false
  }
  await nextTick()
  renderER()
}

// ===== ER 图渲染 =====
function renderER() {
  if (mappings.value.length === 0) {
    if (graph) { graph.dispose(); graph = null }
    return
  }
  if (!erContainer.value) return

  // 收集参与映射的表
  const tableIds = new Set<number>()
  mappings.value.forEach((m) => {
    tableIds.add(m.source_table)
    tableIds.add(m.target_table)
  })
  const idList = Array.from(tableIds)

  // 为每个表加载字段
  const tableFieldsMap = new Map<number, any[]>()
  const loadPromises = idList.map(async (tid) => {
    const res = await fieldApi.list({ table: tid })
    tableFieldsMap.set(tid, res.data.results)
  })

  Promise.all(loadPromises).then(() => doRenderER(idList, tableFieldsMap))
}

function doRenderER(idList: number[], tableFieldsMap: Map<number, any[]>) {
  if (!erContainer.value) return

  const width = erContainer.value.clientWidth || 900
  const height = erContainer.value.clientHeight || 600
  if (graph) { graph.dispose(); graph = null }

  graph = new Graph({
    container: erContainer.value,
    width,
    height,
    interacting: { nodeMovable: true },
    background: { color: '#fafbfc' },
    connecting: { anchor: 'center', connectionPoint: 'boundary' },
    mousewheel: { enabled: true, modifiers: ['ctrl', 'meta'], factor: 1.05 },
    panning: { enabled: true },
  })

  // 网格布局
  const cols = Math.max(1, Math.min(3, Math.ceil(Math.sqrt(idList.length))))
  const nodeWidth = 320
  const gapX = 40
  const gapY = 36
  const totalContentWidth = cols * nodeWidth + (cols - 1) * gapX
  const startX = Math.max(30, Math.floor((width - totalContentWidth) / 2))
  const colY = new Array(cols).fill(30)
  const nodeMap: Record<number, string> = {}

  idList.forEach((tid, idx) => {
    const t = domainTables.value.find((x) => x.id === tid)
    const rawFields = tableFieldsMap.get(tid) || []
    const col = idx % cols
    const y = colY[col]

    // 检测联合主键：如果表有 2+ 个 PK 字段，合并为一个虚拟字段
    const pkFields = rawFields.filter((f: any) => f.is_primary_key)
    const nonPkFields = rawFields.filter((f: any) => !f.is_primary_key)
    let displayFields: any[]
    if (pkFields.length >= 2) {
      const compositeField = {
        id: 'composite_pk',
        name: pkFields.map((f: any) => f.name).join(' + '),
        code: pkFields.map((f: any) => f.code).join(' + '),
        field_type: 'composite',
        is_primary_key: true,
        is_composite: true,
        _pkFieldIds: pkFields.map((f: any) => f.id),
      }
      displayFields = [compositeField, ...nonPkFields]
    } else {
      displayFields = rawFields
    }
    // 保存 displayFields 供边绘制时使用
    tableFieldsMap.set(tid, displayFields)

    // 收集参与映射的字段 id（高亮用）
    const mappedFieldIds = new Set<number>()
    const mappedComposite = { source: false, target: false }
    mappings.value.forEach((m) => {
      if (m.source_table === tid) {
        if (pkFields.length >= 2 && pkFields.some((pf: any) => pf.id === m.source_field)) {
          mappedComposite.source = true
          mappedFieldIds.add('composite_pk' as any)
        } else {
          mappedFieldIds.add(m.source_field)
        }
      }
      if (m.target_table === tid) {
        if (pkFields.length >= 2 && pkFields.some((pf: any) => pf.id === m.target_field)) {
          mappedComposite.target = true
          mappedFieldIds.add('composite_pk' as any)
        } else {
          mappedFieldIds.add(m.target_field)
        }
      }
    })

    // 构建字段行 HTML：中文名优先，英文名括号补充
    const fieldRows = displayFields.length > 0
      ? displayFields.map((f: any) => {
          const isKey = mappedFieldIds.has(f.id) || (f.is_composite && (mappedComposite.source || mappedComposite.target))
          const typeShort = ({ string: 'varchar', number: 'int', date: 'date', boolean: 'bool', enum: 'enum', composite: '⚿联合' } as any)[f.field_type] || f.field_type
          const typeLabel = f.length ? `${typeShort}(${f.length})` : typeShort
          // 中文名优先展示：comment（中文注释）> name > code
          // 外部数据源同步时 name/code 都是英文列名，中文描述在 comment 中
          const displayName = f.comment || f.name || f.code || ''
          const subName = f.code && f.code !== displayName ? escapeHtml(f.code) : ''
          const cnName = escapeHtml(displayName)
          const enName = subName
          const nameHtml = enName
            ? `<div class="er-f__name-cn" title="${cnName} (${enName})">${cnName}</div><div class="er-f__name-en">${enName}</div>`
            : `<div class="er-f__name-cn" title="${cnName}">${cnName}</div>`
          return `
            <div class="er-f${isKey ? ' er-f--key' : ''}${f.is_composite ? ' er-f--composite' : ''}" data-field-id="${f.id}">
              <span class="er-f__icon">${isKey ? '⚿' : '○'}</span>
              <div class="er-f__name-wrap">${nameHtml}</div>
              <span class="er-f__type">${escapeHtml(typeLabel)}</span>
            </div>
          `
        }).join('')
      : '<div class="er-f er-f--empty">暂无字段</div>'

    const nodeHtml = `
      <div class="er-node">
        <div class="er-node__header">
          <span class="er-node__icon">🗂</span>
          <div class="er-node__title-wrap">
            <div class="er-node__name">${escapeHtml(t?.name || `表#${tid}`)}</div>
            <div class="er-node__code">${escapeHtml(t?.code || '')}</div>
          </div>
        </div>
        <div class="er-node__body">${fieldRows}</div>
      </div>
    `

    // 节点高度：显示所有字段（不截断）
    const nodeHeight = ER_HEADER_HEIGHT + Math.max(1, displayFields.length) * ER_ROW_HEIGHT + 4

    const shapeName = `er-table-${tid}`
    Shape.HTML.register({
      shape: shapeName,
      html: nodeHtml,
    })

    // 使用保存的位置或自动布局
    const savedX = t?.er_node_x
    const savedY = t?.er_node_y
    let nodeX: number, nodeY: number
    if (savedX != null && savedY != null) {
      nodeX = savedX
      nodeY = savedY
    } else {
      nodeX = startX + col * (nodeWidth + gapX)
      nodeY = y
    }

    const node = graph!.addNode({
      x: nodeX,
      y: nodeY,
      width: nodeWidth,
      height: nodeHeight,
      shape: shapeName,
      attrs: {
        body: { fill: '#ffffff', stroke: '#c9cdd4', rx: 4, ry: 4, strokeWidth: 1 },
        label: { text: '' },
      },
    })
    nodeMap[tid] = node.id
    erNodeMap[tid] = { node, tableId: tid, tableRef: t }

    node.on('change:position', () => {
      saveErNodePosition(tid, node, t)
    })

    if (savedX == null || savedY == null) {
      colY[col] = nodeY + nodeHeight + gapY
    }
  })

  // 构建字段索引映射（用于边锚点计算）
  // displayFields 已包含虚拟联合主键字段，需处理复合PK字段到虚拟字段的映射
  const fieldIndexMap = new Map<number, Map<number, number>>()
  const compositePkTables = new Set<number>()
  tableFieldsMap.forEach((fields, tid) => {
    const idxMap = new Map<number, number>()
    fields.forEach((f, idx) => {
      idxMap.set(f.id, idx)
      if (f.is_composite) compositePkTables.add(tid)
    })
    fieldIndexMap.set(tid, idxMap)
  })

  // 绘制边：列表有多少行，ER 图就有多少条线（联合主键=一条）
  // 注意：top 锚点的 dx/dy 是比例值(0-1)，不是像素值
  // dx: 0.5 = 右边缘, dx: -0.5 = 左边缘
  // dy: ratio = 像素偏移 / 节点高度
  mappingRows.value.forEach((m) => {
    const sourceIsCompositePk = compositePkTables.has(m.source_table)
    const targetIsCompositePk = compositePkTables.has(m.target_table)

    let sourceIdx = fieldIndexMap.get(m.source_table)?.get(m.source_field) ?? 0
    let targetIdx = fieldIndexMap.get(m.target_table)?.get(m.target_field) ?? 0

    // 联合主键行：指向虚拟联合主键字段（index 0）
    if (m.is_composite) {
      if (sourceIsCompositePk) sourceIdx = 0
      if (targetIsCompositePk) targetIdx = 0
    }

    // 计算节点高度（用于 dy 比例换算）
    const sourceFieldsCount = tableFieldsMap.get(m.source_table)?.length ?? 1
    const targetFieldsCount = tableFieldsMap.get(m.target_table)?.length ?? 1
    const sourceNodeHeight = ER_HEADER_HEIGHT + Math.max(1, sourceFieldsCount) * ER_ROW_HEIGHT + 4
    const targetNodeHeight = ER_HEADER_HEIGHT + Math.max(1, targetFieldsCount) * ER_ROW_HEIGHT + 4

    // 字段行中心 Y 像素偏移 → 转为比例值
    const sourceFieldY = ER_HEADER_HEIGHT + sourceIdx * ER_ROW_HEIGHT + ER_ROW_HEIGHT / 2
    const targetFieldY = ER_HEADER_HEIGHT + targetIdx * ER_ROW_HEIGHT + ER_ROW_HEIGHT / 2

    graph!.addEdge({
      source: {
        cell: nodeMap[m.source_table],
        anchor: {
          name: 'top',
          args: {
            dx: 0.5,  // 右边缘
            dy: sourceFieldY / sourceNodeHeight,
          },
        },
      },
      target: {
        cell: nodeMap[m.target_table],
        anchor: {
          name: 'top',
          args: {
            dx: -0.5, // 左边缘
            dy: targetFieldY / targetNodeHeight,
          },
        },
      },
      router: { name: 'manhattan', args: { padding: 16 } },
      connector: { name: 'rounded', args: { radius: 6 } },
      attrs: {
        line: {
          stroke: '#faad14',
          strokeWidth: 1.5,
          targetMarker: { name: 'block', size: 8, fill: '#faad14' },
        },
      },
    })
  })
}

function escapeHtml(s: string) {
  return String(s).replace(/[<>&"]/g, (c) => ({ '<': '&lt;', '>': '&gt;', '&': '&amp;', '"': '&quot;' }[c]!))
}

async function loadSourceFields() {
  if (form.value.source_table) {
    const res = await fieldApi.list({ table: form.value.source_table })
    sourceFields.value = res.data.results.sort((a: any, b: any) => (b.is_primary_key ? 1 : 0) - (a.is_primary_key ? 1 : 0))
    // 自动选中：联合主键选 'composite'，单主键选该字段
    const pkFields = sourceFields.value.filter((f: any) => f.is_primary_key)
    if (pkFields.length >= 2) {
      form.value.source_field = 'composite'
    } else if (pkFields.length === 1) {
      form.value.source_field = pkFields[0].id
    } else {
      form.value.source_field = null
    }
  }
}

async function loadTargetFields() {
  if (form.value.target_table) {
    const res = await fieldApi.list({ table: form.value.target_table })
    targetFields.value = res.data.results.sort((a: any, b: any) => (b.is_primary_key ? 1 : 0) - (a.is_primary_key ? 1 : 0))
    const pkFields = targetFields.value.filter((f: any) => f.is_primary_key)
    if (pkFields.length >= 2) {
      form.value.target_field = 'composite'
    } else if (pkFields.length === 1) {
      form.value.target_field = pkFields[0].id
    } else {
      form.value.target_field = null
    }
  }
}

function openCreate() {
  editingMappingId.value = null
  editingMappingIds.value = []
  form.value = { source_table: null, source_field: null, target_table: null, target_field: null }
  sourceFields.value = []
  targetFields.value = []
  modalVisible.value = true
}

async function openEdit(row: any) {
  editingMappingIds.value = row.mapping_ids || [row.id]
  editingMappingId.value = editingMappingIds.value[0] || null
  
  form.value = {
    source_table: row.source_table,
    source_field: null,
    target_table: row.target_table,
    target_field: null,
  }
  
  // 加载源字段和目标字段
  await Promise.all([loadSourceFields(), loadTargetFields()])
  
  // 恢复选中值（loadXxxFields 会覆盖 form 值，需要重新设置）
  if (row.is_composite) {
    // 联合主键行：源/目标均选中虚拟联合主键选项
    form.value.source_field = 'composite'
    form.value.target_field = 'composite'
  } else {
    form.value.source_field = row.source_field
    form.value.target_field = row.target_field
  }
  
  modalVisible.value = true
}

async function handleSubmit() {
  if (!form.value.source_field || !form.value.target_field) {
    message.warning('请选择源字段和目标字段')
    return
  }
  saving.value = true
  try {
    // R-021: 先建后删——创建新映射成功后再删除旧映射，避免创建失败时数据丢失
    const sourceIsComposite = form.value.source_field === 'composite'
    const targetIsComposite = form.value.target_field === 'composite'
    
    if (sourceIsComposite && targetIsComposite) {
      const sourcePks = sourceFields.value.filter((f: any) => f.is_primary_key)
      const targetPks = targetFields.value.filter((f: any) => f.is_primary_key)
      const count = Math.min(sourcePks.length, targetPks.length)
      for (let i = 0; i < count; i++) {
        await fieldMappingApi.create({
          source_table: form.value.source_table,
          source_field: sourcePks[i].id,
          target_table: form.value.target_table,
          target_field: targetPks[i].id,
        })
      }
    } else if (sourceIsComposite) {
      const sourcePks = sourceFields.value.filter((f: any) => f.is_primary_key)
      for (const pk of sourcePks) {
        await fieldMappingApi.create({
          source_table: form.value.source_table,
          source_field: pk.id,
          target_table: form.value.target_table,
          target_field: form.value.target_field,
        })
      }
    } else if (targetIsComposite) {
      const targetPks = targetFields.value.filter((f: any) => f.is_primary_key)
      for (const pk of targetPks) {
        await fieldMappingApi.create({
          source_table: form.value.source_table,
          source_field: form.value.source_field,
          target_table: form.value.target_table,
          target_field: pk.id,
        })
      }
    } else {
      await fieldMappingApi.create({
        source_table: form.value.source_table,
        source_field: form.value.source_field,
        target_table: form.value.target_table,
        target_field: form.value.target_field,
      })
    }

    // 新映射创建成功后，再删除旧映射
    for (const id of editingMappingIds.value) {
      await fieldMappingApi.delete(id)
    }
    
    message.success(editingMappingIds.value.length > 0 ? '映射更新成功' : '映射创建成功')
    modalVisible.value = false
    editingMappingId.value = null
    editingMappingIds.value = []
    await loadData()
  } catch (e: any) {
    message.error(extractApiError(e) || e.message || '操作失败')
  } finally {
    saving.value = false
  }
}

async function doDelete(row: any) {
  try {
    const ids = row.mapping_ids || [row.id]
    for (const id of ids) {
      await fieldMappingApi.delete(id)
    }
    message.success('删除成功')
    await loadData()
  } catch (e: any) {
    message.error(e.message || '删除失败')
  }
}

function toggleErFullScreen() {
  erFullScreen.value = !erFullScreen.value
  // 切换后需要重新渲染 ER 图以适应新容器尺寸
  nextTick(() => {
    renderER()
  })
}

async function resetErLayout() {
  resettingEr.value = true
  try {
    await tableApi.batchResetErPosition(domainId)
    const tablesRes = await tableApi.list({ domain: domainId })
    domainTables.value = tablesRes.data.results
    message.success('布局已重置')
    await nextTick()
    renderER()
  } catch (e: any) {
    message.error(e.message || '重置失败')
  } finally {
    resettingEr.value = false
  }
}

onMounted(loadData)

onBeforeUnmount(() => {
  for (const tid of Object.keys(erNodeMap)) {
    const { node, tableRef } = erNodeMap[Number(tid)]
    if (node && graph) {
      saveErNodePosition(Number(tid), node, tableRef)
    }
  }
})
</script>

<style scoped>
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  flex-wrap: wrap;
}
.er-container {
  width: 100%;
  height: 600px;
  border: 1px solid #eef0f4;
  border-radius: 8px;
  background: #fafbfc;
}
.er-container--full {
  height: calc(100vh - 220px);
  min-height: 500px;
}

/* ER 图节点样式 */
:deep(.er-node) {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  background: #fff;
  border-radius: 4px;
  overflow: hidden;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.08);
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  transition: box-shadow 0.2s ease;
}
:deep(.er-node:hover) {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.12);
}
:deep(.er-node__header) {
  background: linear-gradient(135deg, #5b8def 0%, #4a7bd8 100%);
  color: #fff;
  padding: 8px 12px;
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}
:deep(.er-node__icon) {
  font-size: 16px;
  flex-shrink: 0;
}
:deep(.er-node__title-wrap) {
  flex: 1;
  min-width: 0;
}
:deep(.er-node__name) {
  font-weight: 600;
  font-size: 13px;
  line-height: 1.3;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: #fff;
}
:deep(.er-node__code) {
  font-size: 11px;
  opacity: 0.75;
  font-family: 'Consolas', monospace;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: #e0e7ff;
}
:deep(.er-node__body) {
  flex: 1;
  padding: 2px 0;
  overflow-y: auto;
  background: #fff;
  display: flex;
  flex-direction: column;
}
:deep(.er-f) {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 12px;
  font-size: 12px;
  color: #262626;
  border-bottom: 1px solid #f0f0f0;
  line-height: 1.6;
  flex: 0 0 auto;
}
:deep(.er-node__body > .er-f:last-child) {
  border-bottom: none;
  margin-bottom: auto;
}
:deep(.er-f:hover) {
  background: #f5f9ff;
}
:deep(.er-f--key) {
  background: #fffbe6;
  color: #0958d9;
  font-weight: 500;
}
:deep(.er-f--key:hover) {
  background: #fff7cc;
}
:deep(.er-f--empty) {
  color: #bfbfbf;
  font-style: italic;
  justify-content: center;
  padding: 8px;
}
:deep(.er-f__icon) {
  font-size: 11px;
  color: #8c8c8c;
  flex-shrink: 0;
  width: 12px;
  text-align: center;
}
:deep(.er-f--key .er-f__icon) {
  color: #faad14;
}
:deep(.er-f__name-wrap) {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  line-height: 1.3;
}
:deep(.er-f__name-cn) {
  font-size: 12px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
:deep(.er-f__name-en) {
  font-size: 10px;
  color: #8c8c8c;
  font-family: 'Consolas', monospace;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
:deep(.er-f--key .er-f__name-en) {
  color: #1677ff;
}
:deep(.er-f--composite) {
  background: #fff7e6;
  border-left: 3px solid #faad14;
}
:deep(.er-f--composite.er-f--key) {
  background: #fffbe6;
  border-left: 3px solid #faad14;
}
:deep(.er-f__type) {
  color: #8c8c8c;
  font-size: 10px;
  font-family: 'Consolas', monospace;
  padding: 1px 5px;
  background: #f5f5f5;
  border-radius: 3px;
  flex-shrink: 0;
}
:deep(.er-f--key .er-f__type) {
  background: #e6f4ff;
  color: #1677ff;
}
</style>
