<template>
  <a-modal
    :open="open"
    :title="isEdit && field ? `编辑计算字段公式 - ${field.code} (${field.name})` : '新建计算字段'"
    width="1680px"
    :destroy-on-close="true"
    @cancel="$emit('update:open', false)"
    @ok="handleSave"
    :confirm-loading="saving"
  >
    <template #footer>
      <div style="display:flex;justify-content:space-between">
        <a-button @click="$emit('update:open', false)">取消</a-button>
        <a-space>
          <a-button type="primary" ghost :loading="saving" @click="handleSaveAndTrial">保存并试算</a-button>
          <a-button type="primary" :loading="saving" @click="handleSave">保存</a-button>
        </a-space>
      </div>
    </template>
    <!-- AI 自然语言生成表达式（置顶：描述需求 → AI 连带生成编码/名称/输出类型/表达式） -->
    <div class="ai-generate-block">
      <div class="formula-label">
        <span>AI 生成表达式</span>
        <span class="ai-generate-hint">用自然语言描述计算逻辑，AI 自动推导编码、名称、输出类型和公式；已有表达式时按描述在其基础上修改</span>
      </div>
      <div class="ai-generate-row">
        <a-textarea
          v-model:value="aiDescription"
          placeholder="如：门店简称加分部编号用横线连接；或：如果等级为A则基本工资×1.5否则×1.0"
          :auto-size="{ minRows: 2, maxRows: 4 }"
          allow-clear
          :disabled="aiGenerating"
          @pressEnter="handleAiGenerate"
        />
        <a-button type="primary" :loading="aiGenerating" @click="handleAiGenerate" class="ai-generate-btn">AI 生成</a-button>
      </div>
      <!-- AI 提示（a-alert 组件包装，浅黄色） -->
      <a-alert
        v-if="aiExplanation || aiRisk"
        type="warning"
        show-icon
        class="ai-tips-alert"
      >
        <template #message>
          <div v-if="aiExplanation" class="ai-alert-line">
            <span class="ai-alert-label">💡 说明：</span>
            <span class="ai-alert-text">{{ aiExplanation }}</span>
          </div>
          <div v-if="aiExplanation && aiRisk" class="ai-alert-divider"></div>
          <div v-if="aiRisk" class="ai-alert-line">
            <span class="ai-alert-label">⚠️ 风险：</span>
            <span class="ai-alert-text">{{ aiRisk }}</span>
          </div>
        </template>
      </a-alert>
      <a-collapse v-if="aiReasoning" v-model:activeKey="aiReasoningActiveKey" class="ai-reasoning-collapse" :bordered="false">
        <a-collapse-panel key="1" header="思考过程">
          <div class="ai-reasoning-content">{{ aiReasoning }}</div>
        </a-collapse-panel>
      </a-collapse>
    </div>

    <!-- 基础信息行（位于 AI 区块之下，AI 生成时自动回填空白项） -->
    <div class="basic-form">
      <div class="basic-field">
        <span class="basic-field-label"><span class="basic-field-req">*</span>字段编码：</span>
        <a-input v-model:value="form.code" placeholder="如: total_score" :disabled="isEdit" class="basic-field-input" />
      </div>
      <div class="basic-field">
        <span class="basic-field-label"><span class="basic-field-req">*</span>字段名称：</span>
        <a-input v-model:value="form.name" placeholder="如: 总分" class="basic-field-input" />
      </div>
      <div class="basic-field">
        <span class="basic-field-label">输出类型：</span>
        <a-select v-model:value="form.output_type" class="basic-field-select">
          <a-select-option value="text">文本</a-select-option>
          <a-select-option value="number">数字</a-select-option>
          <a-select-option value="date">日期</a-select-option>
          <a-select-option value="boolean">布尔</a-select-option>
        </a-select>
      </div>
    </div>

    <!-- 解析出的依赖列表 + 未引用字段（蓝=已引用可删减，橙=未在表达式中使用），置于双列布局之上避免挤偏左右对齐 -->
    <div v-if="validationResult?.references?.length || unusedReferences.length" class="dep-list">
      <span class="dep-label">依赖字段：</span>
      <a-tag
        v-for="(ref, i) in validationResult?.references || []"
        :key="i"
        color="blue"
        closable
        @close="handleRemoveReference(i)"
      >
        {{ ref.table_name }}.{{ ref.field_code }}
      </a-tag>
      <a-tag
        v-for="ref in unusedReferences"
        :key="ref.ref"
        color="orange"
        closable
        title="未在表达式中使用"
        @close="handleRemoveReferenceByRef(ref.ref)"
      >{{ ref.table_name }}.{{ ref.code }}</a-tag>
    </div>

    <!-- 公式编辑区（计算表达式 + 侧栏） -->
    <div class="formula-editor-layout">
      <div class="formula-main">
        <div class="formula-label">
          <span>计算表达式</span>
          <a-space :size="0">
            <a-button size="small" type="link" @click="handleFormatExpression">格式化</a-button>
            <a-button size="small" type="link" @click="handleValidate" :loading="validating">验证公式</a-button>
          </a-space>
        </div>
        <a-textarea
          ref="textareaRef"
          v-model:value="form.expression"
          :rows="6"
          placeholder="输入 Excel 风格公式，如: IF({员工表.等级}=&quot;A&quot;, {员工表.基本工资}*1.5, {员工表.基本工资})"
          class="formula-textarea"
          @change="onExpressionChange"
        />
        <!-- 验证结果 -->
        <div v-if="validationResult" class="validation-result" :class="validationResult.valid ? 'validation-ok' : 'validation-error'">
          <template v-if="validationResult.valid">
            <span>✔ 公式语法正确</span>
            <span v-if="validationResult.references.length" style="margin-left:12px;color:#595959">
              引用 {{ validationResult.references.length }} 个字段
            </span>
          </template>
          <template v-else>
            <div v-for="(err, i) in validationResult.errors" :key="i" class="validation-error-item">⚠️ {{ err }}</div>
          </template>
        </div>
      </div>

      <!-- 侧边面板：函数库 + 字段引用 -->
      <div class="formula-sidebar">
        <a-tabs v-model:activeKey="sideTab" size="small">
          <a-tab-pane key="fields" tab="字段引用">
            <template v-if="sidebarLoading">
              <div class="sidebar-loading"><a-spin size="small" /><span>加载字段...</span></div>
            </template>
            <template v-else-if="sidebarError">
              <div class="sidebar-error">
                <span>{{ sidebarError }}</span>
                <a-button type="link" size="small" @click="loadSidebarData">重试</a-button>
              </div>
            </template>
            <template v-else>
              <a-input v-model:value="fieldSearch" placeholder="搜索字段" size="small" allow-clear style="margin-bottom:8px" />
              <div class="cascade">
                <!-- 一级：表 -->
                <div class="cascade-l1">
                  <div
                    v-for="group in groupedReferences"
                    :key="group.tableName"
                    class="cascade-l1-item"
                    :class="{ active: selectedRefTable === group.tableName }"
                    :title="group.tableName"
                    @click="selectedRefTable = group.tableName"
                  >
                    <span class="cascade-l1-name">{{ group.tableName }}</span>
                    <span class="cascade-l1-count">{{ group.fields.length }}</span>
                  </div>
                  <div v-if="!groupedReferences.length" class="sidebar-empty">该域暂无可引用字段</div>
                </div>
                <!-- 二级：字段（单行展示） -->
                <div class="cascade-l2">
                  <div
                    v-for="ref in currentRefFields"
                    :key="ref.ref"
                    class="ref-item"
                    :title="`点击插入引用: {${ref.ref}}`"
                    @click="insertReference(ref)"
                  >
                    <span class="ref-name">{{ ref.display_name || ref.name }}</span>
                    <span class="ref-code">{{ ref.code }}</span>
                  </div>
                  <div v-if="groupedReferences.length && !currentRefFields.length" class="sidebar-empty">请选择左侧表</div>
                </div>
              </div>
            </template>
          </a-tab-pane>
          <a-tab-pane key="functions" tab="函数库">
            <template v-if="sidebarLoading">
              <div class="sidebar-loading"><a-spin size="small" /><span>加载函数库...</span></div>
            </template>
            <template v-else-if="sidebarError">
              <div class="sidebar-error">
                <span>{{ sidebarError }}</span>
                <a-button type="link" size="small" @click="loadSidebarData">重试</a-button>
              </div>
            </template>
            <template v-else>
              <a-input v-model:value="funcSearch" placeholder="搜索函数" size="small" allow-clear style="margin-bottom:8px" />
              <div class="cascade">
                <!-- 一级：函数分类 -->
                <div class="cascade-l1">
                  <div
                    v-for="group in groupedFunctions"
                    :key="group.category"
                    class="cascade-l1-item"
                    :class="{ active: selectedFuncCategory === group.category }"
                    :title="group.category"
                    @click="selectedFuncCategory = group.category"
                  >
                    <span class="cascade-l1-name">{{ group.category }}</span>
                    <span class="cascade-l1-count">{{ group.fns.length }}</span>
                  </div>
                  <div v-if="!groupedFunctions.length" class="sidebar-empty">无匹配函数</div>
                </div>
                <!-- 二级：函数（单行展示） -->
                <div class="cascade-l2">
                  <div
                    v-for="fn in currentCategoryFns"
                    :key="fn.name"
                    class="func-item"
                    @click="insertFunction(fn)"
                    :title="`点击插入: ${fn.description}`"
                  >
                    <span class="func-name">{{ fn.name }}</span>
                    <span class="func-desc">{{ fn.description }}</span>
                  </div>
                  <div v-if="groupedFunctions.length && !currentCategoryFns.length" class="sidebar-empty">请选择左侧分类</div>
                </div>
              </div>
            </template>
          </a-tab-pane>
          <a-tab-pane key="tech_plugins" tab="技术函数">
            <div class="tech-plugins-toolbar">
              <a-button size="small" @click="handleDownloadTemplate">下载模板</a-button>
              <a-button size="small" :loading="pluginsLoading" @click="loadPlugins">刷新</a-button>
            </div>
            <a-upload
              name="file"
              :multiple="false"
              :accept="'.py'"
              :show-upload-list="false"
              :custom-request="handlePluginUpload"
              :disabled="pluginUploading"
            >
              <a-button size="small" type="primary" block :loading="pluginUploading">
                {{ pluginUploading ? '上传中...' : '上传 .py 插件' }}
              </a-button>
            </a-upload>
            <div class="tech-plugins-hint">
              上传后自动 AST 安全校验并加载，无需重启服务。同名插件重载覆盖。
            </div>
            <div v-if="pluginsLoading" class="sidebar-loading"><a-spin size="small" /><span>加载插件...</span></div>
            <div v-else-if="!plugins.length" class="sidebar-empty">暂无已加载插件</div>
            <div v-else class="plugin-list">
              <div v-for="p in plugins" :key="p.filename" class="plugin-item">
                <div class="plugin-header">
                  <span class="plugin-filename">{{ p.filename }}</span>
                  <a-tag color="green" size="small">{{ p.function_count }}</a-tag>
                </div>
                <div class="plugin-fns">
                  <a-tag v-for="fn in p.functions" :key="fn.name" size="small" :title="fn.description">
                    {{ fn.name }}
                  </a-tag>
                </div>
                <div class="plugin-actions">
                  <a-button size="small" :loading="pluginReloadingMap[p.filename]" @click="handlePluginReload(p.filename)">重载</a-button>
                  <a-popconfirm
                    :title="`确认卸载 ${p.filename}？`"
                    ok-text="确认"
                    cancel-text="取消"
                    @confirm="handlePluginUnload(p.filename)"
                  >
                    <a-button size="small" danger :loading="pluginUnloadingMap[p.filename]">卸载</a-button>
                  </a-popconfirm>
                </div>
              </div>
            </div>
          </a-tab-pane>
        </a-tabs>
      </div>
    </div>

    <!-- 数据预览面板（窗口底部全宽，常驻展示） -->
    <div class="preview-panel">
      <div class="preview-header">
        <span>
          数据预览
          <span v-if="previewResult && previewResult.valid" class="preview-meta">
            输入参数去重组合共 {{ previewResult.total_possible }} 种{{ previewResult.truncated ? `，仅展示前 ${previewResult.rows.length} 条` : '' }}
          </span>
        </span>
        <a-button
          v-if="previewResult && previewResult.valid && previewResult.truncated"
          size="small"
          type="link"
          :loading="previewLoading"
          @click="handleTogglePreviewAll"
        >{{ showAllPreview ? '收起（前 50 条）' : `全部（${previewResult.total_possible} 条）` }}</a-button>
      </div>
      <template v-if="previewResult">
        <div v-if="!previewResult.valid" class="preview-error">⚠️ {{ previewResult.errors.join('；') }}<span class="preview-error-hint">（以下仅展示输入参数，修正公式后自动计算输出）</span></div>
        <div v-if="previewResult.valid || previewResult.columns.length" class="preview-table-wrap">
          <table class="preview-table">
            <thead>
              <!-- 第一行：功能分组（输入参数 / 输出结果） -->
              <tr class="preview-tr-top">
                <th
                  v-if="previewColumnList.length"
                  :colspan="previewColumnList.length"
                  class="preview-th-top preview-th-input"
                >输入参数</th>
                <th v-if="previewResult.valid" class="preview-th-top preview-th-output-top">输出结果</th>
              </tr>
              <!-- 第二行：表名.字段中文名 + 结果值 -->
              <tr>
                <th
                  v-for="col in previewColumnList"
                  :key="col.key"
                  class="preview-th-sub"
                  :title="col.ref"
                >{{ col.groupDisplayName }}.{{ col.displayName }}</th>
                <th v-if="previewResult.valid" class="preview-th-output">结果值</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(row, ri) in previewResult.rows" :key="ri">
                <td
                  v-for="col in previewColumnList"
                  :key="col.key"
                  :class="{ 'preview-td-group-start': col.isGroupStart }"
                >{{ formatPreviewCell(row.inputs[col.ref]) }}</td>
                <td v-if="previewResult.valid" class="preview-td-output" :class="{ 'preview-td-error': row.error }">
                  {{ row.error ? '⚠ ' + row.error : formatPreviewCell(row.output) }}
                </td>
              </tr>
            </tbody>
          </table>
          <div v-if="!previewResult.rows.length" class="preview-empty">无可预览数据（引用字段暂无去重值缓存）</div>
        </div>
      </template>
      <div v-else class="preview-empty">输入计算表达式后自动展示数据预览（引用字段去重值组合 + 输出结果）</div>
    </div>
  </a-modal>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick } from 'vue'
