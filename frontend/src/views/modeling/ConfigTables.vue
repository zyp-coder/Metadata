<template>
  <div>
    <DomainStageNav :domain-name="domainName" stage="config-tables" />

    <div class="page-header">
      <h3 style="margin: 0">配置表</h3>
      <a-button type="primary" @click="startCreate" :disabled="showCreateForm">+ 新建配置表</a-button>
    </div>

    <!-- 新建表单（内联） -->
    <div v-if="!editingId && showCreateForm" class="create-form">
      <a-space :size="12" align="end">
        <a-form-item label="表名称" required style="margin-bottom: 0">
          <a-input v-model:value="newTableName" placeholder="如：产品类型映射" style="width: 200px" />
        </a-form-item>
        <a-form-item label="表编码" required style="margin-bottom: 0">
          <a-input v-model:value="newTableCode" placeholder="如：product_type" style="width: 200px" />
        </a-form-item>
        <a-form-item style="margin-bottom: 0">
          <a-space>
            <a-button type="primary" :loading="creating" @click="doCreate">确定</a-button>
            <a-button @click="cancelCreate">取消</a-button>
          </a-space>
        </a-form-item>
      </a-space>
    </div>

    <!-- 配置表列表 -->
    <a-table
      :dataSource="configTables"
      :columns="listColumns"
      :loading="loading"
      :pagination="false"
      rowKey="id"
      :scroll="{ x: 800 }"
      :customRow="(record: ConfigTable) => ({ onClick: () => selectTable(record), style: { cursor: 'pointer', background: selectedId === record.id ? '#e6f4ff' : '' } })"
    >
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'status'">
          <a-switch
            :checked="record.status === 'active'"
            checked-children="启用"
            un-checked-children="停用"
            size="small"
            :loading="record._toggling"
            @change="(checked: boolean) => handleToggleStatus(record, checked)"
          />
        </template>
        <template v-if="column.key === 'action'">
          <a-space :size="4" style="white-space: nowrap">
            <a @click.stop="openEditModal(record)" style="color: #1677ff">编辑</a>
            <a style="color: #ff4d4f" @click.stop="confirmDelete(record)">删除</a>
          </a-space>
        </template>
      </template>
    </a-table>

    <!-- 配置表编辑弹窗 -->
    <a-modal
      v-model:open="editModalVisible"
      :title="`编辑配置表 - ${selectedTable?.name || ''}`"
      width="1000px"
      :destroyOnClose="true"
      :footer="null"
    >
      <template v-if="selectedTable">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
          <div>
            <span style="color:#888;font-size:12px">编码：{{ selectedTable.code }}</span>
            <span v-if="selectedTable.last_synced_at" style="color:#52c41a;margin-left:12px;font-size:12px">
              最后同步：{{ formatDateTime(selectedTable.last_synced_at) }}
            </span>
          </div>
          <a-space>
            <a-button size="small" @click="addRow">+ 添加行</a-button>
            <a-button size="small" type="primary" :loading="savingRows" @click="saveRows">保存</a-button>
          </a-space>
        </div>

        <!-- 数据源同步配置区 -->
        <div class="sync-section">
          <a-collapse :bordered="false" v-model:activeKey="syncExpanded">
            <a-collapse-panel key="sync" header="数据源同步配置">
              <a-space direction="vertical" style="width:100%" :size="12">
                <div style="display:flex;gap:12px;align-items:end">
                  <a-form-item label="数据源" style="margin-bottom:0;flex:1">
                    <a-select
                      v-model:value="syncForm.data_source"
                      placeholder="选择数据源"
                      allowClear
                      style="width:100%"
                      @change="onDataSourceChange"
                    >
                      <a-select-option v-for="ds in dataSources" :key="ds.id" :value="ds.id">
                        {{ ds.name }} ({{ ds.db_type }}:{{ ds.host }}/{{ ds.db_name }})
                      </a-select-option>
                    </a-select>
                  </a-form-item>
                  <a-button size="small" :loading="previewing" @click="doPreview" :disabled="!syncForm.data_source || !syncForm.sync_sql.trim()">
                    预览结果
                  </a-button>
                  <a-button size="small" type="primary" :loading="syncing" @click="doSync" :disabled="!syncForm.data_source || !syncForm.sync_sql.trim()">
                    执行同步
                  </a-button>
                </div>
                <a-form-item label="SQL 查询（结果前两列作为 Key-Value）" style="margin-bottom:0">
                  <a-textarea
                    v-model:value="syncForm.sync_sql"
                    :rows="3"
                    placeholder="如：SELECT DISTINCT SUBSTRING(code, -3) AS key, name AS value FROM product_table ORDER BY key"
                    style="font-family:monospace;font-size:12px"
                  />
                </a-form-item>
                <div v-if="syncForm.data_source" style="font-size:12px;color:#888">
                  提示：只允许 SELECT 查询，超时 30 秒，最多返回 10000 行
                </div>
              </a-space>
              <!-- 预览结果 -->
              <div v-if="previewResult" style="margin-top:12px">
                <div style="font-size:12px;color:#888;margin-bottom:4px">
                  预览结果（{{ previewResult.row_count }} 行）
                  <span v-if="previewResult.truncated" style="color:#faad14">（已截断）</span>
                </div>
                <a-table
                  :dataSource="previewRows"
                  :columns="previewColumns"
                  :pagination="false"
                  :scroll="{ y: 200 }"
                  size="small"
                  rowKey="_idx"
                />
              </div>
            </a-collapse-panel>
          </a-collapse>
        </div>

        <div style="font-size:12px;color:#888;margin:12px 0 8px">
          共 {{ dataRows.length }} 行 · 第一列为查找键（Key），第二列为映射结果（Value）
        </div>
        <a-table
          :dataSource="dataRows"
          :columns="dataColumns"
          :pagination="false"
          rowKey="_idx"
          size="small"
          :scroll="{ y: 400 }"
        >
          <template #bodyCell="{ column, record: row, index }">
            <template v-if="column.dataIndex === '__action__'">
              <a-popconfirm
                title="确定删除此行？保存后生效"
                @confirm="dataRows.splice(index, 1)"
                ok-text="确定"
                cancel-text="取消"
              >
                <a style="color:#ff4d4f">删除</a>
              </a-popconfirm>
            </template>
            <template v-else>
              <a-input
                :value="row[column.dataIndex]"
                size="small"
                @change="(e: any) => row[column.dataIndex] = e.target.value"
              />
            </template>
          </template>
        </a-table>
      </template>
    </a-modal>

    <!-- 删除确认 -->
    <a-modal
      v-model:open="deleteConfirmVisible"
      title="确认删除"
      @ok="doDelete"
      :confirmLoading="deleting"
    >
      <p>确定要删除配置表「{{ deletingTable?.name }}」吗？删除后公式中引用该表编码将失效。</p>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { message } from 'ant-design-vue'
