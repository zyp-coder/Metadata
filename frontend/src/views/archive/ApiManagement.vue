<template>
  <div>
    <div class="page-header">
      <h2>API管理</h2>
      <a-button type="primary" @click="openDrawer(null)">新建 API</a-button>
    </div>

    <a-card style="margin-bottom: 16px">
      <a-space wrap>
        <a-select
          v-model:value="filters.archive"
          placeholder="选择档案（默认全部）"
          style="width: 220px"
          allow-clear
          @change="reload"
        >
          <a-select-option v-for="a in archives" :key="a.id" :value="a.id">{{ a.name }}</a-select-option>
        </a-select>
        <a-select v-model:value="filters.status" style="width: 120px" placeholder="状态" allow-clear @change="reload">
          <a-select-option value="enabled">启用</a-select-option>
          <a-select-option value="disabled">停用</a-select-option>
        </a-select>
        <a-button @click="reload">查询</a-button>
      </a-space>
    </a-card>

    <a-table
      :dataSource="apis"
      :columns="columns"
      :loading="loading"
      rowKey="id"
      size="small"
      :scroll="{ x: 1160 }"
      :pagination="{ current: page, pageSize: 20, total, onChange: (p: number) => { page = p; loadApis() }, showTotal: (t: number) => `共 ${t} 条` }"
    >
      <template #bodyCell="{ column, record: api }">
        <template v-if="column.key === 'status'">
          <a-tag :color="api.status === 'enabled' ? 'green' : 'default'">
            {{ api.status === 'enabled' ? '启用' : '停用' }}
          </a-tag>
        </template>
        <template v-if="column.key === 'auth_roles'">
          <template v-if="api.auth_roles?.length">
            <a-tag v-for="(r, i) in api.auth_roles" :key="i">{{ r }}</a-tag>
          </template>
          <span v-else style="color: #999">未授权</span>
        </template>
        <template v-if="column.key === 'action'">
          <a-space :size="4" style="white-space: nowrap">
            <a @click="viewApiData(api)">查看数据</a>
            <a-divider type="vertical" />
            <a @click="openDrawer(api)">编辑</a>
            <a-divider type="vertical" />
            <a v-if="api.status === 'enabled'" @click="toggleStatus(api, 'disabled')" style="color: #ff4d4f">停用</a>
            <a v-else @click="toggleStatus(api, 'enabled')" style="color: #52c41a">启用</a>
            <a-divider type="vertical" />
            <a-popconfirm title="确定删除此 API？" @confirm="doDelete(api.id)">
              <a style="color: #ff4d4f">删除</a>
            </a-popconfirm>
          </a-space>
        </template>
      </template>
    </a-table>

    <!-- 新建/编辑抽屉 -->
    <a-drawer
      v-model:open="drawer"
      :title="form.id ? '编辑 API' : '新建 API'"
      width="900"
      :destroyOnClose="true"
    >
      <a-form layout="vertical">
        <a-descriptions bordered :column="1" size="small">
          <a-descriptions-item label="所属档案">
            <a-select
              v-model:value="form.archive"
              :disabled="!!form.id"
              placeholder="选择档案"
              style="width: 100%"
              @change="onFormArchiveChange"
            >
              <a-select-option v-for="a in archives" :key="a.id" :value="a.id">{{ a.name }}</a-select-option>
            </a-select>
          </a-descriptions-item>
          <a-descriptions-item label="接口名称">
            <a-input v-model:value="form.name" placeholder="如：门店主数据查询接口" />
          </a-descriptions-item>
          <a-descriptions-item label="接口路径">
            <a-input v-model:value="form.path" placeholder="如：/api/data/store-master" />
          </a-descriptions-item>
          <a-descriptions-item label="描述">
            <a-textarea v-model:value="form.description" :rows="2" placeholder="接口用途描述" />
          </a-descriptions-item>
          <a-descriptions-item label="角色/部门授权">
            <a-select
              v-model:value="form.auth_roles"
              mode="tags"
              style="width: 100%"
              placeholder="输入角色或部门名称后回车"
            />
          </a-descriptions-item>
          <a-descriptions-item label="状态">
            <a-switch
              :checked="form.status === 'enabled'"
              checked-children="启用"
              un-checked-children="停用"
              @change="(v: any) => form.status = v ? 'enabled' : 'disabled'"
            />
          </a-descriptions-item>
        </a-descriptions>

        <a-divider>暴露字段<span style="font-size: 12px; color: #999; font-weight: normal">（不选则默认全部）</span></a-divider>
        <a-spin :spinning="schemaLoading">
          <a-empty v-if="!form.archive" description="请先选择所属档案" :image="simpleImage" />
          <div v-else style="max-height: 500px; overflow-y: auto; padding: 8px; border: 1px solid #f0f0f0; border-radius: 4px">
            <template v-for="block in groupedSchemaBlocks" :key="block.key || 'default'">
              <div :style="{ marginBottom: '8px', marginLeft: `${(block.level - 1) * 20}px` }">
                <a-checkbox
                  v-if="block.fields.length"
                  :checked="isGroupAllChecked(block)"
                  :indeterminate="isGroupIndeterminate(block)"
                  @change="(e: any) => toggleGroup(block, e.target.checked)"
                >
                  <strong :style="{ color: block.level <= 1 ? '#1890ff' : '#555' }">{{ block.name || '未分组' }}</strong>
                </a-checkbox>
                <strong v-else :style="{ color: block.level <= 1 ? '#1890ff' : '#555' }">{{ block.name || '未分组' }}</strong>
              </div>
              <a-checkbox-group v-if="block.fields.length" v-model:value="form.exposed_fields" :style="{ width: '100%', paddingLeft: `${block.level * 20}px` }">
                <a-row>
                  <a-col :span="8" v-for="field in block.fields" :key="field.code">
                    <a-checkbox :value="field.code">{{ field.name }}</a-checkbox>
                  </a-col>
                </a-row>
              </a-checkbox-group>
            </template>
          </div>
        </a-spin>

        <a-divider>筛选条件<span style="font-size: 12px; color: #999; font-weight: normal">（多条为 AND 关系）</span></a-divider>
        <div v-for="(cond, idx) in form.filter_conditions" :key="idx" style="margin-bottom: 8px">
          <a-space>
            <a-select v-model:value="cond.field" style="width: 200px" placeholder="字段" show-search>
              <a-select-option v-for="f in formSchema" :key="f.code" :value="f.code">{{ f.name }}</a-select-option>
            </a-select>
            <a-select v-model:value="cond.operator" style="width: 100px">
              <a-select-option value="eq">=</a-select-option>
              <a-select-option value="ne">≠</a-select-option>
              <a-select-option value="gt">&gt;</a-select-option>
              <a-select-option value="lt">&lt;</a-select-option>
              <a-select-option value="contains">包含</a-select-option>
            </a-select>
            <a-input v-model:value="cond.value" style="width: 200px" placeholder="值" />
            <a @click="removeCondition(idx)" style="color: #ff4d4f">删除</a>
          </a-space>
        </div>
        <a-button type="dashed" block @click="addCondition">+ 添加筛选条件</a-button>
      </a-form>

      <template #footer>
        <a-space style="display: flex; justify-content: flex-end">
          <a-button @click="drawer = false">取消</a-button>
          <a-button type="primary" :loading="saving" @click="save">保存</a-button>
        </a-space>
      </template>
    </a-drawer>

    <!-- 查看数据抽屉 -->
    <a-drawer v-model:open="dataDrawer" :title="`${currentApi?.name || ''} — 字段与数据`" width="1000" :destroyOnClose="true">
      <a-spin :spinning="dataLoading">
        <template v-if="apiData">
          <a-divider orientation="left">字段定义（{{ apiData.schema.length }}）</a-divider>
          <a-table :dataSource="apiData.schema" :columns="schemaColumns" :pagination="false" rowKey="code" size="small" />
          <a-divider orientation="left">启用数据（{{ apiData.records.length }} 条）</a-divider>
          <a-table
            :dataSource="apiData.records"
            :columns="dataColumns"
            :pagination="{ pageSize: 20 }"
            rowKey="__id"
            size="small"
            :scroll="{ x: dataScrollX }"
          />
        </template>
      </a-spin>
      <template #footer>
        <a-button @click="dataDrawer = false">关闭</a-button>
      </template>
    </a-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { message, Empty, Modal } from 'ant-design-vue'