import { message } from 'ant-design-vue'
import { computedFieldApi } from '@/api/modeling'
import { formatExpressionText } from '@/utils/formula'
import { extractApiError } from '@/utils/apiError'
import type { ComputedFieldModel, FormulaValidationResult, AvailableFunction, AvailableReference, PreviewDataResult, PluginInfo } from '@/api/modeling'

const props = defineProps<{
  open: boolean
  domainId: number
  field?: ComputedFieldModel | null
}>()

const emit = defineEmits<{
  'update:open': [value: boolean]
  saved: [field: ComputedFieldModel]
  'save-and-trial': [field: ComputedFieldModel]
}>() 

const isEdit = computed(() => !!props.field?.id)

const form = ref({
  code: '',
  name: '',
  expression: '',
  output_type: 'text' as 'text' | 'number' | 'date' | 'boolean',
})

const saving = ref(false)
const validating = ref(false)
const validationResult = ref<FormulaValidationResult | null>(null)
const sideTab = ref('fields')
const funcSearch = ref('')
const fieldSearch = ref('')
const textareaRef = ref<any>(null)
const sidebarLoading = ref(false)
const sidebarError = ref<string | null>(null)
const previewLoading = ref(false)
const previewResult = ref<PreviewDataResult | null>(null)
const showAllPreview = ref(false)
// AI 自然语言生成
const aiDescription = ref('')
const aiGenerating = ref(false)
const aiExplanation = ref('')
const aiReasoning = ref('')
const aiReasoningActiveKey = ref<string[]>([])
const aiRisk = ref('')
// 用户选中的引用字段（可删减，删除后 AI 生成不再携带）
const selectedRefsForAi = ref<string[]>([])
// 技术函数插件
const plugins = ref<PluginInfo[]>([])
const pluginsLoading = ref(false)
const pluginUploading = ref(false)
const pluginReloadingMap = ref<Record<string, boolean>>({})
const pluginUnloadingMap = ref<Record<string, boolean>>({})

