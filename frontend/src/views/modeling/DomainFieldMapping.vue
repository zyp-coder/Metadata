<template>
  <div>
    <DomainStageNav :domain-name="domainName" stage="mappings" />

    <div class="page-header">
      <h3 style="margin: 0">关系管理</h3>
      <a-space :size="16">
        <div v-if="pkStatusData" style="display: flex; align-items: center; gap: 8px">
          <a-progress
            :percent="Math.round((pkStatusData.configured_count / pkStatusData.total) * 100)"
            :show-info="false"
            size="small"
            style="width: 120px"
            :status="pkStatusData.all_configured ? 'success' : 'active'"
          />
          <span style="color: #666; font-size: 13px; white-space: nowrap">
            {{ pkStatusData.configured_count }}/{{ pkStatusData.total }} 表已配置
          </span>
        </div>
        <a-tag v-if="pkStatusData?.all_configured" color="success" style="margin: 0">✓ 全部完成</a-tag>
        <a-button type="primary" @click="openDetailConfigList()">预组合</a-button>
        <a-button type="primary" @click="openCreate()">+ 新建映射</a-button>
        <a-button @click="aiAutoMapping" :loading="aiMappingLoading">
          <template #icon><span style="font-size: 14px">🤖</span></template>
          AI建立关系
        </a-button>
        <a-button :type="erFullScreen ? 'primary' : 'default'" @click="toggleErFullScreen">
          {{ erFullScreen ? '返回列表' : 'ER图全屏' }}
        </a-button>
      </a-space>
    </div>

    <!-- 映射列表（全屏ER图模式下隐藏） -->
    <a-card v-show="!erFullScreen" :loading="loading" :bordered="false">
      <a-table
        :dataSource="mappingRows"
        :columns="mappingColumns"
        :pagination="false"
        rowKey="id"
        size="middle"
        :row-class-name="mappingRowClassName"
        :scroll="{ x: 1160 }"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'source_table'">
            <template v-if="record.relation_type === 'detail' && record.detail_config_combo">
              <div style="font-weight: 500; line-height: 1.4">{{ record.detail_config_combo }}</div>
              <div style="font-size: 12px; color: #1677ff">明细子表（预组合）</div>
            </template>
            <span v-else style="font-weight: 500">{{ record.source_table_name }}</span>
          </template>
          <template v-if="column.key === 'source_field'">
            <span :style="record.is_source_pk ? 'color: #faad14; font-weight: 500' : ''">
              <span v-if="record.is_source_pk" style="margin-right: 2px">⚿</span>{{ record.source_field_name }}
            </span>
          </template>
          <template v-if="column.key === 'target_table'">
            <span style="font-weight: 500">{{ record.target_table_name }}</span>
            <a-tag v-if="primaryTableId && primaryTableId === record.target_table" color="gold" style="margin-left: 4px">主表</a-tag>
          </template>
          <template v-if="column.key === 'target_field'">
            <span :style="record.is_target_pk ? 'color: #faad14; font-weight: 500' : ''">
              <span v-if="record.is_target_pk" style="margin-right: 2px">⚿</span>{{ record.target_field_name }}
            </span>
          </template>
          <template v-if="column.key === 'relation_type'">
            <a-tag v-if="record.relation_type === 'detail'" color="blue">明细子表</a-tag>
            <a-tag v-else color="default">普通关联</a-tag>
          </template>
          <template v-if="column.key === 'join_type'">
            <a-tag v-if="record.join_type === 'inner'" color="blue">INNER JOIN</a-tag>
            <a-tag v-else color="default">LEFT JOIN</a-tag>
          </template>
          <template v-if="column.key === 'action'">
            <a-space :size="4" style="white-space: nowrap">
              <a @click="openEdit(record)" style="color: #1677ff">编辑</a>
              <a @click="confirmDeleteMapping(record)" style="color: #ff4d4f">删除</a>
            </a-space>
          </template>
        </template>
      </a-table>
      <a-empty v-if="!loading && mappingRows.length === 0" description="暂无关系映射，请点击「新建映射」创建" />
    </a-card>

    <a-card title="ER 关系图" :style="erFullScreen ? 'margin-top: 0' : 'margin-top: 16px'">
      <template #extra>
        <div style="display: flex; align-items: center; gap: 12px; width: 100%">
          <span style="color: #999; font-size: 12px">节点展示表与字段，连线标注具体字段映射关系（可拖动节点调整布局）</span>
          <a-button size="small" @click="resetErLayout" :loading="resettingEr" style="margin-left: auto">重置布局</a-button>
          <a-button size="small" @click="toggleErHighlightPrecombine" :type="erHighlightPrecombine ? 'primary' : 'default'" style="font-weight: 600">预组合</a-button>
        </div>
      </template>
      <div v-show="mappings.length > 0" ref="erContainer" :class="erFullScreen ? 'er-container er-container--full' : 'er-container'"></div>
      <a-empty v-if="mappings.length === 0" description="暂无关系可展示" />
    </a-card>

    <!-- detail-check 结果抽屉 -->
    <a-drawer v-model:open="showDetailCheck" title="明细子表配置检查" width="640px" placement="right">
      <template v-if="detailCheckLoading">
        <a-spin /><span style="margin-left: 8px; color: #999">检查中...</span>
      </template>
      <template v-else-if="detailCheckData">
        <div v-if="detailCheckData.registered?.length" style="margin-bottom: 16px">
          <h4>已注册配置 ({{ detailCheckData.registered.length }})</h4>
          <a-list size="small" :dataSource="detailCheckData.registered">
            <template #renderItem="{ item }">
              <a-list-item><a-list-item-meta :description="`${item.source_table} → ${item.target_table}`" /></a-list-item>
            </template>
          </a-list>
        </div>
        <div v-if="detailCheckData.unregistered?.length" style="margin-bottom: 16px">
          <h4 style="color: #faad14">未注册的明细映射 ({{ detailCheckData.unregistered.length }})</h4>
          <p style="color: #999; font-size: 12px">以下 detail 映射未关联子表配置，需要使用「子表注册」更新</p>
          <a-list size="small" :dataSource="detailCheckData.unregistered">
            <template #renderItem="{ item }">
              <a-list-item><a-list-item-meta :description="`${item.source_table} → ${item.target_table}：${item.reason}`" /></a-list-item>
            </template>
          </a-list>
        </div>
        <div v-if="detailCheckData.suspect?.length" style="margin-bottom: 16px">
          <h4 style="color: #ff4d4f">方向可疑的映射 ({{ detailCheckData.suspect.length }})</h4>
          <a-list size="small" :dataSource="detailCheckData.suspect">
            <template #renderItem="{ item }">
              <a-list-item><a-list-item-meta :description="`#${item.id} ${item.source_table} → ${item.target_table}：${item.reason}`" /></a-list-item>
            </template>
          </a-list>
        </div>
        <div v-if="!detailCheckData.registered?.length && !detailCheckData.unregistered?.length && !detailCheckData.suspect?.length">
          <a-empty description="检查完成，无异常" />
        </div>
      </template>
      <template v-else>
        <a-empty description="暂无检查数据" />
      </template>
    </a-drawer>

    <!-- 子表注册管理弹窗（预组合=头表+明细表） -->
    <a-modal v-model:open="dcModalVisible" :title="dcEditingId ? '编辑子表配置' : '新建子表注册（预组合）'" @ok="handleDcSubmit" :confirmLoading="dcSaving" width="860px" :destroyOnClose="true">
      <a-alert v-if="!dcEditingId" type="info" show-icon style="margin-bottom: 16px"
        message="预组合 = 头表 + 明细表"
        description="先选头表和明细表（如 价目表 + 价目表明细），再配头↔明细关联字段；后续挂载时用整个预组合体关联主表" />
      <a-form layout="vertical">
        <!-- 顶栏：关系类型（只读）+ JOIN 类型 -->
        <a-row :gutter="16">
          <a-col :span="12">
            <a-form-item label="关系类型">
              <a-tag color="blue" style="margin: 0; line-height: 32px; height: 32px; font-size: 13px; padding: 0 12px">预组合关系</a-tag>
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="JOIN 类型" help="同步时头表与明细表的 JOIN 方式">
              <a-select v-model:value="dcForm.join_type">
                <a-select-option value="left">LEFT JOIN（保留无匹配头表的明细行）</a-select-option>
                <a-select-option value="inner">INNER JOIN（仅保留有匹配头表的明细行）</a-select-option>
              </a-select>
            </a-form-item>
          </a-col>
        </a-row>

        <!-- 左右分栏：头表（左） ↔ 关联字段（中） ↔ 明细表（右） -->
        <a-row :gutter="16">
          <!-- 左侧：头表列表 + 头表关联字段列表 -->
          <a-col :span="11">
            <a-row :gutter="8">
              <a-col :span="8">
                <div class="field-panel">
                  <div class="field-panel__header">头表（点击选择）</div>
                  <div class="field-panel__list">
                    <div v-for="t in domainTables" :key="t.id"
                         class="field-item"
                         :class="'field-item' + (dcForm.header_table === t.id ? ' field-item--selected' : '') + (dcEditingId ? ' field-item--disabled' : '')"
                         @click="!dcEditingId && selectDcHeaderTable(t.id)">
                      <div style="font-weight: 500; font-size: 12px">{{ t.name }}</div>
                      <div style="font-size: 11px; color: #999; margin-top: 2px">{{ t.code }}</div>
                    </div>
                    <div v-if="domainTables.length === 0" class="field-panel__empty">暂无表</div>
                  </div>
                </div>
              </a-col>
              <a-col :span="16">
                <div class="field-panel">
                  <div class="field-panel__header">头表关联字段</div>
                  <div class="field-panel__list">
                    <div v-for="f in dcHeaderFields" :key="f.id"
                         class="field-item"
                         :class="'field-item' + (dcForm.header_link_field === f.id ? ' field-item--selected' : '') + (dcEditingId ? ' field-item--disabled' : '')"
                         @click="!dcEditingId && (dcForm.header_link_field = f.id)">
                      <span v-if="f.is_primary_key" style="color: #faad14; margin-right: 2px">⚿</span>
                      {{ f.name }} ({{ f.code }})
                    </div>
                    <div v-if="dcHeaderFields.length === 0" class="field-panel__empty">请先选择头表</div>
                  </div>
                </div>
              </a-col>
            </a-row>
          </a-col>
          <!-- 中间：箭头 + 检测按钮 -->
          <a-col :span="2" style="text-align: center; padding-top: 180px">
            <div><span style="font-size: 28px; color: #bbb">↔</span></div>
            <div style="margin-top: 8px"><a-button size="small" :loading="dcDetectingLink" @click="detectDcLink" :disabled="!!dcEditingId">检测</a-button></div>
          </a-col>
          <!-- 右侧：明细表列表 + 明细表关联字段列表 -->
          <a-col :span="11">
            <a-row :gutter="8">
              <a-col :span="8">
                <div class="field-panel">
                  <div class="field-panel__header">明细表（点击选择）</div>
                  <div class="field-panel__list">
                    <div v-for="t in domainTables" :key="t.id"
                         class="field-item"
                         :class="{
                           'field-item--selected': dcForm.table === t.id,
                           'field-item--disabled': (!!dcRegisteredMap[t.id] && dcForm.table !== t.id) || !!dcEditingId
                         }"
                         @click="!dcEditingId && !dcRegisteredMap[t.id] && selectDcDetailTable(t.id)">
                      <div style="font-weight: 500; font-size: 12px">{{ t.name }}</div>
                      <div style="font-size: 11px; color: #999; margin-top: 2px">{{ t.code }}</div>
                      <div v-if="dcRegisteredMap[t.id] && dcForm.table !== t.id" style="font-size: 10px; color: #faad14; margin-top: 2px">已注册</div>
                    </div>
                    <div v-if="domainTables.length === 0" class="field-panel__empty">暂无表</div>
                  </div>
                </div>
              </a-col>
              <a-col :span="16">
                <div class="field-panel">
                  <div class="field-panel__header">明细表关联字段</div>
                  <div class="field-panel__list">
                    <div v-for="f in dcSourceFields" :key="f.id"
                         class="field-item"
                         :class="'field-item' + (dcForm.detail_link_field === f.id ? ' field-item--selected' : '') + (dcEditingId ? ' field-item--disabled' : '')"
                         @click="!dcEditingId && (dcForm.detail_link_field = f.id)">
                      <span v-if="f.is_primary_key" style="color: #faad14; margin-right: 2px">⚿</span>
                      {{ f.name }} ({{ f.code }})
                    </div>
                    <div v-if="dcSourceFields.length === 0" class="field-panel__empty">请先选择明细表</div>
                  </div>
                </div>
              </a-col>
            </a-row>
          </a-col>
        </a-row>

        <a-form-item label="行键字段" help="明细行唯一标识列（如 ENTRY_ID），未配置时同步自动检测并回填">
          <a-space style="width: 100%">
            <a-select v-model:value="dcForm.row_key_field" style="flex: 1" show-search allowClear placeholder="自动检测">
              <a-select-option v-for="f in dcSourceFields" :key="f.id" :value="f.id">
                <span v-if="f.is_primary_key" style="color: #faad14; margin-right: 2px">⚿</span>{{ f.name }} ({{ f.code }})
              </a-select-option>
            </a-select>
            <a-button :loading="dcDetectingRowKey" @click="detectDcRowKey" :disabled="!dcEditingId">检测</a-button>
          </a-space>
        </a-form-item>
        <a-form-item label="筛选条件（可选）" help="仅同步满足条件的明细行，多条件同时满足（AND 关系）">
          <div style="margin-bottom: 4px">
            字段 操作符 值（多条件同时满足，自动转为 AND 查询）
          </div>
          <div v-for="(cond, idx) in dcConditions" :key="idx" style="display: flex; gap: 8px; margin-bottom: 8px; align-items: center">
            <a-select v-model:value="cond.fieldSource" style="width: 90px" placeholder="来源">
              <a-select-option value="detail">明细</a-select-option>
              <a-select-option value="header">头表</a-select-option>
            </a-select>
            <a-select v-model:value="cond.field" style="width: 155px" show-search placeholder="选择字段">
              <a-select-option v-for="f in (cond.fieldSource === 'header' ? dcHeaderFields : dcSourceFields)" :key="f.id" :value="f.code">{{ f.name }} ({{ f.code }})</a-select-option>
            </a-select>
            <a-select v-model:value="cond.operator" style="width: 130px" placeholder="操作符">
              <a-select-option value="eq">等于 (=)</a-select-option>
              <a-select-option value="ne">不等于 (!=)</a-select-option>
              <a-select-option value="gt">大于 (&gt;)</a-select-option>
              <a-select-option value="ge">大于等于 (&gt;=)</a-select-option>
              <a-select-option value="lt">小于 (&lt;)</a-select-option>
              <a-select-option value="le">小于等于 (&lt;=)</a-select-option>
              <a-select-option value="in">在列表中</a-select-option>
              <a-select-option value="starts_with">开头是</a-select-option>
              <a-select-option value="contains">包含</a-select-option>
            </a-select>
            <a-input v-if="cond.operator !== 'in'" v-model:value="cond.value" style="flex: 1" placeholder="值" />
            <a-select v-else v-model:value="cond.value" mode="tags" style="flex: 1" placeholder="输入值后回车" />
            <a-button type="text" danger @click="removeDcCondition(idx)" size="small" style="flex-shrink: 0">✕</a-button>
          </div>
          <a-button size="small" @click="addDcCondition">+ 添加条件</a-button>
        </a-form-item>
      </a-form>
    </a-modal>

    <!-- 子表注册管理列表（2026-08-11 修复：注册管理入口升级为列表，支持查看/编辑/删除已有注册） -->
    <a-modal v-model:open="dcListModalVisible" title="子表注册管理（预组合）" width="860px" :footer="null">
      <a-alert type="info" show-icon style="margin-bottom: 12px" message="预组合 = 头表 + 明细表"
        description="注册（头表+明细表先组合）与挂载（用组合体关联主表）是两步；同一明细表只能注册一次，新建时已注册的明细表不可重复选择" />
      <a-input v-model:value="dcListSearch" placeholder="搜索头表名或明细表名..." allowClear style="margin-bottom: 12px" />
      <div style="text-align: right; margin-bottom: 12px">
        <a-button type="primary" size="small" @click="openDetailConfigCreate">新建注册</a-button>
      </div>
      <a-table :dataSource="filteredDetailConfigs" :columns="dcColumns" rowKey="id" size="small" :pagination="false" :scroll="{ y: 380 }">
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'combo'">
            <span style="font-weight: 500">{{ record.header_table_name ? record.header_table_name + ' + ' : '' }}{{ record.table_name }}</span>
            <div style="font-size: 12px; color: #888">{{ record.header_table_code ? record.header_table_code + '+' : '' }}{{ record.table_code }}</div>
          </template>
          <template v-else-if="column.key === 'link'">
            {{ record.header_link_field_name || '?' }} ↔ {{ record.detail_link_field_name || '?' }}
          </template>
          <template v-else-if="column.key === 'row_key'">{{ record.row_key_field_name || '自动检测' }}</template>
          <template v-else-if="column.key === 'mappings'">{{ record.mapping_count }} 个</template>
          <template v-else-if="column.key === 'action'">
            <a @click="openDetailConfigEdit(record)">编辑</a>
            <a-divider type="vertical" />
            <a-popconfirm :title="record.mapping_count > 0 ? `该组合已被 ${record.mapping_count} 个映射挂载，删除后这些映射将变为未挂载状态，确认删除？` : '确认删除该注册？'" @confirm="removeDetailConfig(record)">
              <a style="color: #ff4d4f">删除</a>
            </a-popconfirm>
          </template>
        </template>
      </a-table>
    </a-modal>

    <a-modal v-model:open="modalVisible" :title="modalTitle" @ok="handleSubmit" :confirmLoading="saving" width="960px">
      <a-form layout="vertical">
        <a-row :gutter="16">
          <a-col :span="12">
            <a-form-item label="关系类型">
              <a-select v-model:value="form.relation_type" style="width: 100%" @change="onRelationTypeChange">
                <a-select-option value="reference">普通关系</a-select-option>
                <a-select-option value="detail">预组合关系</a-select-option>
              </a-select>
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="JOIN 类型" help="数据同步时表间关联所采用的 JOIN 方式">
              <a-select v-model:value="form.join_type">
                <a-select-option value="left">LEFT JOIN（保留无匹配行）</a-select-option>
                <a-select-option value="inner">INNER JOIN（仅保留匹配行）</a-select-option>
              </a-select>
            </a-form-item>
          </a-col>
        </a-row>

        <!-- 明细子表（形态1）：主表 → 子表 → 关联字段；注册与挂载分离，方向由系统处理 -->
        <template v-if="form.relation_type === 'detail'">
          <a-alert
            v-if="editingMappingId && !form.detail_config"
            type="warning"
            show-icon
            message="该映射未关联子表注册配置（存量数据）"
            description="选择下方子表配置完成挂载；未注册的子表请先点击「管理注册」创建"
            style="margin-bottom: 16px"
          />
          <a-form-item label="主表" required help="被挂载明细子表的主记录表">
            <a-select v-model:value="form.target_table" style="width: 100%" show-search @change="loadTargetFields">
              <a-select-option v-for="t in targetTableOptions" :key="t.id" :value="t.id">{{ t.name }} ({{ t.code }})</a-select-option>
            </a-select>
          </a-form-item>
          <a-form-item label="预组合（子表）" required help="选择已注册的预组合体——注册（头表+明细表先组合）与挂载（本弹窗建立与主表的关系）是两步">
            <a-space style="width: 100%">
              <a-select v-model:value="form.detail_config" style="flex: 1" show-search allowClear placeholder="请选择已注册的预组合" @change="onDetailConfigChange">
                <a-select-option v-for="cfg in domainDetailConfigs" :key="cfg.id" :value="cfg.id">
                  {{ cfg.header_table_name ? cfg.header_table_name + ' + ' : '' }}{{ cfg.table_name }}
                  ({{ cfg.header_table_code ? cfg.header_table_code + '+' : '' }}{{ cfg.table_code }})
                  {{ cfg.row_key_field_name ? ' · 行键:' + cfg.row_key_field_name : '' }}
                </a-select-option>
              </a-select>
              <a-button size="small" @click="openDetailConfigList()">管理注册</a-button>
            </a-space>
          </a-form-item>
          <a-form-item v-if="selectedDetailConfig" label="配置摘要" help="组合配置由注册统一管理，编辑映射时不可修改">
            <div style="background: #f5f5f5; padding: 8px 12px; border-radius: 4px; font-size: 13px; line-height: 1.8">
              <div v-if="selectedDetailConfig.header_table_name">
                <strong>预组合：</strong>{{ selectedDetailConfig.header_table_name }} + {{ selectedDetailConfig.table_name }}
                <span style="color: #888">（{{ selectedDetailConfig.header_link_field_name || '?' }} ↔ {{ selectedDetailConfig.detail_link_field_name || '?' }}）</span>
              </div>
              <div><strong>行键：</strong>{{ selectedDetailConfig.row_key_field_name || '自动检测' }}</div>
              <div><strong>排序：</strong>{{ selectedDetailConfig.display_sort_field_name || '未配置' }}
                {{ selectedDetailConfig.display_sort_desc ? '（降序）' : '（升序）' }}</div>
              <div v-if="selectedDetailConfig.conditions?.length">
                <strong>条件：</strong>{{ JSON.stringify(selectedDetailConfig.conditions) }}</div>
              <div v-if="selectedDetailConfig.mapping_count > 0">
                <strong>挂载数：</strong>{{ selectedDetailConfig.mapping_count }} 个映射</div>
            </div>
          </a-form-item>
          <a-form-item label="关联字段" required help="子表中与主表关联的字段（自动推荐可改，系统自动按 子表→主表 方向挂载）">
            <a-select v-model:value="form.source_field" style="width: 100%" show-search allowClear placeholder="请选择关联字段" @change="onDetailSourceFieldChange">
              <a-select-option v-for="f in sourceFields" :key="f.id" :value="f.id">
                <span v-if="f.is_primary_key" style="color: #faad14; margin-right: 4px">⚿</span>{{ f.name }} ({{ f.code }})
                <a-tag v-if="f.id === detailRecommendedFieldId" color="green" style="margin-left: 6px">推荐</a-tag>
              </a-select-option>
            </a-select>
          </a-form-item>
          <a-alert
            v-if="detailTargetNoPk"
            type="warning"
            show-icon
            message="主表需要配置单一主键字段"
            description="明细子表通过关联字段挂载到主表主键，请先在表配置中设置主表的主键字段"
            style="margin-bottom: 16px"
          />
        </template>

        <!-- 引用关系：字段级映射（左右分栏，表列表+字段列表左右布局） -->
        <template v-else>
          <a-row :gutter="16">
            <!-- 左侧：源表列表 + 源字段列表（左右布局） -->
            <a-col :span="12">
              <a-row :gutter="8">
                <a-col :span="8">
                  <div class="field-panel">
                    <div class="field-panel__header">源表（点击选择）</div>
                    <div class="field-panel__list">
                      <div v-for="t in domainTables" :key="t.id"
                           class="field-item"
                           :class="{'field-item--selected': form.source_table === t.id}"
                           @click="selectSourceTable(t.id)">
                        <div style="font-weight: 500; font-size: 12px">{{ t.name }}</div>
                        <div style="font-size: 11px; color: #999; margin-top: 2px">{{ t.code }}</div>
                      </div>
                      <div v-if="domainTables.length === 0" class="field-panel__empty">暂无表</div>
                    </div>
                  </div>
                </a-col>
                <a-col :span="16">
                  <div class="field-panel">
                    <div class="field-panel__header">源字段（点击选择）</div>
                    <div class="field-panel__list">
                      <div v-if="hasCompositeSourceKey" class="field-item field-item--composite"
                           :class="{'field-item--selected': form.source_field === 'composite'}"
                           @click="form.source_field = 'composite'">
                        <span style="color: #faad14; margin-right: 4px">⚿</span>
                        <span style="font-weight: 600">{{ compositeKeyLabel }}</span>
                        <span style="color: #888; font-size: 11px; margin-left: 4px">(联合主键)</span>
                      </div>
                      <div v-for="f in sourceFields" :key="f.id"
                           class="field-item"
                           :class="{'field-item--selected': form.source_field === f.id}"
                           @click="form.source_field = f.id">
                        <span v-if="f.is_primary_key" style="color: #faad14; margin-right: 2px">⚿</span>
                        {{ f.name }} ({{ f.code }})
                      </div>
                      <div v-if="sourceFields.length === 0" class="field-panel__empty">请先选择源表</div>
                    </div>
                  </div>
                </a-col>
              </a-row>
            </a-col>
            <!-- 中间：箭头 -->
            <a-col :span="1" style="text-align: center; padding-top: 200px">
              <span style="font-size: 28px; color: #bbb">→</span>
            </a-col>
            <!-- 右侧：目标表列表 + 目标字段列表（左右布局） -->
            <a-col :span="11">
              <a-row :gutter="8">
                <a-col :span="8">
                  <div class="field-panel">
                    <div class="field-panel__header">目标表（点击选择）</div>
                    <div class="field-panel__list">
                      <div v-for="t in targetTableOptions" :key="t.id"
                           class="field-item"
                           :class="{'field-item--selected': form.target_table === t.id}"
                           @click="selectTargetTable(t.id)">
                        <div style="font-weight: 500; font-size: 12px">{{ t.name }}</div>
                        <div style="font-size: 11px; color: #999; margin-top: 2px">{{ t.code }}</div>
                      </div>
                      <div v-if="targetTableOptions.length === 0" class="field-panel__empty">暂无表</div>
                    </div>
                  </div>
                </a-col>
                <a-col :span="16">
                  <div class="field-panel">
                    <div class="field-panel__header">目标字段（点击选择）</div>
                    <div class="field-panel__list">
                      <div v-if="hasCompositeTargetKey" class="field-item field-item--composite"
                           :class="{'field-item--selected': form.target_field === 'composite'}"
                           @click="form.target_field = 'composite'">
                        <span style="color: #faad14; margin-right: 4px">⚿</span>
                        <span style="font-weight: 600">{{ targetCompositeKeyLabel }}</span>
                        <span style="color: #888; font-size: 11px; margin-left: 4px">(联合主键)</span>
                      </div>
                      <div v-for="f in targetFields" :key="f.id"
                           class="field-item"
                           :class="{'field-item--selected': form.target_field === f.id}"
                           @click="form.target_field = f.id">
                        <span v-if="f.is_primary_key" style="color: #faad14; margin-right: 2px">⚿</span>
                        {{ f.name }} ({{ f.code }})
                      </div>
                      <div v-if="targetFields.length === 0" class="field-panel__empty">请先选择目标表</div>
                    </div>
                  </div>
                </a-col>
              </a-row>
              <!-- 联合主键提示 -->
              <a-alert v-if="hasCompositeSourceKey || hasCompositeTargetKey" type="info" show-icon style="margin-top: 12px"
                message="联合主键"
                :description="(hasCompositeSourceKey ? '源表联合主键：' + compositeKeyLabel : '') + (hasCompositeSourceKey && hasCompositeTargetKey ? ' | ' : '') + (hasCompositeTargetKey ? '目标表联合主键：' + targetCompositeKeyLabel : '')" />
            </a-col>
          </a-row>
        </template>
      </a-form>
    </a-modal>

    <!-- AI 推断映射结果弹窗 -->
    <a-modal
      v-model:open="aiModalVisible"
      title="AI 建议的字段映射关系"
      :width="900"
      :footer="null"
      :bodyStyle="{ maxHeight: '70vh', overflowY: 'auto' }"
    >
      <template v-if="aiSuggestions.length > 0">
        <div style="margin-bottom: 12px; display: flex; justify-content: space-between; align-items: center">
          <span style="color: #666; font-size: 13px">
            共发现 {{ aiSuggestions.length }} 条可能的映射关系，请勾选要创建的映射
          </span>
          <a-space>
            <a-button size="small" @click="selectAllAiSuggestions">全选</a-button>
            <a-button size="small" @click="selectedAiSuggestions = []">清空</a-button>
          </a-space>
        </div>
        <a-table
          :dataSource="aiSuggestions"
          :columns="aiSuggestionColumns"
          :pagination="false"
          rowKey="rowKey"
          size="small"
          :row-selection="{
            selectedRowKeys: selectedAiSuggestions,
            onChange: (keys: any[]) => selectedAiSuggestions = keys
          }"
        >
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'source'">
              <div>
                <div style="font-weight: 500">{{ record.source_table_name }}</div>
                <div style="color: #666; font-size: 12px">
                  <span v-if="record.source_is_primary_key" style="color: #faad14; margin-right: 2px">⚿</span>
                  {{ record.source_field_name }} ({{ record.source_field_code }})
                </div>
              </div>
            </template>
            <template v-if="column.key === 'target'">
              <div>
                <div style="font-weight: 500">{{ record.target_table_name }}</div>
                <div style="color: #666; font-size: 12px">
                  <span v-if="record.target_is_primary_key" style="color: #faad14; margin-right: 2px">⚿</span>
                  {{ record.target_field_name }} ({{ record.target_field_code }})
                </div>
              </div>
            </template>
            <template v-if="column.key === 'confidence'">
              <a-tag :color="record.confidence >= 0.8 ? 'green' : record.confidence >= 0.6 ? 'orange' : 'default'">
                {{ Math.round(record.confidence * 100) }}%
              </a-tag>
            </template>
            <template v-if="column.key === 'reason'">
              <span style="color: #666; font-size: 12px">{{ record.reason }}</span>
            </template>
          </template>
        </a-table>
        <div style="margin-top: 16px; text-align: right">
          <a-button @click="aiModalVisible = false" style="margin-right: 8px">取消</a-button>
          <a-button
            type="primary"
            :loading="aiCreating"
            :disabled="selectedAiSuggestions.length === 0"
            @click="createSelectedMappings"
          >
            创建选中映射 ({{ selectedAiSuggestions.length }})
          </a-button>
        </div>
      </template>
      <template v-else-if="aiMappingLoading">
        <div style="text-align: center; padding: 40px; color: #999">
          <a-spin /> <span style="margin-left: 8px">AI 正在分析表结构和字段关系...</span>
        </div>
      </template>
      <template v-else>
        <a-empty description="未发现新的映射关系建议">
          <template #image>
            <span style="font-size: 48px">🤖</span>
          </template>
          <p style="color: #999">所有可能的字段映射关系已建立，或表结构暂无可识别的关联</p>
        </a-empty>
      </template>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onBeforeUnmount, nextTick, h } from 'vue'
