<template>
  <div>
    <DomainStageNav :domain-name="domainName" stage="tables" />

    <div class="page-header">
      <h3 style="margin: 0">表列表</h3>
      <a-space>
        <span style="color: #888; font-size: 13px">点击行可快速预览字段；点击「字段管理」可维护注释、启停字段及预览数据</span>
        <a-button @click="goConfigTables">配置表</a-button>
        <a-button type="primary" @click="openCreate">新建表</a-button>
      </a-space>
    </div>

    <!-- 引导提示：主表/主键配置引导 -->
    <a-alert
      v-if="setupGuideMessage"
      type="info"
      show-icon
      style="margin-bottom: 12px"
    >
      <template #message>
        <span v-html="setupGuideMessage"></span>
      </template>
    </a-alert>

    <a-table
      :dataSource="tables"
      :columns="columns"
      :loading="loading"
      :pagination="false"
      rowKey="id"
      :scroll="{ x: 1430 }"
      :expandable="{ expandedRowRender, expandRowByClick: true }"
    >
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'type'">
          <a-tag :color="getRealType(record) === 'local' ? 'blue' : 'orange'">
            {{ getRealType(record) === 'local' ? '本地表' : '数据源表' }}
          </a-tag>
        </template>
        <template v-if="column.key === 'data_source'">
          {{ record.data_source_name || '-' }}
        </template>
        <template v-if="column.key === 'is_primary'">
          <a-tag v-if="record.is_primary" color="red" style="margin: 0">主表</a-tag>
          <a v-else @click.stop="setPrimary(record)" style="font-size: 12px">设为主表</a>
        </template>
        <template v-if="column.key === 'primary_keys'">
          <template v-if="record.primary_keys && record.primary_keys.length > 0">
            <a-tooltip>
              <template #title>
                {{ record.primary_keys.length > 1 ? '联合主键：' : '主键：' }}
                {{ record.primary_keys.map((pk: any) => pk.comment ? `${pk.code}(${pk.comment})` : pk.code).join('、') }}
              </template>
              <a-space :size="4" wrap>
                <a-tag
                  v-for="pk in record.primary_keys"
                  :key="pk.id"
                  color="gold"
                  style="margin: 0; font-size: 12px"
                >
                  <KeyOutlined style="font-size: 11px; margin-right: 2px" />{{ pk.code }}
                </a-tag>
              </a-space>
            </a-tooltip>
          </template>
          <a v-else @click.stop="openFieldModal(record)" style="color: #faad14; font-size: 12px">
            <KeyOutlined style="margin-right: 2px" />点击设置主键
          </a>
        </template>
        <template v-if="column.key === 'status'">
          <a-switch
            :checked="record.status === 'active'"
            :loading="tableToggles[record.id]"
            checked-children="启用"
            un-checked-children="停用"
            @click.stop
            @change="(v: any) => toggleTableStatus(record, v)"
          />
        </template>
        <template v-if="column.key === 'action'">
          <a-space :size="16">
            <a @click.stop="openFieldModal(record)">字段管理</a>
            <a style="color: #ff4d4f" @click.stop="confirmDeleteTable(record)">删除</a>
          </a-space>
        </template>
      </template>
    </a-table>

    <!-- ========== 字段管理抽屉（R-059：近全屏 modal → 65vw 大抽屉，不遮表列表可边看边管） ========== -->
    <a-drawer
      v-model:open="fieldModalVisible"
      :title="`字段管理 - ${fieldModalTable?.code || ''} (${fieldModalTable?.name || ''})`"
      width="65vw"
      :destroyOnClose="true"
      :bodyStyle="{ padding: '8px 16px' }"
    >
      <a-tabs v-model:activeKey="fieldModalTab">
        <!-- 字段列表 Tab -->
        <a-tab-pane key="fields" tab="字段列表">
          <!-- 主键标识区 -->
          <div
            v-if="pkFieldsList.length > 0"
            style="margin-bottom: 8px; padding: 6px 12px; background: #fffbe6; border: 1px solid #ffe58f; border-radius: 4px; display: flex; align-items: center; gap: 8px; flex-wrap: wrap;"
          >
            <KeyOutlined style="color: #faad14; font-size: 14px" />
            <span style="font-size: 12px; color: #8c6d1f; font-weight: 500">
              {{ pkFieldsList.length > 1 ? '联合主键' : '主键' }}（{{ pkFieldsList.length }} 个字段）：
            </span>
            <a-tag
              v-for="(pk, idx) in pkFieldsList"
              :key="pk.id"
              color="gold"
              style="margin: 0; font-size: 12px"
            >
              {{ idx + 1 }}. {{ pk.code }}<template v-if="pk.comment"> ({{ pk.comment }})</template>
            </a-tag>
          </div>
          <a-table
            :dataSource="fieldModalFields"
            :columns="fieldColumns"
            :pagination="false"
            rowKey="id"
            size="small"
            :scroll="{ y: fieldTableScrollY }"
            :rowClassName="(record: any) => record.is_primary_key ? 'pk-row' : ''"
          >
            <template #bodyCell="{ column, record: fr }">
              <template v-if="column.key === 'field_type'">
                {{ typeLabels[fr.field_type] || fr.field_type }}
              </template>
              <template v-if="column.key === 'is_primary_key'">
                <KeyOutlined
                  :style="{
                    fontSize: '16px',
                    cursor: 'pointer',
                    color: fr.is_primary_key ? '#faad14' : '#d9d9d9',
                    transition: 'color 0.2s'
                  }"
                  :title="fr.is_primary_key ? '取消主键' : '设为主键'"
                  @click="togglePrimaryKey(fr)"
                />
              </template>
              <template v-if="column.key === 'model_field'">
                <a-switch
                  :checked="fr.release_to_concept !== false && fr.status === 'active'"
                  :loading="fieldToggles[`${fr.id}`]"
                  checked-children="启用"
                  un-checked-children="停用"
                  size="small"
                  @change="(v: any) => toggleModelField(fr, v)"
                />
              </template>
              <template v-if="column.key === 'comment'">
                <div
                  v-if="editingCommentId !== fr.id"
                  @click="editingCommentId = fr.id"
                  style="cursor: pointer; padding: 2px 6px; border-radius: 3px; min-height: 24px; line-height: 20px;"
                  :style="{ color: fr.comment ? '#333' : '#bbb' }"
                  :title="'点击编辑'"
                >
                  {{ fr.comment || '未设置' }}
                </div>
                <a-input
                  v-else
                  v-model:value="fr.comment"
                  size="small"
                  placeholder="字段注释"
                  style="width: 100%"
                  @pressEnter="saveFieldComment(fr)"
                  @blur="saveFieldComment(fr)"
                />
              </template>
            </template>
          </a-table>
        </a-tab-pane>

        <!-- 数据预览 Tab -->
        <a-tab-pane key="preview" tab="数据预览">
          <div v-if="previewLoading" style="padding: 40px; text-align: center; color: #999">
            <a-spin /> 加载数据中...
          </div>
          <div v-else-if="previewData.rawColumns.length === 0" style="padding: 40px; text-align: center; color: #999">
            暂无数据可预览
          </div>
          <template v-else>
            <div style="margin-bottom: 8px; display: flex; justify-content: flex-end; align-items: center; gap: 6px">
              <span style="font-size: 12px; color: #888">显示中文名</span>
              <a-switch :checked="previewShowCn" size="small" @change="(v: any) => previewShowCn = v" />
            </div>
            <a-table
              :dataSource="previewData.rows"
              :columns="previewDisplayColumns"
              :pagination="{ pageSize: 20, size: 'small' }"
              rowKey="_rowIndex"
              size="small"
              :scroll="{ x: previewData.totalWidth, y: fieldTableScrollY }"
            />
          </template>
        </a-tab-pane>
      </a-tabs>
      <template #footer>
        <div style="text-align: right">
          <a-button @click="fieldModalVisible = false">关闭</a-button>
        </div>
      </template>
    </a-drawer>
    <a-modal
      v-model:open="modalVisible"
      title="新建表"
      @ok="handleSubmit"
      :confirmLoading="saving"
      width="1152px"
      :bodyStyle="{ maxHeight: 'calc(100vh - 320px)', overflowY: 'auto', paddingTop: '8px' }"
    >
      <a-form :model="formData" layout="vertical">
        <a-form-item label="表类型" required>
          <a-radio-group v-model:value="formData.type">
            <a-radio value="local">本地数据表</a-radio>
            <a-radio value="source">数据源表（指向外部数据库）</a-radio>
          </a-radio-group>
        </a-form-item>

        <!-- ===== 本地数据表：Excel 导入 ===== -->
        <template v-if="formData.type === 'local'">
          <a-form-item label="上传 Excel 文件">
            <a-upload
              :file-list="excelFileList"
              :before-upload="beforeExcelUpload"
              :multiple="true"
              accept=".xlsx,.xls"
              @remove="onExcelFileRemove"
            >
              <a-button><upload-outlined />选择 Excel 文件</a-button>
            </a-upload>
          </a-form-item>

          <template v-if="excelConfigs.length > 0">
            <a-divider>文件列表配置</a-divider>
            <a-table
              :dataSource="excelConfigs"
              :columns="excelConfigColumns"
              :pagination="false"
              rowKey="file_name"
              size="small"
            >
              <template #bodyCell="{ column, record: cfg, index: idx }">
                <template v-if="column.key === 'ec_code'">
                  <a-input v-model:value="cfg.code" placeholder="编码" size="small" style="width: 130px" />
                </template>
                <template v-if="column.key === 'ec_name_en'">
                  <a-input v-model:value="cfg.name_en" placeholder="英文名称" size="small" style="width: 130px" />
                </template>
                <template v-if="column.key === 'ec_name_cn'">
                  <a-input v-model:value="cfg.name_cn" placeholder="中文名称" size="small" style="width: 130px" />
                </template>
                <template v-if="column.key === 'ec_file_name'">
                  <span>{{ cfg.file_name }}</span>
                </template>
                <template v-if="column.key === 'ec_action'">
                  <a-space>
                    <a-button size="small" type="link" :loading="cfg._previewing" @click="previewExcelFile(idx)">预览</a-button>
                    <a-button size="small" type="text" danger @click="removeExcelConfig(idx)">删除</a-button>
                  </a-space>
                </template>
              </template>
            </a-table>

            <!-- 预览结果（全局展示最后一个预览的文件） -->
            <template v-if="lastPreviewCfg && lastPreviewCfg._previewFields && lastPreviewCfg._previewFields.length > 0">
              <a-divider>字段预览 - {{ lastPreviewCfg.file_name }}</a-divider>
              <a-table
                :dataSource="lastPreviewCfg._previewFields"
                :columns="previewFieldColumns"
                :pagination="false"
                size="small"
                rowKey="name"
                :scroll="{ y: 200 }"
              >
                <template #bodyCell="{ column, record: pf }">
                  <template v-if="column.key === 'pf_type'">
                    <a-select v-model:value="pf.inferred_type" size="small" style="width: 90px">
                      <a-select-option value="string">字符串</a-select-option>
                      <a-select-option value="number">数字</a-select-option>
                      <a-select-option value="date">日期</a-select-option>
                      <a-select-option value="boolean">布尔</a-select-option>
                      <a-select-option value="enum">枚举</a-select-option>
                    </a-select>
                  </template>
                  <template v-if="column.key === 'pf_name_cn'">
                    <a-input v-model:value="pf.name_cn" size="small" style="width: 120px" />
                  </template>
                </template>
              </a-table>
            </template>
          </template>
        </template>

        <!-- ===== 数据源表：左右分栏 ===== -->
        <template v-if="formData.type === 'source'">
          <a-form-item label="关联数据源" required>
            <a-select
              v-model:value="formData.data_source"
              placeholder="选择已配置的数据源"
              :loading="dsLoading"
              show-search
              @change="onSourceDataSourceChange"
            >
              <a-select-option v-for="ds in dataSources" :key="ds.id" :value="ds.id">
                {{ ds.name }} ({{ ds.db_type }}://{{ ds.host }}/{{ ds.db_name }})
              </a-select-option>
            </a-select>
          </a-form-item>

          <template v-if="formData.data_source">
            <a-divider>选择数据库表</a-divider>
            <div style="display: flex; gap: 12px">
              <!-- 左栏：schema 列表 -->
              <div style="width: 200px; border: 1px solid #e8e8e8; border-radius: 4px; overflow-y: auto">
                <div style="padding: 8px 12px; border-bottom: 1px solid #e8e8e8; background: #fafafa">
                  <div style="font-weight: 600; font-size: 13px; margin-bottom: 6px">数据库模式</div>
                  <a-tooltip title="关闭后显示全部模式（含空模式）">
                    <span style="font-size: 12px; color: #888; display: inline-flex; align-items: center; gap: 6px; cursor: help">
                      <a-switch
                        :checked="onlyHasData"
                        size="small"
                        @change="(v: any) => onlyHasData = v"
                      />
                      <span>仅显示有数据的模式</span>
                    </span>
                  </a-tooltip>
                </div>
                <a-menu
                  v-model:selectedKeys="selectedSchemaKeys"
                  mode="inline"
                  style="border: none"
                  @click="onSchemaClick"
                >
                  <a-menu-item v-for="s in visibleSchemas" :key="s">{{ s }}</a-menu-item>
                </a-menu>
                <div v-if="schemasLoading" style="padding: 12px; text-align: center; color: #999">加载中...</div>
                <div v-if="!schemasLoading && visibleSchemas.length === 0" style="padding: 12px; text-align: center; color: #999">无 schema</div>
              </div>
              <!-- 右栏：表列表 -->
              <div style="flex: 1; border: 1px solid #e8e8e8; border-radius: 4px; display: flex; flex-direction: column">
                <div style="padding: 8px 12px; border-bottom: 1px solid #e8e8e8; background: #fafafa; display: flex; justify-content: space-between; align-items: center">
                  <span style="font-weight: 600; font-size: 13px">
                    表列表（{{ currentSchema }}）
                    <span v-if="selectedSourceTables.length > 0" style="color: #1890ff; margin-left: 8px">已选 {{ selectedSourceTables.length }} 个</span>
                  </span>
                  <a-input-search
                    v-model:value="sourceTableSearch"
                    placeholder="搜索表名/备注"
                    size="small"
                    style="width: 220px"
                  />
                </div>
                <div style="flex: 1; overflow-y: auto; padding: 0">
                  <div v-if="extTablesLoading" style="padding: 24px; text-align: center; color: #999">加载中...</div>
                  <div v-else-if="filteredSourceTables.length === 0" style="padding: 24px; text-align: center; color: #999">
                    {{ currentSchema ? '该模式下无表' : '请先选择左侧模式' }}
                  </div>
                  <a-table
                    v-else
                    :dataSource="filteredSourceTables"
                    :columns="extTableColumns"
                    :pagination="false"
                    rowKey="name"
                    size="small"
                    :scroll="{ y: 280 }"
                  >
                    <template #bodyCell="{ column, record }">
                      <template v-if="column.key === 'checkbox'">
                        <a-checkbox
                          :checked="selectedSourceTables.includes(record.name)"
                          @change="(e: any) => onExtTableCheck(record.name, e.target.checked)"
                        />
                      </template>
                      <template v-if="column.key === 'comment'">
                        <span style="color: #888">{{ record.comment || '-' }}</span>
                      </template>
                      <template v-if="column.key === 'row_count'">
                        <span style="color: #999">{{ record.row_count >= 0 ? record.row_count.toLocaleString() : '-' }}</span>
                      </template>
                    </template>
                  </a-table>
                </div>
              </div>
            </div>
          </template>
        </template>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, h, computed, onMounted, watch, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { message, Modal, Switch } from 'ant-design-vue'
import { UploadOutlined, KeyOutlined } from '@ant-design/icons-vue'
import { domainApi, tableApi, fieldApi, dataSourceApi } from '@/api/modeling'
import type { Table, DataSource, Field } from '@/types'
import DomainStageNav from './components/DomainStageNav.vue'
import { formatDateTime } from '@/utils/date'
import { extractApiError } from '@/utils/apiError'

const route = useRoute()
const router = useRouter()
const domainId = Number(route.params.id)
const domainName = ref('')
const tables = ref<Table[]>([])
const fieldsMap = ref<Record<number, Field[]>>({})
const dataSources = ref<DataSource[]>([])
const loading = ref(false)
const dsLoading = ref(false)
const modalVisible = ref(false)
const saving = ref(false)
const fieldToggles = ref<Record<string, boolean>>({})
const commentSaving = ref<Record<string, boolean>>({})
const tableToggles = ref<Record<number, boolean>>({})
const extTables = ref<{name: string; comment: string; row_count: number}[]>([])
const extTablesLoading = ref(false)
const formData = ref<any>({
  type: 'local',
  data_source: null,
})

// ===== 字段管理弹窗 =====
const fieldModalVisible = ref(false)
const fieldModalTable = ref<Table | null>(null)
const fieldModalFields = ref<any[]>([])
const fieldModalTab = ref('fields')
const previewLoading = ref(false)
const previewData = ref<{ rawColumns: string[]; rows: any[]; totalWidth: number }>({ rawColumns: [], rows: [], totalWidth: 0 })
const previewShowCn = ref(true)
const previewDisplayColumns = computed(() => {
  const colWidth = previewShowCn.value ? 200 : 140
  return previewData.value.rawColumns.map((rawName) => {
    const field = fieldModalFields.value.find((f: any) => f.code === rawName)
    let title = rawName
    if (previewShowCn.value && field?.comment) {
      title = `${field.comment}(${rawName})`
    }
    return {
      title,
      dataIndex: rawName,
      key: rawName,
      width: colWidth,
      ellipsis: true,
    }
  })
})
const lastPreviewCfg = computed(() => {
  return excelConfigs.value.find((c) => c._previewFields && c._previewFields.length > 0) || null
})

// ===== Excel 导入 =====
const excelFileList = ref<any[]>([])
const excelFiles = ref<File[]>([])
const excelConfigs = ref<any[]>([])

// ===== 数据源表分栏 =====
const schemas = ref<string[]>([])
const schemasLoading = ref(false)
const selectedSchemaKeys = ref<string[]>([])
const currentSchema = ref('')
const selectedSourceTables = ref<string[]>([])
const sourceTableSearch = ref('')
const onlyHasData = ref(true)
// 记录每个 schema 是否有表
const schemaHasTables = ref<Record<string, boolean>>({})

const filteredSourceTables = computed(() => {
  const kw = sourceTableSearch.value.toLowerCase().trim()
  let list = extTables.value
  if (onlyHasData.value) {
    list = list.filter((t) => t.row_count > 0)
  }
  if (kw) {
    list = list.filter((t) => t.name.toLowerCase().includes(kw) || t.comment.toLowerCase().includes(kw))
  }
  return list
})

// 过滤后的 schema 列表（只显示有表的 schema）
const visibleSchemas = computed(() => {
  if (!onlyHasData.value) return schemas.value
  return schemas.value.filter((s) => schemaHasTables.value[s] !== false)
})

const typeLabels: Record<string, string> = {
  string: '字符串', number: '数字', date: '日期', boolean: '布尔', enum: '枚举',
}

const columns = [
  { title: '表名称（英文）', dataIndex: 'code', key: 'code', width: 180, ellipsis: true },
  { title: '表名称（中文）', dataIndex: 'name', key: 'name', width: 180, ellipsis: true },
  { title: '类型', key: 'type', width: 100 },
  { title: '数据源', key: 'data_source', width: 140, ellipsis: true },
  { title: '字段数', dataIndex: 'field_count', key: 'field_count', width: 90, align: 'center' as const },
  { title: '主表', key: 'is_primary', width: 90, align: 'center' as const },
  { title: '主键', key: 'primary_keys', width: 200, ellipsis: true },
  { title: '状态', key: 'status', width: 90 },
  { title: '创建时间', dataIndex: 'created_at', key: 'created_at', width: 160,
    customRender: ({ text }: any) => formatDateTime(text) },
  { title: '操作', key: 'action', width: 200 },
]

// 字段管理弹窗列定义（注释列不设固定宽，自动填充剩余空间）
const fieldColumns = [
  { title: '编码', dataIndex: 'code', key: 'code', width: 180, ellipsis: true },
  { title: '字段名称（英文）', dataIndex: 'name', key: 'name', width: 200, ellipsis: true },
  { title: '字段名称（中文）', dataIndex: 'comment', key: 'comment' },
  { title: '类型', key: 'field_type', width: 90 },
  { title: '主键', key: 'is_primary_key', width: 60, align: 'center' as const },
  { title: '模型字段', key: 'model_field', width: 120, align: 'center' as const },
]

// 字段表格动态滚动高度：近全屏弹窗下，减去标题栏+Tab+边距 ≈ 300px
const fieldTableScrollY = computed(() => `calc(100vh - 300px)`)

// 主键字段列表（按 sort_order 排序，用于主键标识区展示）
const pkFieldsList = computed(() => {
  return fieldModalFields.value
    .filter((f: any) => f.is_primary_key)
    .sort((a: any, b: any) => (a.sort_order || 0) - (b.sort_order || 0))
})

// ===== 主表/主键配置引导 =====
const hasPrimaryTable = computed(() => tables.value.some((t) => t.is_primary))
const tablesWithoutPk = computed(() =>
  tables.value.filter((t) => !t.primary_keys || t.primary_keys.length === 0)
)
const setupGuideMessage = computed(() => {
  if (tables.value.length === 0) return ''
  const parts: string[] = []
  if (!hasPrimaryTable.value) {
    parts.push('⚠️ <strong>尚未设置主表</strong>：请在「主表」列点击「设为主表」，主表是档案数据合并的基准')
  }
  if (tablesWithoutPk.value.length > 0) {
    const names = tablesWithoutPk.value.slice(0, 3).map((t) => t.name).join('、')
    const suffix = tablesWithoutPk.value.length > 3 ? `等 ${tablesWithoutPk.value.length} 个表` : `${tablesWithoutPk.value.length} 个表`
    parts.push(`🔑 <strong>${suffix}未设置主键</strong>（${names}）：点击主键列的「设置主键」按钮，主键是档案记录匹配的唯一标识`)
  }
  return parts.length > 0 ? parts.join('<br/>') : ''
})

// 字段注释点击编辑
const editingCommentId = ref<number | null>(null)

// Excel 配置表格列定义（一行一个文件）
const excelConfigColumns = [
  { title: '编码', key: 'ec_code', width: 150 },
  { title: '英文名称', key: 'ec_name_en', width: 150 },
  { title: '中文名称', key: 'ec_name_cn', width: 150 },
  { title: '文件名', key: 'ec_file_name', width: 180, ellipsis: true },
  { title: '操作', key: 'ec_action', width: 120 },
]

// Excel 预览字段列定义
const previewFieldColumns = [
  { title: '列名', dataIndex: 'name', key: 'name', width: 160 },
  { title: '推断类型', key: 'pf_type', width: 110 },
  { title: '中文名', key: 'pf_name_cn', width: 160 },
]

// 外部表列表列定义（新建表弹窗右栏）
const extTableColumns = [
  { title: '', key: 'checkbox', width: 40 },
  { title: '表名', dataIndex: 'name', key: 'name', width: 200, ellipsis: true },
  { title: '表备注', dataIndex: 'comment', key: 'comment', ellipsis: true },
  { title: '行数', dataIndex: 'row_count', key: 'row_count', width: 80, align: 'right' as const },
]

function getRealType(record: any): 'local' | 'source' {
  return record.data_source ? 'source' : 'local'
}

function expandedRowRender(record: Table) {
  const fields = fieldsMap.value[record.id] || []
  if (fields.length === 0) {
    return h('div', { style: 'padding: 12px 40px; color: #999' }, '暂无字段，请前往「字段管理」添加')
  }
  const children: any[] = []
  fields.forEach((f: any) => {
    children.push(
      h('tr', { key: f.id, style: 'border-bottom: 1px solid #f0f0f0' }, [
        h('td', { style: 'padding: 8px 12px; font-size: 13px' }, f.name),
        h('td', { style: 'padding: 8px 12px; font-size: 13px; color: #888' }, f.code),
        h('td', { style: 'padding: 8px 12px; font-size: 13px' }, typeLabels[f.field_type] || f.field_type),
        h('td', { style: 'padding: 8px 12px; font-size: 13px; color: #666' }, f.comment || '-'),
        h('td', { style: 'padding: 8px 12px' }, h(Switch, {
          checked: f.status === 'active',
          loading: fieldToggles.value[`${f.id}`],
          size: 'small',
          checkedChildren: '启用',
          unCheckedChildren: '停用',
          onChange: (checked: any) => toggleField(f, checked),
        })),
      ])
    )
  })
  const th = (t: string) => h('th', { style: 'padding: 8px 12px; text-align: left; font-weight: 600; color: #666; font-size: 12px' }, t)
  return h('div', { style: 'padding: 8px 32px' }, [
    h('table', { style: 'width: 100%; border-collapse: collapse' }, [
      h('thead', [
        h('tr', { style: 'border-bottom: 1px solid #e8e8e8' }, [
          th('字段名称'), th('编码'), th('类型'), th('注释'), th('启用'),
        ]),
      ]),
      h('tbody', children),
    ]),
  ])
}

// ===== 数据加载 =====
async function loadFieldsForTable(tableId: number) {
  try {
    const res = await fieldApi.list({ table: tableId })
    fieldsMap.value[tableId] = res.data.results
  } catch {
    fieldsMap.value[tableId] = []
  }
}

async function loadData() {
  loading.value = true
  try {
    const domainRes = await domainApi.get(domainId)
    domainName.value = domainRes.data.name
    const res = await tableApi.list({ domain: domainId })
    tables.value = res.data.results
    for (const t of tables.value) {
      loadFieldsForTable(t.id)
    }
  } finally {
    loading.value = false
  }
}

async function loadDataSources() {
  dsLoading.value = true
  try {
    const res = await dataSourceApi.list()
    dataSources.value = res.data.results
  } finally {
    dsLoading.value = false
  }
}

// ===== 字段管理弹窗 =====
async function openFieldModal(record: Table) {
  fieldModalTable.value = record
  fieldModalTab.value = 'fields'
  previewData.value = { rawColumns: [], rows: [], totalWidth: 0 }
  // 加载字段
  try {
    const res = await fieldApi.list({ table: record.id })
    fieldModalFields.value = (res.data.results || []).map((f: any) => ({
      ...f,
      date_format: f.validation_rule?.date_format || '',
    }))
  } catch {
    fieldModalFields.value = []
  }
  fieldModalVisible.value = true
}

// 切换到"数据预览"Tab 时才加载数据（避免打开弹窗就发请求）
watch(fieldModalTab, (tab) => {
  if (tab === 'preview' && previewData.value.rawColumns.length === 0 && fieldModalTable.value) {
    loadDataPreview(fieldModalTable.value)
  }
})

async function loadDataPreview(record: Table) {
  previewLoading.value = true
  try {
    const res = await tableApi.previewData(record.id, 100)
    const { columns: cols, rows } = res.data
    previewData.value = {
      rawColumns: cols,
      rows: rows.map((row, idx) => {
        const obj: Record<string, any> = { _rowIndex: idx }
        cols.forEach((c, ci) => { obj[c] = row[ci] })
        return obj
      }),
      totalWidth: cols.length * (previewShowCn.value ? 200 : 140),
    }
  } catch (e: any) {
    previewData.value = { rawColumns: [], rows: [], totalWidth: 0 }
    message.error(extractApiError(e) || '数据预览失败')
  } finally {
    previewLoading.value = false
  }
}

async function saveFieldComment(field: any) {
  const key = `${field.id}`
  if (commentSaving.value[key]) return
  commentSaving.value[key] = true
  editingCommentId.value = null
  try {
    await fieldApi.batchUpdateAttributes([{ id: field.id, comment: field.comment }])
  } catch (e: any) {
    message.error(extractApiError(e) || '保存失败')
  } finally {
    commentSaving.value[key] = false
  }
}

async function togglePrimaryKey(field: any) {
  const newVal = !field.is_primary_key

  // 设置主键时，如果已存在其他主键字段，弹出联合主键提醒
  if (newVal) {
    const existingPks = fieldModalFields.value.filter((f: any) => f.is_primary_key && f.id !== field.id)
    if (existingPks.length > 0) {
      const pkNames = existingPks.map((f: any) => f.code).join(', ')
      Modal.confirm({
        title: '联合主键确认',
        content: `当前已有主键字段：${pkNames}。\n继续设置将创建联合主键（${pkNames} + ${field.code}），确认继续？`,
        okText: '确认',
        cancelText: '取消',
        onOk: () => doTogglePrimaryKey(field, newVal),
      })
      return
    }
  }
  await doTogglePrimaryKey(field, newVal)
}

async function doTogglePrimaryKey(field: any, newVal: boolean) {
  field.is_primary_key = newVal
  try {
    await fieldApi.batchUpdateAttributes([{ id: field.id, is_primary_key: newVal }])
    message.success(newVal ? '已设为主键' : '已取消主键')
    syncPrimaryKeysToTableList()
  } catch (e: any) {
    field.is_primary_key = !newVal // 回滚
    message.error(extractApiError(e) || '设置失败')
  }
}

// 从弹窗字段重算主键列表并回写到外层表列表，避免需手动刷新才更新主键列
function syncPrimaryKeysToTableList() {
  if (!fieldModalTable.value) return
  const pks = fieldModalFields.value
    .filter((f: any) => f.is_primary_key)
    .sort((a: any, b: any) => (a.sort_order ?? 0) - (b.sort_order ?? 0) || a.id - b.id)
    .map((f: any) => ({ id: f.id, code: f.code, name: f.name, comment: f.comment }))
  const tid = fieldModalTable.value.id
  const row = tables.value.find((t: any) => t.id === tid)
  if (row) (row as any).primary_keys = pks
  ;(fieldModalTable.value as any).primary_keys = pks
}

async function toggleReleaseToConcept(field: any, newVal: boolean) {
  field.release_to_concept = newVal
  try {
    await fieldApi.batchUpdateAttributes([{ id: field.id, release_to_concept: newVal }])
    message.success(newVal ? '已释放到概念层' : '已取消释放（不进档案）')
  } catch (e: any) {
    field.release_to_concept = !newVal // 回滚
    message.error(extractApiError(e) || '设置失败')
  }
}

async function toggleModelField(field: any, enable: any) {
  const key = `${field.id}`
  fieldToggles.value[key] = true
  const releaseToConcept = !!enable
  const status = enable ? 'active' : 'deprecated'
  const oldRelease = field.release_to_concept
  const oldStatus = field.status
  // 乐观更新
  field.release_to_concept = releaseToConcept
  field.status = status
  try {
    await fieldApi.batchUpdateAttributes([
      { id: field.id, release_to_concept: releaseToConcept, status },
    ])
    message.success(enable ? '字段已启用并释放' : '字段已停用并取消释放')
  } catch (e: any) {
    // 回滚
    field.release_to_concept = oldRelease
    field.status = oldStatus
    message.error(extractApiError(e) || '操作失败')
  } finally {
    fieldToggles.value[key] = false
  }
}

// ===== 配置表跳转 =====
function goConfigTables() {
  router.push(`/modeling/domains/${domainId}/config-tables`)
}

// ===== 新建表 =====
function openCreate() {
  formData.value = { type: 'local', data_source: null }
  excelFileList.value = []
  excelFiles.value = []
  excelConfigs.value = []
  extTables.value = []
  selectedSourceTables.value = []
  schemas.value = []
  selectedSchemaKeys.value = []
  currentSchema.value = ''
  sourceTableSearch.value = ''
  onlyHasData.value = true
  schemaHasTables.value = {}
  modalVisible.value = true
  loadDataSources()
}

// --- Excel 上传 ---
function beforeExcelUpload(file: File) {
  excelFiles.value.push(file)
  excelFileList.value.push({ name: file.name, uid: file.name, status: 'done' })
  excelConfigs.value.push({
    file_name: file.name,
    code: '',
    name_en: '',
    name_cn: '',
    _previewing: false,
    _previewFields: null as any,
  })
  // 自动触发预览（R-005）
  const idx = excelConfigs.value.length - 1
  previewExcelFile(idx)
  return false // 阻止自动上传
}

function onExcelFileRemove(file: any) {
  const idx = excelFileList.value.findIndex((f) => f.uid === file.uid)
  if (idx >= 0) {
    excelFileList.value.splice(idx, 1)
    excelFiles.value.splice(idx, 1)
    excelConfigs.value.splice(idx, 1)
  }
}

function removeExcelConfig(idx: number) {
  excelFileList.value.splice(idx, 1)
  excelFiles.value.splice(idx, 1)
  excelConfigs.value.splice(idx, 1)
}

async function previewExcelFile(idx: number) {
  const cfg = excelConfigs.value[idx]
  const file = excelFiles.value[idx]
  if (!file) return
  cfg._previewing = true
  try {
    const res = await tableApi.previewExcel(file)
    const { columns: cols, inferred_fields } = res.data
    cfg._previewFields = (inferred_fields || []).map((f: any) => ({
      name: f.name || f.code,
      inferred_type: f.field_type || 'string',
      name_cn: f.name_cn || f.comment || '',
    }))
    // 如果用户还没填编码/名称，自动填充
    if (!cfg.code && cols?.length) {
      const baseName = file.name.replace(/\.\w+$/, '').toUpperCase().replace(/[^A-Z0-9_]/g, '_')
      cfg.code = baseName
    }
    if (!cfg.name_en) {
      cfg.name_en = file.name.replace(/\.\w+$/, '')
    }
    if (!cfg.name_cn) {
      cfg.name_cn = file.name.replace(/\.\w+$/, '')
    }
  } catch (e: any) {
    message.error(extractApiError(e) || '预览失败')
  } finally {
    cfg._previewing = false
  }
}

// --- 数据源表 schema 浏览 ---
async function onSourceDataSourceChange() {
  schemas.value = []
  selectedSchemaKeys.value = []
  currentSchema.value = ''
  extTables.value = []
  selectedSourceTables.value = []
  schemaHasTables.value = {}
  if (!formData.value.data_source) return
  // 加载 schemas（含表数量）
  schemasLoading.value = true
  try {
    const res = await dataSourceApi.listSchemas(formData.value.data_source, true)
    schemas.value = res.data.schemas || []
    // 从后端返回的 schema_table_counts 构建 hasTables 映射
    const counts = res.data.schema_table_counts || {}
    const hasTablesMap: Record<string, boolean> = {}
    for (const s of schemas.value) {
      hasTablesMap[s] = (counts[s] || 0) > 0
    }
    schemaHasTables.value = hasTablesMap
    // 默认选中第一个可见的 schema
    const firstVisible = visibleSchemas.value[0] || schemas.value[0]
    if (firstVisible) {
      selectedSchemaKeys.value = [firstVisible]
      currentSchema.value = firstVisible
      await loadExternalTables(firstVisible)
    }
  } catch (e: any) {
    message.error(extractApiError(e) || '加载 schema 列表失败')
  } finally {
    schemasLoading.value = false
  }
}

async function onSchemaClick({ key }: any) {
  currentSchema.value = key
  selectedSourceTables.value = []
  await loadExternalTables(key)
}

function onExtTableCheck(tableName: string, checked: boolean) {
  if (checked) {
    if (!selectedSourceTables.value.includes(tableName)) {
      selectedSourceTables.value.push(tableName)
    }
  } else {
    selectedSourceTables.value = selectedSourceTables.value.filter((n) => n !== tableName)
  }
}

// 监听“只显示有数据”开关变化 — 前端过滤，无需重新请求
watch(onlyHasData, () => {
  // 如果当前选中的 schema 在过滤后无表，自动切换到第一个有表的 schema
  const visible = visibleSchemas.value
  if (visible.length > 0 && !visible.includes(currentSchema.value)) {
    const first = visible[0]
    selectedSchemaKeys.value = [first]
    currentSchema.value = first
    loadExternalTables(first)
  }
})

async function loadExternalTables(schema: string) {
  extTablesLoading.value = true
  try {
    const res = await dataSourceApi.listExternalTables(formData.value.data_source, schema)
    const allTables = res.data.tables || []
    extTables.value = allTables
    // 记录该 schema 是否有表
    schemaHasTables.value[schema] = allTables.length > 0
  } catch (e: any) {
    message.error(extractApiError(e) || '加载表列表失败')
  } finally {
    extTablesLoading.value = false
  }
}

// --- 提交 ---
async function handleSubmit() {
  if (formData.value.type === 'local') {
    return handleSubmitLocal()
  } else {
    return handleSubmitSource()
  }
}

async function handleSubmitLocal() {
  if (excelConfigs.value.length === 0) {
    message.warning('请至少上传一个 Excel 文件')
    return
  }
  // 校验配置
  for (const cfg of excelConfigs.value) {
    if (!cfg.code) {
      message.warning(`文件 ${cfg.file_name} 必须填写编码`)
      return
    }
  }
  saving.value = true
  try {
    const configs = excelConfigs.value.map((c) => ({
      file_name: c.file_name,
      code: c.code,
      name_en: c.name_en || c.code,
      name_cn: c.name_cn || c.code,
    }))
    const res = await tableApi.importExcel(domainId, excelFiles.value, configs)
    const { created, errors } = res.data
    if (errors && errors.length > 0) {
      message.warning(`创建完成，但部分失败：${errors.length} 个错误`)
      Modal.warning({
        title: '部分表创建失败',
        content: h('div', { style: 'max-height: 200px; overflow-y: auto' },
          errors.map((e: any, i: number) => h('div', { key: i }, typeof e === 'string' ? e : JSON.stringify(e)))
        ),
      })
    } else {
      message.success(`成功创建 ${created?.length || 0} 个表`)
    }
    modalVisible.value = false
    await loadData()
  } catch (e: any) {
    message.error(extractApiError(e) || '导入失败')
  } finally {
    saving.value = false
  }
}

async function handleSubmitSource() {
  if (!formData.value.data_source) {
    message.warning('请选择数据源')
    return
  }
  if (selectedSourceTables.value.length === 0) {
    message.warning('请至少选择一个表')
    return
  }
  saving.value = true
  try {
    let successCount = 0
    let failCount = 0
    const errors: string[] = []
    for (const tableName of selectedSourceTables.value) {
      try {
        // 从 extTables 中查找表备注作为中文名称
        const extTable = extTables.value.find((t) => t.name === tableName)
        const tableComment = extTable?.comment || ''
        await tableApi.create({
          domain: domainId,
          name: tableComment || tableName,
          code: tableName,
          data_source: formData.value.data_source,
          external_table_name: tableName,
          schema: currentSchema.value,
        } as any)
        successCount++
      } catch (e: any) {
        failCount++
        errors.push(`${tableName}: ${extractApiError(e) || '失败'}`)
      }
    }
    if (failCount === 0) {
      message.success(`成功导入 ${successCount} 个表`)
    } else {
      message.warning(`成功 ${successCount} 个，失败 ${failCount} 个`)
      if (errors.length > 0) {
        Modal.warning({
          title: '部分表导入失败',
          content: h('div', { style: 'max-height: 200px; overflow-y: auto' }, errors.map((e) => h('div', {}, e))),
        })
      }
    }
    modalVisible.value = false
    await loadData()
  } catch (e: any) {
    message.error(extractApiError(e) || '操作失败')
  } finally {
    saving.value = false
  }
}

function confirmDeleteTable(record: Table) {
  Modal.confirm({
    title: '确认删除此表？',
    content: `表「${record.name}」及其关联的字段映射、标准字段将全部删除，关联档案 schema 也会受影响，此操作不可恢复。`,
    okType: 'danger',
    okText: '删除',
    cancelText: '取消',
    onOk: () => doDelete(record.id),
  })
}

async function doDelete(id: number) {
  try {
    await tableApi.delete(id)
    message.success('删除成功')
    await loadData()
  } catch (e: any) {
    message.error(extractApiError(e) || '删除失败')
  }
}

async function setPrimary(record: Table) {
  Modal.confirm({
    title: '设为主表',
    content: `确认将「${record.name}」设为该域的主表吗？主表将作为档案数据合并的基准。`,
    okText: '确认',
    cancelText: '取消',
    onOk: async () => {
      try {
        await tableApi.setPrimary(record.id)
        message.success('已设为主表')
        await loadData()
      } catch (e: any) {
        message.error(extractApiError(e) || '设置失败')
      }
    },
  })
}

async function toggleTableStatus(record: Table, checked: any) {
  const target = checked ? 'active' : 'deprecated'
  tableToggles.value[record.id] = true
  try {
    await tableApi.toggleStatus(record.id, target)
    record.status = target
    message.success(checked ? '表已启用' : '表已停用')
  } catch (e: any) {
    const data = e.response?.data
    if (data?.mappings?.length) {
      const list = data.mappings.map((m: any) => `${m.source} → ${m.target}`).join('<br/>')
      Modal.warning({
        title: '无法停用该表',
        content: h('div', {}, [
          h('p', {}, data.error || '该表存在字段映射关系'),
          h('div', { style: 'margin-top: 8px; color: #666', innerHTML: list }),
        ]),
      })
    } else {
      message.error(data?.error || '操作失败')
    }
  } finally {
    tableToggles.value[record.id] = false
  }
}

async function toggleField(field: any, enable: any) {
  const key = `${field.id}`
  fieldToggles.value[key] = true
  try {
    await fieldApi.batchUpdateAttributes([
      { id: field.id, status: enable ? 'active' : 'deprecated' },
    ])
    field.status = enable ? 'active' : 'deprecated'
    message.success(enable ? '字段已启用' : '字段已停用')
  } catch (e: any) {
    message.error(extractApiError(e) || '操作失败')
  } finally {
    fieldToggles.value[key] = false
  }
}



onMounted(async () => {
  await loadData()
  // 如果从关系管理跳转过来，自动打开指定表的字段管理弹窗
  const openTableId = route.query.openFieldModal
  if (openTableId) {
    const table = tables.value.find((t) => t.id === Number(openTableId))
    if (table) {
      await nextTick()
      openFieldModal(table)
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
}
.page-header h2 {
  margin: 0;
  font-size: 18px;
  display: inline;
}

/* 主键行橙色高亮 */
:deep(.pk-row) {
  background: #fffbe6 !important;
}
:deep(.pk-row:hover) {
  background: #fff7cc !important;
}
:deep(.pk-row td) {
  border-bottom-color: #ffe58f !important;
}
</style>
