# 开发日记 - 主数据建模引擎（modeling）
> 记录 modeling 模块开发过程中的关键实现决策和技术细节。
---
## 2026-08-13 测试报告1问题：预组合关系表单改左右分栏（第一百五十六轮）
### 变更背景
用户测试报告：新建映射弹窗选「预组合关系」时没有匹配字段可选功能，且不是左源右目标设计。根因：detail 分支仍是 a-select 下拉表单，而 reference 分支已是左右分栏点选。
### 关键实现
- **左右分栏布局**（与 reference 分支同构）：
  - 左侧（span=12，内 8|16）：预组合列表（点选，名称+编码+行键小字，header 右侧「管理注册」链接）+ 关联字段列表（点选，主键 ⚿ 标 + 推荐 tag）
  - 中间（span=1）：→ 箭头
  - 右侧（span=11，内 8|16）：主表列表（点选）+ 主表字段列表（仅主键可选，非主键 field-item--disabled）
- **挂载语义保持**：源=预组合体（onDetailConfigChange 加载关联字段池=明细表字段+头表字段平铺，自动推荐可改）；目标=主表单一主键（loadTargetFields 自动选中，联合主键不支持挂载）；targetTableOptions 自动排除预组合明细表
- **新函数**：selectDetailSourceField（置 sourceFieldTouched 防自动推荐覆盖）、selectDetailTargetField（非主键点击拦截）
- **清理**：删除原 3 个 a-select（主表/预组合/关联字段）及无调用方的冗余 form-item；onDetailSourceFieldChange 保留被 selectDetailSourceField 复用
### 变更文件清单
- `frontend/src/views/modeling/DomainFieldMapping.vue`：detail 模板重写 + 2 新函数
### 验证
vue-tsc --noEmit 0 errors；已 commit+push（ab4c32c）

## 2026-08-13 测试报告3问题4批修复（第一百五十五轮）
### 变更背景
用户新测试报告3个问题：①编辑预组合弹窗改为左右分栏+JOIN类型 ②预组合管理列表搜索筛选+条件构建器支持头表字段 ③全页UXQA。按4批处理。
### 关键实现
- **批1 dcModal左右分栏+JOIN类型**：弹窗 640px→860px；顶栏关系类型 tag + JOIN type 选择器（LEFT/INNER）；主体左-中-右分栏——左侧头表列表(8col)+头表字段列表(16col)、中间↔箭头+检测按钮(padding-top:180px)、右侧明细表列表(8col)+明细表字段列表(16col)；可点选切换（新建模式）vs 只读禁用（编辑模式）；明细表已注册标记（dcRegisteredMap）；新增 selectDcHeaderTable/selectDcDetailTable 辅助函数
- **后端 JoinType**：DetailTableConfig 加 `join_type` 字段（CharField max_length=10, choices=FieldMapping.JoinType.LEFT/INNER, 迁移0034）；DetailTableConfigSerializer fields 追加 'join_type'
- **批2 dcList搜索筛选**：Alert 下方 a-input 搜索框 v-model:value="dcListSearch"；filteredDetailConfigs 按头表名/明细表名/编码过滤（全部 toLowerCase 无视大小写）
- **批3 条件构建器头表字段**：条件行首加"字段来源" a-select（明细/头表）；字段列表按 `cond.fieldSource === 'header' ? dcHeaderFields : dcSourceFields` 切换；后端存储追加 `field_source: c.fieldSource || 'detail'`；老数据回填默认 'detail'
- **批4 UXQA**：映射表加 :scroll="{ x: 1160 }" 防止列宽溢出
### 变更文件清单
- `backend/apps/modeling/models.py`：DetailTableConfig 加 join_type
- `backend/apps/modeling/migrations/0034_detailtableconfig_join_type.py`：新增迁移
- `backend/apps/modeling/serializers.py`：DetailTableConfigSerializer fields 加 join_type
- `frontend/src/views/modeling/DomainFieldMapping.vue`：dcModal 重写（左右分栏+860px+JOIN选）+ dcListSearch+filteredDetailConfigs + 条件行 fieldSource + 映射表 scroll x
### 验证
vue-tsc --noEmit 0 errors（批3/批4各验证一次）；已 commit+push（640ff5a）

## 2026-08-13 测试报告4问题修复批1（第一百五十一轮续）
### 变更背景
测试报告4个问题，分批处理。批1（本次）：Issue 1 明细检查按钮无异常时不显示 + Issue 2 ER图全屏改用浏览器 Fullscreen API。
### 关键实现
- **Issue 1 明细检查按钮**：页面加载时自动调用 loadDetailCheck()；新增 `hasDetailCheckIssues` computed 判断是否有已注册/未注册/方向可疑数据，仅当有结果时才显示按钮；无异常时按钮隐藏，减少认知负担
- **Issue 2 ER 图全屏**：`toggleErFullScreen` 改为调用 `erContainer.requestFullscreen()`（浏览器 Fullscreen API），退出全屏时通过 `fullscreenchange` 事件同步 erFullScreen 状态；Fullscreen API 不可用时回退原逻辑。映射列表 v-show 隐藏逻辑保留（全屏时复用）
### 变更文件清单
- `frontend/src/views/modeling/DomainFieldMapping.vue`：模板（badge v-if hasDetailCheckIssues）+ script（hasDetailCheckIssues computed、onFullscreenChange handler、toggleErFullScreen Fullscreen API 版、onMounted 注册监听、onBeforeUnmount 移除监听）
### 验证
vue-tsc 0 errors + django check 0 issues + 102 tests PASS