import { useRoute } from 'vue-router'
import { message, Modal } from 'ant-design-vue'
import { extractApiError } from '@/utils/apiError'
import { Graph, Shape } from '@antv/x6'
import { domainApi, tableApi, fieldApi, fieldMappingApi, detailConfigApi } from '@/api/modeling'
import type { Table } from '@/types'
import DomainStageNav from './components/DomainStageNav.vue'

const route = useRoute()
const domainId = Number(route.params.id)
const domainName = ref('')
const domainTables = ref<Table[]>([])
const sourceFields = ref<any[]>([])
const targetFields = ref<any[]>([])
const mappings = ref<any[]>([])
const loading = ref(false)
const aiMappingLoading = ref(false)
const modalVisible = ref(false)
const saving = ref(false)
const form = ref<any>({
  source_table: null, source_field: null, target_table: null, target_field: null,
  relation_type: 'reference',
  join_type: 'left',
  row_key_field: null,
  display_sort_field: null,
  display_sort_desc: true,
  conditionsText: '',
})

const editingMappingId = ref<number | null>(null)
// 编辑模式下存储的映射 IDs（联合主键时可能有多个）
const editingMappingIds = ref<number[]>([])

// 主键配置状态
const pkStatusData = ref<any>(null)

// AI 推断映射状态
const aiModalVisible = ref(false)
const aiSuggestions = ref<any[]>([])
const selectedAiSuggestions = ref<string[]>([])
const aiCreating = ref(false)
const detectingRowKey = ref(false)

