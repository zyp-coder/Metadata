---
kind: frontend_style
name: 前端样式体系：Ant Design Vue + CSS 变量主题
category: frontend_style
scope:
    - '**'
source_files:
    - frontend/src/main.ts
    - frontend/src/App.vue
    - frontend/src/styles/theme.css
    - frontend/src/layouts/MainLayout.vue
    - frontend/vite.config.ts
    - frontend/package.json
---

## 1. 系统与工具
- 框架与构建：Vue3 + Vite，使用 TypeScript 与 vue-tsc 进行类型检查。
- UI 组件库：Ant Design Vue 4.x（通过 ant-design-vue 包全局注册），图标来自 @ant-design/icons-vue。
- 样式方案：CSS 自定义属性（:root 变量）+ Ant Design Token + 各组件 <style scoped> 内联样式，未引入 SCSS/Less/Tailwind 等预处理或原子化框架。
- 状态管理：Pinia（与样式无关，但影响组件结构）。

## 2. 关键文件与位置
- 入口与全局样式注入：frontend/src/main.ts（注册 Antd、导入 ant-design-vue/dist/reset.css 与 styles/theme.css）
- 全局主题配置：frontend/src/App.vue（通过 <a-config-provider :theme="themeConfig"> 集中设置 primary color、圆角等 token）
- 全局 CSS 变量：frontend/src/styles/theme.css（定义侧边栏宽度、头部高度、浅色背景与边框色等）
- 布局样式：frontend/src/layouts/MainLayout.vue（侧边栏、顶部面包屑、用户信息区、内容区的布局与局部样式）
- 构建与别名：frontend/vite.config.ts（@ 指向 ./src，开发服务器端口 3000，/api 代理到后端 8000）
- 依赖声明：frontend/package.json（明确列出 ant-design-vue、@ant-design/icons-vue、vue-router、pinia、axios、dayjs 等）

## 3. 架构与约定
- 主题分层
  - 设计令牌层：在 App.vue 中通过 Ant Design 的 token.colorPrimary、token.borderRadius 统一主色与圆角，所有 Antd 组件自动继承。
  - 全局变量层：theme.css 中以 --sidebar-width、--header-height、--color-bg-subtle、--color-border-light 等 CSS 变量提供跨组件一致的尺寸与中性色。
  - 组件样式层：各 .vue 文件内部使用 <style scoped> 编写局部样式，避免全局污染。
- 布局约定
  - 单页应用采用 MainLayout 作为根布局：左侧可折叠 a-layout-sider（宽度 220px，light 主题）、顶部 a-layout-header（面包屑 + 用户头像/名称）、中间 a-layout-content（白底卡片式内容区，带圆角与外边距）。
  - 菜单高亮通过 watchEffect 根据当前路由路径匹配最长前缀 key，保证刷新与程序化导航后仍正确高亮。
- 样式组织
  - 无独立样式目录下的模块级 CSS/SCSS，仅保留一个全局 styles/theme.css；其余样式均内聚于对应 .vue 文件的 <style scoped> 块中。
  - 颜色与尺寸以硬编码为主（如 #1677ff、#f0f0f0、#fff、#333），并通过 CSS 变量暴露少量通用值。

## 4. 约定与约束（基于代码观察到的模式）
- 全局样式入口顺序固定：main.ts 先引入 Antd 与 reset.css，再引入 styles/theme.css，确保变量覆盖生效。
- 主题色统一来源：所有 Antd 组件的主色由 App.vue 的 themeConfig.token.colorPrimary = '#1677ff' 控制，组件内不应重复定义 primary 色。
- 布局尺寸一致性：侧边栏宽度、头部高度、内容区圆角等通过 theme.css 的 CSS 变量与 MainLayout.vue 中的常量共同维护，新增页面应复用这些变量而非自行设定。
- 组件样式隔离：所有业务组件使用 <style scoped> 编写样式，避免全局类名冲突。
- 图标使用规范：统一通过 @ant-design/icons-vue 的命名导出（如 ApartmentOutlined）配合 h() 渲染为菜单项图标。
- 构建与开发约定：vite.config.ts 中 @ 别名指向 src，开发时 /api 请求代理至 http://localhost:8000，前后端联调无需修改接口地址。

## 5. 现状评估
- 样式体系简洁清晰，以 Ant Design Vue 为主题基础，辅以少量 CSS 变量与 scoped 样式，适合当前中等规模的管理后台。
- 尚未引入 SCSS/Less、CSS Modules、Tailwind 或更完善的 Design Token 系统，若未来需要多主题或更精细的设计系统治理，可在现有 theme.css 基础上扩展。