import { archiveApi, archiveApiApi } from '@/api/archive'
import type { Archive, ArchiveApi, ArchiveApiData, ArchiveSchemaItem, ApiFilterCondition } from '@/types'

const simpleImage = Empty.PRESENTED_IMAGE_SIMPLE

const archives = ref<Archive[]>([])
const apis = ref<ArchiveApi[]>([])
const loading = ref(false)
const page = ref(1)
const total = ref(0)
const filters = ref<{ archive?: number; status?: string }>({})

const columns = [
  { title: '接口名称', dataIndex: 'name', key: 'name', width: 180, ellipsis: true },
  { title: '路径', dataIndex: 'path', key: 'path', width: 200, ellipsis: true },
  { title: '所属档案', dataIndex: 'archive_name', key: 'archive_name', width: 160, ellipsis: true },
  { title: '暴露字段数', dataIndex: 'exposed_field_count', key: 'exposed_field_count', width: 100 },
  { title: '授权', key: 'auth_roles', width: 180 },
  { title: '状态', key: 'status', width: 80 },
  { title: '操作', key: 'action', width: 260 },
]

async function loadApis() {
  loading.value = true
  try {
    const params: Record<string, any> = { page: page.value }
    if (filters.value.archive) params.archive = filters.value.archive
    if (filters.value.status) params.status = filters.value.status
    const res = await archiveApiApi.list(params)
    apis.value = res.data.results
    total.value = res.data.count
  } catch (e: any) {
    message.error(e.message || '加载 API 失败')
  } finally {
    loading.value = false
  }
}

