<template>
  <div class="stage-nav">
    <div class="stage-nav__top">
      <a-breadcrumb class="stage-nav__breadcrumb">
        <a-breadcrumb-item>
          <a @click="goDomains">主数据建模</a>
        </a-breadcrumb-item>
        <a-breadcrumb-item>
          <a @click="goDomains">域列表</a>
        </a-breadcrumb-item>
        <a-breadcrumb-item>
          <span class="stage-nav__domain">{{ domainName }}</span>
        </a-breadcrumb-item>
        <a-breadcrumb-item>
          <span class="stage-nav__current">{{ currentTitle }}</span>
        </a-breadcrumb-item>
      </a-breadcrumb>
    </div>
    <div class="stage-nav__steps">
      <template v-for="(s, idx) in stages" :key="s.key">
        <div
          class="stage-item"
          :class="{ 'stage-item--active': s.key === stage, 'stage-item--done': order.indexOf(stage) > idx }"
          @click="goTo(s.key)"
        >
          <span class="stage-item__num">{{ idx + 1 }}</span>
          <span class="stage-item__label">{{ s.title }}</span>
        </div>
        <div v-if="idx < stages.length - 1" class="stage-arrow">›</div>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const props = defineProps<{
  domainName: string
  stage: 'tables' | 'mappings' | 'fields'
}>()

const route = useRoute()
const router = useRouter()
const domainId = Number(route.params.id)

const order = ['tables', 'mappings', 'fields'] as const
const stages = [
  { key: 'tables', title: '管理表' },
  { key: 'mappings', title: '关系管理' },
  { key: 'fields', title: '字段管理' },
] as const

const currentTitle = computed(() => stages.find((s) => s.key === props.stage)?.title || '')

function goDomains() {
  router.push('/modeling/domains')
}

function goTo(key: 'tables' | 'mappings' | 'fields') {
  router.push(`/modeling/domains/${domainId}/${key}`)
}
</script>

<style scoped>
.stage-nav {
  background: #fafbfc;
  border: 1px solid #eef0f4;
  border-radius: 8px;
  padding: 12px 18px;
  margin-bottom: 16px;
}
.stage-nav__top {
  margin-bottom: 10px;
}
.stage-nav__breadcrumb :deep(.ant-breadcrumb-link a) {
  color: #1677ff;
  cursor: pointer;
}
.stage-nav__breadcrumb :deep(.ant-breadcrumb-link a:hover) {
  color: #4096ff;
}
.stage-nav__domain {
  color: #1677ff;
  font-weight: 600;
}
.stage-nav__current {
  color: #595959;
  font-weight: 500;
}
.stage-nav__steps {
  display: flex;
  align-items: center;
  gap: 4px;
}
.stage-arrow {
  color: #c9cdd4;
  font-size: 18px;
  font-weight: 300;
  padding: 0 2px;
  user-select: none;
}
.stage-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 14px;
  border-radius: 16px;
  cursor: pointer;
  transition: background 0.18s ease, color 0.18s ease;
}
.stage-item:hover {
  background: #eef4ff;
}
.stage-item--active {
  background: #e6f0ff;
}
.stage-item--active:hover {
  background: #d9e8ff;
}
.stage-item--done {
  color: #52c41a;
}
.stage-item--done:hover {
  background: #f0fae6;
}
.stage-item__num {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: #e8ecf2;
  color: #595959;
  font-size: 12px;
  font-weight: 600;
  flex-shrink: 0;
}
.stage-item--active .stage-item__num {
  background: #1677ff;
  color: #fff;
}
.stage-item--done .stage-item__num {
  background: #52c41a;
  color: #fff;
}
.stage-item--done .stage-item__num::after {
  content: '✓';
  font-size: 12px;
}
.stage-item--done .stage-item__num span {
  display: none;
}
.stage-item__label {
  font-size: 13px;
  font-weight: 500;
  color: #595959;
}
.stage-item--active .stage-item__label {
  color: #1677ff;
  font-weight: 600;
}
.stage-item--done .stage-item__label {
  color: #52c41a;
}
</style>
