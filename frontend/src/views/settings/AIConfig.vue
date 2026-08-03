<template>
  <div>
    <div class="page-header">
      <h2>系统设置 — AI 配置</h2>
      <a-space>
        <a-button :loading="testing" @click="handleTest">测试连接</a-button>
        <a-button type="primary" :loading="saving" @click="handleSave">保存</a-button>
      </a-space>
    </div>

    <a-alert
      type="info"
      show-icon
      style="margin-bottom: 16px"
      message="AI 用于字段智能分组、语义识别、跨表去重检测与 Excel 字段推断（均按业务主题/业务含义处理）。未启用或未配置 API Key 时，系统自动回退到基于关键词的启发式方案。"
    />

    <a-spin :spinning="loading">
      <a-form :label-col="{ span: 4 }" :wrapper-col="{ span: 14 }">
        <a-form-item label="模型" required>
          <a-select
            v-model:value="form.model"
            :options="modelSelectOptions"
            :filter-option="filterModelOption"
            show-search
            placeholder="选择模型"
            style="max-width: 360px"
            @change="onModelChange"
          />
          <span style="color:#999;margin-left:8px;font-size:12px">选择预设模型自动带出接口地址</span>
        </a-form-item>

        <a-form-item label="API Key" required>
          <a-input-password
            v-model:value="form.api_key"
            :placeholder="form.has_api_key ? '已配置（留空表示不修改）' : '请输入 API Key'"
            autocomplete="new-password"
            style="max-width: 360px"
          />
        </a-form-item>
      </a-form>

      <a-collapse v-model:activeKey="activeAdvancedKeys" style="margin: 0 0 16px 0">
        <a-collapse-panel key="advanced" header="高级设置（服务厂商 / 接口地址 / 采样温度 / 超时 / 名称 / 启用）">
          <a-form :label-col="{ span: 4 }" :wrapper-col="{ span: 14 }">
            <a-form-item label="配置名称">
              <a-input v-model:value="form.name" placeholder="默认AI配置" />
            </a-form-item>
            <a-form-item label="启用">
              <a-switch v-model:checked="form.enabled" checked-children="启用" un-checked-children="停用" />
              <span style="color:#999;margin-left:8px;font-size:12px">启用后优先使用此配置，否则回退到环境变量</span>
            </a-form-item>
            <a-form-item label="服务厂商">
              <a-select v-model:value="form.provider" @change="onProviderChange" style="max-width: 320px">
                <a-select-option v-for="(p, key) in PROVIDERS" :key="key" :value="key">{{ p.label }}</a-select-option>
              </a-select>
              <span style="color:#999;margin-left:8px;font-size:12px">切换厂商会自动填充接口地址</span>
            </a-form-item>
            <a-form-item label="接口地址">
              <a-input
                v-model:value="form.api_base"
                :disabled="!isCustom"
                placeholder="OpenAI 兼容接口 Base URL"
              />
              <span v-if="!isCustom" style="color:#999;margin-left:8px;font-size:12px">已按厂商自动填充（选“自定义”可手改）</span>
            </a-form-item>
            <a-form-item label="采样温度">
              <a-input-number v-model:value="form.temperature" :min="0" :max="2" :step="0.1" style="width: 160px" />
              <span style="color:#999;margin-left:8px;font-size:12px">0~2，越低越稳定（推荐 0.2）</span>
            </a-form-item>
            <a-form-item label="超时时间(秒)">
              <a-input-number v-model:value="form.timeout" :min="5" :max="300" style="width: 160px" />
            </a-form-item>
          </a-form>
        </a-collapse-panel>
      </a-collapse>

      <a-alert
        v-if="testResult"
        :type="testResult.ok ? 'success' : 'error'"
        :message="testResult.message"
        show-icon
        style="margin: 0 0 16px 16.66%; max-width: 60%"
      />

      <a-divider orientation="left">提示词配置</a-divider>
      <div style="color:#999;font-size:12px;margin:0 0 12px 16.66%">
        以下为各 AI 能力使用的提示词（仅指令部分，字段数据由系统自动附加）。留空则使用系统内置默认；点“恢复默认”可填入内置默认再微调。
      </div>
      <a-collapse v-model:activeKey="activePromptKeys" style="margin-left: 16.66%; max-width: 70%">
        <a-collapse-panel v-for="f in PROMPT_FIELDS" :key="f.key" :header="f.label">
          <div style="text-align: right; margin-bottom: 8px">
            <a-button size="small" @click="resetPrompt(f.key)">恢复默认</a-button>
          </div>
          <a-textarea
            v-model:value="prompts[f.key]"
            :rows="6"
            :placeholder="promptDefaults[f.key] || '留空使用系统内置默认'"
          />
        </a-collapse-panel>
      </a-collapse>
    </a-spin>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { message } from 'ant-design-vue'
