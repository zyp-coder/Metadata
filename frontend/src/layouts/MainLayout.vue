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
          <a-avatar style="background-color: #1677ff" size="small">{{ userInitial }}</a-avatar>
          <span class="user-name">{{ displayName }}</span>
          <a-button type="link" size="small" @click="handleLogout">登出</a-button>
        </div>
      </a-layout-header>
      <a-layout-content class="site-content">
        <router-view />
      </a-layout-content>
    </a-layout>
  </a-layout>
</template>

<script setup lang="ts">
import { ref, computed, h, watchEffect, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { message } from 'ant-design-vue'
import {
  ApartmentOutlined,
  DatabaseOutlined,
  FileTextOutlined,
  AuditOutlined,
  SettingOutlined,
  TeamOutlined,
} from '@ant-design/icons-vue'
import { getMeApi, logoutApi } from '@/api/auth'
import type { AuthUser } from '@/types'

const router = useRouter()
const route = useRoute()
const collapsed = ref(false)
const selectedKeys = ref<string[]>([])
const currentUser = ref<AuthUser | null>(null)

const displayName = computed(() => currentUser.value?.display_name || currentUser.value?.username || '用户')
const userInitial = computed(() => displayName.value.charAt(0).toUpperCase())

async function loadUser() {
  // 先重置再拉取：避免账号切换（返回键复用布局实例）时菜单短暂残留上一账号的管理项
  currentUser.value = null
  try {
    const { data } = await getMeApi()
    currentUser.value = data.user
  } catch {
    // 加载失败不阻断页面
  }
}

async function handleLogout() {
  try {
    await logoutApi()
  } catch {
    // 登出失败也清除本地状态
  }
  localStorage.removeItem('token')
  message.success('已登出')
  router.push('/login')
}

// R-013: 菜单高亮随路由同步（刷新/程序化导航后保持正确高亮）
// BUG-2026-0806-01 治本：白名单从 menuItems 递归自动推导（不再手动维护，新增菜单项不会再漏登记）
function collectMenuKeys(items: any[]): string[] {
  const keys: string[] = []
  for (const it of items) {
    if (typeof it.key === 'string' && it.key.startsWith('/')) keys.push(it.key)
    if (it.children) keys.push(...collectMenuKeys(it.children))
  }
  return keys
}
// 无自身菜单项的下钻/明细页 → 映射到所属功能菜单项（最长前缀优先）
const MENU_ALIAS_PREFIX: Record<string, string> = {
  '/archive/versions': '/archive/domain-changes', // 变更日志明细页 → 变更日志
}

const menuItems = computed(() => {
  const items: any[] = [
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
  // REQ-019：权限管理仅管理员可见（后端另有 IsMdmAdmin 403 拦截）
  ...(currentUser.value?.is_admin ? [{
    key: 'auth',
    icon: () => h(AuditOutlined),
    label: '权限管理',
    children: [
      { key: '/settings/users', label: '用户管理' },
      { key: '/settings/roles', label: '角色管理' },
    ],
  }] : []),
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
  ]
  return items
})

// 高亮同步必须在 menuItems 声明之后（watchEffect 首次同步执行时访问 menuItems，提前会 TDZ 白屏）
watchEffect(() => {
  let path = route.path
  const alias = Object.keys(MENU_ALIAS_PREFIX)
    .filter(k => path === k || path.startsWith(k + '/'))
    .sort((a, b) => b.length - a.length)[0]
  if (alias) path = MENU_ALIAS_PREFIX[alias]
  const keys = collectMenuKeys(menuItems.value)
  // 取最长前缀匹配的菜单 key
  const matched = keys
    .filter(k => path === k || path.startsWith(k + '/'))
    .sort((a, b) => b.length - a.length)[0]
  if (matched) {
    selectedKeys.value = [matched]
  } else {
    // 子路由无直接菜单项时，匹配父级（如 /archive/5 → /archive）
    const parentMatch = keys.find(k => path.startsWith(k.split('/').slice(0, 2).join('/') + '/'))
    selectedKeys.value = parentMatch ? [parentMatch] : []
  }
})

const breadcrumbItems = computed(() => [
  { title: '首页' },
  ...(route.meta?.title ? [{ title: route.meta.title as string }] : []),
])

function onMenuClick({ key }: { key: string }) {
  router.push(key)
}

onMounted(() => {
  loadUser()
})
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