## 2026-08-13 测试报告4问题修复批2+3（JOIN类型+左右分栏）
### 变更背景
批2（Issue 3）：映射关系增加 LEFT JOIN / INNER JOIN 配置；批3（Issue 4）：新建映射弹窗左右分栏布局（960px）。
### 关键实现
- **后端模型**：FieldMapping 新增 `join_type` 字段（JoinType.LEFT/INNER，默认 LEFT，迁移 0033）
- **后端序列化器**：FieldMappingSerializer 暴露 `join_type` + `join_type_label`（get_join_type_display）
- **后端同步引擎**：
  - `_join_header_rows`（场景 A 预组合）：新增 `join_type` 参数，`'inner'` 时跳过无匹配头表的明细行
  - 调用处（line ~1333）：传 `first_fm.join_type`
  - `_upsert_dimension_via_mapping`（场景 B+D 维度表中转）：`fm.join_type=='inner'` 时跳过无匹配目标行的源行（LEFT 时保留）
  - `_sync_detail_rows` nested_sources（场景 C+D 嵌套属性）：各 nested_source 携带 FM join_type，`'inner'` 时无匹配嵌套属性则跳过明细行
- **前端 JOIN 类型选择器**：模态框顶栏「关系类型」右侧并列「JOIN 类型」下拉（LEFT JOIN / INNER JOIN）
- **前端列表列**：mappingColumns 新增 `join_type` 列，LEFT JOIN 灰色 tag，INNER JOIN 蓝色 tag
- **前端左右分栏（Issue 4）**：弹窗宽度 640px→960px；引用类型表单改为 `a-row` 左右分栏——左侧源表 select + 字段可点选列表，中间箭头，右侧目标表 select + 字段可点选列表；联合主键展示为特殊行；新增 field-panel/field-item CSS 样式
- **TypeScript 类型**：`FieldMapping` 接口新增 `join_type` / `join_type_label`
### 变更文件清单
- `backend/apps/modeling/models.py`：FieldMapping 新增 `JoinType` + `join_type` 字段
- `backend/apps/modeling/migrations/0033_fieldmapping_join_type.py`（新增）
- `backend/apps/modeling/serializers.py`：FieldMappingSerializer 加入 `join_type` / `join_type_label`
- `backend/apps/archive/views.py`：_join_header_rows 参数 + 调用处 + _upsert_dimension_via_mapping 逻辑 + _sync_detail_rows nested_sources join_type 支持
- `frontend/src/types/index.ts`：FieldMapping 接口加 join_type/join_type_label
- `frontend/src/views/modeling/DomainFieldMapping.vue`：模板(JOIN选择器+左右分栏)+脚本(form初始值+create/update payload+mappingColumns+mappingRows)+样式(field-panel/field-item)
### 验证
vue-tsc 0 errors + django check 0 issues + 102 tests 0.716s PASS
## 2026-08-11~12 内网 Docker Compose 部署（第一百四十六轮）
### 变更背景
局域网开放测试失败——对方 ping 不通用户电脑（公司网络 VLAN 隔离）。用户决定部署到公司内网 Linux 服务器。
### 关键实现
- **Nginx 配置**（frontend/nginx.conf）：serve 前端 build 产物 + 反向代理 /api（含 Host/X-Real-IP 透传）+ SPA fallback + 静态资源 7d 缓存
- **生产 Docker Compose**（deploy/docker-compose.yml）：4 服务——nginx:alpine（80）、backend:gunicorn（8000 仅本机）、postgres:15、redis:7-alpine；启动链：migrate --noinput → loaddata data_dump.json → init_admin → collectstatic --noinput → gunicorn
- **生产环境变量**（deploy/.env）：DEBUG=0 + DB_PASSWORD + ALLOWED_HOSTS 占位
- **Dockerfile** 补 CMD gunicorn（docker-compose 的 command 覆盖此默认值）
- **数据导出**：dumpdata --natural-foreign 导出 138 条业务记录
### 变更文件清单
- `frontend/nginx.conf`（新增）
- `deploy/docker-compose.yml`（新增）
- `deploy/.env`（新增）
- `deploy/data_dump.json`（新增，.gitignore）
- `backend/Dockerfile`（修改）
- `.gitignore`（修改）
### 验证
data_dump.json 138 条记录覆盖全业务模型；docker-compose 语法验证通过
### 所需后续步骤
① 服务器安装 Docker + docker-compose；② 修改 deploy/.env 填入实际 IP 和密码；③ `cd frontend && npm ci && npm run build`；④ `cp -r dist/ ../deploy/nginx/html/ && cd ../deploy && docker compose up -d`；⑤ 浏览器验证 http://服务器IP

### 实际部署执行（第一百四十六轮续，2026-08-12）
- **服务器**：Alibaba Cloud Linux 3（dolphin-1），IP 172.18.148.11
- **Docker**：yum 安装 Docker CE + docker compose
- **Node.js**：v16→v20.20.2（Vite 5 兼容性修复，nodesource setup_20.x）
- **前端构建**：npm ci + npm run build 成功（11.57s，3583 modules）
- **数据导入**：138 条业务记录全量迁移到 PostgreSQL
- **修复清单**：
  - requirements.txt 补 django-cors-headers（local_settings 引用但缺包）
  - settings.py 补 STATIC_ROOT（生产 collectstatic 必需）
  - data_dump.json UTF-16→UTF-8 转码（PowerShell > 重定向的经典坑）
  - .env ALLOWED_HOSTS 补 127.0.0.1（容器内 curl 需本地回环）