import DomainStageNav from './components/DomainStageNav.vue'
import { configTableApi, domainApi, dataSourceApi, type ConfigTable } from '@/api/modeling'
import { formatDateTime } from '@/utils/date'
import { extractApiError } from '@/utils/apiError'

const route = useRoute()
const domainId = Number(route.params.id)

// 域名称
const domainName = ref('')
onMounted(async () => {
  try {
    const res = await domainApi.get(domainId)
    domainName.value = res.data.name
  } catch { /* ignore */ }
  loadData()
})

// ── 列表 ──
const loading = ref(false)
const configTables = ref<(ConfigTable & { _toggling?: boolean })[]>([])

async function loadData() {
  loading.value = true
  try {
    const res = await configTableApi.list({ domain: domainId })
    configTables.value = res.data.results
  } catch (e: any) {
    message.error(extractApiError(e) || '加载配置表失败')
  } finally {
    loading.value = false
  }
}

const listColumns = [
  { title: '表名称', dataIndex: 'name', key: 'name', width: 180 },
  { title: '编码', dataIndex: 'code', key: 'code', width: 160 },
  { title: '数据行数', dataIndex: 'row_count', key: 'row_count', width: 100 },
  { title: '状态', key: 'status', width: 100 },
  { title: '创建时间', dataIndex: 'created_at', key: 'created_at', width: 160,
    customRender: ({ text }: any) => formatDateTime(text) },
  { title: '操作', key: 'action', width: 120, fixed: 'right' as const },
]

