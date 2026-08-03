# STYLE_GUIDE — 代码结构骨架模板
> 回填打样草稿 v1（2026-07-25，第九十轮）——从存量代码提炼

## 一、前端页面骨架（Vue3 + `<script setup lang="ts">` + Ant Design Vue）
来源样本：`views/modeling/DomainList.vue`、`views/archive/ArchiveList.vue`、`views/settings/DataSourceList.vue`、`views/archive/VersionManagement.vue`

### 1. template 布局模式
```
<div>
  <div class="page-header">          <!-- flex 两端对齐，margin-bottom:16px -->
    <h2>页面标题</h2>                 <!-- h2 margin:0，font-size 20px（个别 18px）-->
    <a-button type="primary">主操作</a-button>
  </div>
  <a-card v-if="有筛选区">…a-select/a-input-search + 查询按钮…</a-card>  <!-- VersionManagement.vue -->
  <a-table :dataSource :columns :loading rowKey="id" :pagination="…">
    <template #bodyCell="{ column, record }">   <!-- 状态列用 a-tag + 颜色映射函数；操作列用 a-space + a-divider vertical -->
  </a-table>
  <a-modal v-model:open="xxxVisible" :confirmLoading="saving" @ok="handleSubmit">
    <a-form :model="formData" layout="vertical">…</a-form>
  </a-modal>
</div>
```
- 状态渲染：`statusColor(s)` / `statusLabel(s)` 用字面量对象映射（ArchiveList.vue L149-154）。
- 操作列：`<a>` 链接 + `a-divider type="vertical"` 分隔；删除链接红色 `#ff4d4f`。
- 差异对比展示配色约定：旧值红 `#ff4d4f` → 新值绿 `#52c41a`，字段名蓝 `#1890ff`（ArchiveList/VersionManagement 一致）。

### 2. script setup 组织顺序（各页面高度一致）
1. imports（vue → vue-router → ant-design-vue → @/api → @/types → @/utils）
2. refs 状态区（列表数据、loading、page/total、modal visible、saving、editingId、formData）
3. columns 定义（时间列统一 `customRender: ({ text }) => formatDateTime(text)`）
4. 纯映射函数（statusColor 等）与 computed
5. `loadData()`：`loading=true → try await api → 赋值 results/count → finally loading=false`
6. 事件处理：openCreate/openEdit（重置 formData）、handleSubmit（前置校验 message.warning → saving → try/catch/finally）、doDelete
7. 路由跳转函数 goXxx
8. `onMounted(loadData)` 收尾

### 3. 关键约定
- **分页两种模式**：管理类小列表 `:pagination="false"` + API 层 `withFullPage`（page_size=100000，见 modeling.ts L4-6）；大列表受控分页 `{ current: page, pageSize: 20, total, onChange: p => { page=p; loadData() } }`（ArchiveList.vue L14）。后端 `config/pagination.py` StandardPagination：默认 20 条，`page_size` 可覆盖，上限 100000。
- **loading 模式**：列表 `loading` / 提交 `saving`（confirmLoading）/ 导出 `exporting` / 测试 `testing`，各自独立 ref，finally 复位。
- **message 反馈**：成功 `message.success('创建成功'/'更新成功'/'删除成功')`；校验失败 `message.warning`；异常 `message.error(e.message || '操作失败')`，复杂错误优先 `extractApiError(e)`（utils/apiError.ts）。
- **危险操作两种并存**：轻量删除用 `a-popconfirm`（DomainList/DataSourceList）；重操作（删档案、回滚）用 `Modal.confirm({ okType: 'danger', onOk: async () => … })`（ArchiveList.vue L286、VersionManagement.vue L164）。
- **时间格式化**：统一 `formatDateTime`（`@/utils/date`，yyyy-MM-dd HH:mm:ss），表格列 customRender 或 bodyCell 内调用；禁止各页面自写格式化。
- **弹窗宽度档位**（实测值）：
  - 小：默认宽（≈520）/ 500px（新建档案）/ 600px（数据源表单）
  - 中：760px（刷新预检）/ 800px（试算）/ 860px（变更历史）
  - 大：1400px（记录详情）/ 1680px（公式编辑器）/ `calc(100vw - 80px)`（字段管理全屏弹窗，TableList.vue L80）
  - 抽屉：900/1000（ApiManagement）/ 70vw（去重值抽屉）
- **样式**：`<style scoped>`；`.page-header` 每页重复定义（未抽公共类，theme.css 存在但页头样式未收敛）。

## 二、前端 API 层骨架
来源：`api/index.ts`、`api/modeling.ts`、`api/archive.ts`
- 单例 axios 实例（index.ts）：`baseURL:'/api'`，timeout 30s，响应拦截器把后端 `detail/message/error` 提为 `Error.message` 并保留 `error.response` 供结构化读取。
- 每资源一个 `xxxApi` 对象常量，方法命名固定：`list/get/create/update(put)/patch/delete` + 自定义动作驼峰命名（如 `refreshPreview`、`setPrimaryField`）。
- 泛型返回：`api.get<PaginatedResponse<T>>('/xxx/', { params })`；列表页需全量时包 `withFullPage(params)`。
- 文件上传：FormData + `Content-Type: multipart/form-data`（tableApi.previewExcel/importExcel）。
- 文件下载：`responseType: 'blob'` + `downloadBlob()` 工具（archive.ts L96-108）。
- 类型放置：通用实体在 `types/index.ts`；模块专属 interface 直接定义在 api 文件内（modeling.ts 内有 20+ interface）。

## 三、后端骨架（Django + DRF，简要）
来源：`apps/modeling/views.py`、`apps/archive/views.py`、`*/serializers.py`、`*/urls.py`
- ViewSet 模式：`class XxxViewSet(viewsets.ModelViewSet)`，中文 docstring，`queryset + serializer_class`；列表/详情/创建分 Serializer（如 ArchiveListSerializer / ArchiveDetailSerializer / ArchiveCreateSerializer）。
- 自定义 action：`@action(detail=True|False, methods=[...], url_path='kebab-case')`，返回 `Response({...})`，错误 `{'success': False, 'error': msg}` + 4xx。
- Serializer 模式：ModelSerializer + 显式 `fields` 列表 + `read_only_fields`；关联名用 `serializers.CharField(source='domain.name', read_only=True)`；统计列用 `SerializerMethodField`；敏感字段 `write_only`（password）。
- 路由：每 app 一个 `urls.py`，`DefaultRouter().register(r'kebab-case', ViewSet, basename=…)`；个别函数视图直接 `path()`（domain-change-stats）。
- 模块级私有 helper 以 `_` 前缀放在 views.py 顶部（`_field_released`、`_generate_schema_from_domain`）。