- **启动成功**：migrate → loaddata 138 ➔ init_admin（admin 已存在）→ collectstatic 153 → gunicorn 4 workers @ 0.0.0.0:8000
- **全链路验证**：Nginx(80) → Backend(8000) 登录 API 返回正常 token JSON
- **访问地址**：http://172.18.148.11（浏览器打开即可登录）
- **账号**：admin / admin123456
## 2026-08-11 关系管理列表直观性改进（第一百四十四轮，UX 方案A）
### 变更背景
用户反馈关系管理列表「明细表和主表、普通表的关系不直观」。分析现状：detail 行只显示明细表名（预组合信息丢失）、主表地位无体现、普通关联是裸灰字区分度低。用户选方案A（表格增强）。
### 关键实现
- **后端 serializers.py**：FieldMappingSerializer 新增 `detail_config_combo`（SerializerMethodField）——预组合全名「头表名 + 明细表名」（旧注册无头表时只返回明细表名），供列表展示
- **前端 DomainFieldMapping.vue**：
  - 源表列：detail 且有 combo 时显示预组合全名 + 蓝色小标「明细子表（预组合）」（两行），否则原表名（列宽 150→260）
  - 目标表列：目标表=域主表（domainTables 中 is_primary）时追加金色「主表」tag（primaryTableId computed）
  - 关系类型列：普通关联由裸灰字升级为灰色 tag「普通关联」
  - detail 行浅蓝底：a-table :row-class-name="mappingRowClassName" + scoped 样式 `:deep(.mapping-row-detail) > td { background: #f0f7ff !important }`
### 变更文件清单
- `backend/apps/modeling/serializers.py`：detail_config_combo 字段
- `frontend/src/views/modeling/DomainFieldMapping.vue`：模板（row-class-name/三列渲染）+ script（mappingRowClassName/primaryTableId/mappingRows 透传 combo）+ style
### 验证
后端 APIClient 实测 6 条映射：id=3 combo='EDS_K3_销售价目表 + EDS_K3_销售价目表明细'✓、id=8/9 同格式✓、id=4（旧范式 detail_config 空）combo=None 如实✓、reference 无 combo✓；vue-tsc 0 errors + django check 0 issues；浏览器实测（HMR 后重抓）：4 行 detail 浅蓝底 rgb(240,247,255)✓、预组合名+小标✓、目标表=主表 3 行金色「主表」tag✓、普通关联 tag✓；首次抓取未见 tag 为 HMR 重渲染时序（二次抓取确认）
### 数据现状变化（核对）
映射列表现有 6 条（id=3/4/5/7/8/9）：用户新增 id=7（物料.MATERIAL_ID+MATERIAL_NO→物料信息主表，与 id=5 合并为联合字段行）、id=8（物料分组+物料分组→物料信息主表）、id=9（销售价目表+销售价目表明细→物料信息主表）；域主表已由「物料」切换为「EDS_K3_物料信息主表」（用户操作）；id=8 预组合头表=明细表同名（物料分组），数据如实显示
### 遗留
id=4 旧范式 detail 映射仍无预组合名（detail_config 为空，如实显示浅蓝底+原表名）；截图存档超时未成（DOM 证据已足）

## 2026-08-11 字段映射唯一性报错修复（第一百四十三轮，Bug 六步+方案A）
### 变更背景
用户建「物料主表和明细表的关系」（普通关联：物料.MATERIAL_ID → 物料信息.MATERIAL_ID）报「字段 source_table, source_field, target_table, target_field 必须能构成唯一集合」——四元组与存量映射 id=5 完全重复（用户不知已存在），DRF 默认模板不指明占用方。同类问题（第一百四十二轮遗留待办）确认修复，用户选方案A（后端友好+前端预检）+本次只修字段映射（其余 7 处同类下批）。
### 关键实现
- **后端 serializers.py**：新增 `FieldMappingUniqueValidator(UniqueTogetherValidator)`（与 DetailTableUniqueValidator 同模式），Meta.validators 追加；冲突报错「该关系已存在：源表.源字段 → 目标表.目标字段（ID=N，关系类型=xx）；同一组源/目标字段只能建立一条关系，如需修改请在关系管理列表中找到该关系并编辑」；编辑模式排除自身（exclude pk）；普通关联与 detail 挂载共用序列化器一处覆盖
- **前端 DomainFieldMapping.vue**：handleSubmit 前新增 `checkMappingDuplicates()` 预检——四元组（composite 联合主键展开逐对）与 mappings 现有数据比对（排除 editingMappingIds 自身），重复则 message.warning 指明占用关系并 return 不发请求；普通关联+detail 挂载共用 handleSubmit 一处覆盖
### 变更文件清单
- `backend/apps/modeling/serializers.py`：FieldMappingUniqueValidator + Meta.validators
- `frontend/src/views/modeling/DomainFieldMapping.vue`：checkMappingDuplicates + handleSubmit 预检调用
### 验证
后端 APIClient 实测 6 项全过（重复 id=5 用户场景→400 友好/重复 id=3 detail 挂载→400 友好/全新组合→201+204 清理/编辑自身→200 不误伤/编辑改撞他人→400 友好）；vue-tsc 0 errors + django check 0 issues；浏览器实测：登录→关系管理→新建映射选物料.MATERIAL_ID→物料信息.MATERIAL_ID→OK→message.warning「该关系已存在…（ID=5）」拦截、弹窗保持打开未提交
### 遗留
其余 7 处 unique 约束（Table/Field/StandardField/ComputedField/ConfigTable 编码、FieldOption 枚举值、Domain 编码、DataSource 名称）仍为 DRF 默认模板，用户选择下批处理；存量 id=4 detail 映射 detail_config 为空（旧范式遗留，编辑会触发必填校验，待用户遇到再处理）