// 子表注册管理状态
const dcModalVisible = ref(false)
const dcSaving = ref(false)
const dcEditingId = ref<number | null>(null)
const dcForm = ref<any>({
  header_table: null, table: null,
  header_link_field: null, detail_link_field: null,
  row_key_field: null, display_sort_field: null,
  display_sort_desc: true, join_type: 'left', conditionsText: '',
})
const dcConditions = ref<{ field: string; operator: string; value: any; fieldSource: string }[]>([])
const dcSourceFields = ref<any[]>([])
const dcHeaderFields = ref<any[]>([])
const dcDetectingRowKey = ref(false)
const dcDetectingLink = ref(false)
const domainDetailConfigs = ref<any[]>([])
const dcListModalVisible = ref(false)
const dcListSearch = ref('')

// 预组合列表搜索过滤
const filteredDetailConfigs = computed(() => {
  const q = dcListSearch.value.trim().toLowerCase()
  if (!q) return domainDetailConfigs.value
  return domainDetailConfigs.value.filter((cfg: any) =>
    (cfg.header_table_name || '').toLowerCase().includes(q) ||
    (cfg.table_name || '').toLowerCase().includes(q) ||
    (cfg.header_table_code || '').toLowerCase().includes(q) ||
    (cfg.table_code || '').toLowerCase().includes(q)
  )
})

// detail-check 状态
const showDetailCheck = ref(false)
const detailCheckLoading = ref(false)
const detailCheckData = ref<any>(null)

// Issue 1：有异常时才显示明细检查按钮
const hasDetailCheckIssues = computed(() => {
  const d = detailCheckData.value
  return d && (d.registered?.length > 0 || d.unregistered?.length > 0 || d.suspect?.length > 0)
})

// 关联字段手动修改标记（自动推荐不覆盖用户选择）
const sourceFieldTouched = ref(false)

// 选中的 detail_config 详情（供展示摘要）
const selectedDetailConfig = computed(() => {
  if (!form.value.detail_config) return null
  return domainDetailConfigs.value.find((c: any) => c.id === form.value.detail_config) || null
})