// ── 新建 ──
const showCreateForm = ref(false)
const newTableName = ref('')
const newTableCode = ref('')
const creating = ref(false)
const editingId = ref<number | null>(null)

function startCreate() {
  showCreateForm.value = true
  newTableName.value = ''
  newTableCode.value = ''
}

async function handleToggleStatus(record: ConfigTable & { _toggling?: boolean }, checked: boolean) {
  const newStatus = checked ? 'active' : 'deprecated'
  record._toggling = true
  try {
    await configTableApi.patch(record.id, { status: newStatus })
    record.status = newStatus
    message.success(checked ? '已启用' : '已停用')
  } catch (e: any) {
    message.error(extractApiError(e) || '操作失败')
  } finally {
    record._toggling = false
  }
}

function cancelCreate() {
  showCreateForm.value = false
  newTableName.value = ''
  newTableCode.value = ''
}

async function doCreate() {
  if (!newTableName.value.trim()) { message.warning('请输入表名称'); return }
  if (!newTableCode.value.trim()) { message.warning('请输入表编码'); return }
  creating.value = true
  try {
    const res = await configTableApi.create({
      domain: domainId,
      name: newTableName.value.trim(),
      code: newTableCode.value.trim(),
      columns: ['Key', 'Value'],
      rows: [],
      status: 'active',
    })
    message.success('创建成功，请在下方表格中填写映射数据')
    showCreateForm.value = false
    await loadData()
    // 自动选中新建的表
    selectedId.value = res.data.id
    selectedTable.value = res.data
    openDataEditor(res.data)
  } catch (e: any) {
    message.error(extractApiError(e) || '创建失败')
  } finally {
    creating.value = false
  }
}

// ── 删除 ──
const deleteConfirmVisible = ref(false)
const deletingTable = ref<ConfigTable | null>(null)
const deleting = ref(false)

function confirmDelete(record: ConfigTable) {
  deletingTable.value = record
  deleteConfirmVisible.value = true
}

async function doDelete() {
  if (!deletingTable.value) return
  deleting.value = true
  try {
    await configTableApi.delete(deletingTable.value.id)
    message.success('删除成功')
    if (selectedId.value === deletingTable.value.id) {
      selectedId.value = null
      selectedTable.value = null
      dataRows.value = []
    }
    await loadData()
  } catch (e: any) {
    message.error(extractApiError(e) || '删除失败')
  } finally {
    deleting.value = false
    deleteConfirmVisible.value = false
    deletingTable.value = null
  }
}

// ── 选中 & 数据编辑 ──
const selectedId = ref<number | null>(null)
const selectedTable = ref<ConfigTable | null>(null)
const dataRows = ref<Record<string, any>[]>([])
const savingRows = ref(false)

// ── 数据源同步 ──
const syncExpanded = ref<string[]>([])
const dataSources = ref<any[]>([])
const syncing = ref(false)
const previewing = ref(false)
const previewResult = ref<any>(null)
const previewRows = ref<any[]>([])
const previewColumns = ref<any[]>([])
const syncForm = ref({
  data_source: null as number | null,
  sync_sql: '',
})

onMounted(async () => {
  try {
    const res = await dataSourceApi.list()
    dataSources.value = (res.data as any).results || res.data || []
  } catch { /* ignore */ }
})

function onDataSourceChange() {
  previewResult.value = null
}

async function doPreview() {
  if (!syncForm.value.data_source || !syncForm.value.sync_sql.trim()) return
  previewing.value = true
  try {
    const res = await dataSourceApi.executeQuery(
      syncForm.value.data_source,
      syncForm.value.sync_sql,
      100,
    )
    previewResult.value = res.data
    previewColumns.value = res.data.columns.map((col: string) => ({
      title: col, dataIndex: col, key: col, ellipsis: true,
    }))
    previewRows.value = res.data.rows.map((row: any, idx: number) => ({ _idx: idx, ...row }))
  } catch (e: any) {
    message.error(extractApiError(e) || '预览失败')
  } finally {
    previewing.value = false
  }
}