// 函数库和引用列表
const functions = ref<AvailableFunction[]>([])
const references = ref<AvailableReference[]>([])
const computedReferences = ref<AvailableReference[]>([])
// 两级级联：当前选中的一级项
const selectedRefTable = ref('')
const selectedFuncCategory = ref('')

// 函数分类展示顺序
const FUNC_CATEGORY_ORDER = ['逻辑函数', '字符串函数', '数字函数', '判空函数', '日期函数', '其他']

interface FuncGroup { category: string; fns: AvailableFunction[] }
const groupedFunctions = computed<FuncGroup[]>(() => {
  const s = funcSearch.value.toLowerCase()
  const filtered = s
    ? functions.value.filter(fn => fn.name.toLowerCase().includes(s) || fn.description.toLowerCase().includes(s))
    : functions.value
  const map = new Map<string, AvailableFunction[]>()
  for (const fn of filtered) {
    const cat = fn.category || '其他'
    if (!map.has(cat)) map.set(cat, [])
    map.get(cat)!.push(fn)
  }
  const groups: FuncGroup[] = []
  for (const cat of FUNC_CATEGORY_ORDER) {
    if (map.has(cat)) {
      groups.push({ category: cat, fns: map.get(cat)! })
      map.delete(cat)
    }
  }
  for (const [cat, fns] of map) groups.push({ category: cat, fns })
  return groups
})