## 2026-08-11 子表注册唯一性报错修复（第一百四十二轮，Bug 六步+方案A）
### 变更背景
用户新建子表注册选「物料分组+物料分组_L」点 OK 报「字段DOMAIN，TABLE，必须能构成唯一集合」——明细表已被现有注册占用（域2 已有价格组合/分组组合两个注册），且前端无任何已注册提示、后端报错为 DRF 默认模板、注册管理无列表/编辑入口。用户确认方案A（禁选+友好提示+列表管理）。
### 关键实现
- **后端 serializers.py**：新增 `DetailTableUniqueValidator(UniqueTogetherValidator)`（`Meta.validators` 追加），冲突时返回友好错误「明细表『xx』已注册为组合『头+明细』（ID=N）；一个明细表只能注册一次，如需修改请在「管理注册」中编辑该组合，或选择其他明细表」；编辑模式排除自身不误伤；原 validate()（关联字段归属/必填）不受影响
- **前端 DomainFieldMapping.vue**：
  - 新建弹窗明细表下拉：`dcRegisteredMap` computed（{tableId: '头表名+明细表名'}），已注册项显示橙色「已注册（xx组合）」标记并禁选（:disabled）
  - 「管理注册」（挂载弹窗内）与顶部「子表注册」按钮统一改为打开**列表管理弹窗**（复活死变量 dcListModalVisible，新增 dcColumns 6 列：预组合/头↔明细关联/行键/代表行排序/挂载/操作）
  - 列表操作：编辑→`openDetailConfigEdit(cfg)`（回填表单+Promise.all 并行加载头/明细字段池，头表/明细表/关联字段禁改，行键/排序/条件可改）；删除→`removeDetailConfig(cfg)`（popconfirm 挂载数>0 时提示「删除后 N 个映射将变为未挂载」——detail_config FK=SET_NULL 不级联，安全）
  - 原 `openDetailConfigManager` 拆分为 `openDetailConfigList` + `openDetailConfigCreate`（挂载弹窗新建按钮调用）
