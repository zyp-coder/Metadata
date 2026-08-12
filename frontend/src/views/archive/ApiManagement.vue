<template>
  <div>
    <div class="page-header">
      <h2>API管理</h2>
    </div>

    <a-tabs v-model:activeKey="activeTab" @change="onTabChange">
      <!-- ===== Tab1：接口管理 ===== -->
      <a-tab-pane key="apis" tab="接口管理">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px">
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
          <a-button type="primary" @click="openDrawer(null)">新建</a-button>
        </div>

        <a-table
          :dataSource="apis"
          :columns="columns"
          :loading="loading"
          rowKey="id"
          size="small"
          :scroll="{ x: 1500 }"
          :pagination="{ current: page, pageSize: 20, total, onChange: (p: number) => { page = p; loadApis() }, showTotal: (t: number) => `共 ${t} 条` }"
        >
          <template #bodyCell="{ column, record: api }">
            <template v-if="column.key === 'name'">
              <a @click="openDrawer(api)" style="color: #1677ff; font-weight: 500">{{ api.name }}</a>
            </template>
            <template v-if="column.key === 'public_url'">
              <span v-if="api.public_url" style="font-family: monospace">{{ api.public_url }}</span>
              <span v-else style="color: #999">未生成</span>
            </template>
            <template v-if="column.key === 'allowed_operations'">
              <a-tag v-for="op in (api.allowed_operations?.length ? api.allowed_operations : ['read'])" :key="op">
                {{ opLabel(op) }}
              </a-tag>
            </template>
            <template v-if="column.key === 'rate_limit_per_min'">
              {{ api.rate_limit_per_min ? `${api.rate_limit_per_min}/分` : '不限' }}
            </template>
            <template v-if="column.key === 'status'">
              <a-tag :color="api.status === 'enabled' ? 'green' : 'default'">
                {{ api.status === 'enabled' ? '启用' : '停用' }}
              </a-tag>
            </template>
            <template v-if="column.key === 'action'">
              <a-space :size="4" style="white-space: nowrap">
                <a @click="viewApiData(api)">数据</a>
                <a-divider type="vertical" />
                <a @click="viewDocs(api)">文档</a>
                <a-divider type="vertical" />
                <a @click="openTestModal(api)">测试</a>
              </a-space>
            </template>
          </template>
        </a-table>
      </a-tab-pane>

      <!-- ===== Tab2：密钥管理 ===== -->
      <a-tab-pane key="keys" tab="密钥管理">
        <ApiKeyTab :apis="apis" />
      </a-tab-pane>
    </a-tabs>

    <!-- 新建/编辑接口抽屉 -->
    <a-drawer
      v-model:open="drawer"
      :title="form.id ? `编辑接口 - ${form.name}` : '新建接口'"
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
            <a-input v-model:value="form.path" placeholder="如：/api/data/store-master（展示用）" />
          </a-descriptions-item>
          <a-descriptions-item label="对外标识">
            <span style="color: #999">系统自动生成（从接口路径派生）</span>
          </a-descriptions-item>
          <a-descriptions-item label="操作范围">
            <a-checkbox-group v-model:value="form.allowed_operations">
              <a-checkbox value="read">查询</a-checkbox>
              <a-checkbox value="create" disabled>新增</a-checkbox>
              <a-checkbox value="update" disabled>修改</a-checkbox>
              <a-checkbox value="delete" disabled>删除</a-checkbox>
            </a-checkbox-group>
            <div style="font-size: 12px; color: #999">当前仅开放查询操作</div>
          </a-descriptions-item>
          <a-descriptions-item label="限流">
            <a-input-number v-model:value="form.rate_limit_per_min" :min="0" style="width: 160px" />
            <span style="margin-left: 8px; color: #999">次/分钟/密钥（0=不限）</span>
          </a-descriptions-item>
          <a-descriptions-item label="描述">
            <a-textarea v-model:value="form.description" :rows="2" placeholder="接口用途描述" />
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

        <a-divider>暴露字段<span style="font-size: 12px; color: #999; font-weight: normal">（不选则默认全部，每个接口可释放不同字段子集）</span></a-divider>
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
              <a-checkbox-group v-if="block.fields.length" :value="form.exposed_fields" :style="{ width: '100%', paddingLeft: `${block.level * 20}px` }">
                <a-row>
                  <a-col :span="8" v-for="field in block.fields" :key="field.code">
                    <a-checkbox :value="field.code" :checked="form.exposed_fields.includes(field.code)" @change="(e: any) => toggleField(field.code, e.target.checked)">{{ field.name }}</a-checkbox>
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
    <a-drawer v-model:open="dataDrawer" :title="`数据预览 - ${currentApi?.name || ''}`" width="1000" :destroyOnClose="true">
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

    <!-- 接口文档抽屉 -->
    <a-drawer v-model:open="docsDrawer" :title="`接口文档 - ${docs?.name || ''}`" width="900" :destroyOnClose="true">
      <a-spin :spinning="docsLoading">
        <template v-if="docs">
          <a-descriptions bordered :column="1" size="small">
            <a-descriptions-item label="接口地址">
              <span style="font-family: monospace">{{ docs.base_url }}</span>
            </a-descriptions-item>
            <a-descriptions-item label="认证方式">
              请求头 <span style="font-family: monospace">{{ docs.authentication.header }}</span>（API Key，在「密钥管理」页创建并授权）
            </a-descriptions-item>
            <a-descriptions-item label="操作范围">
              <a-tag v-for="op in docs.allowed_operations" :key="op">{{ opLabel(op) }}</a-tag>
            </a-descriptions-item>
            <a-descriptions-item label="限流">
              {{ docs.rate_limit_per_min ? `${docs.rate_limit_per_min} 次/分钟/密钥` : '不限' }}
            </a-descriptions-item>
            <a-descriptions-item v-if="docs.primary_key_fields.length" label="主键字段">
              <span style="font-family: monospace">{{ docs.primary_key_fields.join(' / ') }}</span>
            </a-descriptions-item>
            <a-descriptions-item v-if="docs.description" label="描述">{{ docs.description }}</a-descriptions-item>
          </a-descriptions>

          <a-divider orientation="left">端点</a-divider>
          <a-table :dataSource="docs.endpoints" :columns="endpointColumns" :pagination="false" rowKey="path" size="small" />

          <a-divider orientation="left">字段（{{ docs.fields.length }}）</a-divider>
          <a-table :dataSource="docs.fields" :columns="docFieldColumns" :pagination="false" rowKey="code" size="small">
            <template #bodyCell="{ column, record: f }">
              <template v-if="column.key === 'writable'">
                <a-tag v-if="f.writable" color="blue">可写</a-tag>
                <span v-else style="color: #999">只读</span>
              </template>
              <template v-if="column.key === 'required_on_create'">
                <a-tag v-if="f.required_on_create" color="red">必填</a-tag>
                <span v-else style="color: #999">-</span>
              </template>
            </template>
          </a-table>

          <a-divider orientation="left">调用示例</a-divider>
          <div style="margin-bottom: 8px; display: flex; justify-content: space-between; align-items: center">
            <strong>curl</strong>
            <a @click="copyText(docs.examples.curl)">复制</a>
          </div>
          <pre class="code-block">{{ docs.examples.curl }}</pre>
          <div style="margin: 8px 0; display: flex; justify-content: space-between; align-items: center">
            <strong>Python</strong>
            <a @click="copyText(docs.examples.python)">复制</a>
          </div>
          <pre class="code-block">{{ docs.examples.python }}</pre>
        </template>
      </a-spin>
      <template #footer>
        <a-button @click="docsDrawer = false">关闭</a-button>
      </template>
    </a-drawer>

    <!-- 测试接口 Modal -->
    <a-modal
      v-model:open="testModalVisible"
      :title="`测试接口 - ${testApi?.name || ''}`"
      width="700px"
      :footer="null"
      :destroyOnClose="true"
    >
      <a-form layout="vertical">
        <a-form-item label="接口地址">
          <a-input :value="testUrl" readonly>
            <template #prefix><span style="color: #52c41a; font-weight: 600">GET</span></template>
            <template #suffix>
              <a @click="copyText(testUrl)" style="font-size: 12px">复制</a>
            </template>
          </a-input>
        </a-form-item>
        <a-form-item label="API Key">
          <a-input v-model:value="testApiKey" placeholder="粘贴 API Key（在密钥管理页创建）" />
        </a-form-item>
        <a-form-item>
          <a-space>
            <a-button type="primary" :loading="testLoading" @click="sendTestRequest">发送请求</a-button>
            <a-button @click="testModalVisible = false">关闭</a-button>
          </a-space>
        </a-form-item>
      </a-form>
      <a-divider v-if="testResponse !== null" orientation="left">响应结果</a-divider>
      <div v-if="testResponse !== null">
        <div style="margin-bottom: 8px">
          <a-tag :color="testStatus >= 200 && testStatus < 300 ? 'green' : 'red'">
            {{ testStatus }} {{ testStatusText }}
          </a-tag>
          <span style="color: #999; font-size: 12px; margin-left: 8px">耗时 {{ testDuration }}ms</span>
        </div>
        <pre class="code-block" style="max-height: 300px; overflow: auto">{{ testResponse }}</pre>
      </div>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { message, Empty } from 'ant-design-vue'