function reload() {
  page.value = 1
  loadApis()
}

// ===== 新建/编辑抽屉 =====
const drawer = ref(false)
const saving = ref(false)
const schemaLoading = ref(false)
const formSchema = ref<ArchiveSchemaItem[]>([])
const form = ref<{
  id: number | null
  archive: number | null
  name: string
  path: string
  description: string
  exposed_fields: string[]
  filter_conditions: ApiFilterCondition[]
  auth_roles: string[]
  status: 'enabled' | 'disabled'
}>({
  id: null, archive: null, name: '', path: '', description: '',
  exposed_fields: [], filter_conditions: [], auth_roles: [], status: 'enabled',
})

async function loadFormSchema(archiveId: number) {
  schemaLoading.value = true
  try {
    const res = await archiveApi.get(archiveId)
    formSchema.value = res.data.schema || []
  } catch (e: any) {
    message.error(e.message || '加载档案字段失败')
    formSchema.value = []
  } finally {
    schemaLoading.value = false
  }
}

function onFormArchiveChange(val: any) {
  form.value.exposed_fields = []
  form.value.filter_conditions = []
  if (val) loadFormSchema(val)
  else formSchema.value = []
}

function openDrawer(api: ArchiveApi | null) {
  if (api) {
    form.value = {
      id: api.id,
      archive: api.archive,
      name: api.name,
      path: api.path,
      description: api.description || '',
      exposed_fields: [...(api.exposed_fields || [])],
      filter_conditions: (api.filter_conditions || []).map(c => ({ ...c })),
      auth_roles: [...(api.auth_roles || [])],
      status: api.status,
    }
    loadFormSchema(api.archive)
  } else {
    form.value = {
      id: null, archive: filters.value.archive || null, name: '', path: '', description: '',
      exposed_fields: [], filter_conditions: [], auth_roles: [], status: 'enabled',
    }
    if (form.value.archive) loadFormSchema(form.value.archive)
    else formSchema.value = []
  }
  drawer.value = true
}

// 按 group_path 分组展平（与档案详情抽屉一致的嵌套分组渲染）
interface SchemaGroupBlock {
  key: string
  name: string
  level: number
  fields: ArchiveSchemaItem[]
}

const groupedSchemaBlocks = computed<SchemaGroupBlock[]>(() => {
  interface Node { name: string; key: string; level: number; fields: ArchiveSchemaItem[]; children: Node[] }
  const roots: Node[] = []
  const nodeMap = new Map<string, Node>()
  const ensureNode = (path: string[]): Node => {
    const key = path.join(' / ')
    let node = nodeMap.get(key)
    if (node) return node
    node = { name: path[path.length - 1] || '', key, level: path.length, fields: [], children: [] }
    nodeMap.set(key, node)
    if (path.length <= 1) roots.push(node)
    else ensureNode(path.slice(0, -1)).children.push(node)
    return node
  }
  for (const field of formSchema.value) {
    const path = field.group_path?.length ? field.group_path : (field.group ? [field.group] : [''])
    ensureNode(path).fields.push(field)
  }
  const blocks: SchemaGroupBlock[] = []
  const walk = (nodes: Node[]) => {
    for (const n of nodes) {
      blocks.push({ key: n.key, name: n.name, level: n.level, fields: n.fields })
      walk(n.children)
    }
  }
  walk(roots)
  return blocks
})

