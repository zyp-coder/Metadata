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
| api（默认导出） | frontend/src/api/index.ts | 全局 axios 单例：baseURL='/api'、30s 超时、请求拦截注入 Token、401 响应拦截单点（清 token+跳登录页，C5）、错误消息拦截器（保留 error.response） | `AxiosInstance` |
| auth API 套件 | frontend/src/api/auth.ts | loginApi/logoutApi/getMeApi/getUsersApi/createUserApi/updateUserApi/resetPasswordApi/getRolesApi/createRoleApi/updateRoleApi/deleteRoleApi/getRolePermissionsApi/putRolePermissionsApi；鉴权相关调用一律走这里 | 函数集 |
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
| open_api_auth | backend/apps/archive/open_api_auth.py | 对外 API 鉴权单点（v19）：generate_api_key/hash_api_key/key_prefix/authenticate/check_grant/check_rate_limit/log_call/cleanup_old_logs；新对外端点一律经此鉴权，禁止另起炉灶 |
| build_docs | backend/apps/archive/open_api_gateway.py | 接口文档 payload 公共构建（v19）：对外 docs 端点与管理端预览共用 |
| ArchiveRecordUpdateSerializer（API 批次复用） | backend/apps/archive/serializers.py | 外部写入（change_source=api）复用同一更新器：传 data/updated_by/change_batch_id 即可，禁止复制写路径逻辑 |
| _find_dup_unmerged_field_groups / _check_domain_config | backend/apps/modeling/views.py | 同名未归并字段组检测（口径单一事实源，豁免主键/未释放字段）；域配置完整性检查 9 项（P0/P1/P2，启用闸门+check-config+dup-fields 共用） |
| permission 单点 | backend/apps/auth/permission.py | 人用字段权限过滤唯一入口（REQ-019 方向承载点）：get_field_permission(user,domain_id)→(visible,editable)（None=管理员/系统级不过滤）+ filter_schema/filter_record_data/filter_writable_data 三投影；新增过滤需求一律扩展本文件，禁止另起炉灶 |

## 六、测试基础设施
| 名称 | 位置 | 用途 |
|---|---|---|
| modeling/tests.py | backend/apps/modeling/tests.py | 27 个测试：模型导入/URL 路由/Domain CRUD/Table CRUD/DataSource/FieldGroup |
| archive/tests.py | backend/apps/archive/tests.py | 37 个测试：模型导入/URL 路由/Archive/Record/ChangeBatch/ChangeDetail/Api + **v19 OpenApiGatewayTest（13：鉴权链/投影/读写/限流）+ ApiKeyManagementTest（6：创建明文一次/裁剪/轮换/吊销/日志统计）** |
| auth/tests.py | backend/apps/auth/tests.py | 32 个测试（REQ-019）：登录体系/用户管理/角色管理/权限单点/档案三处投影端到端 |
| auth_client() | modeling 与 archive tests.py 顶部 | 全局强制登录后测试客户端工厂：superuser force_authenticate（字段权限对 superuser 不生效，既有断言零改动）；新测试文件需要已登录客户端时复制此 helper |
| check-all.ps1 | scripts/check-all.ps1 | 一键全量检查：Django check + 后端测试 + vue-tsc + vite build（注：测试计数随套件增长，现 104 条） |
| dev.ps1 | scripts/dev.ps1 | 本地前后端一键启停（start/stop/status）：后台拉起 runserver :8000 + vite :3000，日志 output/logs/，端口幂等 |
| release.ps1 | scripts/release.ps1 | 本地一键发布（第一百五十三轮）：npm run build（失败中止不提交）→git add -A→commit（-m 参数/交互输入）→push origin master |
| sync.sh | deploy/sync.sh | 服务器一键同步（第一百五十三轮，/opt/metadata/deploy）：git pull→npm run build（无 node_modules 自动 install）→docker compose up -d --build backend（启动链自动 migrate）→nginx reload |
| init_admin / init_test_account | backend/apps/auth/management/commands/ | 幂等初始化命令：init_admin 建 admin（MDM_ADMIN_PASSWORD，默认 admin123456）；init_test_account 建冒烟测试专用 smoke_test（MDM_TEST_PASSWORD，默认 test23456，挂管理员角色）——smoke 脚本一律用 smoke_test 登录，禁止用 admin | 
| pre-push hook | .githooks/pre-push | Git 推送前自动跑后端测试 + 前端类型检查 |

**测试数据工厂模式**（setUp 复用）：
```python
# 域 + 表基础数据
self.domain = Domain.objects.create(name='测试域', code='XXX')
self.table = Table.objects.create(domain=self.domain, name='测试表', code='T1')

# 档案 + 记录
self.archive = Archive.objects.create(domain=self.domain, name='测试档案')
self.record = ArchiveRecord.objects.create(archive=self.archive, data={}, created_by='system')

# 变更批次 + 明细
batch = ArchiveChangeBatch.objects.create(archive=self.archive, change_source='sync', operator='system')
detail = ArchiveChangeDetail.objects.create(batch=batch, archive=self.archive, record=self.record, record_key='K1', change_type='updated', field_changes=[...])
```