### 变更文件清单
- `backend/apps/modeling/serializers.py`：DetailTableUniqueValidator + Meta.validators
- `frontend/src/views/modeling/DomainFieldMapping.vue`：模板（明细表下拉/列表弹窗/按钮指向）+ script（dcRegisteredMap/dcColumns/openDetailConfigList/openDetailConfigCreate/openDetailConfigEdit/removeDetailConfig）
### 验证
- 后端实测 5 项（APIClient 真实请求）：重复分组组合→400 友好错误指明 ID=3✓；重复价格组合→400✓；全新组合（物料+物料信息）→201 后 204 清理✓；编辑 id=3 自身→200 不误伤✓；关联字段归属校验→400 未破坏✓
- vue-tsc 0 errors；django check 0 issues
- 浏览器实测 4 项：顶部子表注册→列表弹窗（2 组合+挂载数+编辑/删除）✓；新建弹窗明细表下拉已注册标记+禁选（2 项 YES）✓；列表编辑→回填+字段池加载+4 select 禁用✓；挂载弹窗管理注册→列表弹窗✓
### 遗留
- 同类点：FieldMapping 唯一性（source_table/source_field/target_table/target_field）仍为 DRF 默认模板，待用户确认后同类修复（已记 debug-diary）
- 删除 popconfirm 的 hover 交互未能浏览器模拟（browser-use 限制），其 DELETE API 已实测 204
## 2026-08-11 明细致子表交互改造第三轮「预组合=头表+明细表」实施+三缺陷修复（第一百四十一轮）
### 变更背景
用户纠正第二轮语义：「子表=预组合=头表+明细表先组合（价格头+价格明细、分组头+分组明细），再用预组合体关联主表」（§11.1 全流程锁定 7 条，constitution 已登记）。本轮实施：DetailTableConfig 三字段扩展 + 同步引擎平铺 JOIN + 挂载/注册弹窗双表形态，浏览器实测发现 3 缺陷+1 UI 问题全部修复。
### 关键实现
- **DetailTableConfig 扩展**（迁移0032）：table=明细表 + header_table FK→Table + header_link_field/detail_link_field FK→Field（头↔明细关联），unique_together=(domain, table)
- **detect-header-link action**：头↔明细关联字段自动检测（同名校验→FID 后缀匹配→头表 PK 兜底），注册弹窗「检测」按钮
- **同步引擎 _join_header_rows**（archive/views.py）：头表全量拉取→hindex 内存 JOIN→明细行并入 `__hdr__{物理列名}` 前缀字段（与明细字段重名不冲突）；同值多行取排序后最后一条（确定性，与 nested_sources 一致）；头表查询失败/未命中降级保留纯明细行不阻断同步
- **归属链路三处配套**：physical_to_schema 与 pk_physical_to_schema 均纳入 `tbl_id == header_table_id`（头表物理列→主键 schema code）；_record_key_for_row 支持 `__hdr__` 前缀回退（先查本表列再查 __hdr__ 列）；detail_data 构建时 `is_hdr = col_name.startswith('__hdr__')` 剥前缀
- **挂载弹窗预组合形态**（DomainFieldMapping.vue）：关系类型置顶，detail 时主表下拉→预组合下拉（头表名+明细表名）→关联字段自动推荐可改（字段池=头字段+明细字段平铺）；配置摘要展示 ID↔FID/行键自动检测/排序；保存先建映射再 PATCH detail_config
- **注册弹窗双表形态**：头表+明细表+头↔明细关联字段三件套 + 行键/排序/条件
### 本轮修复的缺陷（浏览器实测发现）
1. **前端字段池缺头表字段**：loadSourceFields 只加载 cfg.table（明细表），头表字段（GROUP_ID）无法作关联键 → 修复：detail+header_table 时并入头表字段（复测 12 字段=6 明细+6 头表）
2. **后端 pk_physical_to_schema 只收明细表**：头表字段作关联键时 pk 映射为空→明细同步整体跳过 → 修复：纳入 header_table_id
3. **后端 _record_key_for_row 不认 __hdr__ 前缀**：即使映射纳入头表也匹配不到平铺行 → 修复：__hdr__ 回退查找
4. **UI placeholder [object Object]**：`:placeholder='[...]'` Vue 把 JSON 字符串当对象 → 修复：去 : 绑定
### 验证
- django check 0 issues、vue-tsc 0 errors；迁移 0032 OK
- 浏览器实测：注册弹窗双表形态✓ / 挂载预组合下拉✓ / 关联字段推荐 MATERIAL_ID✓ / 手动改选 GROUP_ID✓ / 保存 201×2+列表 2 行✓ / 删除 Modal.confirm+DELETE✓ / 持久化刷新保留✓（3/6 表已配置）
- 平铺行实测（backend/scripts/test_precombine.py，真实外部数据）：价格组合 239,504 行明细平铺每行 35 明细键+6 头字段（__hdr__PK_ID/ID/LOCALE_ID/NAME），头字段命中 3/3；分组组合 __hdr__GROUP_ID 存在、非前缀缺失→归属匹配取 __hdr__ 值；pk 纳入判断 header_table_id=4==True
- 存量数据：DetailTableConfig id=2（价格组合）/id=3（分组组合），FieldMapping 2 条 detail 挂载（MATERIAL_ID→MATERIAL_ID、GROUP_ID→MATERIAL_ID）
### 遗留
- P2 建议：字段池 FID 重名（头表 PK FID + 明细表 FID）下拉显示歧义（功能无碍，field id 区分，显示可加「头表」标记）
- 子表注册弹窗「选择+自动检测+保存」交互未能在浏览器完全走通（browser-use 模拟事件受限，antd Select focus 链断裂），弹窗形态已验证+注册接口后端实测 201
---
## 2026-08-06 第一百二十七轮：批4 整改（R-059 字段管理 modal→大抽屉 + R-061 分组弹窗表单）
### 变更
- TableList.vue：字段管理近全屏 modal（calc(100vw-80px)，footer=null）→ a-drawer 65vw + #footer「关闭」固定底栏；双 Tab/主键标识区/fieldTableScrollY/两入口（openFieldModal 函数+路由参数自动打开）全部不动
- DomainFieldConfig.vue：window.prompt（新建/重命名分组）→ 共用 480px a-modal 表单（空名禁用确认、重命名预填原名、未改动静默关闭零请求）
### 关键教训（antdv 4.x，跨项目通用）
声明式 a-modal 的 @ok 不消费 handler 返回值——Modal.js handleOk 仅 emit('ok')，Promise 自动关闭/loading 仅 Modal.confirm 命令式 API 有。
v1 @ok 返回 Promise → 提交成功后弹窗不关闭且取消/X 均无效（实测拦截）。v2 修复：请求 .then() 内显式置 open=false，catch 不重抛（否则 console unhandled rejection + Vue warn）。
### 验证
- vue-tsc -b --force 0 errors
- Browser：R-059 6/6 PASS（1257 视口实测精确 65vw）+ R-061 v2 7/7 PASS（含 300 字超长名 400 失败保持打开），console 0 error；测后恢复域 11 原 7 分组
---
## 2026-07-25 计算字段功能全栈实现（REQ-017，第三十五轮）
### 变更背景
实现 REQ-017「计算字段配置与自动计算」完整功能，包含10个子任务：模型扩展、公式引擎、计算服务、后端API、档案集成、前端API+组件+视图增强。
### 关键实现决策
#### 公式引擎架构（递归下降解析器）
自定义词法分析器(Lexer) + 递归下降语法分析器(Parser) + AST求值器(Evaluator)：
- **Lexer**：分词 NUMBER/STRING/FIELD_REF/FUNC_NAME/OP/COMMA/LPAREN/RPAREN/EOF
- **Parser**：expression → comparison → additive → multiplicative → unary → primary，优先级正确
- **字段引用**：`{表名.字段名}` 语法，正则 `\{([^.}]+)\.([^}]+)\}`
- **内置函数**：IF/CONCAT/LEFT/RIGHT/LEN/UPPER/LOWER/TRIM/ROUND/ABS/MAX/MIN/SUM/AVG/COUNT/NOW/TODAY/YEAR/MONTH/DAY/IFERROR/SWITCH/IFS/VLOOKUP/SUMIFS/COUNTIFS/MAXIFS/MINIFS
```python
# formula_engine.py 核心结构
class Lexer:   # 分词器
class Parser:  # 递归下降 AST 构建
class Evaluator:  # AST 求值 + 字段上下文注入
def parse_references(expression):  # 从表达式提取所有 {表.字段} 引用
def validate_formula(expression, available_fields):  # 语法+引用合法性校验
def evaluate_formula(expression, field_values):  # 完整执行
```
#### DAG 依赖管理
- **拓扑排序**：Kahn's algorithm 确定 execution_order
- **循环检测**：DFS 三色染色法（白/灰/黑），灰→灰即循环
- **依赖解析**：保存时自动解析 parsed_references → 挂靠 depends_on(M2M→Field) + depends_on_computed(M2M→self)
```python
# computed_service.py
def resolve_dependencies(domain_id):  # 全域拓扑排序+执行顺序写入
def detect_cycle(domain_id, new_cf_id, new_depends_on_computed_ids):  # 含假设节点的循环检测
def batch_recalculate(domain_id):  # 按拓扑序全量重算所有 active 档案记录
def recalculate_affected(domain_id, record_id, changed_field_codes):  # 单记录受影响字段实时重算
```
#### 双触发重算策略
1. **sync-schema 后批量**：`archive/views.py` 数据拉取完成后调 `batch_recalculate(domain.id)`
2. **记录编辑实时**：`archive/serializers.py` ArchiveRecordUpdateSerializer.update() 中调 `recalculate_affected()`，失败不阻塞保存
#### 枚举试算（笛卡尔积）
后端 `trial_calculate` action：
- 从 `field.distinct_values` 自动填充参数候选
- 生成笛卡尔积（上限1000组合）
- 逐组求值返回 `{params, result, error}` 列表
#### 前端组件架构
- **FormulaEditor.vue**（268行）：公式编辑器 modal，含 code/name/output_type 表单 + formula textarea 实时验证 + 函数面板 + 字段引用选择器 + 光标插入
- **TrialCalculation.vue**（246行）：枚举试算 modal，含参数表格 + 自动枚举/手动参数 + 结果表格
- **DomainFieldConfig.vue 增强**：计算字段视图增加工具栏（新建/依赖图/批量重算） + 表格列增强（公式摘要/输出类型/执行顺序/操作按钮）
### 模型变更
```python
# ComputedField 新增字段（migration 0020 已含骨架，本轮扩展）
class ComputedField(models.Model):
    depends_on = models.ManyToManyField('Field', blank=True)  # 物理字段依赖
    depends_on_computed = models.ManyToManyField('self', symmetrical=False, blank=True)  # 计算字段间依赖
    parsed_references = models.JSONField(default=list)  # [{table, field}]
    execution_order = models.IntegerField(default=0)  # 拓扑序
    output_type = models.CharField(max_length=20, default='text')  # text/number/date/boolean
```
### 新增文件
| 文件 | 职责 |
|------|------|
| `backend/apps/modeling/formula_engine.py` | 公式解析+求值引擎（Lexer/Parser/Evaluator） |
| `backend/apps/modeling/computed_service.py` | 依赖解析/循环检测/批量重算/实时重算 |
| `frontend/src/views/modeling/components/FormulaEditor.vue` | 公式编辑器组件 |
| `frontend/src/views/modeling/components/TrialCalculation.vue` | 枚举试算组件 |
### 影响范围
| 文件 | 变更类型 |
|------|----------|
| `backend/apps/modeling/models.py` | Edit: ComputedField 扩展 5 个字段 |
| `backend/apps/modeling/views.py` | Edit: ComputedFieldViewSet +6 actions |
| `backend/apps/modeling/serializers.py` | Edit: ComputedFieldSerializer 扩展 |
| `backend/apps/archive/views.py` | Edit: schema含计算字段 + sync后重算 |
| `backend/apps/archive/serializers.py` | Edit: 记录保存时触发实时重算 |
| `frontend/src/api/modeling.ts` | Edit: +6接口+6方法 |
| `frontend/src/views/modeling/DomainFieldConfig.vue` | Edit: 计算字段视图增强 |
### 验证
- **Django check**：0 issues
- **vue-tsc**：0 errors（修复1个 TS7053 隐式 any 类型错误）
- **Migration**：0020 已含 ComputedField 骨架，扩展字段通过 M2M 和 JSONField 无需新迁移
---
## 2026-07-21 关系管理功能增强
### 变更背景
用户提出 6 项关系管理功能增强需求 + 1 项列表数据模型修正：
1. 恢复 n/m 表已配置进度标识
2. 映射列表主键字段黄色标识
3. 目标字段也支持联合主键虚拟选项
4. 目标表下拉排除源表
5. ER图联合主键显示为虚拟字段
6. ER图字段中文名优先展示（两行布局）
7. **列表改回一行=一条映射关系**（不再按表对合并）
### 关键实现决策
#### 列表数据模型修正
**问题**：之前按 `(source_table, target_table)` 分组，导致同一对表的多条映射被合并为一行。
**修正**：`mappingRows` computed 直接 `mappings.value.map()` 每条映射一行，附带 `is_source_pk` / `is_target_pk` 标记。
```typescript
const mappingRows = computed(() => {
  const pkFieldIdsByTable: Record<number, Set<number>> = {}
  if (pkStatusData.value) {
    for (const t of pkStatusData.value.tables) {
      pkFieldIdsByTable[t.table_id] = new Set(t.pk_fields.map((f: any) => f.id))
    }
  }
  return mappings.value.map((m) => ({
    ...m,
    is_source_pk: pkFieldIdsByTable[m.source_table]?.has(m.source_field) ?? false,
    is_target_pk: pkFieldIdsByTable[m.target_table]?.has(m.target_field) ?? false,
  }))
})
```
#### ER图联合主键虚拟字段
当表有 2+ PK 字段时，创建虚拟字段 `{ id: 'composite_pk', is_composite: true, _pkFieldIds: [...] }`，替换 individual PK 字段显示。边去重用 `drawnCompositeEdges` Set，同一对表只画一条边。
#### X6 v2 锚点比例值
`top` 锚点的 `dx/dy` 是比例值(0-1)，不是像素值。通过阅读源码 `node_modules/@antv/x6/lib/registry/node-anchor/bbox.js` 确认：`NumberExt.normalizePercentage(options.dx, bbox.width)` 中数值型参数直接乘以 bbox 宽/高。
```typescript
anchor: { name: 'top', args: { dx: 0.5, dy: sourceFieldY / sourceNodeHeight } }
```
#### 两行字段显示
ER 图字段行从单行改为两行布局：
- `.er-f__name-cn`（12px，中文名）
- `.er-f__name-en`（10px 灰色等宽，英文名）
### 影响范围
- **文件**：`frontend/src/views/modeling/DomainFieldMapping.vue`（纯前端，无后端变更）
- **波及模块**：无（改动完全封闭在单文件内）
- **编译验证**：vue-tsc 零错误
---
## 2026-08-04 管理表引导提示 + AI建立关系功能（第一百零二轮）
### 变更背景
两项交互增强：①管理表页面增加引导提示用户设置主表和数据主键；②关系管理页面 AI 建立关系功能从占位符升级为完整实现。
### 关键实现决策
#### 任务1：TableList 引导提示
- **顶部 Alert 横幅**：`a-alert type="info"` 展示主表/主键未配置的引导信息
  - 无主表时显示「⚠️ 尚未设置主表：请在「主表」列点击「设为主表」，主表是档案数据合并的基准」
  - 有表未设主键时显示「🔑 N个表未设置主键（表名...）：点击主键列的「设置主键」按钮，主键是档案记录匹配的唯一标识」
