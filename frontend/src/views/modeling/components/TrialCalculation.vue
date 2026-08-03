<template>
  <a-modal
    :open="open"
    :title="field ? `枚举试算 - ${field.code} (${field.name})` : '枚举试算'"
    width="800px"
    :destroy-on-close="true"
    @cancel="$emit('update:open', false)"
  >
    <div v-if="field">
      <div class="trial-header">
        <div>
          <strong>{{ field.name }}</strong>
          <span style="color:#8c8c8c;margin-left:8px">{{ field.code }}</span>
        </div>
        <pre class="trial-expression">{{ formattedExpression }}</pre>
      </div>

      <!-- 参数表格 -->
      <div class="params-section">
        <div class="section-title">参数设置</div>
        <a-alert
          v-if="!paramRows.length"
          type="info"
          show-icon
          message="该计算字段的表达式未引用任何字段，没有可设置的输入参数"
        />
        <a-table
          v-else
          :data-source="paramRows"
          :columns="paramColumns"
          row-key="ref"
          :pagination="false"
          size="small"
        >
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'ref'">
              <div class="param-name">{{ displayName(record.ref) }}</div>
              <div class="param-ref">{{ record.ref }}</div>
            </template>
            <template v-if="column.key === 'values'">
              <a-select
                v-model:value="record.values"
                mode="tags"
                :placeholder="record.distinct_values?.length ? '选择或输入' : '输入测试值'"
                style="width: 100%"
                size="small"
                :options="(record.distinct_values || []).map((v: any) => ({ label: String(v), value: v }))"
              />
            </template>
          </template>
        </a-table>
      </div>

      <!-- 操作按钮 -->
      <div class="trial-actions">
        <a-space>
          <a-button type="primary" size="small" :loading="calculating" @click="runCalculation">
            执行试算
          </a-button>
        </a-space>
        <span v-if="result" style="color:#8c8c8c;font-size:12px">
          共 {{ result.total_possible }} 种组合{{ result.truncated ? '（已截断）' : '' }}
        </span>
      </div>

      <!-- 结果表格 -->
      <div v-if="result && result.combinations.length" class="result-section">
        <div class="section-title">试算结果</div>
        <a-table
          :data-source="result.combinations"
          :columns="resultColumns"
          row-key="_idx"
          :pagination="{ pageSize: 20 }"
          size="small"
          :scroll="{ x: 'max-content', y: 300 }"
        >
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'output'">
              <span v-if="record.error" style="color:#cf1322">{{ record.error }}</span>
              <span v-else>{{ record.output }}</span>
            </template>
          </template>
        </a-table>
      </div>
      <!-- 空结果兜底：执行过试算但 0 种组合 -->
      <a-alert
        v-else-if="result && !result.error"
        type="warning"
        show-icon
        message="无试算结果（0 种组合）"
        description="该字段的引用参数在数据中无可用取值，请在上方手动选择或输入测试值后点击「执行试算」"
        style="margin-top:12px"
      />

      <a-alert v-if="result?.error" type="error" :message="result.error" style="margin-top:12px" />
    </div>
    <template #footer>
      <a-button @click="$emit('update:open', false)">关闭</a-button>
    </template>
  </a-modal>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { message } from 'ant-design-vue'
import { computedFieldApi } from '@/api/modeling'
import { formatExpressionText } from '@/utils/formula'
import { extractApiError } from '@/utils/apiError'
import type { ComputedFieldModel, TrialCalculateResult } from '@/api/modeling'

const props = defineProps<{
  open: boolean
  field?: ComputedFieldModel | null
  domainId: number
}>()

const emit = defineEmits<{
  'update:open': [value: boolean]
}>()

interface ParamRow {
  ref: string
  table_name: string
  field_code: string
  values: any[]
  distinct_values: any[]
}

const paramRows = ref<ParamRow[]>([])
const calculating = ref(false)
const result = ref<(TrialCalculateResult & { combinations: ({ _idx: number } & any)[] }) | null>(null)
/** ref → 中文名（availableReferences.display_name），与 FormulaEditor 侧栏同源 */
const displayNameMap = ref<Map<string, string>>(new Map())

/** 表达式代码编辑器风格多行展示（与 FormulaEditor 格式化同一逻辑） */
const formattedExpression = computed(() =>
  props.field?.expression ? formatExpressionText(props.field.expression) : ''
)

function displayName(refKey: string): string {
  return displayNameMap.value.get(refKey) || refKey
}

