# API参考文档

<cite>
**本文引用的文件**   
- [backend/config/urls.py](file://backend/config/urls.py)
- [backend/apps/modeling/urls.py](file://backend/apps/modeling/urls.py)
- [backend/apps/archive/urls.py](file://backend/apps/archive/urls.py)
- [backend/config/settings.py](file://backend/config/settings.py)
- [backend/config/pagination.py](file://backend/config/pagination.py)
- [backend/apps/modeling/views.py](file://backend/apps/modeling/views.py)
- [backend/apps/archive/views.py](file://backend/apps/archive/views.py)
- [backend/apps/modeling/serializers.py](file://backend/apps/modeling/serializers.py)
- [backend/apps/archive/serializers.py](file://backend/apps/archive/serializers.py)
- [backend/test_api.py](file://backend/test_api.py)
- [.ai/route_index.md](file://.ai/route_index.md)
</cite>

## 目录
1. [简介](#简介)
2. [项目结构](#项目结构)
3. [核心组件](#核心组件)
4. [架构总览](#架构总览)
5. [详细组件分析](#详细组件分析)
6. [依赖分析](#依赖分析)
7. [性能考虑](#性能考虑)
8. [故障排查指南](#故障排查指南)
9. [结论](#结论)
10. [附录](#附录)

## 简介
本文件为 MetaData002 系统的完整 API 参考文档，覆盖建模（modeling）与档案（archive）两大模块的 RESTful 接口。内容包括：
- 所有端点的 HTTP 方法与 URL 模式、请求参数与响应格式
- 认证与授权机制说明（当前版本未启用 JWT，预留扩展点）
- 分页、过滤、搜索、排序规范
- 错误码定义与错误处理策略
- Swagger/OpenAPI 文档访问方式与在线调试方法
- API 版本管理与向后兼容性策略
- 客户端集成示例与最佳实践

## 项目结构
后端基于 Django + DRF，路由通过根 urls 聚合到 apps.modeling 与 apps.archive 两个子模块；每个子模块使用 DefaultRouter 自动注册 ViewSet 端点。分页采用自定义 StandardPagination，支持 page_size 覆盖。OpenAPI 由 drf_spectacular 自动生成。

```mermaid
graph TB
A["Django 根路由<br/>config/urls.py"] --> B["建模模块路由<br/>apps/modeling/urls.py"]
A --> C["档案模块路由<br/>apps/archive/urls.py"]
B --> D["Modeling ViewSets<br/>views.py"]
C --> E["Archive ViewSets<br/>views.py"]
F["DRF 配置<br/>config/settings.py"] --> G["分页器<br/>config/pagination.py"]
F --> H["OpenAPI(Swagger)<br/>drf_spectacular"]
```

图表来源
- [backend/config/urls.py:1-9](file://backend/config/urls.py#L1-L9)
- [backend/apps/modeling/urls.py:1-20](file://backend/apps/modeling/urls.py#L1-L20)
- [backend/apps/archive/urls.py:1-21](file://backend/apps/archive/urls.py#L1-L21)
- [backend/config/settings.py:91-107](file://backend/config/settings.py#L91-L107)
- [backend/config/pagination.py:1-14](file://backend/config/pagination.py#L1-L14)

章节来源
- [backend/config/urls.py:1-9](file://backend/config/urls.py#L1-L9)
- [backend/apps/modeling/urls.py:1-20](file://backend/apps/modeling/urls.py#L1-L20)
- [backend/apps/archive/urls.py:1-21](file://backend/apps/archive/urls.py#L1-L21)
- [backend/config/settings.py:91-107](file://backend/config/settings.py#L91-L107)

## 核心组件
- 路由层
  - 根路由将 /api/* 分发至 modeling 与 archive 两个子应用
  - 各子应用使用 DefaultRouter 注册 ViewSet，自动生成标准 CRUD 路由与 action 路由
- 视图层
  - modeling：数据源、域、表、字段、分组、映射、标准字段、AI 配置、计算字段等
  - archive：档案、记录、同步日志、操作日志、版本、变更批次/明细、一致性检查等
- 序列化层
  - 针对列表/详情/创建/更新分别提供不同 Serializer，控制字段可见性与校验规则
- 分页与查询
  - 统一分页 StandardPagination，支持 page_size 覆盖
  - 内置过滤（django_filters）、搜索（SearchFilter）、排序（OrderingFilter）

章节来源
- [backend/apps/modeling/views.py:31-147](file://backend/apps/modeling/views.py#L31-L147)
- [backend/apps/archive/views.py:246-342](file://backend/apps/archive/views.py#L246-L342)
- [backend/config/pagination.py:1-14](file://backend/config/pagination.py#L1-L14)

## 架构总览
下图展示从请求进入 Django 到 DRF ViewSet 处理的整体流程，以及 OpenAPI 文档生成位置。

```mermaid
sequenceDiagram
participant Client as "客户端"
participant Django as "Django 路由"
participant Router as "DRF DefaultRouter"
participant View as "ViewSet"
participant Serial as "Serializer"
participant DB as "数据库"
participant Schema as "OpenAPI(AutoSchema)"
Client->>Django : HTTP 请求 /api/...
Django->>Router : 匹配子应用路由
Router->>View : 调用对应 ViewSet.action
View->>Serial : 序列化输入/输出
View->>DB : 读写模型数据
DB-->>View : 返回结果
View-->>Client : JSON 响应
Note over Schema : 启动时扫描 ViewSet/Serializer 生成 OpenAPI
```

图表来源
- [backend/config/urls.py:1-9](file://backend/config/urls.py#L1-L9)
- [backend/apps/modeling/urls.py:1-20](file://backend/apps/modeling/urls.py#L1-L20)
- [backend/apps/archive/urls.py:1-21](file://backend/apps/archive/urls.py#L1-L21)
- [backend/config/settings.py:91-107](file://backend/config/settings.py#L91-L107)

## 详细组件分析

### 建模模块 API（/api/）
- 数据源 DataSource
  - 端点：/api/data-sources/
  - 能力：CRUD、连接测试、列出 schema、外部表清单
  - 关键 action
    - POST /api/data-sources/test-connection/ 测试未保存的连接参数
    - GET /api/data-sources/{id}/test-connection/ 测试已有数据源连接
    - GET /api/data-sources/{id}/schemas/?include_counts=true|false
    - GET /api/data-sources/{id}/external-tables/?schema=&has_data=true|false
  - 过滤/搜索：search_fields=name,db_type,host
- 域 Domain
  - 端点：/api/domains/
  - 能力：CRUD、状态切换前置 P0 检查、配置完整性检查、主键状态检查
  - 关键 action
    - GET /api/domains/{id}/check-config/
    - GET /api/domains/{id}/pk-status/
  - 过滤：filterset_fields=status；搜索：search_fields=name,code
- 表 Table
  - 端点：/api/tables/
  - 能力：CRUD、切换启用/停用、预览数据（本地/外部）
  - 关键 action
    - PUT /api/tables/{id}/toggle-status/
    - GET /api/tables/{id}/preview-data/?limit=100
  - 过滤：domain,type,status；搜索：name,code
- 字段 Field
  - 端点：/api/fields/
  - 能力：CRUD、批量更新属性、去重检测与等价组应用、标准字段关联、刷新去重值、归档预览、分类管理
  - 典型 action（按 views 中实现）：batch-update-attributes、detect-duplicates、apply-equivalence、standard-fields、refresh-distinct、archive-preview、field-categories
- 字段分组 FieldGroup
  - 端点：/api/field-groups/
  - 能力：CRUD，层级不超过3层，防环校验
- 字段映射 FieldMapping
  - 端点：/api/field-mappings/
  - 能力：CRUD，用于多表关系映射
- 标准字段 StandardField
  - 端点：/api/standard-fields/
  - 能力：CRUD、成员管理、设置主字段、成员去重值查看
  - 关键 action：set-primary-field、members-distinct、add_member/remove_member
- AI 配置 AIConfig
  - 端点：/api/ai-config/
  - 能力：CRUD、测试连接、获取默认 prompt
- 计算字段 ComputedField
  - 端点：/api/computed-fields/
  - 能力：CRUD、公式验证/表达式验证、试算、依赖图、批量重算、可用函数/引用、技术函数插件管理（上传/卸载/重载/列表/模板）

章节来源
- [backend/apps/modeling/views.py:31-147](file://backend/apps/modeling/views.py#L31-L147)
- [backend/apps/modeling/views.py:430-503](file://backend/apps/modeling/views.py#L430-L503)
- [backend/apps/modeling/views.py:504-800](file://backend/apps/modeling/views.py#L504-L800)
- [backend/apps/modeling/serializers.py:1-200](file://backend/apps/modeling/serializers.py#L1-L200)

#### 数据源连接测试序列图
```mermaid
sequenceDiagram
participant C as "客户端"
participant V as "DataSourceViewSet"
participant Conn as "Django connections"
C->>V : POST /api/data-sources/test-connection/
V->>Conn : 动态注册临时连接别名
V->>Conn : ensure_connection()
V->>Conn : 执行 SELECT 1 或方言特定语句
Conn-->>V : 成功/异常
V-->>C : {success : true/false, message/error}
```

图表来源
- [backend/apps/modeling/views.py:80-147](file://backend/apps/modeling/views.py#L80-L147)

### 档案模块 API（/api/）
- 档案 Archive
  - 端点：/api/archives/
  - 能力：CRUD、同步 schema、立即刷新数据、预检刷新、一致性检查
  - 关键 action
    - POST /api/archives/{id}/sync-schema/
    - POST /api/archives/{id}/refresh-data/
    - GET /api/archives/{id}/refresh-preview/
    - POST /api/archives/{id}/consistency-check/
- 档案记录 ArchiveRecord
  - 端点：/api/records/
  - 能力：CRUD（create 受控，禁止人工新增），版本历史、回滚、对比
  - 关键 action
    - GET /api/records/{id}/versions/
    - GET /api/records/{id}/versions/compare/?v1=&v2=
    - POST /api/records/{id}/rollback/
- 同步日志 SyncLog
  - 端点：/api/sync-logs/
- 操作日志 OperationLog
  - 端点：/api/operation-logs/
- 记录版本 RecordVersion
  - 端点：/api/record-versions/
  - 能力：全局版本列表、定版/取消定版
- 档案 API 配置 ArchiveApi
  - 端点：/api/archive-apis/
- 变更批次 ChangeBatch
  - 端点：/api/change-batches/
- 变更明细 ChangeDetail
  - 端点：/api/change-details/
  - 能力：导出 Excel（GET /api/change-details/export/?archive=N）
- 一致性问题 ConsistencyIssue
  - 端点：/api/consistency-issues/
  - 能力：只读、批量审核（reviewed/ignored/reopen）
- 一致性检查规则 ConsistencyCheckRule
  - 端点：/api/consistency-rules/

章节来源
- [backend/apps/archive/views.py:246-342](file://backend/apps/archive/views.py#L246-L342)
- [backend/apps/archive/views.py:396-601](file://backend/apps/archive/views.py#L396-L601)
- [backend/apps/archive/serializers.py:1-200](file://backend/apps/archive/serializers.py#L1-L200)

#### 档案刷新预检工作流
```mermaid
flowchart TD
Start(["开始"]) --> Preview["调用 refresh-preview零写入"]
Preview --> CheckSchema{"schema 有变化？"}
CheckSchema --> |是| SyncSchema["调用 sync-schema含拉数+变更日志"]
CheckSchema --> |否| CheckData{"数据有变化？"}
CheckData --> |是| RefreshData["调用 refresh-data仅刷新数据"]
CheckData --> |否| EndNoop["提示「数据已是最新」"]
SyncSchema --> End(["结束"])
RefreshData --> End
EndNoop --> End
```

图表来源
- [backend/apps/archive/views.py:331-395](file://backend/apps/archive/views.py#L331-L395)

### 通用规范

#### 分页
- 类：StandardPagination
- 默认页大小：20
- 前端可覆盖：page_size（最大 100000）
- 返回结构遵循 DRF 标准分页（results、count、next、previous 等）

章节来源
- [backend/config/pagination.py:1-14](file://backend/config/pagination.py#L1-L14)
- [backend/config/settings.py:91-101](file://backend/config/settings.py#L91-L101)

#### 过滤、搜索、排序
- 过滤：django_filters，按各 ViewSet 的 filterset_fields 生效
- 搜索：SearchFilter，按 search_fields 生效
- 排序：OrderingFilter，按 ViewSet 的 ordering_fields（如未显式声明则按默认排序）

章节来源
- [backend/config/settings.py:95-99](file://backend/config/settings.py#L95-L99)
- [backend/apps/modeling/views.py:31-36](file://backend/apps/modeling/views.py#L31-L36)
- [backend/apps/modeling/views.py:430-435](file://backend/apps/modeling/views.py#L430-L435)
- [backend/apps/modeling/views.py:504-509](file://backend/apps/modeling/views.py#L504-L509)

#### 认证与授权
- 当前未启用 JWT 或 Token 认证中间件
- 鉴权留待 auth 模块接入后联动（见 route_index 依赖拓扑）
- 建议后续接入 DRF 的 Token/JWT 认证与权限类

章节来源
- [backend/config/settings.py:26-34](file://backend/config/settings.py#L26-L34)
- [.ai/route_index.md:14-22](file://.ai/route_index.md#L14-L22)

#### 错误处理与错误码
- 业务错误：通常返回 4xx（如 400 参数错误、403 无权限、404 不存在）
- 常见错误体包含 success/error 或 detail/message 等字段（因端点而异）
- 连接测试失败会返回 success=false 并附带 error 信息
- 建议客户端对非 2xx 响应进行统一解析与提示

章节来源
- [backend/apps/modeling/views.py:100-147](file://backend/apps/modeling/views.py#L100-L147)
- [backend/test_api.py:1-155](file://backend/test_api.py#L1-L155)

#### OpenAPI/Swagger 文档
- 使用 drf_spectacular AutoSchema
- 标题/描述/版本在 SPECTACULAR_SETTINGS 中配置
- 可通过 /api/schema/ 或 /swagger/（取决于部署）访问

章节来源
- [backend/config/settings.py:103-107](file://backend/config/settings.py#L103-L107)

#### API 版本管理与向后兼容
- 当前未引入 URL 前缀版本（如 /v1/）
- 建议未来通过 URL 前缀或 Header 版本控制，保持向后兼容（新增字段不破坏旧客户端）

章节来源
- [backend/config/urls.py:1-9](file://backend/config/urls.py#L1-L9)

### 请求/响应示例（节选）
以下为常用端点的示例结构与状态码说明（以路径与字段为主，避免粘贴具体代码内容）。

- 数据源连接测试（POST）
  - 路径：/api/data-sources/test-connection/
  - 请求体：{db_type, host, port, db_name, username, password}
  - 成功响应：{success: true, message: "..."}
  - 失败响应：{success: false, error: "..."}
  - 状态码：200（成功/失败均返回 200，以 body.success 区分）

- 数据源外部表清单（GET）
  - 路径：/api/data-sources/{id}/external-tables/
  - 查询参数：schema, has_data
  - 成功响应：{tables: [...], schema: "..."}
  - 失败响应：{error: "..."}
  - 状态码：200/400

- 域配置完整性检查（GET）
  - 路径：/api/domains/{id}/check-config/
  - 成功响应：{checks:[...], can_enable:boolean, p0_fail_count:int, ...}
  - 状态码：200

- 表切换状态（PUT）
  - 路径：/api/tables/{id}/toggle-status/
  - 请求体：{status:"active"|"deprecated"}
  - 成功响应：表对象（列表序列化）
  - 失败响应：{error:"..."}
  - 状态码：200/400

- 档案刷新预检（GET）
  - 路径：/api/archives/{id}/refresh-preview/
  - 成功响应：{schema_changes:{added,removed,changed,has_changes}, data_changes:{...}}
  - 状态码：200

- 档案一致性检查（POST）
  - 路径：/api/archives/{id}/consistency-check/
  - 成功响应：统计信息（checked_fields,mismatch_count,by_type,...）
  - 状态码：200

章节来源
- [backend/apps/modeling/views.py:80-147](file://backend/apps/modeling/views.py#L80-L147)
- [backend/apps/modeling/views.py:148-225](file://backend/apps/modeling/views.py#L148-L225)
- [backend/apps/modeling/views.py:454-469](file://backend/apps/modeling/views.py#L454-L469)
- [backend/apps/modeling/views.py:690-722](file://backend/apps/modeling/views.py#L690-L722)
- [backend/apps/archive/views.py:331-395](file://backend/apps/archive/views.py#L331-L395)
- [backend/apps/archive/views.py:396-601](file://backend/apps/archive/views.py#L396-L601)

## 依赖分析
- 模块依赖
  - archive 依赖 modeling（读取域/表/字段/标准字段/计算字段）
  - 两者均依赖 DRF、django_filters、drf_spectacular
- 路由依赖
  - 根路由聚合两个子应用路由
- 运行时依赖
  - PostgreSQL、Redis（缓存）
  - 可选 AI 服务（OpenAI 兼容）

```mermaid
graph LR
Modeling["建模模块<br/>apps/modeling"] --> Archive["档案模块<br/>apps/archive"]
Root["根路由<br/>config/urls.py"] --> Modeling
Root --> Archive
Settings["DRF 配置<br/>config/settings.py"] --> Modeling
Settings --> Archive
```

图表来源
- [.ai/route_index.md:14-22](file://.ai/route_index.md#L14-L22)
- [backend/config/urls.py:1-9](file://backend/config/urls.py#L1-L9)
- [backend/config/settings.py:91-107](file://backend/config/settings.py#L91-L107)

章节来源
- [.ai/route_index.md:14-22](file://.ai/route_index.md#L14-L22)

## 性能考虑
- 分页上限 max_page_size=100000，防止极端值拖垮服务
- 外部表预览限制 limit≤500，默认 100
- 去重取值缓存 distinct_values 上限 100 条，减少重复查询
- 计算字段批量重算与依赖解析（DAG）提升效率
- 外部数据库连接动态创建与及时释放，避免连接泄漏

章节来源
- [backend/config/pagination.py:1-14](file://backend/config/pagination.py#L1-L14)
- [backend/apps/modeling/views.py:723-800](file://backend/apps/modeling/views.py#L723-L800)
- [.ai/route_index.md:33-44](file://.ai/route_index.md#L33-L44)

## 故障排查指南
- 常见错误
  - 连接失败：检查数据源配置与网络连通性
  - 权限不足：确认账号具备所需数据库权限
  - 约束冲突：检查唯一约束/外键约束
  - 类型不匹配：核对字段类型与长度
- 定位方法
  - 查看后端日志与错误堆栈
  - 使用 test_api.py 快速验证基本流程
  - 打开 OpenAPI 文档比对请求/响应结构

章节来源
- [backend/test_api.py:1-155](file://backend/test_api.py#L1-L155)

## 结论
本系统提供了完善的建模与档案管理 API，涵盖数据源管理、域表字段建模、档案同步与版本控制、一致性检查与变更审计。通过 DRF 与 Spectacular 实现了标准化接口与文档自动化。后续建议补充认证授权与 API 版本化，以提升安全性与可演进性。

## 附录

### 客户端集成示例（Python）
- 基础请求封装
  - 使用 urllib/requests 发送 JSON 请求
  - 统一处理非 2xx 响应，提取 error/detail 字段
- 分页与筛选
  - 使用 page/page_size 控制分页
  - 使用 filters 与 search 参数进行过滤与搜索
- 错误处理
  - 对 4xx/5xx 进行统一捕获与提示
  - 重试策略：对瞬时错误（如网络抖动）进行有限重试

章节来源
- [backend/test_api.py:1-155](file://backend/test_api.py#L1-L155)

### 在线调试方法
- 访问 OpenAPI 文档（/api/schema/ 或 /swagger/）
- 使用浏览器或 Postman 导入 OpenAPI 进行调试
- 结合 test_api.py 快速验证端到端流程

章节来源
- [backend/config/settings.py:103-107](file://backend/config/settings.py#L103-L107)