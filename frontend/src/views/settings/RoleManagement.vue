<template>
  <div>
    <div class="page-header">
      <h2>角色管理</h2>
      <a-button type="primary" @click="openCreate">新建角色</a-button>
    </div>

    <a-table
      :dataSource="roles"
      :columns="columns"
      :loading="loading"
      :pagination="false"
      rowKey="id"
      :scroll="{ x: 900 }"
    >
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'name'">
          {{ record.name }}
          <a-tag v-if="record.is_builtin" color="blue" style="margin-left: 8px">内置</a-tag>
        </template>
        <template v-if="column.key === 'description'">
          <a-tooltip :title="record.description">
            {{ record.description || '—' }}
          </a-tooltip>
        </template>
        <template v-if="column.key === 'configured_domain_count'">
          {{ record.configured_domain_count }} / {{ domainCount }} 域
        </template>
        <template v-if="column.key === 'action'">
          <a-space :size="4" style="white-space: nowrap">
            <a @click="openPermissionDrawer(record)">权限</a>
            <a-divider type="vertical" />
            <a @click="openEdit(record)">编辑</a>
            <a-divider type="vertical" />
            <a v-if="!record.is_builtin" style="color: #ff4d4f" @click="confirmDelete(record)">删除</a>
            <span v-else style="color: #999">删除</span>
          </a-space>
        </template>
      </template>
    </a-table>

    <!-- 新建/编辑角色 Modal (小480) -->
    <a-modal
      v-model:open="modalVisible"
      :title="editingId ? '编辑角色' : '新建角色'"
      @ok="handleSubmit"
      :confirmLoading="saving"
      width="480px"
    >
      <a-form :model="formData" layout="vertical">
        <a-form-item label="角色名" required>
          <a-input v-model:value="formData.name" placeholder="如：数据管理员" :maxlength="64" />
        </a-form-item>
        <a-form-item label="说明">
          <a-textarea v-model:value="formData.description" placeholder="角色职责说明" :rows="3" :maxlength="255" />
        </a-form-item>
      </a-form>
    </a-modal>

    <!-- 权限配置抽屉 (C760) -->
    <a-drawer
      v-model:open="drawerVisible"
      :title="`${currentRole?.name || ''} — 权限配置`"
      width="760px"
      :bodyStyle="{ padding: '16px 24px' }"
    >
      <template v-if="currentRole">
        <div style="margin-bottom: 16px">
          <span style="margin-right: 8px; font-weight: 500">选择域：</span>
          <a-select
            v-model:value="selectedDomainId"
            style="width: 240px"
            placeholder="选择档案域"
            @change="onDomainChange"
          >
            <a-select-option v-for="d in domains" :key="d.id" :value="d.id">{{ d.name }}</a-select-option>
          </a-select>
        </div>

        <div v-if="selectedDomainId" style="margin-bottom: 12px">
          <a-space>
            <a-button size="small" @click="selectAllVisible">全选可见</a-button>
            <a-button size="small" @click="clearAll">清空</a-button>
          </a-space>
        </div>

        <div v-if="selectedDomainId && schemaFields.length > 0">
          <div style="color: #999; font-size: 12px; margin-bottom: 8px">
            仅档案侧维护的字段可配置为可编辑；源系统维护字段已置灰
          </div>
          <a-table
            :dataSource="schemaFields"
            :columns="fieldColumns"
            :pagination="false"
            rowKey="code"
            size="small"
            :scroll="{ y: 500 }"
          >
            <template #bodyCell="{ column, record }">
              <template v-if="column.key === 'visible'">
                <a-checkbox
                  :checked="visibleCodes.has(record.code)"
                  @change="(e: any) => toggleVisible(record.code, e.target.checked)"
                />
              </template>
              <template v-if="column.key === 'editable'">
                <!-- 源系统维护字段档案侧只读，不允许配置为可编辑 -->
                <a-tooltip v-if="record.ownership === 'source'" title="源系统维护，档案侧不可人工编辑">
                  <span><a-checkbox disabled /></span>
                </a-tooltip>
                <a-checkbox
                  v-else
                  :checked="editableCodes.has(record.code)"
                  :disabled="!visibleCodes.has(record.code)"
                  @change="(e: any) => toggleEditable(record.code, e.target.checked)"
                />
              </template>
            </template>
          </a-table>
        </div>

        <div v-else-if="selectedDomainId && schemaFields.length === 0" style="color: #999; padding: 24px 0; text-align: center">
          该域暂无字段配置
        </div>

        <div style="margin-top: 24px; text-align: right">
          <a-space>
            <a-button @click="drawerVisible = false">取消</a-button>
            <a-button type="primary" :loading="permSaving" @click="savePermissions">保存</a-button>
          </a-space>
        </div>
      </template>
    </a-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue'
