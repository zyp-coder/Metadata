<template>
  <div>
    <div class="page-header">
      <h2>域管理</h2>
      <a-button type="primary" @click="openCreate">新建域</a-button>
    </div>

    <a-table
      :dataSource="domains"
      :columns="columns"
      :loading="loading"
      :pagination="false"
      rowKey="id"
      :scroll="{ x: 1400 }"
    >
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'status'">
          <a-switch
            :checked="record.status === 'active'"
            checked-children="启用"
            un-checked-children="停用"
            :loading="record._toggling"
            @change="(checked: boolean) => handleToggleStatus(record, checked)"
          />
        </template>
        <template v-if="column.key === 'config_status'">
          <a-spin v-if="!record._configLoaded" size="small" :indicator="null" />
          <a-tooltip v-else-if="record._configIssues?.length" :title="`${record._configIssues.join('；')}（点击查看详情）`">
            <a-tag color="orange" style="cursor:pointer" @click="showConfigDetail(record)">⚠️ {{ record._configIssues.length }} 项待完善</a-tag>
          </a-tooltip>
          <a-tooltip v-else title="点击查看配置检查详情">
            <a-tag color="green" style="cursor:pointer" @click="showConfigDetail(record)">✅ 就绪</a-tag>
          </a-tooltip>
        </template>
        <template v-if="column.key === 'name'">
          <span @click="goEdit(record)" style="cursor: pointer; font-weight: 500">{{ record.name }}</span>
        </template>
        <template v-if="column.key === 'action'">
          <a-space :size="4" style="white-space: nowrap">
            <a @click="goTables(record)" style="color: #1677ff; font-weight: 500">管理表</a>
            <a-divider type="vertical" />
            <a @click="goMappings(record)">关系管理</a>
            <a-divider type="vertical" />
            <a @click="goFields(record)">字段管理</a>
            <a-divider type="vertical" />
            <a style="color: #ff4d4f" @click="confirmDelete(record)">删除</a>
          </a-space>
        </template>
      </template>
    </a-table>

    <a-modal
      v-model:open="modalVisible"
      :title="editingId ? `编辑域 — ${formData.code}` : '新建域'"
      @ok="handleSubmit"
      :confirmLoading="saving"
    >
      <a-form :model="formData" layout="vertical">
        <a-form-item label="域名称" required>
          <a-input v-model:value="formData.name" placeholder="如：供应商主数据" />
        </a-form-item>
        <a-form-item label="域编码" required>
          <a-input v-model:value="formData.code" placeholder="如：SUPPLIER" :disabled="!!editingId" />
        </a-form-item>
        <a-form-item label="描述">
          <a-textarea v-model:value="formData.description" :rows="3" />
        </a-form-item>
      </a-form>
    </a-modal>

    <!-- 配置检查详情弹窗 -->
    <a-modal
      v-model:open="configModalVisible"
      :title="`配置检查：${configDomainName}`"
      :footer="null"
      :width="640"
    >
      <a-spin :spinning="configLoading">
        <a-alert
          v-if="configResult && !configResult.can_enable"
          type="error"
          show-icon
          style="margin-bottom: 12px"
          :message="`有 ${configResult.p0_fail_count} 项 P0 配置缺失，无法启用该域`"
        />
        <a-alert
          v-else-if="configResult?.can_enable && (configResult.p1_warn_count > 0 || configResult.p2_warn_count > 0)"
          type="warning"
          show-icon
          style="margin-bottom: 12px"
          :message="`配置可启用，但有 ${configResult.p1_warn_count} 项警告 + ${configResult.p2_warn_count} 项建议`"
        />
        <a-alert
          v-else-if="configResult?.can_enable"
          type="success"
          show-icon
          style="margin-bottom: 12px"
          message="所有配置项检查通过"
        />
        <a-table
          v-if="configResult"
          :dataSource="configResult.checks"
          :columns="configColumns"
          :pagination="false"
          rowKey="key"
          size="small"
        >
          <template #bodyCell="{ column, record: check }">
            <template v-if="column.key === 'check_level'">
              <a-tag :color="check.level === 'P0' ? 'red' : check.level === 'P1' ? 'orange' : 'blue'">{{ check.level }}</a-tag>
            </template>
            <template v-if="column.key === 'check_status'">
              <a-tag :color="check.status === 'pass' ? 'green' : check.status === 'warn' ? 'orange' : 'red'">
                {{ check.status === 'pass' ? '✅ 通过' : check.status === 'warn' ? '⚠️ 警告' : '❌ 不通过' }}
              </a-tag>
            </template>
            <template v-if="column.key === 'check_message'">
              <span v-if="check.message" style="color: #ff4d4f; font-size: 12px">{{ check.message }}</span>
              <span v-else style="color: #ccc">-</span>
            </template>
          </template>
        </a-table>
      </a-spin>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { message, Modal } from 'ant-design-vue'
import { domainApi } from '@/api/modeling'
import type { Domain } from '@/types'
import { formatDateTime } from '@/utils/date'
import { extractApiError } from '@/utils/apiError'

const router = useRouter()
const domains = ref<(Domain & { _toggling?: boolean; _configIssues?: string[]; _configLoaded?: boolean })[]>([])
const loading = ref(false)
const modalVisible = ref(false)
const saving = ref(false)
const editingId = ref<number | null>(null)
const formData = ref({ name: '', code: '', description: '' })