- **表格内空状态引导**：主键列未设置时显示金色「点击设置主键」链接（点击打开字段管理弹窗）
- **computed 属性**：`hasPrimaryTable` / `tablesWithoutPk` / `setupGuideMessage`
#### 任务2：AI 推断字段映射关系
- **后端 ai_service.py**：新增 `infer_mappings(domain_id)` 函数
  - 收集域内所有活跃表和字段
  - 启发式匹配：字段编码精确匹配（不同表间同名字段，confidence=0.6）
  - LLM 分析：构建表结构摘要，调用 AI 分析表间字段映射关系，返回带置信度的建议
  - 合并策略：AI 建议优先，启发式补充，去重后返回
- **后端 views.py**：`FieldMappingViewSet.infer_mappings` action（POST /field-mappings/infer-mappings/）
  - 参数：`{ domain: number }`
  - 返回：`{ suggestions: [...], count: number }`
  - 每条建议包含：source/target 的 table_id、field_id、table_name、field_code、field_name、is_primary_key、confidence、reason
- **前端 modeling.ts**：`fieldMappingApi.inferMappings(domainId)` 方法
- **前端 DomainFieldMapping.vue**：
  - AI 建议弹窗（900px）：表格展示建议列表，支持勾选
  - 置信度标签：>=80% 绿色、>=60% 橙色、<60% 灰色
  - 默认选中置信度 >= 0.7 的建议
  - 批量创建：逐条调用 fieldMappingApi.create，汇总成功/失败数量