async function doSync() {
  if (!selectedTable.value || !syncForm.value.data_source || !syncForm.value.sync_sql.trim()) return
  syncing.value = true
  try {
    // 先保存同步配置（PATCH 只更新同步字段，不影响其他数据）
    await configTableApi.patch(selectedTable.value.id, {
      data_source: syncForm.value.data_source,
      sync_sql: syncForm.value.sync_sql,
    })
    // 执行同步
    const res = await configTableApi.sync(selectedTable.value.id)
    message.success(`同步成功：${res.data.row_count} 行`)
    // 刷新数据
    await loadData()
    if (selectedTable.value) {
      await openDataEditor(selectedTable.value)
    }
  } catch (e: any) {
    message.error(extractApiError(e) || '同步失败')
  } finally {
    syncing.value = false
  }
}

const KEY_COL = 'Key'
const VAL_COL = 'Value'

const dataColumns = [
  { title: 'Key（查找值）', dataIndex: KEY_COL, key: KEY_COL, width: '40%' },
  { title: 'Value（映射结果）', dataIndex: VAL_COL, key: VAL_COL, width: '40%' },
  { title: '', dataIndex: '__action__', key: '__action__', width: 60 },
]

function selectTable(record: ConfigTable) {
  if (selectedId.value === record.id) return
  selectedId.value = record.id
  selectedTable.value = record
  // 填充同步表单
  syncForm.value.data_source = record.data_source
  syncForm.value.sync_sql = record.sync_sql || ''
  previewResult.value = null
  openDataEditor(record)
}

async function openDataEditor(record: ConfigTable) {
  try {
    const res = await configTableApi.getRows(record.id)
    const rows = res.data.rows || []
    // 兼容旧表：取第一列=Key，第二列=Value（不管原列名叫什么）
    const cols = record.columns || []
    const origKey = cols[0] || 'Key'
    const origVal = cols[1] || 'Value'
    dataRows.value = rows.map((row: any, idx: number) => ({
      _idx: idx,
      [KEY_COL]: row[origKey] ?? row[KEY_COL] ?? '',
      [VAL_COL]: row[origVal] ?? row[VAL_COL] ?? '',
    }))
  } catch (e: any) {
    message.error(extractApiError(e) || '加载数据失败')
    dataRows.value = []
  }
}

function addRow() {
  const newRow: Record<string, any> = {
    _idx: dataRows.value.length,
    [KEY_COL]: '',
    [VAL_COL]: '',
  }
  dataRows.value.push(newRow)
}

async function saveRows() {
  if (!selectedTable.value) return
  savingRows.value = true
  try {
    const cleanRows = dataRows.value
      .filter(r => (r[KEY_COL] ?? '').toString().trim() !== '')
      .map(({ _idx, ...row }) => row)
    await configTableApi.updateRows(selectedTable.value.id, cleanRows)
    message.success('保存成功')
    await loadData()
  } catch (e: any) {
    message.error(extractApiError(e) || '保存失败')
  } finally {
    savingRows.value = false
  }
}

// ── 编辑弹窗 ──
const editModalVisible = ref(false)

function openEditModal(record: ConfigTable) {
  if (selectedId.value !== record.id) {
    selectTable(record)
  }
  editModalVisible.value = true
}
</script>

<style scoped>
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}
.create-form {
  background: #fafbfc;
  border: 1px solid #eef0f4;
  border-radius: 6px;
  padding: 16px;
  margin-bottom: 16px;
}
.sync-section {
  background: #fafbfc;
  border: 1px solid #eef0f4;
  border-radius: 6px;
  margin-bottom: 12px;
}
.sync-section :deep(.ant-collapse-header) {
  font-weight: 500;
  font-size: 13px;
}
</style>
