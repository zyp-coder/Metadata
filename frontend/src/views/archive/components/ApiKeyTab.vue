<template>
  <div>
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px">
      <a-space wrap>
        <a-select v-model:value="statusFilter" style="width: 140px" placeholder="状态" allow-clear @change="reload">
          <a-select-option value="active">启用</a-select-option>
          <a-select-option value="revoked">已吊销</a-select-option>
        </a-select>
        <a-button @click="reload">查询</a-button>
      </a-space>
      <a-button type="primary" @click="openDrawer(null)">新建密钥</a-button>
    </div>

    <a-table
      :dataSource="keys"
      :columns="columns"
      :loading="loading"
      rowKey="id"
      size="small"
      :scroll="{ x: 1300 }"
      :pagination="{ current: page, pageSize: 20, total, onChange: (p: number) => { page = p; loadKeys() }, showTotal: (t: number) => `共 ${t} 条` }"
    >
      <template #bodyCell="{ column, record: key }">
        <template v-if="column.key === 'status'">
          <a-tag v-if="key.status === 'revoked'" color="red">已吊销</a-tag>
          <a-tag v-else-if="key.expired" color="orange">已过期</a-tag>
          <a-tag v-else color="green">启用</a-tag>
        </template>
        <template v-if="column.key === 'grants'">
          <template v-if="key.grants?.length">
            <a-tag v-for="g in key.grants" :key="g.api">{{ g.api_name }}（{{ opText(g.allowed_operations) }}）</a-tag>
          </template>
          <span v-else style="color: #999">未授权</span>
        </template>
        <template v-if="column.key === 'last_used_at'">
          {{ key.last_used_at ? formatDateTime(key.last_used_at) : '从未调用' }}
        </template>
        <template v-if="column.key === 'expires_at'">
          {{ key.expires_at ? formatDate(key.expires_at) : '永久' }}
        </template>
        <template v-if="column.key === 'action'">
          <a-space :size="4" style="white-space: nowrap">
            <template v-if="key.status === 'active'">
              <a @click="confirmRotate(key)">轮换</a>
              <a-divider type="vertical" />
              <a style="color: #ff4d4f" @click="confirmRevoke(key)">吊销</a>
              <a-divider type="vertical" />
            </template>
            <a @click="openDrawer(key)">编辑</a>
            <a-divider type="vertical" />
            <a @click="openLogDrawer(key)">日志</a>
          </a-space>
        </template>
      </template>
    </a-table>

    <!-- 新建/编辑密钥抽屉 -->
    <a-drawer
      v-model:open="drawer"
      :title="form.id ? `编辑密钥 - ${form.name}` : '新建密钥'"
      width="900"
      :destroyOnClose="true"
    >
      <a-form layout="vertical">
        <a-descriptions bordered :column="1" size="small">
          <a-descriptions-item label="密钥名称">
            <a-input v-model:value="form.name" placeholder="如：门店系统对接密钥" />
          </a-descriptions-item>
          <a-descriptions-item label="过期时间">
            <a-date-picker
              v-model:value="form.expires_at"
              show-time
              style="width: 260px"
              placeholder="不填=永久有效"
              value-format="YYYY-MM-DDTHH:mm:ss"
            />
          </a-descriptions-item>
        </a-descriptions>

        <a-divider>接口授权<span style="font-size: 12px; color: #999; font-weight: normal">（勾选接口并设置操作范围，操作不得超出接口自身开放范围）</span></a-divider>
        <a-empty v-if="!apis.length" description="暂无可授权的 API，请先在接口管理页创建" :image="simpleImage" />
        <div v-else style="max-height: 420px; overflow-y: auto; border: 1px solid #f0f0f0; border-radius: 4px">
          <div v-for="apiItem in apis" :key="apiItem.id" style="display: flex; align-items: center; padding: 8px 12px; border-bottom: 1px solid #f5f5f5">
            <a-checkbox
              :checked="!!grantOf(apiItem.id)"
              @change="(e: any) => toggleGrant(apiItem, e.target.checked)"
              style="width: 320px"
            >
              {{ apiItem.name }}
              <span style="color: #999; font-size: 12px">{{ apiItem.archive_name }}</span>
            </a-checkbox>
            <a-checkbox-group
              v-if="grantOf(apiItem.id)"
              v-model:value="grantOf(apiItem.id)!.allowed_operations"
            >
              <a-checkbox v-for="op in apiOpsOf(apiItem)" :key="op" :value="op">{{ opLabel(op) }}</a-checkbox>
            </a-checkbox-group>
          </div>
        </div>
      </a-form>

      <template #footer>
        <a-space style="display: flex; justify-content: flex-end">
          <a-button @click="drawer = false">取消</a-button>
          <a-button type="primary" :loading="saving" @click="save">保存</a-button>
        </a-space>
      </template>
    </a-drawer>

    <!-- 明文密钥展示弹窗（仅显示一次） -->
    <a-modal v-model:open="plainModal" title="密钥已生成" width="520" :footer="null">
      <a-alert
        type="error"
        show-icon
        style="margin-bottom: 12px"
        message="密钥明文仅此一次展示，请立即复制保存"
        description="关闭后无法再次查看；若丢失请使用「轮换」重新生成。"
      />
      <div style="display: flex; gap: 8px; align-items: center">
        <a-input :value="plainKey" readonly style="font-family: monospace" />
        <a-button type="primary" @click="copyPlain">复制</a-button>
      </div>
      <div style="margin-top: 16px; text-align: right">
        <a-button @click="plainModal = false">已保存，关闭</a-button>
      </div>
    </a-modal>

    <!-- 调用日志抽屉 -->
    <a-drawer
      v-model:open="logDrawer"
      :title="`调用日志 - ${logKey?.name || ''}`"
      width="1000"
      :destroyOnClose="true"
    >
      <a-table
        :dataSource="logs"
        :columns="logColumns"
        :loading="logLoading"
        rowKey="id"
        size="small"
        :scroll="{ x: 1000 }"
        :pagination="{ current: logPage, pageSize: 20, total: logTotal, onChange: (p: number) => { logPage = p; loadLogs() }, showTotal: (t: number) => `共 ${t} 条` }"
      >
        <template #bodyCell="{ column, record: log }">
          <template v-if="column.key === 'created_at'">{{ formatDateTime(log.created_at) }}</template>
          <template v-if="column.key === 'status_code'">
            <a-tag :color="log.status_code >= 400 ? 'red' : log.status_code >= 300 ? 'orange' : 'green'">{{ log.status_code }}</a-tag>
          </template>
          <template v-if="column.key === 'duration_ms'">{{ log.duration_ms }}ms</template>
          <template v-if="column.key === 'error_summary'">
            <span v-if="log.error_summary" style="color: #ff4d4f">{{ log.error_summary }}</span>
            <span v-else style="color: #999">-</span>
          </template>
        </template>
      </a-table>
      <template #footer>
        <a-button @click="logDrawer = false">关闭</a-button>
      </template>
    </a-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { message, Empty, Modal } from 'ant-design-vue'