const paramColumns = [
  { title: '参数字段', dataIndex: 'ref', key: 'ref', width: 220 },
  { title: '测试值（多选构建笛卡尔积）', key: 'values', ellipsis: true },
]

const resultColumns = computed(() => {
  const inputCols = paramRows.value.map(p => ({
    title: displayName(p.ref),
    dataIndex: ['inputs', p.ref],
    key: `input_${p.ref}`,
    width: 140,
    ellipsis: true,
  }))
  return [
    ...inputCols,
    { title: '计算结果', key: 'output', width: 150 },
  ]
})

watch(() => props.open, async (val) => {
  if (val && props.field) {
    result.value = null
    // 从 parsed_references 构建参数行
    const refs = props.field.parsed_references || []
    // 获取中文名与 distinct_values（与 FormulaEditor 同源接口）
    try {
      const refRes = await computedFieldApi.availableReferences(props.domainId)
      const fieldMap = new Map(refRes.data.fields.map(f => [f.ref, f]))
      displayNameMap.value = new Map(
        refRes.data.fields.map(f => [f.ref, f.display_name || f.name || f.ref])
      )
      paramRows.value = refs.map(r => {
        const refKey = `${r.table_name}.${r.field_code}`
        const meta = fieldMap.get(refKey)
        return {
          ref: refKey,
          table_name: r.table_name,
          field_code: r.field_code,
          values: [],
          distinct_values: meta?.sample_values || [],
        }
      })
    } catch {
      displayNameMap.value = new Map()
      paramRows.value = refs.map(r => ({
        ref: `${r.table_name}.${r.field_code}`,
        table_name: r.table_name,
        field_code: r.field_code,
        values: [],
        distinct_values: [],
      }))
    }
    // 默认自动枚举试算：打开弹窗即展示数据预览并回填测试值/下拉选项
    if (paramRows.value.length) {
      await autoEnumerate()
    }
  }
})

async function autoEnumerate() {
  if (!props.field) return
  calculating.value = true
  try {
    const res = await computedFieldApi.trialCalculate(props.field.id, { auto_enumerate: true })
    result.value = {
      ...res.data,
      combinations: res.data.combinations.map((c, i) => ({ ...c, _idx: i })),
    }
    // 回填参数行的值（过滤 undefined/null/空串，避免产生空 tag），并将枚举值并入下拉选项
    if (res.data.combinations.length > 0) {
      for (const row of paramRows.value) {
        const vals = new Set(res.data.combinations.map(c => c.inputs[row.ref]))
        row.values = [...vals].filter(v => v !== undefined && v !== null && v !== '')
        // 下拉选项 = 字段去重样本 ∪ 枚举回填值（保证选项始终有值）
        const optionSet = new Set([...(row.distinct_values || []), ...row.values])
        row.distinct_values = [...optionSet]
      }
    }
  } catch (e: any) {
    message.error(extractApiError(e) || '自动枚举失败')
  } finally {
    calculating.value = false
  }
}

async function runCalculation() {
  if (!props.field) return
  // 构建参数
  const params: Record<string, any[]> = {}
  let hasParams = false
  for (const row of paramRows.value) {
    if (row.values.length > 0) {
      params[row.ref] = row.values
      hasParams = true
    }
  }
  if (!hasParams) {
    message.warning('请为至少一个参数选择或输入测试值')
    return
  }
  calculating.value = true
  try {
    const res = await computedFieldApi.trialCalculate(props.field.id, { params })
    result.value = {
      ...res.data,
      combinations: res.data.combinations.map((c, i) => ({ ...c, _idx: i })),
    }
  } catch (e: any) {
    message.error(extractApiError(e) || '试算失败')
  } finally {
    calculating.value = false
  }
}
</script>

<style scoped>
.trial-header {
  margin-bottom: 16px;
  padding: 8px 12px;
  background: #fafafa;
  border-radius: 6px;
}
.trial-expression {
  font-family: 'Fira Code', 'Consolas', monospace;
  font-size: 12px;
  color: #595959;
  margin: 4px 0 0;
  white-space: pre-wrap;
  word-break: break-all;
}
.param-name {
  color: rgba(0, 0, 0, 0.88);
}
.param-ref {
  font-size: 11px;
  color: #8c8c8c;
  font-family: 'Fira Code', 'Consolas', monospace;
}
.section-title {
  font-weight: 500;
  margin-bottom: 8px;
  color: #262626;
}
.params-section {
  margin-bottom: 16px;
}
.trial-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}
.result-section {
  margin-top: 12px;
}
</style>