// 已注册明细表映射 { tableId: '头表名 + 明细表名' }（2026-08-11 修复：新建弹窗明细表下拉禁选+标记）
const dcRegisteredMap = computed<Record<number, string>>(() => {
  const map: Record<number, string> = {}
  for (const c of domainDetailConfigs.value) {
    map[c.table] = c.header_table_name ? `${c.header_table_name} + ${c.table_name}` : c.table_name
  }
  return map
})

// 关联字段自动推荐：子表字段与主表主键 code 匹配（完全同名 > FID↔ID 后缀模式）
const detailRecommendedFieldId = computed<number | null>(() => {
  if (form.value.relation_type !== 'detail' || !form.value.target_table || sourceFields.value.length === 0) return null
  const pkFields = targetFields.value.filter((f: any) => f.is_primary_key)
  if (pkFields.length !== 1) return null
  const pkCode = String(pkFields[0].code || '')
  if (!pkCode) return null
  const exact = sourceFields.value.find((f: any) => String(f.code) === pkCode)
  if (exact) return exact.id
  const suffix = sourceFields.value.find((f: any) => String(f.code).endsWith(pkCode) && String(f.code).length > pkCode.length)
  if (suffix) return suffix.id
  return null
})

// 主表主键检查：明细子表挂载需要主表单一主键
const detailTargetNoPk = computed(() => {
  if (form.value.relation_type !== 'detail' || !form.value.target_table) return false
  return targetFields.value.filter((f: any) => f.is_primary_key).length !== 1
})

// AI 建议表格列定义
const aiSuggestionColumns = [
  { title: '源表.字段', key: 'source', width: 220 },
  { title: '', key: 'arrow', width: 40, customRender: () => '→' },
  { title: '目标表.字段', key: 'target', width: 220 },
  { title: '置信度', key: 'confidence', width: 80, align: 'center' as const },
  { title: '说明', key: 'reason' },
]

// 映射列表列定义
const mappingColumns = [
  { title: '源表', key: 'source_table', width: 260 },
  { title: '源字段', key: 'source_field', width: 170 },
  { title: '目标表', key: 'target_table', width: 170 },
  { title: '目标字段', key: 'target_field', width: 170 },
  { title: '关系类型', key: 'relation_type', width: 110 },
  { title: 'JOIN 类型', key: 'join_type', width: 120 },
  { title: '操作', key: 'action', width: 120 },
]

// detail 行浅蓝底（第一百四十四轮直观性改进）
function mappingRowClassName(record: any) {
  return record.relation_type === 'detail' ? 'mapping-row-detail' : ''
}

// 域主表 id（目标表为主表时显示金色「主表」tag）
const primaryTableId = computed(() => {
  return domainTables.value.find((t: any) => t.is_primary)?.id ?? null
})

// 子表注册管理列表列定义（2026-08-11 修复）
const dcColumns = [
  { title: '预组合（头表 + 明细表）', key: 'combo', width: 280 },
  { title: '头↔明细关联', key: 'link', width: 140 },
  { title: '操作', key: 'action', width: 110 },
]

// 映射列表数据：同一对表的映射合并为一行（联合字段=一行，独立关系=一行）
const mappingRows = computed(() => {
  // 构建 PK 字段 ID 集合（用于判断字段是否为主键）
  const pkFieldIdsByTable: Record<number, Set<number>> = {}
  if (pkStatusData.value) {
    for (const t of pkStatusData.value.tables) {
      pkFieldIdsByTable[t.table_id] = new Set(t.pk_fields.map((f: any) => f.id))
    }
  }

  // 第一遍：按 (source_table, target_table) 分组
  const groups: Record<string, any> = {}
  const groupOrder: string[] = []
  for (const m of mappings.value) {
    const key = `${m.source_table}-${m.target_table}`
    if (!groups[key]) {
      groups[key] = {
        key,
        source_table: m.source_table,
        source_table_name: m.source_table_name,
        target_table: m.target_table,
        target_table_name: m.target_table_name,
        relation_type: m.relation_type || 'reference',
        relation_type_label: m.relation_type_label || '',
        join_type: m.join_type || 'left',
        join_type_label: m.join_type_label || 'LEFT JOIN',
        row_key_field: m.row_key_field,
        row_key_field_name: m.row_key_field_name || '',
        display_sort_field: m.display_sort_field,
        display_sort_field_name: m.display_sort_field_name || '',
        display_sort_desc: m.display_sort_desc,
        conditions: m.conditions,
        detail_config_id: m.detail_config_id || null,
        detail_config_name: m.detail_config_name || '',
        detail_config_combo: m.detail_config_combo || '',
        mapping_ids: [] as number[],
        _srcNames: [] as string[],
        _tgtNames: [] as string[],
        _srcFields: [] as number[],
        _tgtFields: [] as number[],
      }
      groupOrder.push(key)
    }
    groups[key].mapping_ids.push(m.id)
    groups[key]._srcNames.push(m.source_field_name)
    groups[key]._tgtNames.push(m.target_field_name)
    groups[key]._srcFields.push(m.source_field)
    groups[key]._tgtFields.push(m.target_field)
  }

  // 第二遍：判断每组是否涉及联合字段，生成行
  return groupOrder.map((key) => {
    const g = groups[key]
    const srcUnique = new Set(g._srcFields).size
    const tgtUnique = new Set(g._tgtFields).size
    // 联合字段：源端或目标端使用了多个不同字段
    const isComposite = g.mapping_ids.length > 1 && (srcUnique > 1 || tgtUnique > 1)

    // 判断主键标识
    const srcPkSet = pkFieldIdsByTable[g.source_table]
    const tgtPkSet = pkFieldIdsByTable[g.target_table]

    if (isComposite) {
      return {
        id: `composite-${key}`,
        is_composite: true,
        source_table: g.source_table,
        source_table_name: g.source_table_name,
        target_table: g.target_table,
        target_table_name: g.target_table_name,
        source_field: g._srcFields[0],
        target_field: g._tgtFields[0],
        source_field_name: [...new Set(g._srcNames)].join(' + '),
        target_field_name: [...new Set(g._tgtNames)].join(' + '),
        mapping_ids: g.mapping_ids,
        is_source_pk: g._srcFields.some((f: number) => srcPkSet?.has(f)),
        is_target_pk: g._tgtFields.some((f: number) => tgtPkSet?.has(f)),
        relation_type: g.relation_type,
        relation_type_label: g.relation_type_label,
        join_type: g.join_type,
        join_type_label: g.join_type_label,
        row_key_field: g.row_key_field,
        row_key_field_name: g.row_key_field_name,
        display_sort_field: g.display_sort_field,
        display_sort_field_name: g.display_sort_field_name,
        display_sort_desc: g.display_sort_desc,
        conditions: g.conditions,
        detail_config_id: g.detail_config_id,
        detail_config_name: g.detail_config_name,
        detail_config_combo: g.detail_config_combo,
      }
    } else {
      // 单条映射（普通映射 或 多对一/一对多但不跨多字段）
      const m = mappings.value.find((mm) => mm.source_table === g.source_table && mm.target_table === g.target_table)!
      return {
        ...m,
        is_composite: false,
        mapping_ids: [m.id],
        is_source_pk: srcPkSet?.has(m.source_field) ?? false,
        is_target_pk: tgtPkSet?.has(m.target_field) ?? false,
      }
    }
  })
})

// 联合主键检测（源表）
const hasCompositeSourceKey = computed(() => {
  const pkFields = sourceFields.value.filter((f: any) => f.is_primary_key)
  return pkFields.length >= 2
})
const compositeKeyLabel = computed(() => {
  const pkFields = sourceFields.value.filter((f: any) => f.is_primary_key)
  return pkFields.map((f: any) => f.code).join(' + ')
})

// 联合主键检测（目标表）
const hasCompositeTargetKey = computed(() => {
  const pkFields = targetFields.value.filter((f: any) => f.is_primary_key)
  return pkFields.length >= 2
})
const targetCompositeKeyLabel = computed(() => {
  const pkFields = targetFields.value.filter((f: any) => f.is_primary_key)
  return pkFields.map((f: any) => f.code).join(' + ')
})

// 目标表选项：排除源表
const targetTableOptions = computed(() => {
  if (!form.value.source_table) return domainTables.value
  return domainTables.value.filter((t) => t.id !== form.value.source_table)
})

// 弹窗标题：编辑时标识具体表对
const modalTitle = computed(() => {
  if (editingMappingId.value && form.value.source_table && form.value.target_table) {
    const src = domainTables.value.find((t) => t.id === form.value.source_table)
    const tgt = domainTables.value.find((t) => t.id === form.value.target_table)
    if (src && tgt) return `编辑字段映射 - ${src.name} → ${tgt.name}`
  }
  return editingMappingId.value ? '编辑字段映射' : '新建字段映射'
})

const erFullScreen = ref(false)
const erContainer = ref<HTMLElement | null>(null)
let graph: Graph | null = null
const resettingEr = ref(false)
const erHighlightPrecombine = ref(false)
const erNodeMap: Record<number, { node: any; tableId: number; tableRef: any }> = {}

// ER 图常量
const ER_HEADER_HEIGHT = 40
const ER_ROW_HEIGHT = 32

async function saveErNodePosition(tid: number, node: any, t: any) {
  const pos = node.getPosition()
  const x = Math.round(pos.x)
  const y = Math.round(pos.y)
  try {
    await tableApi.saveErPosition(tid, x, y)
    if (t) { t.er_node_x = x; t.er_node_y = y }
  } catch { /* 静默失败 */ }
}

async function loadData() {
  loading.value = true
  try {
    const domainRes = await domainApi.get(domainId)
    domainName.value = domainRes.data.name

    const tablesRes = await tableApi.list({ domain: domainId })
    domainTables.value = tablesRes.data.results

    const mapRes = await fieldMappingApi.list({ domain: domainId })
    mappings.value = mapRes.data.results

    // 加载主键配置状态
    const pkRes = await domainApi.pkStatus(domainId)
    pkStatusData.value = pkRes.data

    // 加载子表注册配置
    await loadDetailConfigs()

    // Issue 1：预加载明细检查数据（结果为空时不显示按钮）
    loadDetailCheck()
  } finally {
    loading.value = false
  }
  await nextTick()
  renderER()
}

// ===== ER 图渲染 =====
function renderER() {
  if (mappings.value.length === 0) {
    if (graph) { graph.dispose(); graph = null }
    return
  }
  if (!erContainer.value) return

  // 收集参与映射的表
  const tableIds = new Set<number>()
  mappings.value.forEach((m) => {
    tableIds.add(m.source_table)
    tableIds.add(m.target_table)
  })
  const idList = Array.from(tableIds)

  // 为每个表加载字段
  const tableFieldsMap = new Map<number, any[]>()
  const loadPromises = idList.map(async (tid) => {
    const res = await fieldApi.list({ table: tid })
    tableFieldsMap.set(tid, res.data.results)
  })

  Promise.all(loadPromises).then(() => doRenderER(idList, tableFieldsMap))
}