import { apiKeyApi } from '@/api/archive'
import { extractApiError } from '@/utils/apiError'
import { formatDateTime, formatDate } from '@/utils/date'
import type { ApiKey, ApiCallLog, ArchiveApi } from '@/types'

defineProps<{ apis: ArchiveApi[] }>()

const simpleImage = Empty.PRESENTED_IMAGE_SIMPLE

const keys = ref<ApiKey[]>([])
const loading = ref(false)
const page = ref(1)
const total = ref(0)
const statusFilter = ref<string | undefined>(undefined)

const columns = [
  { title: '密钥名称', dataIndex: 'name', key: 'name', width: 180, ellipsis: true },
  { title: '密钥标识', dataIndex: 'key_prefix', key: 'key_prefix', width: 130 },
  { title: '状态', key: 'status', width: 90 },
  { title: '授权', key: 'grants', width: 280, ellipsis: true },
  { title: '累计调用', dataIndex: 'total_calls', key: 'total_calls', width: 90 },
  { title: '最近调用', key: 'last_used_at', width: 150 },
  { title: '到期时间', key: 'expires_at', width: 110 },
  { title: '操作', key: 'action', width: 200 },
]

const OP_LABELS: Record<string, string> = { read: '查询', create: '新增', update: '修改', delete: '删除' }
function opLabel(op: string) { return OP_LABELS[op] || op }
function opText(ops: string[]) { return (ops || []).map(opLabel).join('/') }
function apiOpsOf(apiItem: ArchiveApi) {
  const ops = apiItem.allowed_operations?.length ? apiItem.allowed_operations : ['read']
  return ['read', 'create', 'update', 'delete'].filter(op => ops.includes(op))
}

async function loadKeys() {
  loading.value = true
  try {
    const params: Record<string, any> = { page: page.value }
    if (statusFilter.value) params.status = statusFilter.value
    const res = await apiKeyApi.list(params)
    keys.value = res.data.results
    total.value = res.data.count
  } catch (e: any) {
    message.error(extractApiError(e) || '加载密钥失败')
  } finally {
    loading.value = false
  }
}

function reload() {
  page.value = 1
  loadKeys()
}

// ===== 新建/编辑抽屉 =====
const drawer = ref(false)
const saving = ref(false)
const form = ref<{
  id: number | null
  name: string
  expires_at: string | null
  grants: { api: number; allowed_operations: string[] }[]
}>({ id: null, name: '', expires_at: null, grants: [] })

