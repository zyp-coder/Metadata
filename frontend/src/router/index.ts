import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory('/'),
  routes: [
    {
      path: '/',
      redirect: '/modeling/domains',
    },
    {
      path: '/modeling',
      component: () => import('@/layouts/MainLayout.vue'),
      children: [
        { path: 'domains', name: 'DomainList', component: () => import('@/views/modeling/DomainList.vue'), meta: { title: '域管理' } },
        { path: 'domains/:id/tables', name: 'TableList', component: () => import('@/views/modeling/TableList.vue'), meta: { title: '表管理' } },
        { path: 'domains/:id/fields', name: 'DomainFieldConfig', component: () => import('@/views/modeling/DomainFieldConfig.vue'), meta: { title: '字段管理' } },
        { path: 'domains/:id/mappings', name: 'DomainFieldMapping', component: () => import('@/views/modeling/DomainFieldMapping.vue'), meta: { title: '关系管理' } },
      ],
    },
    {
      path: '/archive',
      component: () => import('@/layouts/MainLayout.vue'),
      children: [
        { path: '', name: 'ArchiveList', component: () => import('@/views/archive/ArchiveList.vue'), meta: { title: '档案管理' } },
        { path: 'api-management', name: 'ApiManagement', component: () => import('@/views/archive/ApiManagement.vue'), meta: { title: 'API管理' } },
        { path: 'domain-changes', name: 'DomainChangeOverview', component: () => import('@/views/archive/DomainChangeOverview.vue'), meta: { title: '变更日志' } },
        { path: 'versions', name: 'VersionManagement', component: () => import('@/views/archive/VersionManagement.vue'), meta: { title: '变更日志 — 明细' } },
        { path: ':id/consistency', name: 'ConsistencyCheck', component: () => import('@/views/archive/ConsistencyCheck.vue'), meta: { title: '一致性检查' } },
        { path: ':id', name: 'ArchiveDetail', component: () => import('@/views/archive/ArchiveDetail.vue'), meta: { title: '档案详情' } },
      ],
    },
    {
      path: '/settings',
      component: () => import('@/layouts/MainLayout.vue'),
      children: [
        { path: 'data-sources', name: 'DataSourceList', component: () => import('@/views/settings/DataSourceList.vue'), meta: { title: '数据源配置' } },
        { path: 'ai', name: 'AIConfig', component: () => import('@/views/settings/AIConfig.vue'), meta: { title: 'AI配置' } },
        { path: 'tech-functions', name: 'TechFunctions', component: () => import('@/views/settings/TechFunctions.vue'), meta: { title: '技术函数' } },
      ],
    },
  ],
})

export default router