function doRenderER(idList: number[], tableFieldsMap: Map<number, any[]>) {
  if (!erContainer.value) return

  const width = erContainer.value.clientWidth || 900
  const height = erContainer.value.clientHeight || 600
  if (graph) { graph.dispose(); graph = null }

  graph = new Graph({
    container: erContainer.value,
    width,
    height,
    interacting: { nodeMovable: true },
    background: { color: '#fafbfc' },
    connecting: { anchor: 'center', connectionPoint: 'boundary' },
    mousewheel: { enabled: true, modifiers: ['ctrl', 'meta'], factor: 1.05 },
    panning: { enabled: true },
  })

  // 网格布局
  const cols = Math.max(1, Math.min(3, Math.ceil(Math.sqrt(idList.length))))
  const nodeWidth = 320
  const gapX = 40
  const gapY = 36
  const totalContentWidth = cols * nodeWidth + (cols - 1) * gapX
  const startX = Math.max(30, Math.floor((width - totalContentWidth) / 2))
  const colY = new Array(cols).fill(30)
  const nodeMap: Record<number, string> = {}

  // 预组合查找表（Issue 8: ER图展示组合表效果）
  const headerTableToDetails: Record<number, any[]> = {}
  const detailTableToHeaders: Record<number, string> = {}
  domainDetailConfigs.value.forEach((dc: any) => {
    if (!dc.header_table || !dc.table) return
    if (!headerTableToDetails[dc.header_table]) headerTableToDetails[dc.header_table] = []
    headerTableToDetails[dc.header_table].push(dc)
    detailTableToHeaders[dc.table] = dc.header_table_name
  })

  idList.forEach((tid, idx) => {
    const t = domainTables.value.find((x) => x.id === tid)
    const rawFields = tableFieldsMap.get(tid) || []
    const col = idx % cols
    const y = colY[col]

    // 检测联合主键：如果表有 2+ 个 PK 字段，合并为一个虚拟字段
    const pkFields = rawFields.filter((f: any) => f.is_primary_key)
    const nonPkFields = rawFields.filter((f: any) => !f.is_primary_key)
    let displayFields: any[]
    if (pkFields.length >= 2) {
      const compositeField = {
        id: 'composite_pk',
        name: pkFields.map((f: any) => f.name).join(' + '),
        code: pkFields.map((f: any) => f.code).join(' + '),
        field_type: 'composite',
        is_primary_key: true,
        is_composite: true,
        _pkFieldIds: pkFields.map((f: any) => f.id),
      }
      displayFields = [compositeField, ...nonPkFields]
    } else {
      displayFields = rawFields
    }
    // 保存 displayFields 供边绘制时使用
    tableFieldsMap.set(tid, displayFields)

    // 收集参与映射的字段 id（高亮用）
    const mappedFieldIds = new Set<number>()
    const mappedComposite = { source: false, target: false }
    mappings.value.forEach((m) => {
      if (m.source_table === tid) {
        if (pkFields.length >= 2 && pkFields.some((pf: any) => pf.id === m.source_field)) {
          mappedComposite.source = true
          mappedFieldIds.add('composite_pk' as any)
        } else {
          mappedFieldIds.add(m.source_field)
        }
      }
      if (m.target_table === tid) {
        if (pkFields.length >= 2 && pkFields.some((pf: any) => pf.id === m.target_field)) {
          mappedComposite.target = true
          mappedFieldIds.add('composite_pk' as any)
        } else {
          mappedFieldIds.add(m.target_field)
        }
      }
    })

    // 构建字段行 HTML：中文名优先，英文名括号补充
    const fieldRows = displayFields.length > 0
      ? displayFields.map((f: any) => {
          const isKey = mappedFieldIds.has(f.id) || (f.is_composite && (mappedComposite.source || mappedComposite.target))
          const typeShort = ({ string: 'varchar', number: 'int', date: 'date', boolean: 'bool', enum: 'enum', composite: '⚿联合' } as any)[f.field_type] || f.field_type
          const typeLabel = f.length ? `${typeShort}(${f.length})` : typeShort
          // 中文名优先展示：comment（中文注释）> name > code
          // 外部数据源同步时 name/code 都是英文列名，中文描述在 comment 中
          const displayName = f.comment || f.name || f.code || ''
          const subName = f.code && f.code !== displayName ? escapeHtml(f.code) : ''
          const cnName = escapeHtml(displayName)
          const enName = subName
          const nameHtml = enName
            ? `<div class="er-f__name-cn" title="${cnName} (${enName})">${cnName}</div><div class="er-f__name-en">${enName}</div>`
            : `<div class="er-f__name-cn" title="${cnName}">${cnName}</div>`
          return `
            <div class="er-f${isKey ? ' er-f--key' : ''}${f.is_composite ? ' er-f--composite' : ''}" data-field-id="${f.id}">
              <span class="er-f__icon">${isKey ? '⚿' : '○'}</span>
              <div class="er-f__name-wrap">${nameHtml}</div>
              <span class="er-f__type">${escapeHtml(typeLabel)}</span>
            </div>
          `
        }).join('')
      : '<div class="er-f er-f--empty">暂无字段</div>'

    // 预组合标签（Issue 8: ER图展示组合表效果）
    const pcDetails = headerTableToDetails[tid]
    const pcHeaderName = detailTableToHeaders[tid]
    let precombineHtml = ''
    if (pcDetails) {
      // 头表：显示预组合标签 + 明细表名列表
      const detailNames = pcDetails.map((dc: any) => escapeHtml(dc.table_name)).join(', ')
      precombineHtml = `<div style="display: flex; flex-wrap: wrap; gap: 4px; padding: 2px 12px 6px">
        <span style="display: inline-block; background: #52c41a; color: #fff; font-size: 11px; padding: 0 6px; border-radius: 2px; line-height: 20px; font-weight: 500">预组合</span>
        <span style="font-size: 11px; color: #52c41a; line-height: 20px">包含：${detailNames}</span>
      </div>`
    } else if (pcHeaderName) {
      // 明细表：显示预组合标签 + 头表名
      precombineHtml = `<div style="display: flex; flex-wrap: wrap; gap: 4px; padding: 2px 12px 6px">
        <span style="display: inline-block; background: #e6f7ff; color: #13c2c2; font-size: 11px; padding: 0 6px; border-radius: 2px; line-height: 20px; font-weight: 500">预组合</span>
        <span style="font-size: 11px; color: #13c2c2; line-height: 20px">头表：${escapeHtml(pcHeaderName)}</span>
      </div>`
    }

    const nodeHtml = `
      <div class="er-node">
        <div class="er-node__header">
          <span class="er-node__icon">🗂</span>
          <div class="er-node__title-wrap">
            <div class="er-node__name">${escapeHtml(t?.name || `表#${tid}`)}</div>
            <div class="er-node__code">${escapeHtml(t?.code || '')}</div>
          </div>
        </div>
        ${precombineHtml}
        <div class="er-node__body">${fieldRows}</div>
      </div>
    `

    // 节点高度：显示所有字段（不截断）
    const nodeHeight = ER_HEADER_HEIGHT + Math.max(1, displayFields.length) * ER_ROW_HEIGHT + 4

    const shapeName = `er-table-${tid}`
    Shape.HTML.register({
      shape: shapeName,
      html: nodeHtml,
    })

    // 使用保存的位置或自动布局
    const savedX = t?.er_node_x
    const savedY = t?.er_node_y
    let nodeX: number, nodeY: number
    if (savedX != null && savedY != null) {
      nodeX = savedX
      nodeY = savedY
    } else {
      nodeX = startX + col * (nodeWidth + gapX)
      nodeY = y
    }

    const node = graph!.addNode({
      x: nodeX,
      y: nodeY,
      width: nodeWidth,
      height: nodeHeight,
      shape: shapeName,
      attrs: {
        body: { fill: '#ffffff', stroke: '#c9cdd4', rx: 4, ry: 4, strokeWidth: 1 },
        label: { text: '' },
      },
    })
    nodeMap[tid] = node.id
    erNodeMap[tid] = { node, tableId: tid, tableRef: t }

    node.on('change:position', () => {
      saveErNodePosition(tid, node, t)
    })

    if (savedX == null || savedY == null) {
      colY[col] = nodeY + nodeHeight + gapY
    }
  })

  // 构建字段索引映射（用于边锚点计算）
  // displayFields 已包含虚拟联合主键字段，需处理复合PK字段到虚拟字段的映射
  const fieldIndexMap = new Map<number, Map<number, number>>()
  const compositePkTables = new Set<number>()
  tableFieldsMap.forEach((fields, tid) => {
    const idxMap = new Map<number, number>()
    fields.forEach((f, idx) => {
      idxMap.set(f.id, idx)
      if (f.is_composite) compositePkTables.add(tid)
    })
    fieldIndexMap.set(tid, idxMap)
  })

  // 绘制边：列表有多少行，ER 图就有多少条线（联合主键=一条）
  // 注意：top 锚点的 dx/dy 是比例值(0-1)，不是像素值
  // dx: 0.5 = 右边缘, dx: -0.5 = 左边缘
  // dy: ratio = 像素偏移 / 节点高度
  mappingRows.value.forEach((m) => {
    const sourceIsCompositePk = compositePkTables.has(m.source_table)
    const targetIsCompositePk = compositePkTables.has(m.target_table)

    let sourceIdx = fieldIndexMap.get(m.source_table)?.get(m.source_field) ?? 0
    let targetIdx = fieldIndexMap.get(m.target_table)?.get(m.target_field) ?? 0

    // 联合主键行：指向虚拟联合主键字段（index 0）
    if (m.is_composite) {
      if (sourceIsCompositePk) sourceIdx = 0
      if (targetIsCompositePk) targetIdx = 0
    }

    // 计算节点高度（用于 dy 比例换算）
    const sourceFieldsCount = tableFieldsMap.get(m.source_table)?.length ?? 1
    const targetFieldsCount = tableFieldsMap.get(m.target_table)?.length ?? 1
    const sourceNodeHeight = ER_HEADER_HEIGHT + Math.max(1, sourceFieldsCount) * ER_ROW_HEIGHT + 4
    const targetNodeHeight = ER_HEADER_HEIGHT + Math.max(1, targetFieldsCount) * ER_ROW_HEIGHT + 4

    // 字段行中心 Y 像素偏移 → 转为比例值
    const sourceFieldY = ER_HEADER_HEIGHT + sourceIdx * ER_ROW_HEIGHT + ER_ROW_HEIGHT / 2
    const targetFieldY = ER_HEADER_HEIGHT + targetIdx * ER_ROW_HEIGHT + ER_ROW_HEIGHT / 2

    graph!.addEdge({
      source: {
        cell: nodeMap[m.source_table],
        anchor: {
          name: 'top',
          args: {
            dx: 0.5,  // 右边缘
            dy: sourceFieldY / sourceNodeHeight,
          },
        },
      },
      target: {
        cell: nodeMap[m.target_table],
        anchor: {
          name: 'top',
          args: {
            dx: -0.5, // 左边缘
            dy: targetFieldY / targetNodeHeight,
          },
        },
      },
      router: { name: 'manhattan', args: { padding: 16 } },
      connector: { name: 'rounded', args: { radius: 6 } },
      attrs: {
        line: {
          stroke: '#faad14',
          strokeWidth: 1.5,
          targetMarker: { name: 'block', size: 8, fill: '#faad14' },
        },
      },
    })
  })

  // 绘制预组合（头表↔明细表）关联虚线（Issue 1: ER图展现预组合概念）
  const precombineTableIds = new Set<number>()
  domainDetailConfigs.value.forEach((dc: any) => {
    if (!dc.header_table || !dc.table) return
    precombineTableIds.add(dc.header_table)
    precombineTableIds.add(dc.table)
    const srcNodeId = nodeMap[dc.header_table]
    const tgtNodeId = nodeMap[dc.table]
    if (srcNodeId && tgtNodeId) {
      graph!.addEdge({
        source: { cell: srcNodeId, anchor: { name: 'top', args: { dx: 0.8, dy: 0.05 } } },
        target: { cell: tgtNodeId, anchor: { name: 'top', args: { dx: 0.8, dy: 0.05 } } },
        router: { name: 'manhattan', args: { padding: 16 } },
        connector: { name: 'rounded', args: { radius: 6 } },
        attrs: {
          line: {
            stroke: '#52c41a',
            strokeWidth: 1.5,
            strokeDasharray: '5,5',
            targetMarker: { name: 'block', size: 6, fill: '#52c41a' },
          },
        },
        labels: [{
          attrs: {
            text: { text: '预组合', fill: '#52c41a', fontSize: 11 },
          },
          position: { distance: 0.5 },
        }],
      })
    }
  })

  // Issue 3: 预组合表高亮——边框变绿
  if (erHighlightPrecombine.value) {
    precombineTableIds.forEach((tid) => {
      const entry = erNodeMap[tid]
      if (entry) {
        const view = graph!.findViewByCell(entry.node.id)
        if (view) {
          const el = view.container as HTMLElement
          el.style.border = '2px solid #52c41a'
          el.style.boxShadow = '0 0 8px rgba(82, 196, 26, 0.4)'
          el.style.borderRadius = '4px'
        }
      }
    })
  }
}

function escapeHtml(s: string) {
  return String(s).replace(/[<>&"]/g, (c) => ({ '<': '&lt;', '>': '&gt;', '&': '&amp;', '"': '&quot;' }[c]!))
}

// 点击选择源表（替代原下拉选择）
function selectSourceTable(tableId: number) {
  if (form.value.source_table === tableId) return
  form.value.source_table = tableId
  form.value.source_field = null as any
  loadSourceFields()
}

async function loadSourceFields() {
  if (form.value.source_table) {
    let results: any[] = []
    const res = await fieldApi.list({ table: form.value.source_table })
    results = res.data.results
    // 预组合（2026-08-11 第三轮）：头表字段并入字段池（平铺），支持头表字段作挂载关联键
    const cfg = form.value.detail_config ? domainDetailConfigs.value.find((c: any) => c.id === form.value.detail_config) : null
    if (form.value.relation_type === 'detail' && cfg?.header_table) {
      const hres = await fieldApi.list({ table: cfg.header_table })
      results = results.concat(hres.data.results)
    }
    sourceFields.value = results.sort((a: any, b: any) => (b.is_primary_key ? 1 : 0) - (a.is_primary_key ? 1 : 0))
    if (form.value.relation_type === 'detail') {
      // 明细子表：关联字段自动推荐（用户可改，touched 后不覆盖）
      applyDetailRecommendation()
    } else {
      // 自动选中：联合主键选 'composite'，单主键选该字段
      const pkFields = sourceFields.value.filter((f: any) => f.is_primary_key)
      if (pkFields.length >= 2) {
        form.value.source_field = 'composite'
      } else if (pkFields.length === 1) {
        form.value.source_field = pkFields[0].id
      } else {
        form.value.source_field = null
      }
    }
  }
}

// 点击选择目标表（替代原下拉选择）
function selectTargetTable(tableId: number) {
  if (form.value.target_table === tableId) return
  form.value.target_table = tableId
  form.value.target_field = null as any
  loadTargetFields()
}

async function loadTargetFields() {
  if (form.value.target_table) {
    const res = await fieldApi.list({ table: form.value.target_table })
    targetFields.value = res.data.results.sort((a: any, b: any) => (b.is_primary_key ? 1 : 0) - (a.is_primary_key ? 1 : 0))
    const pkFields = targetFields.value.filter((f: any) => f.is_primary_key)
    if (form.value.relation_type === 'detail') {
      // 明细子表挂载：目标字段=主表单一主键（联合主键不支持挂载）
      form.value.target_field = pkFields.length === 1 ? pkFields[0].id : null
      // 主表变化后重新推荐关联字段
      applyDetailRecommendation()
    } else if (pkFields.length >= 2) {
      form.value.target_field = 'composite'
    } else if (pkFields.length === 1) {
      form.value.target_field = pkFields[0].id
    } else {
      form.value.target_field = null
    }
  }
}

async function aiAutoMapping() {
  aiMappingLoading.value = true
  aiSuggestions.value = []
  selectedAiSuggestions.value = []
  aiModalVisible.value = true
  try {
    const res = await fieldMappingApi.inferMappings(domainId)
    const suggestions = res.data.suggestions || []
    // 为每条建议生成唯一行键
    aiSuggestions.value = suggestions.map((s, idx) => ({
      ...s,
      rowKey: `${s.source_table_id}-${s.source_field_id}-${s.target_table_id}-${s.target_field_id}-${idx}`,
    }))
    // 默认选中置信度 >= 0.7 的建议
    selectedAiSuggestions.value = aiSuggestions.value
      .filter((s) => s.confidence >= 0.7)
      .map((s) => s.rowKey)
  } catch (e: any) {
    message.error(extractApiError(e) || 'AI 分析失败')
    aiModalVisible.value = false
  } finally {
    aiMappingLoading.value = false
  }
}

function selectAllAiSuggestions() {
  selectedAiSuggestions.value = aiSuggestions.value.map((s) => s.rowKey)
}

async function createSelectedMappings() {
  if (selectedAiSuggestions.value.length === 0) return
  aiCreating.value = true
  const selected = aiSuggestions.value.filter((s) => selectedAiSuggestions.value.includes(s.rowKey))
  let successCount = 0
  let failCount = 0
  const errors: string[] = []
  try {
    for (const s of selected) {
      try {
        await fieldMappingApi.create({
          source_table: s.source_table_id,
          source_field: s.source_field_id,
          target_table: s.target_table_id,
          target_field: s.target_field_id,
        })
        successCount++
      } catch (e: any) {
        failCount++
        const srcLabel = `${s.source_table_name}.${s.source_field_code}`
        const tgtLabel = `${s.target_table_name}.${s.target_field_code}`
        errors.push(`${srcLabel} → ${tgtLabel}: ${extractApiError(e) || '创建失败'}`)
      }
    }
    if (failCount === 0) {
      message.success(`成功创建 ${successCount} 条映射关系`)
    } else {
      message.warning(`成功 ${successCount} 条，失败 ${failCount} 条`)
      if (errors.length > 0) {
        Modal.warning({
          title: '部分映射创建失败',
          content: h('div', { style: 'max-height: 200px; overflow-y: auto' },
            errors.map((e, i) => h('div', { key: i }, e))
          ),
        })
      }
    }
    aiModalVisible.value = false
    await loadData()
  } finally {
    aiCreating.value = false
  }
}

function openCreate() {
  editingMappingId.value = null
  editingMappingIds.value = []
  sourceFieldTouched.value = false
  form.value = {
    source_table: null, source_field: null, target_table: null, target_field: null,
    relation_type: 'reference',
    join_type: 'left',
    row_key_field: null,
    display_sort_field: null,
    display_sort_desc: true,
    conditionsText: '',
    detail_config: null,
  }
  sourceFields.value = []
  targetFields.value = []
  modalVisible.value = true
}

async function openEdit(row: any) {
  editingMappingIds.value = row.mapping_ids || [row.id]
  editingMappingId.value = editingMappingIds.value[0] || null
  // 编辑模式恢复原关联字段，禁止自动推荐覆盖
  sourceFieldTouched.value = true

  form.value = {
    source_table: row.source_table,
    source_field: null,
    target_table: row.target_table,
    target_field: null,
    relation_type: row.relation_type || 'reference',
    join_type: row.join_type || 'left',
    row_key_field: row.row_key_field || null,
    display_sort_field: row.display_sort_field || null,
    display_sort_desc: row.display_sort_desc !== false,
    conditionsText: '',
    detail_config: row.detail_config_id || row.detail_config || null,
  }
  
  // 解析 conditions JSON 为文本
  if (row.conditions) {
    try {
      form.value.conditionsText = JSON.stringify(row.conditions)
    } catch { /* 保持空 */ }
  }
  
  // 加载源字段和目标字段
  await Promise.all([loadSourceFields(), loadTargetFields()])
  
  // 恢复选中值（loadXxxFields 会覆盖 form 值，需要重新设置）
  if (row.is_composite) {
    // 联合主键行：源/目标均选中虚拟联合主键选项
    form.value.source_field = 'composite'
    form.value.target_field = 'composite'
  } else {
    form.value.source_field = row.source_field
    form.value.target_field = row.target_field
  }
  
  modalVisible.value = true
}

// 唯一性预检：四元组与已存在映射重复时拦截并提示（2026-08-11 第一百四十三轮，方案A前端预检）
// 排除编辑中的自身；composite 联合主键展开为逐对检查
function checkMappingDuplicates(): boolean {
  const pairs: { st: number; sf: number | string; tt: number; tf: number | string }[] = []
  const preSourceIsComposite = form.value.source_field === 'composite'
  const preTargetIsComposite = form.value.target_field === 'composite'
  if (preSourceIsComposite && preTargetIsComposite) {
    const sourcePks = sourceFields.value.filter((f: any) => f.is_primary_key)
    const targetPks = targetFields.value.filter((f: any) => f.is_primary_key)
    const count = Math.min(sourcePks.length, targetPks.length)
    for (let i = 0; i < count; i++) pairs.push({ st: form.value.source_table, sf: sourcePks[i].id, tt: form.value.target_table, tf: targetPks[i].id })
  } else if (preSourceIsComposite) {
    for (const pk of sourceFields.value.filter((f: any) => f.is_primary_key)) pairs.push({ st: form.value.source_table, sf: pk.id, tt: form.value.target_table, tf: form.value.target_field })
  } else if (preTargetIsComposite) {
    for (const pk of targetFields.value.filter((f: any) => f.is_primary_key)) pairs.push({ st: form.value.source_table, sf: form.value.source_field, tt: form.value.target_table, tf: pk.id })
  } else {
    pairs.push({ st: form.value.source_table, sf: form.value.source_field, tt: form.value.target_table, tf: form.value.target_field })
  }
  for (const p of pairs) {
    for (const m of mappings.value) {
      if (editingMappingIds.value.includes(m.id)) continue
      if (m.source_table === p.st && String(m.source_field) === String(p.sf) &&
          m.target_table === p.tt && String(m.target_field) === String(p.tf)) {
        message.warning(`该关系已存在：${m.source_table_name}.${m.source_field_name} → ${m.target_table_name}.${m.target_field_name}（ID=${m.id}）；如需修改请在列表中找到该关系并编辑，不要重复创建`)
        return true
      }
    }
  }
  return false
}

async function handleSubmit() {
  if (form.value.relation_type === 'detail') {
    if (!form.value.target_table) {
      message.warning('请选择主表')
      return
    }
    if (!form.value.detail_config) {
      message.warning('请选择已注册的子表（未注册的请先通过「子表注册」创建）')
      return
    }
    if (!form.value.source_field) {
      message.warning('请选择关联字段')
      return
    }
    if (!form.value.target_field) {
      message.warning('主表需要配置单一主键字段，请先在表配置中设置主表主键')
      return
    }
  } else {
    if (!form.value.source_table || !form.value.target_table) {
      message.warning('请选择源表和目标表')
      return
    }
    if (!form.value.source_field || !form.value.target_field) {
      message.warning('请选择源字段和目标字段')
      return
    }
  }
  // 唯一性预检：重复关系直接拦截，不等后端报错
  if (checkMappingDuplicates()) return
  saving.value = true
  try {
    // R-021: 先建后删——创建新映射成功后再删除旧映射，避免创建失败时数据丢失
    // 补充：编辑模式且四元组未变化时，跳过建删，直接更新现有记录（防 unique_together 冲突）
    const sourceIsComposite = form.value.source_field === 'composite'
    const targetIsComposite = form.value.target_field === 'composite'

    // 辅助函数：查找编辑中与该四元组匹配的现有映射 ID
    function findEditingMappingId(sourceTable: number, sourceField: number | string, targetTable: number, targetField: number | string): number | null {
      if (editingMappingIds.value.length === 0) return null
      for (const m of mappings.value) {
        if (editingMappingIds.value.includes(m.id) &&
            m.source_table === sourceTable &&
            String(m.source_field) === String(sourceField) &&
            m.target_table === targetTable &&
            String(m.target_field) === String(targetField)) {
          return m.id
        }
      }
      return null
    }
    
    const createdIds: number[] = []
    
    if (sourceIsComposite && targetIsComposite) {
      const sourcePks = sourceFields.value.filter((f: any) => f.is_primary_key)
      const targetPks = targetFields.value.filter((f: any) => f.is_primary_key)
      const count = Math.min(sourcePks.length, targetPks.length)
      for (let i = 0; i < count; i++) {
        const existingId = findEditingMappingId(form.value.source_table, sourcePks[i].id, form.value.target_table, targetPks[i].id)
        if (existingId) {
          createdIds.push(existingId)
        } else {
          const res = await fieldMappingApi.create({
            source_table: form.value.source_table,
            source_field: sourcePks[i].id,
            target_table: form.value.target_table,
            target_field: targetPks[i].id,
            join_type: form.value.join_type,
          })
          createdIds.push(res.data.id)
        }
      }
    } else if (sourceIsComposite) {
      const sourcePks = sourceFields.value.filter((f: any) => f.is_primary_key)
      for (const pk of sourcePks) {
        const existingId = findEditingMappingId(form.value.source_table, pk.id, form.value.target_table, form.value.target_field)
        if (existingId) {
          createdIds.push(existingId)
        } else {
          const res = await fieldMappingApi.create({
            source_table: form.value.source_table,
            source_field: pk.id,
            target_table: form.value.target_table,
            target_field: form.value.target_field,
            join_type: form.value.join_type,
          })
          createdIds.push(res.data.id)
        }
      }
    } else if (targetIsComposite) {
      const targetPks = targetFields.value.filter((f: any) => f.is_primary_key)
      for (const pk of targetPks) {
        const existingId = findEditingMappingId(form.value.source_table, form.value.source_field, form.value.target_table, pk.id)
        if (existingId) {
          createdIds.push(existingId)
        } else {
          const res = await fieldMappingApi.create({
            source_table: form.value.source_table,
            source_field: form.value.source_field,
            target_table: form.value.target_table,
            target_field: pk.id,
            join_type: form.value.join_type,
          })
          createdIds.push(res.data.id)
        }
      }
    } else {
      const existingId = findEditingMappingId(form.value.source_table, form.value.source_field, form.value.target_table, form.value.target_field)
      if (existingId) {
        createdIds.push(existingId)
      } else {
        const res = await fieldMappingApi.create({
          source_table: form.value.source_table,
          source_field: form.value.source_field,
          target_table: form.value.target_table,
          target_field: form.value.target_field,
          join_type: form.value.join_type,
        })
        createdIds.push(res.data.id)
      }
    }

    // 仅删除未被复用的旧映射（四元组未变化的映射跳过删除）
    const idsToDelete = editingMappingIds.value.filter(id => !createdIds.includes(id))
    for (const id of idsToDelete) {
      await fieldMappingApi.delete(id)
    }

    // 批3a：更新 detail 配置（新范式优先 detail_config，旧 inline 字段 deprecated 兼容）
    if (createdIds.length > 0) {
      if (form.value.relation_type === 'detail') {
        const detailData: Record<string, any> = { relation_type: 'detail', join_type: form.value.join_type }
        // 新范式：挂载 detail_config（优先）
        if (form.value.detail_config) {
          detailData.detail_config = form.value.detail_config
        }
        // 兼容旧范式：inline 字段（已 deprecated，存量兼容）
        if (form.value.row_key_field) detailData.row_key_field = form.value.row_key_field
        if (form.value.display_sort_field) detailData.display_sort_field = form.value.display_sort_field
        detailData.display_sort_desc = form.value.display_sort_desc
        if (form.value.conditionsText) {
          try {
            detailData.conditions = JSON.parse(form.value.conditionsText)
          } catch { /* 格式错误，保持 null */ }
        }
        for (const id of createdIds) {
          await fieldMappingApi.update(id, detailData)
        }
      } else {
        // 引用类型，清除可能遗留的 detail 配置
        for (const id of createdIds) {
          await fieldMappingApi.update(id, {
            relation_type: 'reference',
            join_type: form.value.join_type,
            detail_config: null,
            row_key_field: null,
            display_sort_field: null,
            display_sort_desc: false,
            conditions: null,
          })
        }
      }
    }
    
    message.success(editingMappingIds.value.length > 0 ? '映射更新成功' : '映射创建成功')
    modalVisible.value = false
    editingMappingId.value = null
    editingMappingIds.value = []
    await loadData()
  } catch (e: any) {
    message.error(extractApiError(e) || '操作失败')
  } finally {
    saving.value = false
  }
}

async function detectRowKey() {
  if (!editingMappingId.value) return
  detectingRowKey.value = true
  try {
    const res = await fieldMappingApi.detectRowKey(editingMappingId.value)
    const { candidate, total_rows, column_count, note } = res.data
    if (candidate) {
      // 在 sourceFields 中匹配候选字段
      const matched = sourceFields.value.find((f: any) => f.code === candidate)
      if (matched) {
        form.value.row_key_field = matched.id
      }
      message.success(`检测完成：推荐行键「${candidate}」（共 ${total_rows} 行，${column_count} 列）${note ? '，' + note : ''}`)
    } else {
      message.warning('未检测到合适的行键字段，请手动选择')
    }
  } catch (e: any) {
    message.error(extractApiError(e) || '行键检测失败')
  } finally {
    detectingRowKey.value = false
  }
}

// ===== 子表注册管理函数 =====

async function loadDetailConfigs() {
  try {
    const res = await detailConfigApi.list({ domain: domainId })
    domainDetailConfigs.value = res.data.results || []
  } catch { /* 静默 */ }
}

function openDetailConfigList() {
  dcListModalVisible.value = true
  loadDetailConfigs()
}

function openDetailConfigCreate() {
  dcEditingId.value = null
  dcForm.value = {
    header_table: null, table: null,
    header_link_field: null, detail_link_field: null,
    row_key_field: null, conditionsText: '',
  }
  dcConditions.value = []
  dcSourceFields.value = []
  dcHeaderFields.value = []
  dcModalVisible.value = true
}

async function openDetailConfigEdit(cfg: any) {
  dcEditingId.value = cfg.id
  dcForm.value = {
    header_table: cfg.header_table,
    table: cfg.table,
    header_link_field: cfg.header_link_field,
    detail_link_field: cfg.detail_link_field,
    row_key_field: cfg.row_key_field || null,
    join_type: cfg.join_type || 'left',
    conditionsText: '',
  }
  // 回填条件行（结构化 -> 可视化行列表）
  dcConditions.value = cfg.conditions?.length
    ? cfg.conditions.map((c: any) => ({ field: c.field, operator: c.operator, value: c.value ?? '', fieldSource: c.field_source || 'detail' }))
    : []
  dcSourceFields.value = []
  dcHeaderFields.value = []
  if (cfg.header_table) {
    try {
      const [hres, sres] = await Promise.all([
        fieldApi.list({ table: cfg.header_table }),
        fieldApi.list({ table: cfg.table }),
      ])
      dcHeaderFields.value = hres.data.results
      dcSourceFields.value = sres.data.results
    } catch { /* 静默 */ }
  }
  dcModalVisible.value = true
}

async function removeDetailConfig(cfg: any) {
  try {
    await detailConfigApi.delete(cfg.id)
    message.success('注册已删除')
    await loadDetailConfigs()
  } catch (e: any) {
    message.error(extractApiError(e) || '删除失败')
  }
}

async function onDcHeaderChange() {
  if (dcForm.value.header_table) {
    const res = await fieldApi.list({ table: dcForm.value.header_table })
    dcHeaderFields.value = res.data.results
  } else {
    dcHeaderFields.value = []
  }
}

// 头表点击选择（替代 a-select 下拉）
function selectDcHeaderTable(tableId: number) {
  if (dcEditingId.value) return
  if (dcForm.value.header_table === tableId) return
  dcForm.value.header_table = tableId
  dcForm.value.header_link_field = null
  onDcHeaderChange()
  // 头表+明细表都选好时自动检测关联字段
  if (dcForm.value.table && !dcForm.value.detail_link_field) {
    detectDcLink()
  }
}

async function onDcTableChange() {
  if (dcForm.value.table) {
    const res = await fieldApi.list({ table: dcForm.value.table })
    dcSourceFields.value = res.data.results
    // 头表+明细表都选好时自动检测关联字段（预组合语义，2026-08-11 第三轮）
    if (dcForm.value.header_table && !dcForm.value.detail_link_field) {
      detectDcLink()
    }
  } else {
    dcSourceFields.value = []
  }
}

// 明细表点击选择（替代 a-select 下拉）
function selectDcDetailTable(tableId: number) {
  if (dcEditingId.value) return
  if (dcRegisteredMap.value[tableId] && dcForm.value.table !== tableId) return
  if (dcForm.value.table === tableId) return
  dcForm.value.table = tableId
  dcForm.value.detail_link_field = null
  onDcTableChange()
}

async function detectDcLink() {
  if (!dcForm.value.header_table || !dcForm.value.table) {
    message.warning('请先选择头表和明细表')
    return
  }
  dcDetectingLink.value = true
  try {
    const res = await detailConfigApi.detectHeaderLink({
      header_table: dcForm.value.header_table,
      detail_table: dcForm.value.table,
    })
    const { header_link_field, detail_link_field, matched_by, note } = res.data
    if (header_link_field && detail_link_field) {
      dcForm.value.header_link_field = header_link_field
      dcForm.value.detail_link_field = detail_link_field
      message.success(`自动检测关联字段成功（${matched_by === '同名' ? '同名' : matched_by === '后缀' ? 'ID↔FID 后缀' : '手动'}匹配）${note ? '，' + note : ''}`)
    } else {
      message.warning(note || '自动检测未命中，请手动选择关联字段')
    }
  } catch (e: any) {
    message.error(extractApiError(e) || '关联字段检测失败')
  } finally {
    dcDetectingLink.value = false
  }
}

async function handleDcSubmit() {
  if (!dcForm.value.header_table || !dcForm.value.table) {
    message.warning('请选择头表和明细表')
    return
  }
  if (!dcForm.value.header_link_field || !dcForm.value.detail_link_field) {
    message.warning('请配置头↔明细关联字段')
    return
  }
  dcSaving.value = true
  try {
    const payload: Record<string, any> = {
      header_table: dcForm.value.header_table,
      table: dcForm.value.table,
      header_link_field: dcForm.value.header_link_field,
      detail_link_field: dcForm.value.detail_link_field,
      row_key_field: dcForm.value.row_key_field || null,
      join_type: dcForm.value.join_type || 'left',
    }
    // 条件行 -> JSON
    if (dcConditions.value.length > 0) {
      payload.conditions = dcConditions.value.map(c => ({
        field: c.field,
        operator: c.operator,
        value: c.operator === 'in' ? (Array.isArray(c.value) ? c.value : []) : c.value,
        field_source: c.fieldSource || 'detail',
      }))
    }
    payload.domain = domainId

    if (dcEditingId.value) {
      await detailConfigApi.update(dcEditingId.value, payload)
    } else {
      await detailConfigApi.create(payload)
    }
    message.success(dcEditingId.value ? '子表配置更新成功' : '预组合注册成功')
    dcModalVisible.value = false
    await loadDetailConfigs()
  } catch (e: any) {
    message.error(extractApiError(e) || '保存失败')
  } finally {
    dcSaving.value = false
  }
}

async function detectDcRowKey() {
  if (!dcEditingId.value) return
  dcDetectingRowKey.value = true
  try {
    const res = await detailConfigApi.detectRowKey(dcEditingId.value)
    const { candidate, total_rows, note } = res.data
    if (candidate) {
      const matched = dcSourceFields.value.find((f: any) => f.code === candidate)
      if (matched) { dcForm.value.row_key_field = matched.id }
      message.success(`检测完成：推荐行键「${candidate}」（共 ${total_rows} 行）${note ? '，' + note : ''}`)
    } else {
      message.warning('未检测到合适的行键字段')
    }
  } catch (e: any) {
    message.error(extractApiError(e) || '行键检测失败')
  } finally {
    dcDetectingRowKey.value = false
  }
}

function addDcCondition() {
  dcConditions.value.push({ field: '', operator: 'eq', value: '', fieldSource: 'detail' })
}

function removeDcCondition(idx: number) {
  dcConditions.value.splice(idx, 1)
}

function onDetailConfigChange(configId: number | undefined) {
  form.value.detail_config = configId || null
  const cfg = configId ? domainDetailConfigs.value.find((c: any) => c.id === configId) : null
  if (cfg?.table) {
    // 挂载语义：源表=子表注册的表，方向由系统处理（用户只关心主表）
    if (form.value.target_table === cfg.table) {
      form.value.target_table = null // 主表不能是子表自身
    }
    form.value.source_table = cfg.table
    form.value.source_field = null
    sourceFields.value = []
    sourceFieldTouched.value = false // 换子表后重新推荐
    loadSourceFields()
  } else {
    form.value.source_table = null
    form.value.source_field = null
    sourceFields.value = []
    sourceFieldTouched.value = false
  }
}

function onDetailSourceFieldChange() {
  sourceFieldTouched.value = true
}

function applyDetailRecommendation() {
  if (sourceFieldTouched.value) return
  form.value.source_field = detailRecommendedFieldId.value
}

async function loadDetailCheck() {
  detailCheckLoading.value = true
  try {
    const res = await fieldMappingApi.detailCheck(domainId)
    detailCheckData.value = res.data
  } catch (e: any) {
    message.error(extractApiError(e) || '检查失败')
  } finally {
    detailCheckLoading.value = false
  }
}

function onRelationTypeChange(value: string) {
  if (value === 'reference') {
    form.value.row_key_field = null
    form.value.display_sort_field = null
    form.value.display_sort_desc = true
    form.value.conditionsText = ''
    form.value.detail_config = null
  } else {
    // 明细子表：源表/源字段由子表决定，清空待选
    form.value.source_table = null
    form.value.source_field = null
    form.value.row_key_field = null
    form.value.display_sort_field = null
    form.value.display_sort_desc = true
    form.value.conditionsText = ''
    form.value.detail_config = null
    sourceFields.value = []
    sourceFieldTouched.value = false
    if (form.value.target_table) loadTargetFields() // 重置目标字段为主表主键
  }
}

function confirmDeleteMapping(row: any) {
  Modal.confirm({
    title: '确认删除此映射？',
    content: '删除后源表与目标表的字段映射关系将被清除，需要重新创建。',
    okText: '确认删除', okType: 'danger', cancelText: '取消',
    onOk: () => doDelete(row),
  })
}

async function doDelete(row: any) {
  try {
    const ids = row.mapping_ids || [row.id]
    for (const id of ids) {
      await fieldMappingApi.delete(id)
    }
    message.success('删除成功')
    await loadData()
  } catch (e: any) {
    message.error(extractApiError(e) || '删除失败')
  }
}

function toggleErHighlightPrecombine() {
  erHighlightPrecombine.value = !erHighlightPrecombine.value
  renderER()
}

async function resetErLayout() {
  resettingEr.value = true
  try {
    await tableApi.batchResetErPosition(domainId)
    const tablesRes = await tableApi.list({ domain: domainId })
    domainTables.value = tablesRes.data.results
    message.success('布局已重置')
    await nextTick()
    renderER()
  } catch (e: any) {
    message.error(extractApiError(e) || '重置失败')
  } finally {
    resettingEr.value = false
  }
}

onMounted(() => {
  loadData()
  // Issue 2：监听浏览器全屏/退出事件
  document.addEventListener('fullscreenchange', onFullscreenChange)
})

// 监听 detail-check 打开时重新加载（用户手动打开抽屉时刷新数据）
watch(showDetailCheck, (val) => {
  if (val) loadDetailCheck()
})

// 监听子表注册弹窗的表切换
watch(() => dcForm.value.table, (val) => {
  if (val) {
    onDcTableChange()
  } else {
    dcSourceFields.value = []
  }
})

// 监听子表注册弹窗的头表切换
watch(() => dcForm.value.header_table, (val) => {
  if (val) {
    onDcHeaderChange()
  } else {
    dcHeaderFields.value = []
  }
})

function onFullscreenChange() {
  if (!document.fullscreenElement && erFullScreen.value) {
    erFullScreen.value = false
    nextTick(() => {
      if (mappings.value.length > 0) renderER()
    })
  }
}

function toggleErFullScreen() {
  if (!erContainer.value) return
  if (document.fullscreenElement) {
    document.exitFullscreen()
    // fullscreenchange 事件处理程序会自动同步状态
  } else {
    erContainer.value.requestFullscreen().then(() => {
      erFullScreen.value = true
      nextTick(() => renderER())
    }).catch(() => {
      // Fullscreen API 不可用时的回退
      erFullScreen.value = !erFullScreen.value
      nextTick(() => renderER())
    })
  }
}

onBeforeUnmount(() => {
  document.removeEventListener('fullscreenchange', onFullscreenChange)
  for (const tid of Object.keys(erNodeMap)) {
    const { node, tableRef } = erNodeMap[Number(tid)]
    if (node && graph) {
      saveErNodePosition(Number(tid), node, tableRef)
    }
  }
})
</script>

<style scoped>
/* detail 子表关系行浅蓝底（第一百四十四轮直观性改进） */
:deep(.mapping-row-detail) > td {
  background: #f0f7ff !important;
}
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  flex-wrap: wrap;
}
.er-container {
  width: 100%;
  height: 600px;
  border: 1px solid #eef0f4;
  border-radius: 8px;
  background: #fafbfc;
}
.er-container--full {
  height: calc(100vh - 220px);
  min-height: 500px;
}

/* ER 图节点样式 */
:deep(.er-node) {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  background: #fff;
  border-radius: 4px;
  overflow: hidden;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.08);
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  transition: box-shadow 0.2s ease;
}
:deep(.er-node:hover) {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.12);
}
:deep(.er-node__header) {
  background: linear-gradient(135deg, #5b8def 0%, #4a7bd8 100%);
  color: #fff;
  padding: 8px 12px;
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}
:deep(.er-node__icon) {
  font-size: 16px;
  flex-shrink: 0;
}
:deep(.er-node__title-wrap) {
  flex: 1;
  min-width: 0;
}
:deep(.er-node__name) {
  font-weight: 600;
  font-size: 13px;
  line-height: 1.3;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: #fff;
}
:deep(.er-node__code) {
  font-size: 11px;
  opacity: 0.75;
  font-family: 'Consolas', monospace;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: #e0e7ff;
}
:deep(.er-node__body) {
  flex: 1;
  padding: 2px 0;
  overflow-y: auto;
  background: #fff;
  display: flex;
  flex-direction: column;
}
:deep(.er-f) {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 12px;
  font-size: 12px;
  color: #262626;
  border-bottom: 1px solid #f0f0f0;
  line-height: 1.6;
  flex: 0 0 auto;
}
:deep(.er-node__body > .er-f:last-child) {
  border-bottom: none;
  margin-bottom: auto;
}
:deep(.er-f:hover) {
  background: #f5f9ff;
}
:deep(.er-f--key) {
  background: #fffbe6;
  color: #0958d9;
  font-weight: 500;
}
:deep(.er-f--key:hover) {
  background: #fff7cc;
}
:deep(.er-f--empty) {
  color: #bfbfbf;
  font-style: italic;
  justify-content: center;
  padding: 8px;
}
:deep(.er-f__icon) {
  font-size: 11px;
  color: #8c8c8c;
  flex-shrink: 0;
  width: 12px;
  text-align: center;
}
:deep(.er-f--key .er-f__icon) {
  color: #faad14;
}
:deep(.er-f__name-wrap) {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  line-height: 1.3;
}
:deep(.er-f__name-cn) {
  font-size: 12px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
:deep(.er-f__name-en) {
  font-size: 10px;
  color: #8c8c8c;
  font-family: 'Consolas', monospace;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
:deep(.er-f--key .er-f__name-en) {
  color: #1677ff;
}
:deep(.er-f--composite) {
  background: #fff7e6;
  border-left: 3px solid #faad14;
}
:deep(.er-f--composite.er-f--key) {
  background: #fffbe6;
  border-left: 3px solid #faad14;
}
:deep(.er-f__type) {
  color: #8c8c8c;
  font-size: 10px;
  font-family: 'Consolas', monospace;
  padding: 1px 5px;
  background: #f5f5f5;
  border-radius: 3px;
  flex-shrink: 0;
}
:deep(.er-f--key .er-f__type) {
  background: #e6f4ff;
  color: #1677ff;
}

/* 字段面板（Issue 4 左右分栏） */
.field-panel {
  border: 1px solid #e8e8e8;
  border-radius: 4px;
  overflow: hidden;
}
.field-panel__header {
  background: #fafafa;
  padding: 8px 12px;
  font-size: 12px;
  color: #666;
  border-bottom: 1px solid #e8e8e8;
  font-weight: 500;
}
.field-panel__list {
  max-height: 280px;
  overflow-y: auto;
}
.field-panel__empty {
  padding: 24px 12px;
  text-align: center;
  color: #bbb;
  font-size: 13px;
}
.field-item {
  padding: 8px 12px;
  cursor: pointer;
  font-size: 13px;
  border-bottom: 1px solid #f5f5f5;
  transition: background 0.15s;
  line-height: 1.5;
}
.field-item:hover {
  background: #f0f5ff;
}
.field-item--selected {
  background: #e6f4ff;
  color: #1677ff;
  font-weight: 500;
}
.field-item--composite {
  background: #fffbe6;
  border-left: 3px solid #faad14;
}
.field-item--composite:hover {
  background: #fff7cc;
}
.field-item--composite.field-item--selected {
  background: #fff7cc;
}
.field-item--disabled {
  cursor: not-allowed;
  opacity: 0.5;
}
.field-item--disabled:hover {
  background: transparent;
}
</style>