import { aiConfigApi } from '@/api/modeling'
import type { AIConfigModel } from '@/api/modeling'

// 厂商预设：选定后自动填充接口地址与可选模型
const PROVIDERS: Record<string, { label: string; api_base: string; models: string[] }> = {
  deepseek: { label: 'DeepSeek', api_base: 'https://api.deepseek.com', models: ['deepseek-v4-flash', 'deepseek-v4-pro'] },
  openai: { label: 'OpenAI', api_base: 'https://api.openai.com/v1', models: ['gpt-4o-mini', 'gpt-4o', 'gpt-4-turbo', 'gpt-3.5-turbo'] },
  qwen: { label: '通义千问 Qwen', api_base: 'https://dashscope.aliyuncs.com/compatible-mode/v1', models: ['qwen-plus', 'qwen-max', 'qwen-turbo', 'qwen-long'] },
  zhipu: { label: '智谱 GLM', api_base: 'https://open.bigmodel.cn/api/paas/v4', models: ['glm-4-plus', 'glm-4', 'glm-4-flash'] },
  moonshot: { label: 'Moonshot (Kimi)', api_base: 'https://api.moonshot.cn/v1', models: ['moonshot-v1-8k', 'moonshot-v1-32k', 'moonshot-v1-128k'] },
  custom: { label: '自定义', api_base: '', models: [] },
}

const PROMPT_FIELDS = [
  { key: 'prompt_auto_group', label: '字段分组（按业务主题）' },
  { key: 'prompt_semantic', label: '语义识别（注释补全 / 同义歧义）' },
  { key: 'prompt_dedup', label: '跨表去重检测（等价字段）' },
  { key: 'prompt_infer', label: 'Excel 字段推断' },
]

const loading = ref(false)
const saving = ref(false)
const testing = ref(false)
const testResult = ref<{ ok: boolean; message: string } | null>(null)
const activePromptKeys = ref<string[]>([])
const activeAdvancedKeys = ref<string[]>([])

// 扁平模型索引：模型名 → 所属厂商与接口地址（选中预设模型时自动带出接口地址）
const MODEL_INDEX: Record<string, { provider: string; api_base: string }> = {}
Object.entries(PROVIDERS).forEach(([key, p]) => {
  if (key === 'custom') return
  p.models.forEach((m) => {
    MODEL_INDEX[m] = { provider: key, api_base: p.api_base }
  })
})

const form = reactive<AIConfigModel>({
  name: '默认AI配置',
  provider: 'deepseek',
  api_base: PROVIDERS.deepseek.api_base,
  api_key: '',
  has_api_key: false,
  model: 'deepseek-v4-flash',
  temperature: 0.2,
  timeout: 30,
  enabled: true,
})

const prompts = reactive<Record<string, string>>({
  prompt_auto_group: '',
  prompt_semantic: '',
  prompt_dedup: '',
  prompt_infer: '',
})
const promptDefaults = reactive<Record<string, string>>({})

const isCustom = computed(() => form.provider === 'custom')