// 当前分类下的函数列表（二级栏）
const currentCategoryFns = computed<AvailableFunction[]>(() =>
  groupedFunctions.value.find(g => g.category === selectedFuncCategory.value)?.fns || []
)

// 搜索过滤后选中分类不存在时自动切到第一组
watch(groupedFunctions, (groups) => {
  if (!groups.find(g => g.category === selectedFuncCategory.value)) {
    selectedFuncCategory.value = groups[0]?.category || ''
  }
}, { immediate: true })

// 按表分组的引用字段（支持搜索过滤）
interface RefGroup { tableName: string; fields: AvailableReference[] }
const groupedReferences = computed<RefGroup[]>(() => {
  const s = fieldSearch.value.toLowerCase()
  const all = [...references.value, ...computedReferences.value]
  const filtered = s ? all.filter(r => r.ref.toLowerCase().includes(s) || r.name.toLowerCase().includes(s) || (r.display_name || '').toLowerCase().includes(s)) : all

  const map = new Map<string, AvailableReference[]>()
  for (const r of filtered) {
    const key = r.table_name || '$computed'
    if (!map.has(key)) map.set(key, [])
    map.get(key)!.push(r)
  }

  const groups: RefGroup[] = []
  for (const [tableName, fields] of map) {
    groups.push({ tableName: tableName === '$computed' ? '计算字段' : tableName, fields })
  }
  return groups
})

// 当前选中表下的字段列表（二级栏）
const currentRefFields = computed<AvailableReference[]>(() =>
  groupedReferences.value.find(g => g.tableName === selectedRefTable.value)?.fields || []
)

// 搜索过滤后选中表不存在时自动切到第一组
watch(groupedReferences, (groups) => {
  if (!groups.find(g => g.tableName === selectedRefTable.value)) {
    selectedRefTable.value = groups[0]?.tableName || ''
  }
}, { immediate: true })

// -------- 数据预览·中国式表格（两行表头：输入参数/输出 → 表名.字段中文名） --------
interface PreviewColumnItem {
  key: string
  ref: string
  displayName: string
  groupDisplayName: string
  isGroupStart: boolean
}

// 字段引用 ref → 中文名 查找表（物理字段 + 计算字段）
const refDisplayNameMap = computed<Record<string, string>>(() => {
  const map: Record<string, string> = {}
  for (const r of references.value) {
    map[r.ref] = r.display_name || r.name || r.code
  }
  for (const r of computedReferences.value) {
    map[r.ref] = r.display_name || r.name || r.code
  }
  return map
})

// 展平后的列列表（tbody 用 + 第二行表头「表名.字段中文名」）
const previewColumnList = computed<PreviewColumnItem[]>(() => {
  if (!previewResult.value) return []
  const cols = previewResult.value.columns
  if (!cols.length) return []
  return cols.map((colRef, idx) => {
    // colRef 格式："表名.字段code" 或 "$computed.xxx"
    const dotIdx = colRef.indexOf('.')
    const tableName = dotIdx > 0 ? colRef.slice(0, dotIdx) : '其他'
    const fieldCode = dotIdx > 0 ? colRef.slice(dotIdx + 1) : colRef
    const groupDisplayName = tableName === '$computed' ? '计算字段' : tableName
    const displayName = refDisplayNameMap.value[colRef] || fieldCode
    return {
      key: `${colRef}-${idx}`,
      ref: colRef,
      displayName,
      groupDisplayName,
      isGroupStart: idx > 0 && cols[idx - 1]?.indexOf('.') !== dotIdx,
    }
  })
})

// 未使用的引用字段（验证结果里有引用但表达式里没用到的）
const unusedReferences = computed(() => {
  if (!validationResult.value?.valid || !validationResult.value.references?.length) return []
  const usedRefs = new Set(selectedRefsForAi.value)
  if (!usedRefs.size) return []
  const allRefs = [...references.value, ...computedReferences.value]
  return allRefs.filter(r => {
    const refStr = r.ref
    if (!usedRefs.has(refStr)) return false
    // 检查该引用是否在验证结果的 references 里
    return !validationResult.value!.references.some(
      vr => `${vr.table_name}.${vr.field_code}` === refStr
    )
  })
})

watch(() => props.open, async (val) => {
  if (val) {
    // 初始化表单
    if (props.field) {
      form.value = {
        code: props.field.code,
        name: props.field.name,
        expression: props.field.expression || '',
        output_type: props.field.output_type || 'text',
      }
    } else {
      form.value = { code: '', name: '', expression: '', output_type: 'text' }
    }
    validationResult.value = null
    previewResult.value = null
    aiDescription.value = ''
    aiExplanation.value = ''
    aiReasoning.value = ''
    aiReasoningActiveKey.value = []
    aiRisk.value = ''
    selectedRefsForAi.value = []
    showAllPreview.value = false
    await loadSidebarData()
    loadPlugins()
    // 编辑模式已有表达式：自动验证 + 默认展示数据预览
    if (form.value.expression.trim()) {
      handleValidate()
      handlePreviewData(true)
    }
  }
})

async function loadSidebarData() {
  sidebarLoading.value = true
  sidebarError.value = null
  try {
    const [fnRes, refRes] = await Promise.all([
      computedFieldApi.availableFunctions(),
      computedFieldApi.availableReferences(props.domainId),
    ])
    functions.value = fnRes.data.functions || []
    references.value = refRes.data.fields || []
    computedReferences.value = refRes.data.computed_fields || []
    // 主动选中第一个表（确保二级栏有数据展示）
    const firstTable = references.value[0]?.table_name
      || (computedReferences.value.length ? '计算字段' : '')
    if (firstTable) {
      selectedRefTable.value = firstTable
    }
  } catch (e: any) {
    sidebarError.value = '加载失败，请检查后端服务是否正常'
    console.error('[FormulaEditor] loadSidebarData failed:', e)
  } finally {
    sidebarLoading.value = false
  }
}

