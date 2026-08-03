# REUSE_CATALOG — 可复用工具/组件清单
> 回填打样草稿 v1（2026-07-25，第九十轮）——从存量代码提炼

## 一、前端工具函数（utils/）
| 名称 | 位置 | 用途 | 签名 |
|---|---|---|---|
| formatDateTime | frontend/src/utils/date.ts | 时间格式化为 `yyyy-MM-dd HH:mm:ss`，空/非法输入返回 '' | `(input: string\|number\|Date\|null\|undefined) => string` |
| formatDate | frontend/src/utils/date.ts | 仅日期部分 `yyyy-MM-dd` | 同上 |
| extractApiError | frontend/src/utils/apiError.ts | 从 axios 错误提取后端可读消息（error→detail→message→non_field_errors→DRF 字段级），未命中返回 undefined | `(e: any) => string \| undefined` |
| formatExpressionText | frontend/src/utils/formula.ts | 计算表达式格式化：函数名大写、补右括号、超长换行缩进；FormulaEditor 与 TrialCalculation 共用 | `(raw: string) => string` |

## 二、前端 API 层基础设施（api/）
| 名称 | 位置 | 用途 | 签名 |
|---|---|---|---|
| api（默认导出） | frontend/src/api/index.ts | 全局 axios 单例：baseURL='/api'、30s 超时、错误消息拦截器（保留 error.response） | `AxiosInstance` |
| withFullPage | frontend/src/api/modeling.ts L6 | 给 params 注入 page_size=100000 拉全量（配合 pagination=false 页面）；**模块私有，未导出** | `(params?: any) => any` |
| downloadBlob | frontend/src/api/archive.ts L97 | 触发浏览器下载 blob，从 Content-Disposition 解析文件名（filename*=UTF-8''） | `(res: {data: Blob; headers?: any}, fallbackName: string) => void` |
| PaginatedResponse\<T\> | frontend/src/types/index.ts L355 | DRF 分页响应通用泛型 `{count,next,previous,results}` | interface |

## 三、前端组件
| 名称 | 位置 | 用途 |
|---|---|---|
| DomainStageNav | views/modeling/components/DomainStageNav.vue | 域建模流程导航：面包屑 + 步骤条（props: domainName/stage），建模各阶段页面共用 |
| FormulaEditor | views/modeling/components/FormulaEditor.vue | 计算字段公式编辑弹窗（1680px）：编辑/新建、校验、AI 生成、数据预览 |
| TrialCalculation | views/modeling/components/TrialCalculation.vue | 计算字段枚举试算弹窗（800px） |

注：`frontend/src/components/` 全局组件目录为空；页面级复用靠模式复制（page-header 样式、statusColor/statusLabel 映射函数在多页重复定义，尚无公共抽取）。

## 四、状态与主题
| 名称 | 位置 | 用途 |
|---|---|---|
| useModelingStore | frontend/src/stores/modeling.ts | Pinia store：仅存 currentDomain（当前域上下文） |
| theme.css | frontend/src/styles/theme.css | 全局主题样式 |

## 五、后端共享 helper（简要）
| 名称 | 位置 | 用途 |
|---|---|---|
| StandardPagination | backend/config/pagination.py | DRF 分页：默认 20 条，page_size 可覆盖，上限 100000 |
| ENGINE_MAP / json_safe / fetch_distinct_values / ensure_distinct_cache | backend/apps/modeling/distinct_cache.py | db_type→Django 引擎映射；JSON 安全转换；外部表去重取值抓取与缓存（views.py 多处复用） |
| ai_service | backend/apps/modeling/ai_service.py | AI 调用封装（自动分组/语义/公式生成等） |
| formula_engine / computed_service / custom_functions / plugin_loader | backend/apps/modeling/*.py | 公式解析执行引擎、计算字段服务、内置函数、技术函数插件加载 |
| excel_service | backend/apps/modeling/excel_service.py | Excel 预览/导入解析 |
| _field_released / _generate_schema_from_domain | backend/apps/archive/views.py L23/L45 | 档案字段释放门控判断；从域模型生成档案 schema（模块私有约定 `_` 前缀） |
