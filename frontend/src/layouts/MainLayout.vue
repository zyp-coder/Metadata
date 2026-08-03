<template>
  <a-layout style="min-height: 100vh">
    <a-layout-sider v-model:collapsed="collapsed" collapsible theme="light" :width="220">
      <div class="logo">
        <span v-if="!collapsed" class="logo-text">主数据管理</span>
        <span v-else class="logo-text-short">MDM</span>
      </div>
      <a-menu
        v-model:selectedKeys="selectedKeys"
        mode="inline"
        :items="menuItems"
        @click="onMenuClick"
      />
    </a-layout-sider>
    <a-layout>
      <a-layout-header class="site-header">
        <a-breadcrumb :items="breadcrumbItems" />
        <div class="header-right">
          <a-avatar style="background-color: #1677ff" size="small">U</a-avatar>
          <span class="user-name">管理员</span>
        </div>
      </a-layout-header>
      <a-layout-content class="site-content">
        <router-view />
      </a-layout-content>
    </a-layout>
  </a-layout>
</template>

<script setup lang="ts">
import { ref, computed, h, watchEffect } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import {
  ApartmentOutlined,
  DatabaseOutlined,
  FileTextOutlined,
  AuditOutlined,
  SettingOutlined,
} from '@ant-design/icons-vue'

const router = useRouter()
const route = useRoute()
const collapsed = ref(false)
const selectedKeys = ref<string[]>([])

// R-013: 菜单高亮随路由同步（刷新/程序化导航后保持正确高亮）
const allMenuKeys = ['/modeling/domains', '/archive', '/archive/api-management', '/archive/domain-changes', '/settings/data-sources', '/settings/ai', '/settings/tech-functions']
watchEffect(() => {
  const path = route.path
  // 取最长前缀匹配的菜单 key
  const matched = allMenuKeys
    .filter(k => path === k || path.startsWith(k + '/'))
    .sort((a, b) => b.length - a.length)[0]
  if (matched) {
    selectedKeys.value = [matched]
  } else {
    // 子路由无直接菜单项时，匹配父级（如 /archive/5 → /archive）
    const parentMatch = allMenuKeys.find(k => path.startsWith(k.split('/').slice(0, 2).join('/') + '/'))
    selectedKeys.value = parentMatch ? [parentMatch] : []
  }
})

const menuItems = computed(() => [
  {
    key: 'modeling',
    icon: () => h(ApartmentOutlined),
    label: '主数据建模',
    children: [
      { key: '/modeling/domains', label: '域管理' },
    ],
  },
  {
    key: 'archive',
    icon: () => h(DatabaseOutlined),
    label: '档案维护',
    children: [
      { key: '/archive', label: '档案管理' },
      { key: '/archive/api-management', label: 'API管理' },
      { key: '/archive/domain-changes', label: '变更日志' },
    ],
  },
  {
    key: 'quality',
    icon: () => h(FileTextOutlined),
    label: '质量规则',
    disabled: true,
  },
  {
    key: 'auth',
    icon: () => h(AuditOutlined),
    label: '权限管理',
    disabled: true,
  },
  {
    key: 'settings',
    icon: () => h(SettingOutlined),
    label: '系统设置',
    children: [
      { key: '/settings/data-sources', label: '数据源配置' },
      { key: '/settings/ai', label: 'AI配置' },
      { key: '/settings/tech-functions', label: '技术函数' },
    ],
  },
])

const breadcrumbItems = computed(() => [
  { title: '首页' },
  ...(route.meta?.title ? [{ title: route.meta.title as string }] : []),
])

function onMenuClick({ key }: { key: string }) {
  router.push(key)
}
</script>

<style scoped>
.logo {
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-bottom: 1px solid #f0f0f0;
}
.logo-text {
  font-size: 18px;
  font-weight: 700;
  color: #1677ff;
  white-space: nowrap;
}
.logo-text-short {
  font-size: 20px;
  font-weight: 700;
  color: #1677ff;
}
.site-header {
  background: #fff;
  padding: 0 24px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 48px;
  line-height: 48px;
  border-bottom: 1px solid #f0f0f0;
}
.header-right {
  display: flex;
  align-items: center;
  gap: 8px;
}
.user-name {
  color: #333;
  font-size: 14px;
}
.site-content {
  margin: 16px;
  padding: 24px;
  background: #fff;
  border-radius: 8px;
  min-height: calc(100vh - 64px - 48px - 32px);
}
</style>