// -------- 技术函数插件管理 --------
async function loadPlugins() {
  pluginsLoading.value = true
  try {
    const res = await computedFieldApi.pluginList()
    plugins.value = res.data.plugins || []
  } catch (e: any) {
    message.error('加载技术函数插件失败')
  } finally {
    pluginsLoading.value = false
  }
}

async function handlePluginUpload(options: any) {
  const file = options.file as File
  if (!file.name.endsWith('.py')) {
    message.error('仅支持 .py 文件')
    options.onError?.(new Error('only .py'))
    return
  }
  pluginUploading.value = true
  try {
    const res = await computedFieldApi.pluginUpload(file)
    const info = res.data
    message.success(`插件 ${info.filename} 上传成功，注册 ${info.functions.length} 个函数`)
    options.onSuccess?.(info)
    await loadPlugins()
    // 同步刷新函数库
    const fnRes = await computedFieldApi.availableFunctions()
    functions.value = fnRes.data.functions || []
  } catch (e: any) {
    const data = e.response?.data
    let errMsg = data?.error || '上传失败'
    if (data?.details && Array.isArray(data.details)) {
      errMsg += '；' + data.details.slice(0, 3).join('；')
    }
    message.error({ content: errMsg, duration: 6 })
    options.onError?.(e)
  } finally {
    pluginUploading.value = false
  }
}

async function handlePluginReload(filename: string) {
  pluginReloadingMap.value[filename] = true
  try {
    await computedFieldApi.pluginReload(filename)
    message.success(`插件 ${filename} 已重载`)
    await loadPlugins()
    const fnRes = await computedFieldApi.availableFunctions()
    functions.value = fnRes.data.functions || []
  } catch (e: any) {
    message.error(extractApiError(e) || '重载失败')
  } finally {
    pluginReloadingMap.value[filename] = false
  }
}

async function handlePluginUnload(filename: string) {
  pluginUnloadingMap.value[filename] = true
  try {
    await computedFieldApi.pluginUnload(filename)
    message.success(`插件 ${filename} 已卸载`)
    await loadPlugins()
    const fnRes = await computedFieldApi.availableFunctions()
    functions.value = fnRes.data.functions || []
  } catch (e: any) {
    message.error(extractApiError(e) || '卸载失败')
  } finally {
    pluginUnloadingMap.value[filename] = false
  }
}