### 影响范围
- **文件**：
  - `frontend/src/views/modeling/TableList.vue`（引导提示）
  - `frontend/src/views/modeling/DomainFieldMapping.vue`（AI 建立关系交互）
  - `frontend/src/api/modeling.ts`（新增 inferMappings API）
  - `frontend/src/types/index.ts`（Table 接口加 primary_keys）
  - `backend/apps/modeling/ai_service.py`（新增 infer_mappings 函数）
  - `backend/apps/modeling/views.py`（新增 infer-mappings action）
- **波及模块**：无（均在 modeling 模块内，不影响 archive）
- **编译验证**：vue-tsc 0 errors，45 测试全 PASS
## 2026-08-05 域配置检查新增第 9 项：多表同名未归并字段告警（第一百一十二轮）
背景：BUG-2026-0805-01（同名未映射列写入越权造成假变更风暴）遗留建议落地——在配置层提前曝出隐患土壤。
### 变更内容
- `_check_domain_config` 8 项 → 9 项，新增 P1 级 `multi_table_dup_field_merged`（多表同名字段已归并）：
  - 扫描域内各活跃表的活跃字段，按物理列 code 分组
  - 同名存在于 ≥2 张表且未全部挂靠同一标准字段 → warn（不阻断启用，与第一百零八轮「警告不阻断」决策一致）
  - 豁免：主键字段（跨表记录匹配结构性必需）、`release_to_concept=False` 字段（用户已显式排除）
  - message 列出前 5 组同名字段及其所属表，提示归并到同一标准字段或将多余列设为不释放