// 配置检查弹窗
const configModalVisible = ref(false)
const configDomainName = ref('')
const configLoading = ref(false)
const configResult = ref<{
  checks: { key: string; label: string; level: string; status: string; message: string }[];
  can_enable: boolean; p0_fail_count: number; p1_warn_count: number; p2_warn_count: number;
} | null>(null)

const columns = [
  { title: '名称', dataIndex: 'name', key: 'name', width: 200 },
  { title: '编码', dataIndex: 'code', key: 'code', width: 140 },
  { title: '描述', dataIndex: 'description', key: 'description', width: 300, ellipsis: true },
  { title: '状态', key: 'status', width: 100 },
  { title: '配置状态', key: 'config_status', width: 140 },
  { title: '表数量', dataIndex: 'table_count', key: 'table_count', width: 80 },
  { title: '创建时间', dataIndex: 'created_at', key: 'created_at', width: 160,
    customRender: ({ text }: any) => formatDateTime(text) },
  { title: '操作', key: 'action', width: 280 },
]

const configColumns = [
  { title: '级别', key: 'check_level', width: 70 },
  { title: '检查项', dataIndex: 'label', key: 'label', width: 200 },
  { title: '结果', key: 'check_status', width: 110 },
  { title: '说明', key: 'check_message' },
]

async function loadData() {
  loading.value = true
  try {
    const res = await domainApi.list()
    domains.value = res.data.results
    // 异步加载每个域的配置状态（不阻塞主列表）
    res.data.results.forEach(async (d: any) => {
      try {
        const cfg = await domainApi.checkConfig(d.id)
        const issues = cfg.data.checks
          .filter((c: any) => c.status !== 'pass')
          .map((c: any) => `[${c.level}] ${c.message || c.label}`)
        const target = domains.value.find(x => x.id === d.id)
        if (target) {
          target._configIssues = issues
          target._configLoaded = true
        }
      } catch { 
        const target = domains.value.find(x => x.id === d.id)
        if (target) target._configLoaded = true
      }
    })
  } finally {
    loading.value = false
  }
}

function openCreate() {
  editingId.value = null
  formData.value = { name: '', code: '', description: '' }
  modalVisible.value = true
}

async function handleSubmit() {
  if (!formData.value.name || !formData.value.code) {
    message.warning('请填写名称和编码')
    return
  }
  saving.value = true
  try {
    if (editingId.value) {
      await domainApi.update(editingId.value, formData.value)
      message.success('更新成功')
    } else {
      await domainApi.create(formData.value)
      message.success('创建成功')
    }
    modalVisible.value = false
    await loadData()
  } catch (e: any) {
    message.error(extractApiError(e) || '操作失败')
  } finally {
    saving.value = false
  }
}

async function handleToggleStatus(record: Domain & { _toggling?: boolean }, checked: boolean) {
  const newStatus = checked ? 'active' : 'deprecated'
  const actionLabel = checked ? '启用' : '停用'
  if (!checked) {
    // 停用不需要检查
    Modal.confirm({
      title: `确认停用域「${record.name}」？`,
      content: '停用后该域关联的档案也将受到影响。',
      okText: '停用',
      okType: 'danger',
      cancelText: '取消',
      onOk: async () => {
        record._toggling = true
        try {
          await domainApi.patch(record.id, { status: newStatus })
          message.success(`已停用`)
          await loadData()
        } catch (e: any) {
          message.error(extractApiError(e) || '停用失败')
        } finally {
          record._toggling = false
        }
      },
    })
    return
  }
  // 启用需要前置检查
  record._toggling = true
  try {
    await domainApi.patch(record.id, { status: newStatus })
    message.success(`已启用`)
    await loadData()
  } catch (e: any) {
    const errMsg = extractApiError(e) || ''
    if (errMsg.includes('配置不完整')) {
      Modal.error({
        title: '无法启用',
        content: errMsg,
      })
    } else {
      message.error(errMsg || '启用失败')
    }
  } finally {
    record._toggling = false
  }
}

async function showConfigDetail(record: Domain) {
  configDomainName.value = record.name
  configModalVisible.value = true
  configLoading.value = true
  configResult.value = null
  try {
    const res = await domainApi.checkConfig(record.id)
    configResult.value = res.data
  } catch (e: any) {
    message.error(extractApiError(e) || '加载配置检查结果失败')
  } finally {
    configLoading.value = false
  }
}

function confirmDelete(record: Domain) {
  Modal.confirm({
    title: '确认删除此域？',
    content: `域「${record.name}」及其下表、字段、档案将全部删除，此操作不可恢复。`,
    okType: 'danger',
    okText: '删除',
    cancelText: '取消',
    onOk: () => doDelete(record.id),
  })
}

async function doDelete(id: number) {
  try {
    await domainApi.delete(id)
    message.success('删除成功')
    await loadData()
  } catch (e: any) {
    message.error(extractApiError(e) || '删除失败')
  }
}

function goTables(record: Domain) {
  router.push(`/modeling/domains/${record.id}/tables`)
}

function goMappings(record: Domain) {
  router.push(`/modeling/domains/${record.id}/mappings`)
}

function goFields(record: Domain) {
  router.push(`/modeling/domains/${record.id}/fields`)
}

function goEdit(record: Domain) {
  editingId.value = record.id
  formData.value = { name: record.name, code: record.code, description: record.description }
  modalVisible.value = true
}

onMounted(loadData)
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
</style>