function grantOf(apiId: number) {
  return form.value.grants.find(g => g.api === apiId)
}

function toggleGrant(apiItem: ArchiveApi, checked: boolean) {
  if (checked) {
    form.value.grants.push({ api: apiItem.id, allowed_operations: ['read'] })
  } else {
    form.value.grants = form.value.grants.filter(g => g.api !== apiItem.id)
  }
}

function openDrawer(key: ApiKey | null) {
  if (key) {
    form.value = {
      id: key.id,
      name: key.name,
      expires_at: key.expires_at,
      grants: (key.grants || []).map(g => ({ api: g.api, allowed_operations: [...g.allowed_operations] })),
    }
  } else {
    form.value = { id: null, name: '', expires_at: null, grants: [] }
  }
  drawer.value = true
}

async function save() {
  if (!form.value.name) {
    message.warning('请填写密钥名称')
    return
  }
  for (const g of form.value.grants) {
    if (!g.allowed_operations.length) {
      message.warning('每个授权接口至少选择一种操作')
      return
    }
  }
  saving.value = true
  try {
    const payload = {
      name: form.value.name,
      expires_at: form.value.expires_at || null,
      grants: form.value.grants,
    }
    if (form.value.id) {
      await apiKeyApi.update(form.value.id, payload)
      message.success('更新成功')
      drawer.value = false
      await loadKeys()
    } else {
      const res = await apiKeyApi.create(payload)
      message.success('创建成功')
      drawer.value = false
      await loadKeys()
      if (res.data.plain_key) {
        plainKey.value = res.data.plain_key
        plainModal.value = true
      }
    }
  } catch (e: any) {
    message.error(extractApiError(e) || '保存失败')
  } finally {
    saving.value = false
  }
}

// ===== 明文展示 =====
const plainModal = ref(false)
const plainKey = ref('')

async function copyPlain() {
  try {
    await navigator.clipboard.writeText(plainKey.value)
    message.success('已复制到剪贴板')
  } catch {
    message.warning('复制失败，请手动选择复制')
  }
}

// ===== 轮换/吊销 =====
function confirmRotate(key: ApiKey) {
  Modal.confirm({
    title: '确认轮换此密钥？',
    content: `轮换后旧密钥「${key.key_prefix}****」将立即失效，所有使用旧密钥的调用方需更换为新密钥。`,
    okText: '确认轮换', okType: 'danger', cancelText: '取消',
    async onOk() {
      try {
        const res = await apiKeyApi.rotate(key.id)
        message.success('轮换成功')
        await loadKeys()
        if (res.data.plain_key) {
          plainKey.value = res.data.plain_key
          plainModal.value = true
        }
      } catch (e: any) {
        message.error(extractApiError(e) || '轮换失败')
      }
    },
  })
}

function confirmRevoke(key: ApiKey) {
  Modal.confirm({
    title: '确认吊销此密钥？',
    content: `吊销后密钥「${key.name}」将立即失效且不可恢复，所有使用该密钥的调用方将无法访问。`,
    okText: '确认吊销', okType: 'danger', cancelText: '取消',
    async onOk() {
      try {
        await apiKeyApi.revoke(key.id)
        message.success('已吊销')
        await loadKeys()
      } catch (e: any) {
        message.error(extractApiError(e) || '吊销失败')
      }
    },
  })
}

// ===== 调用日志 =====
const logDrawer = ref(false)
const logLoading = ref(false)
const logKey = ref<ApiKey | null>(null)
const logs = ref<ApiCallLog[]>([])
const logPage = ref(1)
const logTotal = ref(0)

const logColumns = [
  { title: '时间', key: 'created_at', width: 160 },
  { title: '接口', dataIndex: 'api_name', key: 'api_name', width: 160, ellipsis: true },
  { title: '方法', dataIndex: 'method', key: 'method', width: 70 },
  { title: '路径', dataIndex: 'path', key: 'path', width: 220, ellipsis: true },
  { title: '状态码', key: 'status_code', width: 80 },
  { title: '耗时', key: 'duration_ms', width: 80 },
  { title: 'IP', dataIndex: 'client_ip', key: 'client_ip', width: 120 },
  { title: '错误摘要', key: 'error_summary', ellipsis: true },
]

function openLogDrawer(key: ApiKey) {
  logKey.value = key
  logPage.value = 1
  logs.value = []
  logDrawer.value = true
  loadLogs()
}

async function loadLogs() {
  if (!logKey.value) return
  logLoading.value = true
  try {
    const res = await apiKeyApi.callLogs(logKey.value.id, { page: logPage.value, page_size: 20 })
    logs.value = res.data.results
    logTotal.value = res.data.count
  } catch (e: any) {
    message.error(extractApiError(e) || '加载日志失败')
  } finally {
    logLoading.value = false
  }
}

onMounted(loadKeys)
</script>