import { archiveApi, archiveApiApi } from '@/api/archive'
import { extractApiError } from '@/utils/apiError'
import ApiKeyTab from './components/ApiKeyTab.vue'
import type { Archive, ArchiveApi, ArchiveApiData, ArchiveSchemaItem, ApiFilterCondition, OpenApiDocs } from '@/types'

const simpleImage = Empty.PRESENTED_IMAGE_SIMPLE

const route = useRoute()
const router = useRouter()

const OP_LABELS: Record<string, string> = { read: '查询', create: '新增', update: '修改', delete: '删除' }
function opLabel(op: string) { return OP_LABELS[op] || op }

// ===== Tab 切换（状态隔离：接口/密钥各自维护筛选分页，深链 ?tab=）=====
const activeTab = ref<string>((route.query.tab as string) || 'apis')
function onTabChange(key: string | number) {
  router.replace({ query: { ...route.query, tab: key } })
}

const archives = ref<Archive[]>([])
const apis = ref<ArchiveApi[]>([])
const loading = ref(false)
const page = ref(1)
const total = ref(0)
const filters = ref<{ archive?: number; status?: string }>({})

const columns = [
  { title: '接口名称', dataIndex: 'name', key: 'name', width: 180, ellipsis: true },
  { title: '对外地址', key: 'public_url', width: 200, ellipsis: true },
  { title: '所属档案', dataIndex: 'archive_name', key: 'archive_name', width: 160, ellipsis: true },
  { title: '操作范围', key: 'allowed_operations', width: 160 },
  { title: '限流', key: 'rate_limit_per_min', width: 80 },
  { title: '暴露字段数', dataIndex: 'exposed_field_count', key: 'exposed_field_count', width: 90 },
  { title: '状态', key: 'status', width: 80 },
  { title: '操作', key: 'action', width: 200 },
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
    message.error(extractApiError(e) || '加载 API 失败')
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
  slug: string
  allowed_operations: string[]
  rate_limit_per_min: number
  description: string
  exposed_fields: string[]
  filter_conditions: ApiFilterCondition[]
  status: 'enabled' | 'disabled'
}>({
  id: null, archive: null, name: '', path: '', slug: '', allowed_operations: ['read'],
  rate_limit_per_min: 0, description: '',
  exposed_fields: [], filter_conditions: [], status: 'enabled',
})