// 模型下拉选项（跨厂商扁平列表，label 带厂商前缀）
const modelSelectOptions = computed(() =>
  Object.entries(PROVIDERS)
    .filter(([key]) => key !== 'custom')
    .flatMap(([, p]) => p.models.map((m) => ({ value: m, label: `${p.label} · ${m}` }))),
)

function filterModelOption(input: string, option: any) {
  const s = input.toLowerCase()
  return (
    String(option.value ?? '').toLowerCase().includes(s) ||
    String(option.label ?? '').toLowerCase().includes(s)
  )
}

// 选择/输入模型后：预设模型自动带出厂商与接口地址；自定义模型名保持当前接口地址不变
function onModelChange(val: string) {
  const hit = MODEL_INDEX[val]
  if (hit) {
    form.provider = hit.provider
    form.api_base = hit.api_base
  }
}

function onProviderChange(key: string) {
  const preset = PROVIDERS[key]
  if (!preset || key === 'custom') return
  form.api_base = preset.api_base
  // 若当前模型不属于该厂商，自动切到该厂商第一个模型
  if (!preset.models.includes(form.model)) {
    form.model = preset.models[0] || ''
  }
}

function inferProvider(apiBase: string): string {
  const hit = Object.keys(PROVIDERS).find((k) => k !== 'custom' && PROVIDERS[k].api_base === apiBase)
  return hit || (apiBase ? 'custom' : 'deepseek')
}

async function load() {
  loading.value = true
  try {
    const res = await aiConfigApi.current()
    const d = res.data
    form.name = d.name
    form.provider = d.provider || inferProvider(d.api_base)
    form.api_base = d.api_base || PROVIDERS[form.provider]?.api_base || ''
    form.api_key = ''
    form.has_api_key = d.has_api_key
    form.model = d.model || PROVIDERS[form.provider]?.models[0] || ''
    form.temperature = d.temperature
    form.timeout = d.timeout
    form.enabled = d.enabled
    prompts.prompt_auto_group = d.prompt_auto_group || ''
    prompts.prompt_semantic = d.prompt_semantic || ''
    prompts.prompt_dedup = d.prompt_dedup || ''
    prompts.prompt_infer = d.prompt_infer || ''
    Object.assign(promptDefaults, d.prompt_defaults || {})
  } catch (e: any) {
    message.error(e.message || '加载配置失败')
  } finally {
    loading.value = false
  }
}

function resetPrompt(key: string) {
  prompts[key] = promptDefaults[key] || ''
}

function payload(): Partial<AIConfigModel> {
  const p: Partial<AIConfigModel> = {
    name: form.name,
    provider: form.provider,
    api_base: form.api_base,
    model: form.model,
    temperature: form.temperature,
    timeout: form.timeout,
    enabled: form.enabled,
    prompt_auto_group: prompts.prompt_auto_group,
    prompt_semantic: prompts.prompt_semantic,
    prompt_dedup: prompts.prompt_dedup,
    prompt_infer: prompts.prompt_infer,
  }
  // 仅在填写时提交 api_key（留空表示不修改）
  if (form.api_key) p.api_key = form.api_key
  return p
}

async function handleSave() {
  // R-030: 必填校验（启用时必须有 api_key）
  if (form.enabled && !form.has_api_key && !form.api_key) {
    message.warning('启用 AI 时必须填写 API Key')
    return
  }
  saving.value = true
  try {
    const res = await aiConfigApi.update(payload())
    form.has_api_key = res.data.has_api_key
    form.api_key = ''
    message.success('保存成功')
  } catch (e: any) {
    message.error(e.message || '保存失败')
  } finally {
    saving.value = false
  }
}

async function handleTest() {
  testing.value = true
  testResult.value = null
  try {
    const res = await aiConfigApi.testConnection(payload())
    testResult.value = res.data
    if (res.data.ok) message.success('连接成功')
    else message.warning(res.data.message)
  } catch (e: any) {
    testResult.value = { ok: false, message: e.message || '测试失败' }
    message.error(e.message || '测试失败')
  } finally {
    testing.value = false
  }
}

onMounted(load)
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
}
</style>
