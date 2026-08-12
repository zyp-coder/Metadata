<template>
  <a-drawer
    :open="open"
    :title="`权限全景 — ${archiveName}`"
    width="960px"
    :bodyStyle="{ padding: '16px 24px' }"
    @close="$emit('update:open', false)"
  >
    <a-spin :spinning="loading">
      <template v-if="data">
        <!-- 机器权限（API 开放） -->
        <section style="margin-bottom: 28px">
          <div class="section-header">
            <span class="section-title">机器权限（API 开放）</span>
            <a @click="goApiManagement">去配置 →</a>
          </div>
          <a-table
            v-if="data.apis.length"
            :dataSource="data.apis"
            :columns="apiColumns"
            :pagination="false"
            rowKey="id"
            size="small"
            :scroll="{ x: 910 }"
          >
            <template #bodyCell="{ column, record }">
              <template v-if="column.key === 'slug'">
                <span style="color: #666">/api/open/{{ record.slug || '-' }}/</span>
              </template>
              <template v-if="column.key === 'status'">
                <a-tag :color="record.status === 'enabled' ? 'green' : 'default'">
                  {{ record.status === 'enabled' ? '启用' : '停用' }}
                </a-tag>
              </template>
              <template v-if="column.key === 'allowed_operations'">
                <a-tag v-for="op in record.allowed_operations" :key="op">{{ opLabel(op) }}</a-tag>
                <span v-if="!record.allowed_operations.length" style="color: #999">—</span>
              </template>
              <template v-if="column.key === 'exposed_fields'">
                <template v-if="record.exposed_fields.length">
                  <a-tooltip v-for="code in record.exposed_fields" :key="code" :title="code">
                    <a-tag style="margin: 2px">{{ fieldName(code) }}</a-tag>
                  </a-tooltip>
                </template>
                <span v-else style="color: #999">全部字段</span>
              </template>
              <template v-if="column.key === 'grants'">
                <div v-if="record.grants.length">
                  <div v-for="(g, i) in record.grants" :key="i" style="line-height: 1.8">
                    <a-tooltip :title="`操作范围：${g.allowed_operations.map(opLabel).join('/') || '无'}`">
                      <a-tag :color="g.key_status === 'active' ? 'blue' : 'default'" style="margin: 2px">
                        {{ g.key_name }}<span v-if="g.key_status !== 'active'">（已吊销）</span>
                      </a-tag>
                    </a-tooltip>
                  </div>
                </div>
                <span v-else style="color: #999">无授权密钥</span>
              </template>
              <template v-if="column.key === 'call_stats'">
                <template v-if="record.call_stats.total > 0">
                  <div>共 <b>{{ record.call_stats.total }}</b> 次（近90天）</div>
                  <div style="color: #999; font-size: 12px">最近：{{ formatDateTime(record.call_stats.last_at) }}</div>
                  <div v-for="k in record.call_stats.by_key" :key="k.key_name" style="color: #666; font-size: 12px; line-height: 1.7">
                    {{ k.key_name }}：{{ k.count }} 次<span v-if="k.ips.length"> · {{ k.ips.join(', ') }}</span>
                  </div>
                </template>
                <span v-else style="color: #999">暂无调用</span>
              </template>
            </template>
          </a-table>
          <a-empty v-else description="该档案未配置 API" :image-style="{ height: '40px' }" />
        </section>

        <!-- 人用权限（角色授权） -->
        <section>
          <div class="section-header">
            <span class="section-title">人用权限（角色授权）</span>
            <a @click="goRoles">去配置 →</a>
          </div>
          <a-table
            v-if="data.roles.length"
            :dataSource="data.roles"
            :columns="roleColumns"
            :pagination="false"
            rowKey="role_id"
            size="small"
          >
            <template #bodyCell="{ column, record }">
              <template v-if="column.key === 'role_name'">
                {{ record.role_name }}
                <a-tag v-if="record.is_builtin" color="blue" style="margin-left: 4px">内置</a-tag>
              </template>
              <template v-if="column.key === 'visible_codes'">
                <template v-if="record.visible_codes.length">
                  <a-tooltip v-for="code in record.visible_codes" :key="code" :title="code">
                    <a-tag style="margin: 2px">{{ fieldName(code) }}</a-tag>
                  </a-tooltip>
                </template>
                <span v-else style="color: #999">无可见字段</span>
              </template>
              <template v-if="column.key === 'editable_codes'">
                <template v-if="record.editable_codes.length">
                  <a-tooltip v-for="code in record.editable_codes" :key="code" :title="code">
                    <a-tag color="green" style="margin: 2px">{{ fieldName(code) }}</a-tag>
                  </a-tooltip>
                </template>
                <span v-else style="color: #999">无可编辑字段</span>
              </template>
              <template v-if="column.key === 'users'">
                <template v-if="record.users.length">
                  <a-tooltip v-for="u in record.users" :key="u.username" :title="`${u.username}${u.is_active ? '' : '（已禁用）'}`">
                    <a-tag :color="u.is_active ? undefined : 'default'" style="margin: 2px">
                      {{ u.display_name }}<span v-if="!u.is_active" style="color: #999">（禁用）</span>
                    </a-tag>
                  </a-tooltip>
                </template>
                <span v-else style="color: #999">无用户</span>
              </template>
            </template>
          </a-table>
          <a-empty v-else description="该档案所在域未配置角色权限" :image-style="{ height: '40px' }" />
        </section>
      </template>
    </a-spin>
  </a-drawer>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { archiveApi } from '@/api/archive'
import { extractApiError } from '@/utils/apiError'
import { formatDateTime } from '@/utils/date'
import type { PermissionOverview } from '@/types'

const props = defineProps<{
  open: boolean
  archiveId: number | null
  archiveName: string
}>()
defineEmits(['update:open'])

const router = useRouter()
const loading = ref(false)
const data = ref<PermissionOverview | null>(null)

const OP_LABELS: Record<string, string> = { read: '查询', create: '新增', update: '修改', delete: '删除' }
function opLabel(op: string) { return OP_LABELS[op] || op }
function fieldName(code: string) { return data.value?.field_names[code] || code }

const apiColumns = [
  { title: '接口名称', dataIndex: 'name', key: 'name', width: 140 },
  { title: '对外路径', key: 'slug', width: 150 },
  { title: '状态', key: 'status', width: 60 },
  { title: '允许操作', key: 'allowed_operations', width: 110 },
  { title: '暴露字段', key: 'exposed_fields', width: 190 },
  { title: '授权密钥', key: 'grants', width: 130 },
  { title: '调用情况', key: 'call_stats', width: 180 },
]

const roleColumns = [
  { title: '角色', key: 'role_name', width: 150 },
  { title: '可见字段', key: 'visible_codes', width: 280 },
  { title: '可编辑字段', key: 'editable_codes', width: 220 },
  { title: '用户', key: 'users', width: 250 },
]

watch(() => props.open, async (opened) => {
  if (!opened || !props.archiveId) return
  loading.value = true
  data.value = null
  try {
    const { data: body } = await archiveApi.permissionOverview(props.archiveId)
    data.value = body
  } catch (e: any) {
    message.error(extractApiError(e) || '加载权限全景失败')
  } finally {
    loading.value = false
  }
})

function goApiManagement() {
  router.push('/archive/api-management')
}
function goRoles() {
  router.push('/settings/roles')
}
</script>

<style scoped>
.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}
.section-title {
  font-weight: 600;
  font-size: 15px;
}
</style>