- check-config API 与启用闸门（perform_update P0 前置拦截）自动包含新项；前端 DomainList 配置检查弹窗为通用动态渲染，无需改动
### 变更文件
- `backend/apps/modeling/views.py`：`_check_domain_config` 新增 P1-4 检查项
- `backend/apps/modeling/tests.py`：新增 DomainConfigDupFieldTest（5 用例：未归并 warn/已归并 pass/主键豁免/未释放豁免/单表不告警）
### 验证
- 新增 5 用例全 PASS；modeling+archive 定向回归 51/51 PASS
- 真实数据实测：域#11（门店，即 BUG-2026-0805-01 涉事域）命中 4 组同名未归并字段 warn（含 D_CHECK_DATE/N_AREA/STORE_VERSION）；域#12/#13 pass
## 2026-08-05 字段属性配置页同名未归并字段标记+告警条（第一百一十三轮）
背景：用户要求在字段属性配置处直接定位同名冲突（那里支持改名）；第112轮域配置检查只能整体告知，本页补齐"定位到行"能力。
### 变更内容
- 后端口径单点化：第112轮内联检测逻辑提取为 `_find_dup_unmerged_field_groups(domain)`（返回 [{code, table_names, field_ids}]），配置检查 P1-4 与新增接口共用（方向承载点：该函数即口径单点）
- 新增端点 `GET /api/domains/{id}/dup-fields/`（DomainViewSet.dup_fields）
- 前端 DomainFieldConfig.vue：
  - 属性配置 Tab 顶部橙色告警条（N 组冲突 + 处置指引 + 「只看冲突字段」过滤开关）
  - 冲突行编码旁橙色「同名」角标 + tooltip（列出其他冲突表名 + 改名区分/归并/不释放三选处置指引）
  - 字段分类 Tab 基础字段/未分配字段表格 code 列同标记（按 field_id 精确匹配）
  - AttrRow 新增 physical_field_ids（equiv 行按成员 id 匹配，避免标准编码≠物理编码漏检）；loadData/refreshAllData（改名/归并后）自动刷新冲突数据
- api/modeling.ts：domainApi.dupFields
### 验证
- 后端：新增 dup-fields 端点实测用例（APIClient 200 + code/table_names/field_ids 断言）；回归 52/52 PASS
- 真实请求实测：运行中后端 GET /api/domains/11/dup-fields/ → 200，返回 4 组（D_CHECK_DATE field_ids=[183,193] 即 BUG 涉事字段对）
- vue-tsc 0 errors；浏览器实测（localhost:3003 域#11）4/4 通过：告警条文案完整/同名角标+tooltip/只看冲突过滤剩 3 行（REMARK 在未分配分类属预期）/未分配表格 5 个角标覆盖 4 组冲突；控制台无报错。截图 verify_attr_1~4_*.png
## 2026-08-05 同日更正：同名检查口径收敛为仅档案字段（用户纠正）
用户指出：配置检查里的检查项只包含已维护到档案的字段，未分配/未分组字段不包含——与第一百零八轮已定决策（配置检查范围仅 archive_category='base'）对齐，第112/113轮实现时未引用该决策属口径遗漏。
### 变更
- `_find_dup_unmerged_field_groups` 增加 `archive_category='base'` 过滤（口径单点，配置检查 P1-4 与 dup-fields 接口同步生效）
- 前端移除字段分类 Tab（基础/未分配表格）的「同名」角标（分类表含大量非档案字段，标记会误导），仅保留属性配置 Tab 的告警条+角标
- 测试：新增 2 用例（未分配同名不告警/混合范围仅档案侧计数），原用例补 archive_category='base'
### 验证
- 回归 54/54 PASS；vue-tsc 0 errors
- 真实域#11 复测：dup-fields 返回空 groups（原 4 组冲突均为未分配字段，档案范围内确无同名冲突），属性配置页告警条/角标已消失（浏览器 DOM 复核 .ant-alert=0、无橙色角标）
教训：新增检查项前必须核对既有范围决策（第一百零八轮口径），配置检查类功能默认继承「仅档案字段」范围。

## 2026-08-13 测试报告8问题4批修复（第一百五十四轮）
### 变更背景
测试报告8个问题，按4批处理：批1 #6（关系类型选项改名）+ #2（ER按钮改名加粗）+ #3（dcColumns移除行键/挂载列）；批2 #5（表选择由下拉改为左右布局列表点选）；批3 #1（移除明细检查按钮）+ #2（子表注册→预组合高亮）；批4 #8（ER图预组合标签）。
### 关键实现
- **批1 改名+列显隐**：a-select-option value="reference" → "普通关系"、value="detail" → "预组合关系"；ER按钮 "预组合表"→"预组合" + font-weight:600；dcColumns 移除 row_key（width:120）和 挂载（width:80）两列
- **批2 表列表点选**：源侧 reference 表单重写为 a-row:gutter=8 布局——a-col:span=8 源表列表（可点选 field-item）+ a-col:span=16 源字段列表（左右布局）+ 箭头 padding-top 200px + 目标侧 a-col:span=11 内同样 8|16 布局；新增 selectSourceTable(直接切换+自动清空源字段+加载)+ selectTargetTable；样式 field-item--disabled（opacity 0.5 + cursor not-allowed）
- **批3 按钮去重+改名**：移除 a-badge +「明细检查」按钮及关联代码；子表注册按钮 type="primary" + label "预组合"
- **批4 ER图预组合标签**：renderER 内置变量——headerTableToDetails（头表→明细表配置数组）和 detailTableToHeaders（明细表→头表名）；节点 HTML 中：头表节点追加绿色"预组合" tag + 包含明细表名；明细表节点追加青色"预组合" tag + 头表名
### 变更文件清单
- `frontend/src/views/modeling/DomainFieldMapping.vue`：批1~批4 全在此文件（约+97/-57 行）
### 验证
vue-tsc --noEmit 0 errors；已 commit+push（3a93caa）