async function handleDownloadTemplate() {
  try {
    const res = await computedFieldApi.pluginTemplate()
    const blob = new Blob([res.data.template], { type: 'text/x-python' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'tech_function_template.py'
    a.click()
    URL.revokeObjectURL(url)
  } catch {
    message.error('获取模板失败')
  }
}

let validateTimer: ReturnType<typeof setTimeout> | null = null
function onExpressionChange() {
  validationResult.value = null
  if (validateTimer) clearTimeout(validateTimer)
  validateTimer = setTimeout(() => {
    if (form.value.expression.trim()) {
      handleValidate()
      handlePreviewData(true)
    } else {
      previewResult.value = null
    }
  }, 800)
}

/**
 * 格式化计算表达式（代码编辑器风格）：
 * 函数名大写化 + 补全缺失右括号 + 长函数调用换行缩进（每个参数独立一行，两空格缩进）。
 * 保护字段引用 {...} 和字符串字面量 "..." 不被误改。
 */
function handleFormatExpression() {
  const raw = form.value.expression
  if (!raw.trim()) return
  form.value.expression = formatExpressionText(raw)
  message.success('格式化完成')
}

async function handleValidate() {
  const expr = form.value.expression.trim()
  if (!expr) return
  validating.value = true
  try {
    if (props.field?.id) {
      const res = await computedFieldApi.validateFormula(props.field.id, form.value.expression)
      validationResult.value = res.data
    } else {
      // 新建模式：调用纯语法验证接口
      const res = await computedFieldApi.validateExpression(form.value.expression, props.domainId)
      validationResult.value = res.data
    }
    // 验证成功后，同步更新 AI 参考引用（保留用户已删除的，补充新发现的）
    if (validationResult.value?.valid && validationResult.value.references?.length) {
      const newRefs = validationResult.value.references.map(r => `${r.table_name}.${r.field_code}`)
      const merged = new Set([...selectedRefsForAi.value, ...newRefs])
      selectedRefsForAi.value = Array.from(merged)
    }
  } catch (e: any) {
    validationResult.value = { valid: false, references: [], cycle: null, errors: [extractApiError(e) || '验证请求失败'] }
  } finally {
    validating.value = false
  }
}

async function handlePreviewData(silent = false) {
  const expr = form.value.expression.trim()
  if (!expr) {
    if (!silent) message.warning('请先输入计算表达式')
    return
  }
  previewLoading.value = true
  try {
    // 根据 showAllPreview 状态决定拉取数量：全部时传 total_possible（或一个较大值），否则默认 50
    const maxCombinations = showAllPreview.value ? undefined : 50
    const res = await computedFieldApi.previewData(expr, props.domainId, maxCombinations)
    previewResult.value = res.data
  } catch (e: any) {
    if (!silent) message.error(extractApiError(e) || '数据预览失败')
  } finally {
    previewLoading.value = false
  }
}

// 切换「全部 / 前 50 条」预览
async function handleTogglePreviewAll() {
  showAllPreview.value = !showAllPreview.value
  await handlePreviewData(true)
}

function formatPreviewCell(val: any): string {
  if (val === null || val === undefined || val === '') return '(空)'
  return String(val)
}

async function handleAiGenerate() {
  const desc = aiDescription.value.trim()
  if (!desc) {
    message.warning('请先用自然语言描述计算逻辑')
    return
  }
  aiGenerating.value = true
  aiExplanation.value = ''
  aiReasoning.value = ''
  aiReasoningActiveKey.value = []
  aiRisk.value = ''
  try {
    // 携带引用字段作为 AI 参考：已依赖（验证结果）+ 表达式未引用的字段全部并入，供 AI 重新生成时一并考虑
    const refUnion = new Set(selectedRefsForAi.value)
    validationResult.value?.references?.forEach(r => refUnion.add(`${r.table_name}.${r.field_code}`))
    unusedReferences.value.forEach(r => refUnion.add(r.ref))
    const selectedRefs = refUnion.size ? Array.from(refUnion) : undefined
    // 联动：已有表达式时一并传给 AI，按描述在其基础上修改；为空时按描述全新生成
    const currentExpr = form.value.expression.trim() || undefined
    const res = await computedFieldApi.generateFormula(desc, props.domainId, selectedRefs, currentExpr)
    // AI 生成完的表达式自动格式化（代码编辑器风格）
    form.value.expression = formatExpressionText(res.data.expression)
    // AI 连带生成基础信息：仅回填空白项，不覆盖用户已填内容（编辑态编码不可改）
    if (!isEdit.value && !form.value.code.trim() && res.data.code) form.value.code = res.data.code
    if (!form.value.name.trim() && res.data.name) form.value.name = res.data.name
    if (res.data.output_type && ['text', 'number', 'date', 'boolean'].includes(res.data.output_type)) {
      form.value.output_type = res.data.output_type as 'text' | 'number' | 'date' | 'boolean'
    }
    aiExplanation.value = res.data.explanation || ''
    aiReasoning.value = res.data.reasoning || ''
    aiRisk.value = res.data.risk || ''
    // 有推理内容时默认展开思考过程折叠
    if (aiReasoning.value) aiReasoningActiveKey.value = ['1']
    message.success('AI 已生成表达式，正在验证…')
    handleValidate()
    handlePreviewData(true)
  } catch (e: any) {
    message.error(extractApiError(e) || 'AI 生成失败，请重试')
  } finally {
    aiGenerating.value = false
  }
}

// 删除依赖字段 tag（从验证结果和 AI 参考中同步移除）
function handleRemoveReference(index: number) {
  if (!validationResult.value?.references) return
  const removed = validationResult.value.references.splice(index, 1)
  if (removed[0]) {
    const ref = `${removed[0].table_name}.${removed[0].field_code}`
    selectedRefsForAi.value = selectedRefsForAi.value.filter(r => r !== ref)
  }
}

// 通过 ref 字符串删除引用（未使用警告区 tag 删除）
function handleRemoveReferenceByRef(ref: string) {
  if (!validationResult.value?.references) return
  const idx = validationResult.value.references.findIndex(r => `${r.table_name}.${r.field_code}` === ref)
  if (idx >= 0) {
    validationResult.value.references.splice(idx, 1)
  }
  selectedRefsForAi.value = selectedRefsForAi.value.filter(r => r !== ref)
}

/**
 * 从函数 description 解析签名模板。
 * 例如 'IF(条件, 真值, [假值]) — 条件判断' → 'IF(条件, 真值, [假值])'
 */
function extractFunctionTemplate(fn: AvailableFunction): string {
  const desc = fn.description || ''
  // 尝试匹配 "FUNC_NAME(...)" 模式
  const match = desc.match(/^([A-Z_]+\([^)]*\))/)
  if (match) return match[1]
  // 退回默认
  return `${fn.name}()`
}

function insertFunction(fn: AvailableFunction) {
  const template = extractFunctionTemplate(fn)
  // 光标放到第一个参数位置（左括号后）
  const parenIdx = template.indexOf('(')
  const cursorOffset = parenIdx >= 0 ? parenIdx + 1 : template.length
  insertAtCursor(template, cursorOffset)
}

function insertReference(ref: AvailableReference) {
  const insert = `{${ref.ref}}`
  insertAtCursor(insert, insert.length)
  // 同步加入 AI 参考引用（确保 AI 下次生成时携带该字段）
  if (!selectedRefsForAi.value.includes(ref.ref)) {
    selectedRefsForAi.value.push(ref.ref)
  }
}

function insertAtCursor(text: string, cursorOffset: number) {
  const el = textareaRef.value?.$el?.querySelector?.('textarea') || textareaRef.value?.resizableTextArea?.textArea
  if (!el) {
    form.value.expression += text
    return
  }
  const start = el.selectionStart ?? form.value.expression.length
  const end = el.selectionEnd ?? start
  const before = form.value.expression.slice(0, start)
  const after = form.value.expression.slice(end)
  form.value.expression = before + text + after
  nextTick(() => {
    const pos = start + cursorOffset
    el.focus()
    el.setSelectionRange(pos, pos)
  })
}

async function handleSave() {
  if (!form.value.code.trim() || !form.value.name.trim()) {
    message.warning('请填写字段编码和名称')
    return
  }
  saving.value = true
  try {
    let result: ComputedFieldModel
    const payload = { ...form.value, release_to_archive: true, domain: props.domainId }
    if (isEdit.value && props.field) {
      payload.release_to_archive = props.field.release_to_archive ?? true
      const res = await computedFieldApi.update(props.field.id, payload)
      result = res.data
    } else {
      const res = await computedFieldApi.create(payload)
      result = res.data
    }
    message.success(isEdit.value ? '保存成功' : '创建成功')
    emit('saved', result)
    emit('update:open', false)
  } catch (e: any) {
    message.error(extractApiError(e) || '保存失败')
  } finally {
    saving.value = false
  }
}

async function handleSaveAndTrial() {
  if (!form.value.code.trim() || !form.value.name.trim()) {
    message.warning('请填写字段编码和名称')
    return
  }
  saving.value = true
  try {
    let result: ComputedFieldModel
    const payload = { ...form.value, release_to_archive: true, domain: props.domainId }
    if (isEdit.value && props.field) {
      payload.release_to_archive = props.field.release_to_archive ?? true
      const res = await computedFieldApi.update(props.field.id, payload)
      result = res.data
    } else {
      const res = await computedFieldApi.create(payload)
      result = res.data
    }
    message.success('保存成功，正在打开试算...')
    emit('save-and-trial', result)
    emit('update:open', false)
  } catch (e: any) {
    message.error(extractApiError(e) || '保存失败')
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
/* 基础信息行：自定义 flex 布局，label 自然宽度紧贴输入框 */
.basic-form {
  display: flex;
  gap: 24px;
  margin-bottom: 16px;
}
.basic-field {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}
.basic-field-label {
  flex: none;
  color: rgba(0, 0, 0, 0.88);
  white-space: nowrap;
}
.basic-field-req {
  color: #ff4d4f;
  margin-right: 2px;
}
.basic-field-input {
  flex: 1;
  min-width: 0;
}
.basic-field-select {
  flex: 1;
  min-width: 0;
}
.formula-editor-layout {
  display: flex;
  gap: 16px;
  margin-top: 12px;
}
.formula-main {
  flex: 1;
  min-width: 0;
}
.formula-sidebar {
  width: 720px; /* 加宽侧栏：计算表达式列不需要过宽，把空间让给字段引用 */
  border-left: 1px solid #f0f0f0;
  padding-left: 12px;
}
.formula-label {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 4px;
  font-weight: 500;
}
.formula-main .formula-label {
  height: 38px; /* 与侧栏 Tab 导航栏等高，保证两列表头行对齐 */
}
/* 侧栏 Tab 导航栏 margin 与左列 label 一致，使 textarea 与搜索框顶部对齐 */
.formula-sidebar :deep(.ant-tabs-nav) {
  height: 38px;
  margin-bottom: 4px;
}
.formula-textarea {
  font-family: 'Fira Code', 'Consolas', monospace;
  font-size: 13px;
  height: 332px !important; /* = 搜索框 24px + 间距 8px + 级联 300px，底部与侧栏平齐 */
  resize: vertical;
}
.ai-generate-block {
  margin-bottom: 20px; /* 与下方基础信息行拉开间隔 */
}
.ai-generate-block .formula-label {
  margin-bottom: 4px;
  text-align: left;
}
.ai-generate-hint {
  font-size: 11px;
  color: #8c8c8c;
  font-weight: 400;
}
.ai-generate-row {
  display: flex;
  gap: 8px;
  align-items: flex-start;
}
.ai-generate-row :deep(.ant-input-affix-wrapper),
.ai-generate-row :deep(textarea) {
  font-family: 'Fira Code', 'Consolas', monospace;
  font-size: 13px;
}
.ai-generate-row > button {
  flex-shrink: 0;
}
.ai-generate-btn {
  padding: 0 20px !important;
  align-self: stretch !important;
  height: auto !important;
  line-height: 1.5 !important;
  font-size: 14px !important;
}
/* AI 提示（a-alert 组件包装，浅黄背景 + 浅黄文字） */
.ai-tips-alert {
  margin-top: 8px;
}
.ai-tips-alert :deep(.ant-alert-message) {
  color: #d48806;
}
.ai-alert-line {
  display: flex;
  gap: 4px;
  line-height: 1.6;
}
.ai-alert-label {
  font-weight: 600;
  flex-shrink: 0;
}
.ai-alert-text {
  flex: 1;
}
.ai-alert-divider {
  height: 1px;
  background: #ffe58f;
  margin: 6px 0;
}
.ai-reasoning-collapse {
  margin-top: 6px;
}
.ai-reasoning-collapse :deep(.ant-collapse-item) {
  border: none !important;
  background: transparent !important;
}
.ai-reasoning-collapse :deep(.ant-collapse-header) {
  font-size: 11px;
  color: #8c8c8c;
  padding: 2px 8px !important;
}
.ai-reasoning-collapse :deep(.ant-collapse-header-text) {
  color: #8c8c8c;
}
.ai-reasoning-collapse :deep(.ant-collapse-content) {
  border: none !important;
  background: transparent !important;
}
.ai-reasoning-collapse :deep(.ant-collapse-content-box) {
  padding: 4px 8px !important;
}
.ai-reasoning-content {
  white-space: pre-wrap;
  font-size: 11px;
  line-height: 1.5;
  color: #8c8c8c;
  max-height: 180px;
  overflow-y: auto;
}
.validation-result {
  margin-top: 6px;
  padding: 8px 12px;
  border-radius: 4px;
  font-size: 13px;
}
.validation-ok {
  background: #f6ffed;
  color: #389e0d;
  border: 1px solid #b7eb8f;
}
.validation-error {
  background: #fff2f0;
  color: #cf1322;
  border: 1px solid #ffa39e;
}
.validation-error-item {
  font-weight: 600;
  font-size: 13px;
  line-height: 1.6;
}
.dep-list {
  margin-top: 6px;
  margin-bottom: 6px;
  font-size: 12px;
}
.dep-label {
  color: #8c8c8c;
  margin-right: 4px;
}
/* 两级级联双栏 */
.cascade {
  display: flex;
  gap: 8px;
  height: 300px;
}
.cascade-l1 {
  width: 300px; /* 一级表名栏加宽，长表名不再截断 */
  flex-shrink: 0;
  overflow-y: auto;
  border-right: 1px solid #f0f0f0;
  padding-right: 4px;
}
.cascade-l1-item {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 5px 6px;
  cursor: pointer;
  border-radius: 4px;
  font-size: 12px;
  color: #262626;
  user-select: none;
}
.cascade-l1-item:hover {
  background: #fafafa;
}
.cascade-l1-item.active {
  background: #e6f4ff;
  color: #1677ff;
  font-weight: 500;
}
.cascade-l1-name {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.cascade-l1-count {
  font-size: 10px;
  color: #bfbfbf;
  background: #f5f5f5;
  padding: 0 4px;
  border-radius: 8px;
  flex-shrink: 0;
}
.cascade-l2 {
  flex: 1;
  min-width: 0;
  overflow-y: auto;
}
.sidebar-loading {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 16px 0;
  color: #8c8c8c;
  font-size: 12px;
}
.sidebar-error {
  padding: 12px 0;
  font-size: 12px;
  color: #cf1322;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.sidebar-empty {
  padding: 12px 0;
  text-align: center;
  color: #bfbfbf;
  font-size: 12px;
}
.func-item {
  padding: 4px 6px;
  cursor: pointer;
  border-radius: 4px;
  font-size: 12px;
  display: flex;
  align-items: baseline;
  gap: 6px;
}
.func-item:hover {
  background: #e6f4ff;
}
.func-name {
  font-weight: 600;
  color: #1677ff;
  flex-shrink: 0;
}
.func-desc {
  color: #8c8c8c;
  font-size: 11px;
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
/* 技术函数插件 Tab */
.tech-plugins-toolbar {
  display: flex;
  gap: 4px;
  margin-bottom: 8px;
  padding-bottom: 8px;
  border-bottom: 1px dashed #f0f0f0;
}
.tech-plugins-hint {
  font-size: 11px;
  color: #8c8c8c;
  margin: 6px 0 8px;
  line-height: 1.5;
}
.plugin-list {
  margin-top: 8px;
  max-height: 420px;
  overflow-y: auto;
}
.plugin-item {
  padding: 6px 8px;
  border: 1px solid #f0f0f0;
  border-radius: 4px;
  margin-bottom: 6px;
  background: #fafafa;
}
.plugin-item:hover {
  border-color: #bae0ff;
  background: #f0f7ff;
}
.plugin-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 4px;
}
.plugin-filename {
  font-family: 'Fira Code', 'Consolas', monospace;
  font-size: 12px;
  font-weight: 600;
  color: #262626;
}
.plugin-fns {
  display: flex;
  flex-wrap: wrap;
  gap: 2px;
  margin-bottom: 4px;
}
.plugin-actions {
  display: flex;
  gap: 4px;
  justify-content: flex-end;
}
.ref-item {
  padding: 4px 6px;
  cursor: pointer;
  border-radius: 4px;
  font-size: 12px;
  display: flex;
  align-items: baseline;
  gap: 6px;
}
.ref-item:hover {
  background: #e6f4ff;
}
.ref-code {
  font-family: monospace;
  color: #8c8c8c;
  font-size: 11px;
  flex: 1;
  min-width: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.ref-name {
  color: #262626;
  font-size: 12px;
  white-space: nowrap;
  flex-shrink: 0;
  max-width: 60%;
  overflow: hidden;
  text-overflow: ellipsis;
}
/* 数据预览面板 */
.preview-panel {
  margin-top: 10px;
  border: 1px solid #f0f0f0;
  border-radius: 6px;
  background: #fafafa;
  padding: 8px 10px;
}
.preview-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: 500;
  font-size: 12px;
  margin-bottom: 6px;
}
.preview-meta {
  font-weight: 400;
  color: #8c8c8c;
  margin-left: 8px;
  font-size: 11px;
}
.preview-error {
  color: #cf1322;
  font-size: 12px;
  font-weight: 600;
  margin-bottom: 6px;
}
.preview-error-hint {
  color: #8c8c8c;
  font-weight: 400;
  font-size: 11px;
}
.preview-table-wrap {
  max-height: 220px;
  overflow: auto;
  background: #fff;
  border: 1px solid #f0f0f0;
  border-radius: 4px;
}
.preview-table {
  width: max-content;
  min-width: 100%;
  border-collapse: separate;
  border-spacing: 0;
  font-size: 12px;
  table-layout: auto;
}
.preview-table th {
  position: sticky;
  top: 0;
  background: #f5f5f5;
  color: #595959;
  font-weight: 500;
  padding: 4px 8px;
  text-align: left;
  border-bottom: 1px solid #e8e8e8;
  border-right: 1px solid #f0f0f0;
  white-space: nowrap;
  max-width: 400px;
  overflow: hidden;
  text-overflow: ellipsis;
}
.preview-table td {
  padding: 3px 8px;
  border-bottom: 1px solid #f5f5f5;
  border-right: 1px solid #f0f0f0;
  color: #595959;
  white-space: nowrap;
  max-width: 400px;
  overflow: hidden;
  text-overflow: ellipsis;
}
.preview-tr-top th {
  top: 0;
  z-index: 3;
  font-size: 13px;
  font-weight: 600;
  text-align: center;
  padding: 8px;
  border-bottom: 1px solid #d9d9d9;
  background: #fafafa !important;
  color: #262626 !important;
}
.preview-th-input {
  text-align: left;
}
.preview-th-output-top {
  text-align: left;
  border-left: 1px solid #d9d9d9;
}
.preview-table th.preview-th-sub {
  position: sticky;
  top: 37px;
  z-index: 2;
  font-size: 12px;
  font-weight: 500;
  color: #262626;
  background: #fafafa;
  border-bottom: 1px solid #d9d9d9;
  border-right: 1px solid #d9d9d9;
  text-align: left;
  padding: 6px 8px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 400px;
}
.preview-table th.preview-th-output {
  position: sticky;
  top: 37px;
  z-index: 2;
  color: #262626 !important;
  background: #fafafa;
  font-weight: 600;
  border-left: 1px solid #d9d9d9;
}
.preview-table tbody tr:first-child td {
  border-top: 1px solid #d9d9d9;
}
.preview-td-group-start {
  border-left: 1px solid #d9d9d9;
}
.preview-table td.preview-td-output {
  color: #262626;
  font-weight: 500;
}
.preview-table td.preview-td-error {
  color: #cf1322;
}
.preview-empty {
  padding: 12px;
  text-align: center;
  color: #bfbfbf;
  font-size: 12px;
}
</style>
