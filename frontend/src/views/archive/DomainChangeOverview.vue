<template>
  <div>
    <div class="page-header" style="margin-bottom: 16px">
      <h2>变更日志 — 域概览</h2>
    </div>

    <a-table
      :dataSource="domainStats"
      :columns="columns"
      :loading="loading"
      rowKey="domain_id"
      :pagination="false"
      size="small"
    >
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'change_count_7d'">
          <span :style="{ color: record.change_count_7d > 0 ? '#1890ff' : '#999', fontWeight: record.change_count_7d > 0 ? '600' : 'normal' }">
            {{ record.change_count_7d }}
          </span>
        </template>
        <template v-if="column.key === 'last_change_at'">
          {{ record.last_change_at ? formatDateTime(record.last_change_at) : '暂无' }}
        </template>
        <template v-if="column.key === 'action'">
          <a @click="gotoDomain(record)">查看变更</a>
        </template>
      </template>
    </a-table>

    <a-empty v-if="!loading && domainStats.length === 0" description="暂无域数据（请先在建模模块创建域并关联档案）" style="margin-top: 40px" />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { domainChangeApi } from '@/api/archive'
import type { DomainChangeStat } from '@/api/archive'
import { formatDateTime } from '@/utils/date'

const router = useRouter()
const loading = ref(false)
const domainStats = ref<DomainChangeStat[]>([])

const columns = [
  { title: '域名称', dataIndex: 'domain_name', key: 'domain_name', width: 200 },
  { title: '档案数', dataIndex: 'archive_count', key: 'archive_count', width: 100 },
  { title: '近7天变更', key: 'change_count_7d', width: 120 },
  { title: '最近变更时间', key: 'last_change_at', width: 180 },
  { title: '操作', key: 'action', width: 120 },
]

async function loadStats() {
  loading.value = true
  try {
    const res = await domainChangeApi.stats()
    domainStats.value = res.data
  } catch (e: any) {
    message.error(e.message || '加载域变更统计失败')
  } finally {
    loading.value = false
  }
}

function gotoDomain(item: DomainChangeStat) {
  router.push({
    path: '/archive/versions',
    query: { domain: String(item.domain_id), domain_name: item.domain_name },
  })
}

onMounted(() => {
  loadStats()
})
</script>