function isGroupAllChecked(group: SchemaGroupBlock) {
  return group.fields.length > 0 && group.fields.every(f => form.value.exposed_fields.includes(f.code))
}
function isGroupIndeterminate(group: SchemaGroupBlock) {
  const checked = group.fields.filter(f => form.value.exposed_fields.includes(f.code)).length
  return checked > 0 && checked < group.fields.length
}
function toggleGroup(group: SchemaGroupBlock, checked: boolean) {
  const codes = group.fields.map(f => f.code)
  if (checked) {
    form.value.exposed_fields = Array.from(new Set([...form.value.exposed_fields, ...codes]))
  } else {
    form.value.exposed_fields = form.value.exposed_fields.filter(c => !codes.includes(c))
  }
}

function addCondition() {
  form.value.filter_conditions.push({ field: '', operator: 'eq', value: '' })
}
function removeCondition(idx: number) {
  form.value.filter_conditions.splice(idx, 1)
}

async function save() {
  if (!form.value.archive) {
    message.warning('请选择所属档案')
    return
  }
  if (!form.value.name || !form.value.path) {
    message.warning('请填写接口名称和路径')
    return
  }
  saving.value = true
  try {
    const payload = {
      archive: form.value.archive,
      name: form.value.name,
      path: form.value.path,
      description: form.value.description,
      exposed_fields: form.value.exposed_fields,
      filter_conditions: form.value.filter_conditions.filter(c => c.field),
      auth_roles: form.value.auth_roles,
      status: form.value.status,
    }
    if (form.value.id) {
      await archiveApiApi.update(form.value.id, payload)
      message.success('更新成功')
    } else {
      await archiveApiApi.create(payload)
      message.success('创建成功')
    }
    drawer.value = false
    await loadApis()
  } catch (e: any) {
    const err = e.response?.data
    if (err?.path) {
      message.error('接口路径已存在，请换一个')
    } else {
      message.error(e.message || '保存失败')
    }
  } finally {
    saving.value = false
  }
}

async function toggleStatus(api: ArchiveApi, status: 'enabled' | 'disabled') {
  // R-015: 停用是危险操作（调用方立即失败），需确认
  if (status === 'disabled') {
    Modal.confirm({
      title: '确认停用此 API？',
      content: `停用后所有调用方将立即无法访问接口「${api.name}」。`,
      okText: '确认停用',
      okType: 'danger',
      cancelText: '取消',
      async onOk() {
        await doToggleStatus(api, status)
      },
    })
    return
  }
  await doToggleStatus(api, status)
}

async function doToggleStatus(api: ArchiveApi, status: 'enabled' | 'disabled') {
  try {
    await archiveApiApi.update(api.id, {
      archive: api.archive,
      name: api.name,
      path: api.path,
      description: api.description,
      exposed_fields: api.exposed_fields,
      filter_conditions: api.filter_conditions,
      auth_roles: api.auth_roles,
      status,
    })
    message.success(status === 'enabled' ? '已启用' : '已停用')
    await loadApis()
  } catch (e: any) {
    message.error(e.message || '操作失败')
  }
}

async function doDelete(id: number) {
  try {
    await archiveApiApi.delete(id)
    message.success('删除成功')
    await loadApis()
  } catch (e: any) {
    message.error(e.message || '删除失败')
  }
}

// ===== 查看数据抽屉 =====
const dataDrawer = ref(false)
const dataLoading = ref(false)
const currentApi = ref<ArchiveApi | null>(null)
const apiData = ref<ArchiveApiData | null>(null)

const schemaColumns = [
  { title: '字段名', dataIndex: 'name', key: 'name', width: 180 },
  { title: '编码', dataIndex: 'code', key: 'code', width: 200 },
  { title: '类型', dataIndex: 'type', key: 'type', width: 100 },
  { title: '分组', dataIndex: 'group', key: 'group', width: 120 },
]

const dataColumns = computed(() => {
  const schema = apiData.value?.schema || []
  return schema.map((f) => ({
    title: f.name || f.code,
    dataIndex: f.code,
    key: f.code,
    width: 160,
    ellipsis: true,
  }))
})

const dataScrollX = computed(() => (apiData.value?.schema?.length || 0) * 160)

async function viewApiData(api: ArchiveApi) {
  currentApi.value = api
  apiData.value = null
  dataDrawer.value = true
  dataLoading.value = true
  try {
    const res = await archiveApiApi.getData(api.id)
    apiData.value = res.data
  } catch (e: any) {
    message.error(e.message || '加载数据失败')
  } finally {
    dataLoading.value = false
  }
}

onMounted(async () => {
  const res = await archiveApi.list({ page_size: 10000 })
  archives.value = res.data.results
  await loadApis()
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