async function loadFormSchema(archiveId: number) {
  schemaLoading.value = true
  try {
    const res = await archiveApi.get(archiveId)
    formSchema.value = res.data.schema || []
  } catch (e: any) {
    message.error(extractApiError(e) || '加载档案字段失败')
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
      slug: api.slug || '',
      allowed_operations: [...(api.allowed_operations?.length ? api.allowed_operations : ['read'])],
      rate_limit_per_min: api.rate_limit_per_min || 0,
      description: api.description || '',
      exposed_fields: [...(api.exposed_fields || [])],
      filter_conditions: (api.filter_conditions || []).map(c => ({ ...c })),
      status: api.status,
    }
    loadFormSchema(api.archive)
  } else {
    form.value = {
      id: null, archive: filters.value.archive || null, name: '', path: '', slug: '',
      allowed_operations: ['read'], rate_limit_per_min: 0, description: '',
      exposed_fields: [], filter_conditions: [], status: 'enabled',
    }
    if (form.value.archive) loadFormSchema(form.value.archive)
    else formSchema.value = []
  }
  drawer.value = true
}

// 按 group_path 分组展平
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

function toggleField(code: string, checked: boolean) {
  if (checked) {
    if (!form.value.exposed_fields.includes(code)) {
      form.value.exposed_fields = [...form.value.exposed_fields, code]
    }
  } else {
    form.value.exposed_fields = form.value.exposed_fields.filter(c => c !== code)
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
  if (!form.value.allowed_operations.length) {
    message.warning('请至少选择一种操作范围')
    return
  }
  saving.value = true
  try {
    const payload: Record<string, any> = {
      archive: form.value.archive,
      name: form.value.name,
      path: form.value.path,
      slug: form.value.slug || null,
      allowed_operations: form.value.allowed_operations,
      rate_limit_per_min: form.value.rate_limit_per_min || 0,
      description: form.value.description,
      exposed_fields: form.value.exposed_fields,
      filter_conditions: form.value.filter_conditions.filter(c => c.field),
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
    } else if (err?.slug) {
      message.error('对外标识已存在，请换一个')
    } else {
      message.error(extractApiError(e) || '保存失败')
    }
  } finally {
    saving.value = false
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
    message.error(extractApiError(e) || '加载数据失败')
  } finally {
    dataLoading.value = false
  }
}

// ===== 接口文档抽屉 =====
const docsDrawer = ref(false)
const docsLoading = ref(false)
const docs = ref<OpenApiDocs | null>(null)

const endpointColumns = [
  { title: '方法', dataIndex: 'method', key: 'method', width: 80 },
  { title: '路径', dataIndex: 'path', key: 'path', width: 320 },
  { title: '说明', dataIndex: 'desc', key: 'desc' },
]

const docFieldColumns = [
  { title: '编码', dataIndex: 'code', key: 'code', width: 180 },
  { title: '名称', dataIndex: 'name', key: 'name', width: 180 },
  { title: '类型', dataIndex: 'type', key: 'type', width: 100 },
  { title: '维护方', dataIndex: 'ownership', key: 'ownership', width: 100 },
  { title: '可写', key: 'writable', width: 80 },
  { title: '新增必填', key: 'required_on_create', width: 90 },
]

async function viewDocs(api: ArchiveApi) {
  docs.value = null
  docsDrawer.value = true
  docsLoading.value = true
  try {
    const res = await archiveApiApi.getDocs(api.id)
    docs.value = res.data
  } catch (e: any) {
    message.error(extractApiError(e) || '加载文档失败')
  } finally {
    docsLoading.value = false
  }
}

async function copyText(text: string) {
  try {
    await navigator.clipboard.writeText(text)
    message.success('已复制到剪贴板')
  } catch {
    message.warning('复制失败，请手动选择复制')
  }
}

// ===== 测试接口 Modal =====
const testModalVisible = ref(false)
const testApi = ref<ArchiveApi | null>(null)
const testUrl = ref('')
const testApiKey = ref('')
const testLoading = ref(false)
const testResponse = ref<string | null>(null)
const testStatus = ref(0)
const testStatusText = ref('')
const testDuration = ref(0)

function openTestModal(api: ArchiveApi) {
  testApi.value = api
  testUrl.value = `${window.location.origin}/api/open/${api.slug || api.id}/`
  testApiKey.value = localStorage.getItem('test_api_key') || ''
  testResponse.value = null
  testStatus.value = 0
  testStatusText.value = ''
  testDuration.value = 0
  testModalVisible.value = true
}

async function sendTestRequest() {
  if (!testApiKey.value) {
    message.warning('请输入 API Key')
    return
  }
  testLoading.value = true
  testResponse.value = null
  const start = Date.now()
  try {
    const res = await fetch(testUrl.value, {
      method: 'GET',
      headers: {
        'X-API-Key': testApiKey.value,
        'Content-Type': 'application/json',
      },
    })
    testDuration.value = Date.now() - start
    testStatus.value = res.status
    testStatusText.value = res.statusText
    const data = await res.text()
    try {
      testResponse.value = JSON.stringify(JSON.parse(data), null, 2)
    } catch {
      testResponse.value = data
    }
    // 记住 API Key 方便下次使用
    localStorage.setItem('test_api_key', testApiKey.value)
  } catch (e: any) {
    testDuration.value = Date.now() - start
    testStatus.value = 0
    testStatusText.value = 'Network Error'
    testResponse.value = e.message || '请求失败'
  } finally {
    testLoading.value = false
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
.code-block {
  background: #f6f8fa;
  border: 1px solid #e8e8e8;
  border-radius: 4px;
  padding: 12px;
  font-family: monospace;
  font-size: 12px;
  white-space: pre-wrap;
  word-break: break-all;
  margin: 0;
}
</style>