import { message, Modal } from 'ant-design-vue'
import { getRolesApi, createRoleApi, updateRoleApi, deleteRoleApi, getRolePermissionsApi, putRolePermissionsApi } from '@/api/auth'
import { archiveApi } from '@/api/archive'
import { domainApi } from '@/api/modeling'
import { extractApiError } from '@/utils/apiError'
import type { MdmRole, Domain, ArchiveSchemaItem } from '@/types'

const loading = ref(false)
const saving = ref(false)
const roles = ref<MdmRole[]>([])
const domains = ref<Domain[]>([])
const domainCount = ref(0)

const columns = [
  { title: '角色名', key: 'name', width: 180 },
  { title: '说明', key: 'description', width: 240, ellipsis: true },
  { title: '用户数', dataIndex: 'user_count', key: 'user_count', width: 80 },
  { title: '已配置域数', key: 'configured_domain_count', width: 120 },
  { title: '操作', key: 'action', width: 180 },
]

// ===== 列表 =====
async function loadData() {
  loading.value = true
  try {
    const { data } = await getRolesApi({ page_size: 1000 })
    roles.value = data.results
  } catch (e: any) {
    message.error(extractApiError(e) || '加载角色列表失败')
  } finally {
    loading.value = false
  }
}

async function loadDomains() {
  try {
    const { data } = await domainApi.list({ page_size: 1000 })
    domains.value = data.results
    domainCount.value = data.count
  } catch { /* 域加载失败不阻断 */ }
}

// ===== 新建/编辑 =====
const modalVisible = ref(false)
const editingId = ref<number | null>(null)
const formData = reactive({ name: '', description: '' })

function openCreate() {
  editingId.value = null
  formData.name = ''
  formData.description = ''
  modalVisible.value = true
}

function openEdit(record: MdmRole) {
  editingId.value = record.id
  formData.name = record.name
  formData.description = record.description
  modalVisible.value = true
}

async function handleSubmit() {
  if (!formData.name) {
    message.warning('请填写角色名')
    return
  }
  saving.value = true
  try {
    if (editingId.value) {
      await updateRoleApi(editingId.value, formData)
      message.success('更新成功')
    } else {
      await createRoleApi(formData)
      message.success('创建成功')
    }
    modalVisible.value = false
    loadData()
  } catch (e: any) {
    message.error(extractApiError(e) || '操作失败')
  } finally {
    saving.value = false
  }
}

// ===== 删除（R-058：不可逆删除 popconfirm→Modal.confirm，与全站删除防护对齐） =====
function confirmDelete(record: MdmRole) {
  Modal.confirm({
    title: '确认删除该角色',
    content: `删除后角色「${record.name}」不可恢复，其字段可见/可编辑配置一并清除。（若角色下仍有用户，后端会拦截并提示先调整用户角色）`,
    okText: '确认删除',
    okType: 'danger',
    cancelText: '取消',
    onOk() {
      return handleDelete(record)
    },
  })
}

async function handleDelete(record: MdmRole) {
  try {
    await deleteRoleApi(record.id)
    message.success('删除成功')
    loadData()
  } catch (e: any) {
    message.error(extractApiError(e) || '删除失败')
  }
}

// ===== 权限配置抽屉 =====
const drawerVisible = ref(false)
const currentRole = ref<MdmRole | null>(null)
const selectedDomainId = ref<number | null>(null)
const schemaFields = ref<ArchiveSchemaItem[]>([])
const visibleCodes = ref<Set<string>>(new Set())
const editableCodes = ref<Set<string>>(new Set())
// 全部域配置快照（后端 PUT 整体覆盖语义：保存时需带上其他域配置，否则会被误收回）
const allPerms = ref<{ domain: number; visible_codes: string[]; editable_codes: string[] }[]>([])
const permSaving = ref(false)

const fieldColumns = [
  { title: '字段编码', dataIndex: 'code', key: 'code', width: 160 },
  { title: '字段名称', dataIndex: 'name', key: 'name', width: 200 },
  { title: '可见', key: 'visible', width: 60 },
  { title: '可编辑', key: 'editable', width: 80 },
]

async function openPermissionDrawer(record: MdmRole) {
  currentRole.value = record
  selectedDomainId.value = null
  schemaFields.value = []
  visibleCodes.value = new Set()
  editableCodes.value = new Set()
  drawerVisible.value = true
}

async function onDomainChange(domainId: number) {
  if (!currentRole.value || !domainId) return
  // 加载该域的 schema 字段（列表接口不含 schema，需拉档案详情）
  try {
    const { data } = await archiveApi.list({ domain: domainId, page_size: 1 })
    if (data.results.length > 0) {
      const detail = await archiveApi.get(data.results[0].id)
      schemaFields.value = detail.data.schema || []
    } else {
      schemaFields.value = []
    }
    // 源系统维护字段不可配置为可编辑：加载历史配置时剔除可能误存的 source 字段
    const sourceCodes = new Set(
      schemaFields.value.filter(f => f.ownership === 'source').map(f => f.code),
    )
    // 加载当前全部域权限配置（保存时需整体回传）
    const { data: perms } = await getRolePermissionsApi(currentRole.value.id)
    allPerms.value = perms.map(p => ({
      domain: p.domain,
      visible_codes: p.visible_codes || [],
      editable_codes: p.editable_codes || [],
    }))
    const perm = perms.find(p => p.domain === domainId)
    visibleCodes.value = new Set(perm?.visible_codes || [])
    editableCodes.value = new Set((perm?.editable_codes || []).filter(c => !sourceCodes.has(c)))
  } catch (e: any) {
    message.error(extractApiError(e) || '加载字段配置失败')
  }
}

function toggleVisible(code: string, checked: boolean) {
  if (checked) {
    visibleCodes.value.add(code)
  } else {
    visibleCodes.value.delete(code)
    editableCodes.value.delete(code) // 取消可见时同时取消可编辑
  }
  visibleCodes.value = new Set(visibleCodes.value)
  editableCodes.value = new Set(editableCodes.value)
}

function toggleEditable(code: string, checked: boolean) {
  if (checked) {
    editableCodes.value.add(code)
  } else {
    editableCodes.value.delete(code)
  }
  editableCodes.value = new Set(editableCodes.value)
}

function selectAllVisible() {
  visibleCodes.value = new Set(schemaFields.value.map(f => f.code))
}

function clearAll() {
  visibleCodes.value = new Set()
  editableCodes.value = new Set()
}

async function savePermissions() {
  if (!currentRole.value || !selectedDomainId.value) return
  permSaving.value = true
  try {
    const domainId = selectedDomainId.value
    // 整体覆盖：其他域配置原样回传 + 当前域用编辑后的值替换/新增；全清空则移除该域行（收回授权）
    const others = allPerms.value.filter(p => p.domain !== domainId)
    const visible = Array.from(visibleCodes.value)
    const editable = Array.from(editableCodes.value)
    const current = (visible.length || editable.length)
      ? [{ domain: domainId, visible_codes: visible, editable_codes: editable }]
      : []
    await putRolePermissionsApi(currentRole.value.id, [...others, ...current])
    message.success('保存成功')
    drawerVisible.value = false
    loadData()
  } catch (e: any) {
    message.error(extractApiError(e) || '保存失败')
  } finally {
    permSaving.value = false
  }
}

onMounted(() => {
  loadData()
  loadDomains()
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
  font-size: 20px;
}
</style>
