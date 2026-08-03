<template>
  <div>
    <DomainStageNav :domain-name="domainName" stage="fields" />

    <a-empty v-if="!loading && totalFieldCount === 0" description="该域下暂无字段">
      <a-button type="primary" @click="$router.push(`/modeling/domains/${domainId}/tables`)">去管理表</a-button>
    </a-empty>

    <!-- Tab 导航 -->
    <div v-else class="page-header-tabs">
      <a-tabs v-model:activeKey="mainTab" style="flex:1" @change="onTabChange">
        <a-tab-pane key="category" tab="字段分类" />
        <a-tab-pane key="group" tab="字段分组" />
        <a-tab-pane key="attr" tab="属性配置" />
      </a-tabs>
    </div>

    <!-- ========================= Tab 1: 字段分类 ========================= -->
    <div v-if="mainTab === 'category' && totalFieldCount > 0" class="split-layout">
      <!-- 左栏：字段分类导航 -->
      <div class="split-layout__left">
        <div class="panel-header">
          <span class="panel-title">字段分类</span>
        </div>
        <div class="category-list">
          <div class="category-item category-item--parent" :class="{ 'category-item--active': activeCategory === 'archive' }" @click="setCategory('archive')">
            <span class="category-item__name">📁 档案字段</span>
            <a-badge :count="categoryCounts.base + categoryCounts.composite + categoryCounts.computed" :number-style="{ backgroundColor: '#f0f0f0', color: '#595959', fontSize: '11px' }" />
          </div>
          <div class="category-item category-item--child" :class="{ 'category-item--active': activeCategory === 'base', 'category-item--drop-target': catDropTarget === 'base' }" @click="setCategory('base')"
            @dragover.prevent="catDropTarget = 'base'" @dragleave="catDropTarget = null" @drop="onDropToCategory('base')">
            <span class="category-item__name">基础字段</span>
            <a-badge :count="categoryCounts.base" :number-style="{ backgroundColor: '#e6f4ff', color: '#1677ff', fontSize: '11px' }" />
          </div>
          <div class="category-item category-item--child" :class="{ 'category-item--active': activeCategory === 'composite', 'category-item--drop-target': catDropTarget === 'composite' }" @click="setCategory('composite')"
            @dragover.prevent="catDropTarget = 'composite'" @dragleave="catDropTarget = null" @drop="onDropToCategory('composite')">
            <span class="category-item__name">组合字段</span>
            <a-badge :count="categoryCounts.composite" :number-style="{ backgroundColor: '#e6f4ff', color: '#1677ff', fontSize: '11px' }" />
          </div>
          <div class="category-item category-item--child" :class="{ 'category-item--active': activeCategory === 'computed' }" @click="setCategory('computed')">
            <span class="category-item__name">计算字段</span>
            <a-badge :count="categoryCounts.computed" :number-style="{ backgroundColor: '#e6f4ff', color: '#1677ff', fontSize: '11px' }" />
          </div>
          <div class="category-divider"></div>
          <div class="category-item category-item--parent" :class="{ 'category-item--active': activeCategory === 'unassigned', 'category-item--drop-target': catDropTarget === 'unassigned' }" @click="setCategory('unassigned')"
            @dragover.prevent="catDropTarget = 'unassigned'" @dragleave="catDropTarget = null" @drop="onDropToCategory('unassigned')">
            <span class="category-item__name">📥 未分配字段</span>
            <a-badge :count="categoryCounts.unassigned" :number-style="{ backgroundColor: '#fff7e6', color: '#d46b08', fontSize: '11px' }" />
          </div>
          <div class="category-item category-item--parent" :class="{ 'category-item--active': activeCategory === 'discarded', 'category-item--drop-target': catDropTarget === 'discarded' }" @click="setCategory('discarded')"
            @dragover.prevent="catDropTarget = 'discarded'" @dragleave="catDropTarget = null" @drop="onDropToCategory('discarded')">
            <span class="category-item__name">🗑️ 废弃字段</span>
            <a-badge :count="categoryCounts.discarded" :number-style="{ backgroundColor: '#fff1f0', color: '#cf1322', fontSize: '11px' }" />
          </div>
        </div>
      </div>

      <!-- 右栏：字段列表 -->
      <div class="split-layout__right">
        <div class="panel-header">
          <span class="panel-title">
            {{ categoryLabel }}
            <span class="panel-sub">{{ currentDataCount }} 个字段</span>
          </span>
          <a-space>
            <a-input v-model:value="searchText" placeholder="搜索：编码/名称" allow-clear style="width: 240px" size="small" />
            <a-button :loading="manualRefreshing" size="small" @click="refreshManualDistinct">刷新去重内容</a-button>
          </a-space>
        </div>

        <!-- 基础字段表格 -->
        <div v-if="activeCategory === 'base' || activeCategory === 'archive'" class="table-wrapper">
          <a-table :data-source="filteredBaseFields" :columns="baseColumns" :row-selection="rowSelection" row-key="id" :pagination="false" size="small" :scroll="{ y: 'calc(100vh - 360px)' }"
            :custom-row="(record: any) => ({ draggable: true, class: 'draggable-row', onDragstart: (e: DragEvent) => onCatDragStart(e, record), onDragend: onCatDragEnd })">
            <template #bodyCell="{ column, record }">
              <template v-if="column.key === 'drag_handle'">
                <span class="drag-handle">☰</span>
              </template>
              <template v-else-if="column.key === 'distinct'">
                <a-tooltip v-if="record.distinct_values && record.distinct_values.length" :title="record.distinct_values.map((v: any) => String(v)).join(', ')">
                  <span><a-tag v-for="(v, i) in record.distinct_values.slice(0, 3)" :key="i" style="margin-bottom:2px">{{ String(v) }}</a-tag><span v-if="record.distinct_values.length > 3" style="color:#999">…共 {{ record.distinct_values.length }} 项</span></span>
                </a-tooltip>
                <span v-else style="color:#bbb">—</span>
              </template>
            </template>
          </a-table>
        </div>
        <!-- 组合字段表格 -->
        <div v-if="activeCategory === 'composite'" class="table-wrapper">
          <a-table :data-source="compositeExpandedRows" :columns="compositeColumns" row-key="_rowKey" :pagination="false" size="small" :scroll="{ y: 'calc(100vh - 360px)' }"
            :custom-row="getCompositeCustomRow">
            <template #bodyCell="{ column, record }">
              <template v-if="column.key === 'composite_code'">
                <span v-if="record._isFirst" style="font-weight:600">{{ record._compositeCode }}</span>
              </template>
              <template v-else-if="column.key === 'composite_name'">
                <span v-if="record._isFirst" style="font-weight:600">{{ record._compositeName }}</span>
              </template>
              <template v-else-if="column.key === 'code'">
                <span>{{ record.code }}</span>
              </template>
              <template v-else-if="column.key === 'table_name'">
                <span>{{ record.table_name }}</span>
              </template>
              <template v-else-if="column.key === 'primary_table'">
                <a-tag v-if="record._tableIsPrimary" color="gold">主表</a-tag>
                <span v-else style="color:#bfbfbf">—</span>
              </template>
              <template v-else-if="column.key === 'primary_field'">
                <template v-if="record._memberId">
                  <a-tooltip v-if="record._isPrimaryField" title="主字段：档案更新的数据源头；其余成员仅作一致性检查">
                    <a-tag color="gold">主字段</a-tag>
                  </a-tooltip>
                  <a-tooltip v-else title="设为主字段">
                    <a-button type="text" size="small" style="padding:0 4px" @click="setPrimaryFromComposite(record)"><KeyOutlined style="color:#bfbfbf" /></a-button>
                  </a-tooltip>
                </template>
                <span v-else style="color:#bfbfbf">—</span>
              </template>
              <template v-else-if="column.key === 'distinct'">
                <a-tooltip v-if="record.distinct_values && record.distinct_values.length" :title="record.distinct_values.map((v: any) => String(v)).join(', ')">
                  <span><a-tag v-for="(v, i) in record.distinct_values.slice(0, 3)" :key="i" style="margin-bottom:2px">{{ String(v) }}</a-tag><span v-if="record.distinct_values.length > 3" style="color:#999">…共 {{ record.distinct_values.length }} 项</span></span>
                </a-tooltip>
                <span v-else style="color:#bbb">—</span>
              </template>
              <template v-else-if="column.key === 'action'">
                <a-space v-if="record._isFirst">
                  <a-button type="link" size="small" @click="openMembersDistinct(record._sfRecord)">管理</a-button>
                  <a-popconfirm title="释放该组合字段？成员将回到未分配" @confirm="deleteCompositeField(record._sfRecord)">
                    <a-button type="link" size="small" danger>释放</a-button>
                  </a-popconfirm>
                </a-space>
              </template>
            </template>
          </a-table>
        </div>
        <!-- 计算字段表格 -->
        <div v-if="activeCategory === 'computed'" class="table-wrapper">
          <div class="panel-toolbar" style="margin-bottom:8px;display:flex;justify-content:space-between;align-items:center">
            <a-space>
              <a-button type="primary" size="small" @click="openFormulaEditor(null)">+ 新建计算字段</a-button>
              <a-button size="small" :loading="batchRecalculating" @click="handleBatchRecalculate">批量重算</a-button>
            </a-space>
          </div>
          <a-table :data-source="filteredComputedFields" :columns="computedColumns" row-key="id" :pagination="false" size="small" :scroll="{ y: 'calc(100vh - 400px)' }">
            <template #bodyCell="{ column, record }">
              <template v-if="column.key === 'expression'">
                <span v-if="record.expression" style="color:#595959;font-family:monospace;font-size:12px">{{ (record.expression || '').slice(0, 40) }}{{ (record.expression || '').length > 40 ? '...' : '' }}</span>
                <span v-else style="color:#bbb">未配置</span>
              </template>
              <template v-else-if="column.key === 'output_type'">
                <a-tag>{{ ({ text: '文本', number: '数字', date: '日期', boolean: '布尔' } as Record<string, string>)[record.output_type] || record.output_type }}</a-tag>
              </template>
              <template v-else-if="column.key === 'actions'">
                <a-space>
                  <a-button type="link" size="small" @click="openFormulaEditor(record)">编辑</a-button>
                  <a-button type="link" size="small" @click="openTrialCalc(record)">试算</a-button>
                  <a-popconfirm title="废弃后字段移入左栏「废弃字段」分类，公式保留、可随时恢复。确定废弃？" @confirm="toggleComputedStatus(record)">
                    <a-button type="link" size="small" danger>废弃</a-button>
                  </a-popconfirm>
                </a-space>
              </template>
            </template>
          </a-table>
        </div>
        <!-- 未分配字段表格 -->
        <div v-if="activeCategory === 'unassigned'" class="table-wrapper">
          <a-table :data-source="filteredUnassignedFields" :columns="unassignedColumns" :row-selection="rowSelection" row-key="id" :pagination="false" size="small" :scroll="{ y: 'calc(100vh - 360px)' }"
            :custom-row="(record: any) => ({ draggable: true, class: 'draggable-row', onDragstart: (e: DragEvent) => onCatDragStart(e, record), onDragend: onCatDragEnd })">
            <template #bodyCell="{ column, record }">
              <template v-if="column.key === 'drag_handle'">
                <span class="drag-handle">☰</span>
              </template>
              <template v-else-if="column.key === 'distinct'">
                <a-tooltip v-if="record.distinct_values && record.distinct_values.length" :title="record.distinct_values.map((v: any) => String(v)).join(', ')">
                  <span><a-tag v-for="(v, i) in record.distinct_values.slice(0, 3)" :key="i" style="margin-bottom:2px">{{ String(v) }}</a-tag><span v-if="record.distinct_values.length > 3" style="color:#999">…共 {{ record.distinct_values.length }} 项</span></span>
                </a-tooltip>
                <span v-else style="color:#bbb">—</span>
              </template>
            </template>
          </a-table>
        </div>
        <!-- 废弃字段表格 -->
        <div v-if="activeCategory === 'discarded'" class="table-wrapper">
          <a-table :data-source="filteredDiscardedFields" :columns="discardedColumns" :row-selection="rowSelection" row-key="id" :pagination="false" size="small" :scroll="{ y: 'calc(100vh - 360px)' }"
            :custom-row="(record: any) => ({ draggable: true, class: 'draggable-row', onDragstart: (e: DragEvent) => onCatDragStart(e, record), onDragend: onCatDragEnd })">
            <template #bodyCell="{ column, record }">
              <template v-if="column.key === 'drag_handle'">
                <span class="drag-handle">☰</span>
              </template>
              <template v-else-if="column.key === 'distinct'">
                <a-tooltip v-if="record.distinct_values && record.distinct_values.length" :title="record.distinct_values.map((v: any) => String(v)).join(', ')">
                  <span><a-tag v-for="(v, i) in record.distinct_values.slice(0, 3)" :key="i" style="margin-bottom:2px">{{ String(v) }}</a-tag><span v-if="record.distinct_values.length > 3" style="color:#999">…共 {{ record.distinct_values.length }} 项</span></span>
                </a-tooltip>
                <span v-else style="color:#bbb">—</span>
              </template>
              <template v-else-if="column.key === 'kind'">
                <a-tag v-if="record._kind === 'physical'" color="blue">物理</a-tag>
                <a-tag v-else-if="record._kind === 'standard'" color="purple">组合</a-tag>
                <a-tag v-else color="orange">计算</a-tag>
              </template>
            </template>
          </a-table>
        </div>
      </div>
    </div>

    <!-- ========================= Tab 2: 字段分组 ========================= -->
    <div v-if="mainTab === 'group' && totalFieldCount > 0" class="split-layout">
      <!-- 左栏：树形分组 -->
      <div class="split-layout__left">
        <div class="panel-header">
          <span class="panel-title">分组</span>
          <a-space :size="4">
            <a-button type="link" size="small" :loading="aiLoading.group" @click="runAutoGroup">AI分组</a-button>
            <a-button type="link" size="small" @click="openCreateGroupModal(null)">+ 新建</a-button>
          </a-space>
        </div>
        <div class="category-list">
          <div class="category-item category-item--parent" :class="{ 'category-item--active': activeGroupId === null }" @click="activeGroupId = null">
            <span class="category-item__name">全部字段</span>
            <a-badge :count="groupAggregates.length" :number-style="{ backgroundColor: '#f0f0f0', color: '#595959', fontSize: '11px' }" />
          </div>
          <div class="category-item category-item--parent" :class="{ 'category-item--active': activeGroupId === 0, 'category-item--drop-target': dropTargetGroupId === 0 }" @click="activeGroupId = 0"
            @dragover.prevent="dropTargetGroupId = 0" @dragleave="dropTargetGroupId = null" @drop="onDropToGroup(null)">
            <span class="category-item__name">未分组</span>
            <a-badge :count="groupAggregates.filter(a => !a.group).length" :number-style="{ backgroundColor: '#fff7e6', color: '#d46b08', fontSize: '11px' }" />
          </div>
          <!-- 树形分组节点（可拖拽排序：同父级内） -->
          <template v-for="node in flatGroupTree" :key="node.id">
            <div class="category-item category-item--child" :class="{ 'category-item--active': activeGroupId === node.id, 'category-item--drop-target': dropTargetGroupId === node.id }" :style="{ paddingLeft: (node.level - 1) * 16 + 12 + 'px' }"
              draggable="true"
              @dragstart="onGroupNodeDragStart($event, node.id)" @dragend="onGroupNodeDragEnd"
              @click="activeGroupId = node.id" @dragover.prevent="dropTargetGroupId = node.id" @dragleave="dropTargetGroupId = null" @drop="onDropToGroup(node.id)">
              <span class="category-item__name">
                <span v-if="node.hasChildren" class="tree-toggle" @click.stop="toggleGroupExpand(node.id)">{{ expandedGroupIds.has(node.id) ? '▾' : '▸' }}</span>
                <span v-else style="display:inline-block;width:14px"></span>
                {{ node.name }}
              </span>
              <a-space :size="4">
                <a-badge :count="getGroupFieldCount(node.id)" :number-style="{ backgroundColor: '#e6f4ff', color: '#1677ff', fontSize: '11px' }" />
                <a-button v-if="node.level < 3" type="link" size="small" style="padding:0;font-size:12px" @click.stop="openCreateGroupModal(node.id)" title="新建子分组">➕</a-button>
                <a-button type="link" size="small" style="padding:0;font-size:12px" @click.stop="renameGroup(node)">✏️</a-button>
                <a-popconfirm title="确认删除该分组？子分组上浮，字段变为未分组" @confirm="deleteGroup(node.id)">
                  <a-button type="link" size="small" danger style="padding:0;font-size:12px" @click.stop>🗑️</a-button>
                </a-popconfirm>
              </a-space>
            </div>
          </template>
        </div>
      </div>

      <!-- 右栏：分组字段列表 -->
      <div class="split-layout__right">
        <div class="panel-header">
          <span class="panel-title">
            {{ activeGroupId === null ? '全部字段' : activeGroupId === 0 ? '未分组' : getGroupName(activeGroupId) || '' }}
            <span v-if="groupSelectedKeys.length" class="panel-sub">已选 {{ groupSelectedKeys.length }} 项，拖拽到左侧分组</span>
          </span>
          <a-input v-model:value="groupSearchText" placeholder="搜索" allow-clear style="width: 200px" size="small" />
        </div>
        <div class="table-wrapper">
          <a-table :data-source="filteredGroupAggregates" :columns="groupColumns" :row-selection="groupRowSelection" row-key="key" :pagination="false" size="small" :scroll="{ y: 'calc(100vh - 320px)' }"
            :custom-row="(record: any) => ({ draggable: true, class: 'draggable-row' + (activeGroupId && record.group !== activeGroupId ? ' row-descendant' : ''), onDragstart: (e: DragEvent) => onGroupDragStart(e, record), onDragend: onGroupDragEnd })">
            <template #bodyCell="{ column, record }">
              <template v-if="column.key === 'drag_handle'">
                <span class="drag-handle">☰</span>
              </template>
              <template v-else-if="column.key === 'kind_tag'">
                <a-tag v-if="record.kind === 'computed'" color="orange">计算</a-tag>
                <a-tag v-else-if="record.kind === 'equiv'" color="purple">组合</a-tag>
                <a-tag v-else color="blue">基础</a-tag>
              </template>
              <template v-else-if="column.key === 'sub_group'">
                <span :style="{ color: subGroupDisplay(record) === '--' ? '#bfbfbf' : '#595959' }">{{ subGroupDisplay(record) }}</span>
              </template>

            </template>
          </a-table>
        </div>
      </div>
    </div>

    <!-- ========================= Tab 3: 属性配置 ========================= -->
    <div v-if="mainTab === 'attr' && totalFieldCount > 0" class="split-layout">
      <!-- 左栏：分组筛选导航（只读） -->
      <div class="split-layout__left">
        <div class="panel-header">
          <span class="panel-title">分组筛选</span>
        </div>
        <div class="category-list">
          <div class="category-item category-item--parent" :class="{ 'category-item--active': attrActiveGroupId === null }" @click="attrActiveGroupId = null">
            <span class="category-item__name">全部字段</span>
            <a-badge :count="attrRows.length" :number-style="{ backgroundColor: '#f0f0f0', color: '#595959', fontSize: '11px' }" />
          </div>
          <div class="category-item category-item--parent" :class="{ 'category-item--active': attrActiveGroupId === 0 }" @click="attrActiveGroupId = 0">
            <span class="category-item__name">未分组</span>
            <a-badge :count="attrRows.filter(r => !r.group).length" :number-style="{ backgroundColor: '#fff7e6', color: '#d46b08', fontSize: '11px' }" />
          </div>
          <template v-for="node in flatGroupTree" :key="'attr_g_' + node.id">
            <div class="category-item category-item--child" :class="{ 'category-item--active': attrActiveGroupId === node.id }" :style="{ paddingLeft: (node.level - 1) * 16 + 12 + 'px' }" @click="attrActiveGroupId = node.id">
              <span class="category-item__name">
                <span v-if="node.hasChildren" class="tree-toggle" @click.stop="toggleGroupExpand(node.id)">{{ expandedGroupIds.has(node.id) ? '▾' : '▸' }}</span>
                <span v-else style="display:inline-block;width:14px"></span>
                {{ node.name }}
              </span>
              <a-badge :count="getAttrGroupCount(node.id)" :number-style="{ backgroundColor: '#e6f4ff', color: '#1677ff', fontSize: '11px' }" />
            </div>
          </template>
        </div>
      </div>

      <!-- 右栏：属性表 -->
      <div class="split-layout__right">
        <div class="panel-header">
          <span class="panel-title">
            {{ attrActiveGroupId === null ? '全部字段' : attrActiveGroupId === 0 ? '未分组' : getGroupName(attrActiveGroupId) || '' }}
            <span class="panel-sub">配置字段的数据类型、长度、必填、默认值等；计算字段仅可切换释放到档案</span>
          </span>
          <a-space>
            <a-button :loading="aiLoading.semantic" size="small" @click="runSemantic">AI自动配置</a-button>
            <a-input v-model:value="attrSearchText" placeholder="搜索：编码/名称" allow-clear style="width: 240px" size="small" />
          </a-space>
        </div>
        <div class="table-wrapper">
          <a-table :data-source="filteredAttrFields" :columns="attrColumns" row-key="key" :pagination="false" size="small" :scroll="{ y: 'calc(100vh - 320px)' }">
            <template #bodyCell="{ column, record }">
              <template v-if="column.key === 'kind_tag'">
                <a-tag v-if="record.kind === 'equiv'" color="purple">组合</a-tag>
                <a-tag v-else-if="record.kind === 'solo'" color="blue">基础</a-tag>
                <a-tag v-else color="orange">计算</a-tag>
              </template>
              <template v-else-if="column.key === 'standard_code'">
                <a-tooltip v-if="record.is_primary_key" title="主键字段">
                  <KeyOutlined style="color:#faad14;margin-right:4px" />
                </a-tooltip>
                <span>{{ record.standard_code }}</span>
              </template>
              <template v-else-if="column.key === 'tables'">
                <span v-if="!record.tables || !record.tables.length" style="color:#bfbfbf">—</span>
                <template v-else>
                  <span v-for="(t, ti) in record.tables" :key="ti" style="margin-right:6px;white-space:nowrap">
                    {{ t.name }}<a-tag v-if="t.is_primary" color="gold" style="margin-left:2px">主表</a-tag>
                  </span>
                </template>
              </template>
              <template v-else-if="column.key === 'field_type'">
                <a-tag v-if="record.kind === 'computed'">{{ outputTypeLabel(record.field_type) }}</a-tag>
                <a-select v-else v-model:value="record.field_type" size="small" style="width:90px" @change="() => saveAttrField(record)">
                  <a-select-option value="string">字符串</a-select-option>
                  <a-select-option value="number">数字</a-select-option>
                  <a-select-option value="date">日期</a-select-option>
                  <a-select-option value="boolean">布尔</a-select-option>
                  <a-select-option value="enum">枚举</a-select-option>
                </a-select>
              </template>
              <template v-else-if="column.key === 'length'">
                <span v-if="record.kind === 'computed'" style="color:#bfbfbf">—</span>
                <a-input-number v-else v-model:value="record.length" size="small" style="width:70px" :min="0" @change="() => saveAttrField(record)" />
              </template>
              <template v-else-if="column.key === 'required'">
                <span v-if="record.kind === 'computed'" style="color:#bfbfbf">—</span>
                <a-switch v-else :checked="record.required" size="small" @change="(val: any) => { record.required = val; saveAttrField(record) }" />
              </template>
              <template v-else-if="column.key === 'default_value'">
                <span v-if="record.kind === 'computed'" style="color:#bfbfbf">—</span>
                <a-input v-else v-model:value="record.default_value" size="small" style="width:120px" @blur="saveAttrField(record)" @pressEnter="saveAttrField(record)" />
              </template>
              <template v-else-if="column.key === 'ownership'">
                <a-tooltip v-if="record.kind === 'computed'" title="计算字段由公式产出，固定档案维护">
                  <a-tag color="orange">档案维护</a-tag>
                </a-tooltip>
                <a-tooltip v-else title="源系统维护：档案只读，同步直接覆盖；档案维护：档案可编辑，同步不覆盖">
                  <a-switch
                    :checked="record.ownership === 'source'"
                    size="small"
                    checked-children="源系统维护"
                    un-checked-children="档案维护"
                    @change="(val: any) => { record.ownership = val ? 'source' : 'archive'; saveAttrField(record) }"
                  />
                </a-tooltip>
              </template>
              <template v-else-if="column.key === 'distinct'">
                <span v-if="record.kind === 'computed'" style="color:#bfbfbf">—</span>
                <a-tooltip v-else-if="record.distinct_values && record.distinct_values.length" :title="record.distinct_values.map((v: any) => String(v)).join(', ')">
                  <span><a-tag v-for="(v, i) in record.distinct_values.slice(0, 3)" :key="i" style="margin-bottom:2px">{{ String(v) }}</a-tag><span v-if="record.distinct_values.length > 3" style="color:#999">…共 {{ record.distinct_values.length }} 项</span></span>
                </a-tooltip>
                <span v-else style="color:#bbb">—</span>
              </template>
              <template v-else-if="column.key === 'member_count'">
                <span v-if="record.kind === 'computed'" style="color:#bfbfbf">—</span>
                <span v-else>{{ record.member_count }}</span>
              </template>
            </template>
          </a-table>
        </div>
      </div>
    </div>

    <!-- 组合字段成员查看抽屉 -->
    <a-drawer v-model:open="distinctDrawerVisible" :title="distinctDrawerTitle" placement="right" width="70vw">
      <a-spin :spinning="distinctLoading">
        <div style="color:#999;font-size:12px;margin-bottom:12px">并排展示该组合字段下每个物理字段（表名.编码）的去重取值。金色「主字段」为档案更新的数据源头（默认取主表成员），其余成员仅作一致性检查。</div>
        <div v-if="distinctMembers.length" style="display:flex;gap:12px;overflow-x:auto;padding-bottom:8px">
          <div v-for="m in distinctMembers" :key="m.field_id" style="min-width:220px;max-width:320px;flex:1;border:1px solid #f0f0f0;border-radius:8px;padding:10px"
            :style="m.is_primary_field ? 'border-color:#faad14;box-shadow:0 0 0 1px #faad14' : ''">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px">
              <span style="font-weight:600;font-size:13px">{{ m.table_name }}.{{ m.code }}<a-tag v-if="m.table_is_primary" color="gold" style="margin-left:4px">主表</a-tag></span>
              <a-popconfirm title="确认释放该成员？" @confirm="confirmReleaseMember(m.field_id)">
                <a-button type="link" size="small" danger style="padding:0;font-size:12px">释放</a-button>
              </a-popconfirm>
            </div>
            <div style="margin-bottom:6px">
              <a-tooltip v-if="m.is_primary_field" title="档案更新的数据源头；其余成员仅作一致性检查">
                <a-tag color="gold">主字段（数据源头）</a-tag>
              </a-tooltip>
              <a-button v-else type="link" size="small" style="padding:0;font-size:12px" @click="setPrimaryMember(m.field_id)">设为主字段</a-button>
            </div>
            <div style="color:#999;font-size:12px;margin-bottom:8px">{{ m.name }}{{ m.comment ? '（' + m.comment + '）' : '' }}</div>
            <div style="font-size:12px;color:#595959">
              <a-tag v-for="(v, i) in (m.distinct_values || []).slice(0, 30)" :key="i" style="margin-bottom:2px">{{ String(v) }}</a-tag>
              <span v-if="m.count > 30" style="color:#999">…共 {{ m.count }} 项</span>
              <span v-if="m.count === 0" style="color:#bbb">无数据</span>
            </div>
          </div>
        </div>
        <a-empty v-else description="暂无成员字段" />
      </a-spin>
    </a-drawer>

    <!-- 合并为组合字段弹窗 -->
    <a-modal v-model:open="mergeModalVisible" title="合并为组合字段" ok-text="确认" cancel-text="取消" :confirm-loading="mergeSubmitting" @ok="submitMerge">
      <div style="color:#999;font-size:12px;margin-bottom:12px">将选中的 {{ selectedRowKeys.length }} 个字段归并为一个组合字段。</div>
      <a-form layout="vertical">
        <a-form-item label="字段编码" required>
          <a-input v-model:value="mergeForm.standard_code" placeholder="字段编码（必填）" />
        </a-form-item>
        <a-form-item label="字段名称">
          <a-input v-model:value="mergeForm.standard_name" placeholder="字段名称（选填）" />
        </a-form-item>
      </a-form>
    </a-modal>

    <!-- 计算字段公式编辑器 -->
    <FormulaEditor
      v-model:open="formulaEditorOpen"
      :domain-id="domainId"
      :field="editingComputedField"
      @saved="onComputedFieldSaved"
      @save-and-trial="onSaveAndTrial"
    />
    <!-- 枚举试算 -->
    <TrialCalculation
      v-model:open="trialCalcOpen"
      :domain-id="domainId"
      :field="trialCalcField"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { message, Modal } from 'ant-design-vue'
import { KeyOutlined } from '@ant-design/icons-vue'
import { extractApiError } from '@/utils/apiError'
import { domainApi, fieldApi, standardFieldApi, computedFieldApi, fieldGroupApi } from '@/api/modeling'
import type { StandardFieldModel, ManualFieldCandidate, StandardFieldMemberDistinct, ComputedFieldModel, FieldCategoryCounts, StandardFieldAggregate } from '@/api/modeling'
import type { FieldGroup } from '@/types'
import DomainStageNav from './components/DomainStageNav.vue'
import FormulaEditor from './components/FormulaEditor.vue'
import TrialCalculation from './components/TrialCalculation.vue'

const route = useRoute()
const domainId = Number(route.params.id)
const domainName = ref('')
const loading = ref(false)
const totalFieldCount = ref(0)

// ===== 顶部Tab =====
const mainTab = ref<'category' | 'group' | 'attr'>('category')

function onTabChange(key: string) {
  if (key === 'group') loadGroupTabData()
  if (key === 'attr') loadAttrTabData()
}

// ===== Tab 1: 字段分类 =====
type CategoryType = 'archive' | 'base' | 'composite' | 'computed' | 'unassigned' | 'discarded'
const activeCategory = ref<CategoryType>('unassigned')
const categoryCounts = reactive<FieldCategoryCounts>({ base: 0, composite: 0, computed: 0, unassigned: 0, discarded: 0 })

const categoryLabel = computed(() => {
  const map: Record<CategoryType, string> = { archive: '档案字段（全部）', base: '基础字段', composite: '组合字段', computed: '计算字段', unassigned: '未分配字段', discarded: '废弃字段' }
  return map[activeCategory.value]
})
const currentDataCount = computed(() => {
  switch (activeCategory.value) {
    case 'archive': return filteredBaseFields.value.length
    case 'base': return filteredBaseFields.value.length
    case 'composite': return filteredCompositeFields.value.length
    case 'computed': return filteredComputedFields.value.length
    case 'unassigned': return filteredUnassignedFields.value.length
    case 'discarded': return filteredDiscardedFields.value.length
    default: return 0
  }
})
function setCategory(cat: CategoryType) { activeCategory.value = cat; selectedRowKeys.value = [] }

const searchText = ref('')
const selectedRowKeys = ref<(number | string)[]>([])
const rowSelection = computed(() => ({ selectedRowKeys: selectedRowKeys.value, onChange: (keys: (number | string)[]) => { selectedRowKeys.value = keys } }))

// 数据
const baseFields = ref<ManualFieldCandidate[]>([])
const compositeFields = ref<StandardFieldModel[]>([])
const computedFields = ref<ComputedFieldModel[]>([])
const unassignedFields = ref<ManualFieldCandidate[]>([])
const discardedFields = ref<any[]>([])

const filteredBaseFields = computed(() => { const q = searchText.value.toLowerCase().trim(); if (!q) return baseFields.value; return baseFields.value.filter(f => f.code.toLowerCase().includes(q) || (f.comment || f.name || '').toLowerCase().includes(q)) })
const filteredCompositeFields = computed(() => { const q = searchText.value.toLowerCase().trim(); if (!q) return compositeFields.value; return compositeFields.value.filter(f => f.standard_code.toLowerCase().includes(q) || f.standard_name.toLowerCase().includes(q)) })

// 组合字段展开行：每个成员为一行，携带父级组合字段信息
const compositeExpandedRows = computed(() => {
  const rows: any[] = []
  const q = searchText.value.toLowerCase().trim()
  for (const sf of compositeFields.value) {
    if (q && !sf.standard_code.toLowerCase().includes(q) && !sf.standard_name.toLowerCase().includes(q)) continue
    const members = sf.members || []
    if (members.length === 0) {
      // 0成员的幽灵记录，仍然显示以便用户删除
      rows.push({
        _rowKey: `sf_${sf.id}_empty`,
        _isFirst: true,
        _compositeCode: sf.standard_code,
        _compositeName: sf.standard_name,
        _sfRecord: sf,
        code: '— 无成员 —',
        name: '',
        table_name: '',
        distinct_values: [],
      })
    } else {
      members.forEach((m: any, idx: number) => {
        rows.push({
          _rowKey: `sf_${sf.id}_m_${m.id}`,
          _isFirst: idx === 0,
          _compositeCode: sf.standard_code,
          _compositeName: sf.standard_name,
          _sfRecord: sf,
          _memberId: m.id,
          _isPrimaryField: !!m.is_primary_field,
          _tableIsPrimary: !!m.table_is_primary,
          code: m.code,
          name: m.comment || m.name,
          table_name: m.table_name,
          distinct_values: m.distinct_values || [],
        })
      })
    }
  }
  return rows
})
const filteredComputedFields = computed(() => { const q = searchText.value.toLowerCase().trim(); if (!q) return computedFields.value; return computedFields.value.filter(f => f.code.toLowerCase().includes(q) || f.name.toLowerCase().includes(q)) })
const filteredUnassignedFields = computed(() => { const q = searchText.value.toLowerCase().trim(); if (!q) return unassignedFields.value; return unassignedFields.value.filter(f => f.code.toLowerCase().includes(q) || (f.comment || f.name || '').toLowerCase().includes(q) || (f.source_label || '').toLowerCase().includes(q)) })
const filteredDiscardedFields = computed(() => { const q = searchText.value.toLowerCase().trim(); if (!q) return discardedFields.value; return discardedFields.value.filter((f: any) => (f.code || '').toLowerCase().includes(q) || (f.name || '').toLowerCase().includes(q)) })

// 列定义
const dragHandleCol = { title: '', key: 'drag_handle', width: 36, align: 'center' as const }
const baseColumns = [
  dragHandleCol,
  { title: '字段编码', dataIndex: 'code', key: 'code', width: 160, ellipsis: true, sorter: (a: any, b: any) => (a.code || '').localeCompare(b.code || '') },
  { title: '字段名称', key: 'name', width: 160, ellipsis: true, customRender: ({ record }: any) => record.comment || record.name || '-', sorter: (a: any, b: any) => (a.comment || a.name || '').localeCompare(b.comment || b.name || '') },
  { title: '来源表', dataIndex: 'source_label', key: 'source_label', width: 200, ellipsis: true, sorter: (a: any, b: any) => (a.source_label || '').localeCompare(b.source_label || '') },
  { title: '数据去重内容', key: 'distinct', sorter: (a: any, b: any) => (a.distinct_values?.length || 0) - (b.distinct_values?.length || 0) },
]
const compositeColumns = [
  { title: '组合字段编码', key: 'composite_code', width: 140, ellipsis: true },
  { title: '组合字段名称', key: 'composite_name', width: 140, ellipsis: true },
  { title: '成员编码', dataIndex: 'code', key: 'code', width: 140, ellipsis: true, sorter: (a: any, b: any) => (a.code || '').localeCompare(b.code || '') },
  { title: '成员名称', dataIndex: 'name', key: 'name', width: 140, ellipsis: true, sorter: (a: any, b: any) => (a.name || '').localeCompare(b.name || '') },
  { title: '来源表', dataIndex: 'table_name', key: 'table_name', width: 220, ellipsis: true, sorter: (a: any, b: any) => (a.table_name || '').localeCompare(b.table_name || '') },
  { title: '数据去重内容', key: 'distinct', sorter: (a: any, b: any) => (a.distinct_values?.length || 0) - (b.distinct_values?.length || 0) },
  { title: '主表', key: 'primary_table', width: 70, align: 'center' as const },
  { title: '主字段', key: 'primary_field', width: 70, align: 'center' as const },
  { title: '操作', key: 'action', width: 120, align: 'center' as const },
]
const computedColumns = [
  { title: '字段编码', dataIndex: 'code', key: 'code', width: 130, ellipsis: true, sorter: (a: any, b: any) => (a.code || '').localeCompare(b.code || '') },
  { title: '字段名称', dataIndex: 'name', key: 'name', width: 130, ellipsis: true, sorter: (a: any, b: any) => (a.name || '').localeCompare(b.name || '') },
  { title: '公式摘要', key: 'expression' },
  { title: '输出类型', key: 'output_type', width: 80, align: 'center' as const },
  { title: '执行顺序', dataIndex: 'execution_order', key: 'execution_order', width: 80, align: 'center' as const, sorter: (a: any, b: any) => (a.execution_order || 0) - (b.execution_order || 0) },
  { title: '操作', key: 'actions', width: 160, align: 'center' as const },
]
const unassignedColumns = [
  dragHandleCol,
  { title: '字段编码', dataIndex: 'code', key: 'code', width: 160, ellipsis: true, sorter: (a: any, b: any) => (a.code || '').localeCompare(b.code || '') },
  { title: '字段名称', key: 'name_display', width: 160, ellipsis: true, customRender: ({ record }: any) => record.comment || record.name || '-', sorter: (a: any, b: any) => (a.comment || a.name || '').localeCompare(b.comment || b.name || '') },
  { title: '来源表', dataIndex: 'source_label', key: 'source_label', width: 200, ellipsis: true, sorter: (a: any, b: any) => (a.source_label || '').localeCompare(b.source_label || '') },
  { title: '数据去重内容', key: 'distinct', sorter: (a: any, b: any) => (a.distinct_values?.length || 0) - (b.distinct_values?.length || 0) },
]
const discardedColumns = [
  dragHandleCol,
  { title: '字段编码', dataIndex: 'code', key: 'code', width: 160, ellipsis: true, sorter: (a: any, b: any) => (a.code || '').localeCompare(b.code || '') },
  { title: '字段名称', dataIndex: 'name', key: 'name', width: 160, ellipsis: true, sorter: (a: any, b: any) => (a.name || '').localeCompare(b.name || '') },
  { title: '来源表', dataIndex: 'source_label', key: 'source_label', width: 200, ellipsis: true, sorter: (a: any, b: any) => (a.source_label || '').localeCompare(b.source_label || '') },
  { title: '数据去重内容', key: 'distinct', sorter: (a: any, b: any) => (a.distinct_values?.length || 0) - (b.distinct_values?.length || 0) },
  { title: '类型', key: 'kind', width: 80, align: 'center' as const },
]

// 数据加载
async function loadCategoryCounts() {
  try {
    const res = await fieldApi.fieldCategories(domainId)
    const data = (res as any).data || res
    Object.assign(categoryCounts, data)
    totalFieldCount.value = data.base + data.composite + data.computed + data.unassigned + data.discarded
  } catch { /* ignore */ }
}

async function loadBaseFields() {
  try {
    const res = await fieldApi.manualCandidates(domainId)
    const data = (res as any).data || res
    const all: ManualFieldCandidate[] = data.candidates || []
    baseFields.value = all.filter((f: any) => f.archive_category === 'base')
    unassignedFields.value = all.filter((f: any) => !f.archive_category || f.archive_category === 'unassigned')
  } catch { /* ignore */ }
}

async function loadCompositeFields() {
  try {
    const res = await standardFieldApi.list({ domain: domainId })
    const data = (res as any).data || res
    const all: StandardFieldModel[] = data.results || data || []
    compositeFields.value = all.filter(f => f.status === 'active')
  } catch { /* ignore */ }
}

async function loadComputedFields() {
  try {
    const res = await computedFieldApi.list({ domain: domainId, status: 'active' })
    const data = (res as any).data || res
    computedFields.value = data.results || data || []
  } catch { /* ignore */ }
}

async function loadDiscardedFields() {
  try {
    const physRes = await fieldApi.list({ table__domain: domainId, status: 'deprecated' })
    const physData = (physRes as any).data || physRes
    const physFields = (physData.results || physData || []).map((f: any) => ({ id: `phys_${f.id}`, _id: f.id, _kind: 'physical', code: f.code, name: f.comment || f.name, source_label: f.table_name || '', distinct_values: f.distinct_values || [] }))
    const stdRes = await standardFieldApi.list({ domain: domainId })
    const stdData = (stdRes as any).data || stdRes
    const stdAll: StandardFieldModel[] = stdData.results || stdData || []
    const stdDiscarded = stdAll.filter(f => f.status === 'discarded').map(f => ({ id: `std_${f.id}`, _id: f.id, _kind: 'standard', code: f.standard_code, name: f.standard_name, source_label: '组合字段', distinct_values: f.first_member_distinct_values || [] }))
    const compRes = await computedFieldApi.list({ domain: domainId, status: 'discarded' })
    const compData = (compRes as any).data || compRes
    const compDiscarded = (compData.results || compData || []).map((f: any) => ({ id: `comp_${f.id}`, _id: f.id, _kind: 'computed', code: f.code, name: f.name, source_label: '计算字段', distinct_values: [] }))
    discardedFields.value = [...physFields, ...stdDiscarded, ...compDiscarded]
  } catch { /* ignore */ }
}

async function refreshCategoryData() {
  loading.value = true
  await Promise.all([loadCategoryCounts(), loadBaseFields(), loadCompositeFields(), loadComputedFields(), loadDiscardedFields()])
  loading.value = false
}

// ===== Tab 2: 字段分组 =====
const fieldGroups = ref<FieldGroup[]>([])
const groupAggregates = ref<StandardFieldAggregate[]>([])
const activeGroupId = ref<number | null>(null)
const groupSearchText = ref('')
const expandedGroupIds = ref<Set<number>>(new Set())

// 树形分组展开/收起
function toggleGroupExpand(id: number) {
  const s = new Set(expandedGroupIds.value)
  if (s.has(id)) s.delete(id)
  else s.add(id)
  expandedGroupIds.value = s
}

// 将树形数据展平为带 level 的列表（受展开状态控制）
interface FlatGroupNode { id: number; name: string; level: number; hasChildren: boolean; parentId: number | null }
const flatGroupTree = computed<FlatGroupNode[]>(() => {
  const result: FlatGroupNode[] = []
  function walk(nodes: FieldGroup[], level: number) {
    for (const g of nodes) {
      const hasChildren = !!(g.children && g.children.length)
      result.push({ id: g.id, name: g.name, level, hasChildren, parentId: g.parent })
      if (hasChildren && expandedGroupIds.value.has(g.id)) {
        walk(g.children!, level + 1)
      }
    }
  }
  walk(fieldGroups.value, 1)
  return result
})

// 获取分组及其所有后代ID
function getDescendantGroupIds(groupId: number): number[] {
  const ids: number[] = [groupId]
  function walk(nodes: FieldGroup[]) {
    for (const g of nodes) {
      if (ids.includes(g.parent!)) {
        ids.push(g.id)
      }
      if (g.children && g.children.length) walk(g.children)
    }
  }
  // 从树中查找
  function walkTree(nodes: FieldGroup[]) {
    for (const g of nodes) {
      if (g.id === groupId && g.children) {
        collectAll(g.children)
      } else if (g.children) {
        walkTree(g.children)
      }
    }
  }
  function collectAll(nodes: FieldGroup[]) {
    for (const g of nodes) {
      ids.push(g.id)
      if (g.children) collectAll(g.children)
    }
  }
  walkTree(fieldGroups.value)
  return ids
}

// 获取分组名称（从树中查找）
function getGroupName(id: number): string {
  function find(nodes: FieldGroup[]): string | null {
    for (const g of nodes) {
      if (g.id === id) return g.name
      if (g.children) {
        const r = find(g.children)
        if (r) return r
      }
    }
    return null
  }
  return find(fieldGroups.value) || ''
}

// 获取分组及后代的字段数
function getGroupFieldCount(groupId: number): number {
  const ids = getDescendantGroupIds(groupId)
  return groupAggregates.value.filter(a => ids.includes(a.group as number)).length
}

const filteredGroupAggregates = computed(() => {
  let list = groupAggregates.value
  if (activeGroupId.value === 0) list = list.filter(a => !a.group)
  else if (activeGroupId.value !== null) {
    // 点击父分组时展示它及所有后代分组的字段
    const ids = getDescendantGroupIds(activeGroupId.value)
    list = list.filter(a => ids.includes(a.group as number))
  }
  const q = groupSearchText.value.toLowerCase().trim()
  if (q) list = list.filter(a => a.standard_code.toLowerCase().includes(q) || a.standard_name.toLowerCase().includes(q))
  return list
})

const groupColumns = [
  { title: '', key: 'drag_handle', width: 36, align: 'center' as const },
  { title: '类型', key: 'kind_tag', width: 70, align: 'center' as const },
  { title: '字段编码', dataIndex: 'standard_code', key: 'standard_code', width: 160, ellipsis: true, sorter: (a: any, b: any) => (a.standard_code || '').localeCompare(b.standard_code || '') },
  { title: '字段名称', dataIndex: 'standard_name', key: 'standard_name', width: 160, ellipsis: true, sorter: (a: any, b: any) => (a.standard_name || '').localeCompare(b.standard_name || '') },
  { title: '成员数', dataIndex: 'member_count', key: 'member_count', width: 80, align: 'center' as const, sorter: (a: any, b: any) => (a.member_count || 0) - (b.member_count || 0) },
  { title: '下级分组', key: 'sub_group', width: 100, ellipsis: true, sorter: (a: any, b: any) => subGroupDisplay(a).localeCompare(subGroupDisplay(b)) },
]

// 下级分组列显示：本级字段（属于当前选中分组）或无分组显示 --，仅子分组字段显示分组名
function subGroupDisplay(record: StandardFieldAggregate): string {
  if (!record.group) return '--'
  if (activeGroupId.value !== null && activeGroupId.value !== 0 && record.group === activeGroupId.value) return '--'
  return getGroupName(record.group as number) || '--'
}

async function loadGroupTabData() {
  const [groupsRes, aggsRes, compRes] = await Promise.all([
    fieldGroupApi.tree(domainId),
    fieldApi.standardFields(domainId),
    computedFieldApi.list({ domain: domainId }),
  ])
  const gData = (groupsRes as any).data || groupsRes
  fieldGroups.value = gData.results || gData || []
  // 默认展开顶层分组
  const topIds = fieldGroups.value.map(g => g.id)
  expandedGroupIds.value = new Set(topIds)
  const aData = (aggsRes as any).data || aggsRes
  const aggs = (aData.results || aData || []) as StandardFieldAggregate[]
  // 计算字段并入分组视图（仅启用状态），可拖拽/换组
  const cData = (compRes as any).data || compRes
  const comps = ((cData.results || cData || []) as ComputedFieldModel[]).filter(c => c.status === 'active')
  const compRows: StandardFieldAggregate[] = comps.map(c => ({
    kind: 'computed',
    key: `computed-${c.id}`,
    standard_code: c.code,
    standard_name: c.name,
    physical_field_ids: [],
    group: c.group ?? null,
    computed_id: c.id,
    group_name: c.group_name ?? null,
    source: 'computed',
    member_count: 0,
    release_to_archive: c.release_to_archive,
  }))
  groupAggregates.value = [...aggs, ...compRows]
}

function openCreateGroupModal(parentId: number | null) {
  const parentName = parentId ? getGroupName(parentId) : null
  const label = parentName ? `请输入「${parentName}」下的子分组名称` : '请输入分组名称'
  const name = prompt(label)
  if (!name?.trim()) return
  fieldGroupApi.create({ domain: domainId, name: name.trim(), parent: parentId }).then(() => { message.success('分组已创建'); loadGroupTabData() }).catch(() => message.error('创建失败'))
}

function renameGroup(g: { id: number; name: string }) {
  const name = prompt('修改分组名称', g.name)
  if (!name?.trim() || name.trim() === g.name) return
  fieldGroupApi.update(g.id, { name: name.trim() }).then(() => { message.success('已重命名'); loadGroupTabData() }).catch(() => message.error('重命名失败'))
}

async function deleteGroup(id: number) {
  try {
    await fieldGroupApi.delete(id)
    message.success('分组已删除')
    if (activeGroupId.value === id) activeGroupId.value = null
    await loadGroupTabData()
  } catch { message.error('删除失败') }
}

async function changeFieldGroup(record: StandardFieldAggregate, groupId: number | null) {
  try {
    if (record.kind === 'computed') {
      await computedFieldApi.patch(record.computed_id!, { group: groupId } as any)
    } else {
      await fieldApi.batchUpdateAttributes(
        record.physical_field_ids.map(id => ({ id, group: groupId })) as any
      )
    }
    message.success('分组已更新')
  } catch { message.error('更新失败') }
}



// 分组Tab多选+拖拽
const groupSelectedKeys = ref<string[]>([])
const groupRowSelection = computed(() => ({
  selectedRowKeys: groupSelectedKeys.value,
  onChange: (keys: string[]) => { groupSelectedKeys.value = keys },
}))
const dropTargetGroupId = ref<number | null>(null)
let _dragRecords: StandardFieldAggregate[] = []

function onGroupDragStart(e: DragEvent, record: StandardFieldAggregate) {
  // 如果拖拽的行在已选中列表中，拖动所有已选行；否则只拖动当前行
  if (groupSelectedKeys.value.includes(record.key)) {
    _dragRecords = groupAggregates.value.filter(a => groupSelectedKeys.value.includes(a.key))
  } else {
    _dragRecords = [record]
  }
  e.dataTransfer?.setData('text/plain', 'drag-group-fields')
}

function onGroupDragEnd() {
  dropTargetGroupId.value = null
}

async function onDropToGroup(targetGroupId: number | null) {
  dropTargetGroupId.value = null
  // 分组节点拖拽 → 同父级重排序
  if (_dragGroupId !== null) {
    const dragId = _dragGroupId
    _dragGroupId = null
    if (targetGroupId === null || targetGroupId === dragId) return
    await reorderGroups(dragId, targetGroupId)
    return
  }
  if (_dragRecords.length === 0) return
  const physicalIds = _dragRecords.filter(r => r.kind !== 'computed').flatMap(r => r.physical_field_ids)
  const computedIds = _dragRecords.filter(r => r.kind === 'computed' && r.computed_id).map(r => r.computed_id!)
  if (physicalIds.length === 0 && computedIds.length === 0) return
  try {
    if (physicalIds.length > 0) {
      await fieldApi.batchUpdateAttributes(
        physicalIds.map(id => ({ id, group: targetGroupId })) as any
      )
    }
    for (const cid of computedIds) {
      await computedFieldApi.patch(cid, { group: targetGroupId } as any)
    }
    message.success(`已移动 ${_dragRecords.length} 项到分组`)
    groupSelectedKeys.value = []
    await loadGroupTabData()
  } catch { message.error('移动失败') }
}

// ===== 左栏分组节点拖拽排序 =====
let _dragGroupId: number | null = null

function onGroupNodeDragStart(e: DragEvent, id: number) {
  _dragGroupId = id
  _dragRecords = []
  e.dataTransfer?.setData('text/plain', 'drag-group-node')
}

function onGroupNodeDragEnd() {
  _dragGroupId = null
  dropTargetGroupId.value = null
}

// 找到包含指定分组的同级列表（顶层或某父组的 children）
function findSiblingList(id: number): FieldGroup[] | null {
  if (fieldGroups.value.some(g => g.id === id)) return fieldGroups.value
  function walk(nodes: FieldGroup[]): FieldGroup[] | null {
    for (const g of nodes) {
      if (g.children?.some(c => c.id === id)) return g.children
      if (g.children) {
        const r = walk(g.children)
        if (r) return r
      }
    }
    return null
  }
  return walk(fieldGroups.value)
}

async function reorderGroups(dragId: number, targetId: number) {
  const siblings = findSiblingList(dragId)
  if (!siblings || !siblings.some(g => g.id === targetId)) {
    message.warning('仅支持同一父级内拖拽排序')
    return
  }
  const origIdx = siblings.findIndex(g => g.id === dragId)
  const targetOrigIdx = siblings.findIndex(g => g.id === targetId)
  const ids = siblings.map(g => g.id).filter(i => i !== dragId)
  let insertIdx = ids.indexOf(targetId)
  if (origIdx < targetOrigIdx) insertIdx += 1 // 从上往下拖 → 放到目标之后
  ids.splice(insertIdx, 0, dragId)
  try {
    await fieldGroupApi.reorder(ids)
    message.success('排序已更新')
    await loadGroupTabData()
  } catch { message.error('排序失败') }
}

// ===== Tab 3: 属性配置 =====
// 统一行结构：组合（equiv）/ 基础（solo）/ 计算（computed）
interface AttrRow {
  kind: 'equiv' | 'solo' | 'computed'
  key: string
  id: number // equiv→StandardField.id，solo→物理字段id，computed→ComputedField.id
  standard_code: string
  standard_name: string
  field_type: string
  length: number | null
  required: boolean
  default_value: string
  member_count: number
  release_to_archive: boolean
  is_active: boolean | null
  ownership: 'source' | 'archive'
  group: number | null
  distinct_values: any[]
  tables: { name: string; is_primary: boolean }[]
  is_primary_key: boolean
  // 主字段（仅 equiv）：档案更新数据源头；null=未设置（刷新将被拦截）
  primary_field_id: number | null
  primary_field_label: string | null
  primary_field_manual: boolean
}
const attrRows = ref<AttrRow[]>([])
const attrSearchText = ref('')
const attrActiveGroupId = ref<number | null>(null)

const filteredAttrFields = computed(() => {
  let list = attrRows.value
  if (attrActiveGroupId.value === 0) list = list.filter(r => !r.group)
  else if (attrActiveGroupId.value !== null) {
    const ids = getDescendantGroupIds(attrActiveGroupId.value)
    list = list.filter(r => ids.includes(r.group as number))
  }
  const q = attrSearchText.value.toLowerCase().trim()
  if (q) list = list.filter(r => r.standard_code.toLowerCase().includes(q) || r.standard_name.toLowerCase().includes(q))
  return list
})

// 分组（含后代）内属性行数
function getAttrGroupCount(groupId: number): number {
  const ids = getDescendantGroupIds(groupId)
  return attrRows.value.filter(r => ids.includes(r.group as number)).length
}

function outputTypeLabel(t: string): string {
  const map: Record<string, string> = { text: '文本', number: '数字', date: '日期', boolean: '布尔' }
  return map[t] || t
}

const attrColumns = [
  { title: '类型', key: 'kind_tag', width: 70, align: 'center' as const },
  { title: '字段编码', key: 'standard_code', width: 150, ellipsis: true, sorter: (a: any, b: any) => (a.standard_code || '').localeCompare(b.standard_code || '') },
  { title: '字段名称', dataIndex: 'standard_name', key: 'standard_name', width: 140, ellipsis: true, sorter: (a: any, b: any) => (a.standard_name || '').localeCompare(b.standard_name || '') },
  { title: '所属表', key: 'tables', width: 160, ellipsis: true },
  { title: '数据类型', key: 'field_type', width: 110 },
  { title: '长度', key: 'length', width: 90 },
  { title: '必填', key: 'required', width: 70, align: 'center' as const },
  { title: '默认值', key: 'default_value', width: 140 },
  { title: '维护方', key: 'ownership', width: 130, align: 'center' as const },
  { title: '数据去重内容', key: 'distinct', ellipsis: true, sorter: (a: any, b: any) => (a.distinct_values?.length || 0) - (b.distinct_values?.length || 0) },
  { title: '成员数', key: 'member_count', width: 70, align: 'center' as const },
]

async function loadAttrTabData() {
  try {
    const [groupsRes, aggsRes, compRes] = await Promise.all([
      fieldGroupApi.tree(domainId),
      fieldApi.standardFields(domainId),
      computedFieldApi.list({ domain: domainId, status: 'active' }),
    ])
    const gData = (groupsRes as any).data || groupsRes
    fieldGroups.value = gData.results || gData || []
    expandedGroupIds.value = new Set(fieldGroups.value.map(g => g.id))
    const aData = (aggsRes as any).data || aggsRes
    const aggs = (aData.results || aData || []) as StandardFieldAggregate[]
    const cData = (compRes as any).data || compRes
    const comps = (cData.results || cData || []) as ComputedFieldModel[]
    const rows: AttrRow[] = []
    for (const a of aggs) {
      rows.push({
        kind: a.kind,
        key: a.key,
        id: a.kind === 'equiv' ? (a.sf_id as number) : a.physical_field_ids[0],
        standard_code: a.standard_code,
        standard_name: a.standard_name,
        field_type: a.field_type || 'string',
        length: a.length ?? null,
        required: !!a.required,
        default_value: a.default_value || '',
        member_count: a.member_count,
        release_to_archive: a.release_to_archive,
        is_active: a.kind === 'equiv' ? (a.is_active ?? true) : null,
        ownership: (a.ownership as any) || 'source',
        group: a.group,
        distinct_values: a.distinct_values || [],
        tables: (a as any).tables || [],
        is_primary_key: !!(a as any).is_primary_key,
        primary_field_id: a.primary_field_id ?? null,
        primary_field_label: a.primary_field_label ?? null,
        primary_field_manual: !!a.primary_field_manual,
      })
    }
    for (const c of comps) {
      rows.push({
        kind: 'computed',
        key: `computed_${c.id}`,
        id: c.id,
        standard_code: c.code,
        standard_name: c.name,
        field_type: c.output_type,
        length: null,
        required: false,
        default_value: '',
        member_count: 0,
        release_to_archive: c.release_to_archive,
        is_active: null,
        ownership: 'archive',
        group: c.group ?? null,
        distinct_values: [],
        tables: [],
        is_primary_key: false,
        primary_field_id: null,
        primary_field_label: null,
        primary_field_manual: false,
      })
    }
    attrRows.value = rows
  } catch { /* ignore */ }
}

let _saveTimer: ReturnType<typeof setTimeout> | null = null
function saveAttrField(record: AttrRow) {
  if (_saveTimer) clearTimeout(_saveTimer)
  _saveTimer = setTimeout(async () => {
    try {
      if (record.kind === 'equiv') {
        await standardFieldApi.patch(record.id, {
          field_type: record.field_type,
          length: record.length,
          required: record.required,
          default_value: record.default_value,
          release_to_archive: record.release_to_archive,
          is_active: record.is_active as boolean,
          ownership: record.ownership,
        })
      } else if (record.kind === 'solo') {
        await fieldApi.batchUpdateAttributes([{
          id: record.id,
          field_type: record.field_type,
          length: record.length,
          required: record.required,
          default_value: record.default_value,
          release_to_archive: record.release_to_archive,
          ownership: record.ownership,
        }] as any)
      } else {
        // 计算字段：仅支持切换释放到档案
        await computedFieldApi.patch(record.id, { release_to_archive: record.release_to_archive })
      }
    } catch { message.error('保存失败') }
  }, 500)
}

// ===== AI 操作 =====
const aiLoading = reactive({ group: false, semantic: false })
async function runAutoGroup() {
  aiLoading.group = true
  try { await fieldApi.aiAutoGroup(domainId); message.success('AI自动分组完成'); await refreshAllData() }
  catch (e: any) { message.error(extractApiError(e) || '自动分组失败') }
  finally { aiLoading.group = false }
}
async function runSemantic() {
  aiLoading.semantic = true
  try { await fieldApi.aiSemantic(domainId); message.success('AI自动配置完成'); await refreshAllData() }
  catch (e: any) { message.error(extractApiError(e) || '自动配置失败') }
  finally { aiLoading.semantic = false }
}

// ===== 字段分类操作 =====
async function confirmAsBase() {
  if (selectedRowKeys.value.length === 0) return
  Modal.confirm({ title: '确认为基础字段？', content: `将 ${selectedRowKeys.value.length} 个字段标记为基础字段。`, okText: '确认', async onOk() {
    try { await fieldApi.batchUpdateAttributes(selectedRowKeys.value.map(id => ({ id: Number(id), archive_category: 'base', release_to_archive: true })) as any); message.success('已确认为基础字段'); selectedRowKeys.value = []; await refreshCategoryData() }
    catch (e: any) { message.error(extractApiError(e) || '操作失败') }
  }})
}
async function discardSelected() {
  if (selectedRowKeys.value.length === 0) return
  Modal.confirm({ title: '设为废弃？', content: `将 ${selectedRowKeys.value.length} 个字段标记为废弃。`, okText: '确认', okType: 'danger', async onOk() {
    try { await fieldApi.batchUpdateAttributes(selectedRowKeys.value.map(id => ({ id: Number(id), status: 'deprecated' })) as any); message.success('已设为废弃'); selectedRowKeys.value = []; await refreshCategoryData() }
    catch (e: any) { message.error(extractApiError(e) || '操作失败') }
  }})
}
async function moveToUnassigned() {
  if (selectedRowKeys.value.length === 0) return
  try { await fieldApi.batchUpdateAttributes(selectedRowKeys.value.map(id => ({ id: Number(id), archive_category: 'unassigned', release_to_archive: false })) as any); message.success('已移到未分配'); selectedRowKeys.value = []; await refreshCategoryData() }
  catch (e: any) { message.error(extractApiError(e) || '操作失败') }
}
async function discardComposite() {
  if (selectedRowKeys.value.length === 0) return
  Modal.confirm({ title: '将组合字段设为废弃？', content: `将 ${selectedRowKeys.value.length} 个组合字段标记为废弃。`, okText: '确认', okType: 'danger', async onOk() {
    try { for (const id of selectedRowKeys.value) { await standardFieldApi.patch(Number(id), { status: 'discarded' } as any) }; message.success('已设为废弃'); selectedRowKeys.value = []; await refreshCategoryData() }
    catch (e: any) { message.error(extractApiError(e) || '操作失败') }
  }})
}
async function deleteCompositeField(record: StandardFieldModel) {
  try {
    await standardFieldApi.delete(record.id)
    message.success('组合字段已释放，成员已回到未分配')
    await refreshCategoryData()
  } catch (e: any) { message.error(extractApiError(e) || '释放失败') }
}

// ===== 组合字段表内拖拽调整成员归属 =====
const compositeDragTarget = ref<number | null>(null)
let _compositeDragRecord: any = null

function getCompositeCustomRow(record: any) {
  return {
    draggable: !record._rowKey.endsWith('_empty'),
    class: record._isFirst ? 'composite-group-header' : 'draggable-row',
    onDragstart: (e: DragEvent) => onCompositeDragStart(e, record),
    onDragover: (e: DragEvent) => onCompositeDragOver(e, record),
    onDragleave: () => { compositeDragTarget.value = null },
    onDrop: (e: DragEvent) => onCompositeDrop(e, record),
    onDragend: () => { compositeDragTarget.value = null },
    style: compositeDragTarget.value === record._sfRecord?.id && record._isFirst ? 'background:#d9f7be;outline:2px dashed #52c41a' : '',
  }
}

function onCompositeDragStart(e: DragEvent, record: any) {
  _compositeDragRecord = record
  e.dataTransfer?.setData('text/plain', 'composite-member')
}
function onCompositeDragOver(e: DragEvent, record: any) {
  e.preventDefault()
  // 高亮目标组合字段（不能放到自己所属的组合字段）
  if (!_compositeDragRecord || !record._sfRecord) return
  if (record._sfRecord.id !== _compositeDragRecord._sfRecord?.id) {
    compositeDragTarget.value = record._sfRecord.id
  }
}
async function onCompositeDrop(e: DragEvent, record: any) {
  e.preventDefault()
  compositeDragTarget.value = null
  if (!_compositeDragRecord || !record._sfRecord) return
  const sourceSfId = _compositeDragRecord._sfRecord?.id
  const targetSfId = record._sfRecord.id
  if (!sourceSfId || !targetSfId || sourceSfId === targetSfId) return
  // 获取被拖拽成员的物理字段ID
  const memberId = _compositeDragRecord._memberId
  if (!memberId) return
  try {
    await standardFieldApi.removeMember(sourceSfId, memberId)
    await standardFieldApi.addMember(targetSfId, [memberId])
    message.success('成员已移动到目标组合字段')
    await refreshCategoryData()
  } catch (e: any) { message.error(extractApiError(e) || '移动失败') }
}

async function discardComputed() {
  if (selectedRowKeys.value.length === 0) return
  Modal.confirm({ title: '将计算字段设为废弃？', content: `将 ${selectedRowKeys.value.length} 个计算字段标记为废弃。`, okText: '确认', okType: 'danger', async onOk() {
    try { for (const id of selectedRowKeys.value) { await computedFieldApi.patch(Number(id), { status: 'discarded' }) }; message.success('已设为废弃'); selectedRowKeys.value = []; await refreshCategoryData() }
    catch (e: any) { message.error(extractApiError(e) || '操作失败') }
  }})
}
async function restoreSelected() {
  if (selectedRowKeys.value.length === 0) return
  try {
    for (const id of selectedRowKeys.value) {
      const raw = String(id)
      if (raw.startsWith('phys_')) { await fieldApi.batchUpdateAttributes([{ id: Number(raw.replace('phys_', '')), status: 'active', archive_category: 'unassigned' }] as any) }
      else if (raw.startsWith('std_')) { await standardFieldApi.patch(Number(raw.replace('std_', '')), { status: 'active' } as any) }
      else if (raw.startsWith('comp_')) { await computedFieldApi.patch(Number(raw.replace('comp_', '')), { status: 'active' }) }
    }
    message.success('已恢复'); selectedRowKeys.value = []; await refreshCategoryData()
  } catch (e: any) { message.error(extractApiError(e) || '恢复失败') }
}

// ===== 分类 Tab 拖拽到左侧分类 =====
const catDropTarget = ref<string | null>(null)
let _catDragRecords: any[] = []

function onCatDragStart(e: DragEvent, record: any) {
  // 如果当前行已选中，拖动所有已选行；否则只拖动当前行
  if (selectedRowKeys.value.includes(record.id)) {
    _catDragRecords = selectedRowKeys.value.map(id => ({ id }))
  } else {
    _catDragRecords = [record]
  }
  e.dataTransfer?.setData('text/plain', 'drag-cat-fields')
}

function onCatDragEnd() {
  catDropTarget.value = null
}

async function onDropToCategory(target: string) {
  catDropTarget.value = null
  if (_catDragRecords.length === 0) return
  const ids = _catDragRecords.map(r => r.id)
  try {
    if (target === 'composite') {
      // 拖到组合字段：预填充已选字段，打开合并弹窗
      selectedRowKeys.value = ids
      openMergeModal()
      return
    }
    if (target === 'base') {
      await fieldApi.batchUpdateAttributes(ids.map(id => ({ id: Number(id), archive_category: 'base', release_to_archive: true })) as any)
      message.success(`已移入基础字段`)
    } else if (target === 'unassigned') {
      // 支持从废弃状态恢复：设 status=active + archive_category=unassigned
      const isFromDiscarded = activeCategory.value === 'discarded'
      if (isFromDiscarded) {
        // 废弃字段含多种类型，逐个处理
        for (const record of _catDragRecords) {
          const raw = String(record.id)
          if (raw.startsWith('phys_')) { await fieldApi.batchUpdateAttributes([{ id: Number(raw.replace('phys_', '')), status: 'active', archive_category: 'unassigned' }] as any) }
          else if (raw.startsWith('std_')) { await standardFieldApi.patch(Number(raw.replace('std_', '')), { status: 'active' } as any) }
          else if (raw.startsWith('comp_')) { await computedFieldApi.patch(Number(raw.replace('comp_', '')), { status: 'active' }) }
        }
        message.success('已恢复到未分配')
      } else {
        await fieldApi.batchUpdateAttributes(ids.map(id => ({ id: Number(id), archive_category: 'unassigned', release_to_archive: false })) as any)
        message.success(`已移入未分配`)
      }
    } else if (target === 'discarded') {
      await fieldApi.batchUpdateAttributes(ids.map(id => ({ id: Number(id), status: 'deprecated' })) as any)
      message.success(`已设为废弃`)
    }
    selectedRowKeys.value = []
    await refreshCategoryData()
  } catch (e: any) { message.error(extractApiError(e) || '移动失败') }
}

// ===== 合并为组合字段 =====
const mergeModalVisible = ref(false)
const mergeSubmitting = ref(false)
const mergeForm = reactive({ standard_code: '', standard_name: '' })
function openMergeModal() { mergeForm.standard_code = ''; mergeForm.standard_name = ''; mergeModalVisible.value = true }
async function submitMerge() {
  const code = mergeForm.standard_code.trim()
  if (!code) { message.warning('请填写字段编码'); return }
  if (selectedRowKeys.value.length < 2) { message.warning('至少选择两个字段'); return }
  mergeSubmitting.value = true
  try { await standardFieldApi.create({ domain: domainId, standard_code: code, standard_name: mergeForm.standard_name.trim(), member_field_ids: selectedRowKeys.value.map(Number) }); message.success('已合并为组合字段'); mergeModalVisible.value = false; selectedRowKeys.value = []; await refreshCategoryData() }
  catch (e: any) { message.error(extractApiError(e) || '合并失败') }
  finally { mergeSubmitting.value = false }
}

// ===== 组合字段成员查看 =====
const distinctDrawerVisible = ref(false)
const distinctLoading = ref(false)
const distinctDrawerTitle = ref('')
const distinctMembers = ref<StandardFieldMemberDistinct[]>([])
const distinctStandardFieldId = ref<number>(0)

async function openMembersDistinct(record: StandardFieldModel) {
  distinctDrawerVisible.value = true
  distinctStandardFieldId.value = record.id
  distinctDrawerTitle.value = `查看成员：${record.standard_code}${record.standard_name ? '（' + record.standard_name + '）' : ''}`
  distinctMembers.value = []
  distinctLoading.value = true
  try { const res = await standardFieldApi.membersDistinct(record.id); const data = (res as any).data || res; distinctMembers.value = data.members || [] }
  catch { message.error('加载失败') }
  finally { distinctLoading.value = false }
}

async function releaseMember(fieldId: number) {
  if (!distinctStandardFieldId.value) return
  try {
    // 如果当前成员数≤2，释放意味着整个组合字段都不要了，删除组合字段
    if (distinctMembers.value.length <= 2) {
      await standardFieldApi.delete(distinctStandardFieldId.value)
      message.success('组合字段已删除，所有成员已释放')
      distinctDrawerVisible.value = false
      distinctMembers.value = []
      await refreshCategoryData()
      return
    }
    await standardFieldApi.removeMember(distinctStandardFieldId.value, fieldId)
    message.success('已释放')
    // 刷新抽屉数据
    const res = await standardFieldApi.membersDistinct(distinctStandardFieldId.value)
    const data = (res as any).data || res
    distinctMembers.value = data.members || []
    // 同步刷新分类数据
    await refreshCategoryData()
  } catch (e: any) { message.error(extractApiError(e) || '释放失败') }
}

// R-023: 成员≤2 时释放 = 删除整个组合字段，需明确警告
function confirmReleaseMember(fieldId: number) {
  if (distinctMembers.value.length <= 2) {
    Modal.confirm({
      title: '确认删除整个组合字段？',
      content: '当前组合字段仅剩 2 个成员，释放后将删除整个组合字段，所有成员都将解除关联。',
      okText: '确认删除',
      okType: 'danger',
      cancelText: '取消',
      onOk: () => releaseMember(fieldId),
    })
  } else {
    releaseMember(fieldId)
  }
}

// 设为主字段（档案更新数据源头）；成功后刷新抽屉与分类数据
async function setPrimaryMember(fieldId: number) {
  if (!distinctStandardFieldId.value) return
  try {
    await standardFieldApi.setPrimaryField(distinctStandardFieldId.value, fieldId)
    message.success('已设为主字段')
    const res = await standardFieldApi.membersDistinct(distinctStandardFieldId.value)
    const data = (res as any).data || res
    distinctMembers.value = data.members || []
    await refreshCategoryData()
    if (mainTab.value === 'attr') await loadAttrTabData()
  } catch (e: any) { message.error(extractApiError(e) || '设置失败') }
}

// 组合字段表内直接设置主字段（复用 set-primary-field 专用端点）
async function setPrimaryFromComposite(row: any) {
  if (!row._sfRecord || !row._memberId) return
  try {
    await standardFieldApi.setPrimaryField(row._sfRecord.id, row._memberId)
    message.success('已设为主字段')
    await refreshCategoryData()
  } catch (e: any) { message.error(extractApiError(e) || '设置失败') }
}


// ===== 计算字段操作 =====
const formulaEditorOpen = ref(false)
const editingComputedField = ref<ComputedFieldModel | null>(null)
const trialCalcOpen = ref(false)
const trialCalcField = ref<ComputedFieldModel | null>(null)
const batchRecalculating = ref(false)

function openFormulaEditor(field: ComputedFieldModel | null) {
  editingComputedField.value = field
  formulaEditorOpen.value = true
}

function openTrialCalc(field: ComputedFieldModel) {
  trialCalcField.value = field
  trialCalcOpen.value = true
}

async function onComputedFieldSaved(_field: ComputedFieldModel) {
  await loadComputedFields()
  await loadCategoryCounts()
}

function onSaveAndTrial(field: ComputedFieldModel) {
  onComputedFieldSaved(field)
  // 延迟打开试算弹窗，等FormulaEditor关闭动画完成
  setTimeout(() => {
    trialCalcField.value = field
    trialCalcOpen.value = true
  }, 200)
}

async function toggleComputedStatus(record: ComputedFieldModel) {
  try {
    await computedFieldApi.patch(record.id, { status: 'discarded' })
    message.success('已废弃，可在左栏「废弃字段」分类中恢复')
    await loadComputedFields()
    await loadCategoryCounts()
  } catch (e: any) { message.error(extractApiError(e) || '操作失败') }
}

async function handleBatchRecalculate() {
  batchRecalculating.value = true
  try {
    const res = await computedFieldApi.batchRecalculate(domainId)
    const data = (res as any).data || res
    message.success(`批量重算完成：更新 ${data.records_updated} 条记录`)
  } catch (e: any) { message.error(extractApiError(e) || '批量重算失败') }
  finally { batchRecalculating.value = false }
}

// ===== 刷新去重内容 =====
const manualRefreshing = ref(false)
async function refreshManualDistinct() {
  manualRefreshing.value = true
  try { await fieldApi.refreshDistinct(domainId); message.success('去重内容已刷新'); await loadBaseFields(); await loadCompositeFields() }
  catch { message.error('刷新失败') }
  finally { manualRefreshing.value = false }
}

// ===== 全量刷新 =====
async function refreshAllData() {
  await refreshCategoryData()
  if (mainTab.value === 'group') await loadGroupTabData()
  if (mainTab.value === 'attr') await loadAttrTabData()
}

// ===== 初始化 =====
async function loadData() {
  loading.value = true
  try { const domainRes = await domainApi.get(domainId); const domainData = (domainRes as any).data || domainRes; domainName.value = domainData.name || '' } catch { /* ignore */ }
  await refreshCategoryData()
  loading.value = false
}

onMounted(() => { loadData() })
</script>

<style scoped>
.page-header-tabs { display: flex; align-items: center; margin-bottom: 16px; }
.split-layout { display: flex; gap: 16px; min-height: max(520px, calc(100vh - 260px)); }
.split-layout__left { width: 270px; flex-shrink: 0; background: #fff; border: 1px solid #f0f0f0; border-radius: 8px; display: flex; flex-direction: column; overflow: hidden; }
.split-layout__right { flex: 1; background: #fff; border: 1px solid #f0f0f0; border-radius: 8px; display: flex; flex-direction: column; overflow: hidden; }
.panel-header { padding: 12px 16px; border-bottom: 1px solid #f0f0f0; display: flex; justify-content: space-between; align-items: center; background: #fafbfc; flex-wrap: wrap; gap: 8px; }
.panel-title { font-weight: 600; font-size: 14px; color: #262626; }
.panel-sub { font-weight: normal; font-size: 12px; color: #8c8c8c; margin-left: 8px; }
.category-list { flex: 1; overflow-y: auto; padding: 8px 0; }
.category-item { padding: 8px 14px; margin: 2px 8px; border-radius: 6px; cursor: pointer; display: flex; justify-content: space-between; align-items: center; transition: background 0.15s; }
.category-item:hover { background: #f5f5f5; }
.category-item--active { background: #e6f4ff; }
.category-item--active:hover { background: #bae0ff; }
.category-item--drop-target { background: #d9f7be; outline: 2px dashed #52c41a; }
.category-divider { height: 1px; background: #e8e8e8; margin: 8px 12px; }
.category-item--parent { font-weight: 500; margin-top: 4px; }
.category-item--child { padding-left: 32px; font-size: 13px; }
.category-item__name { font-size: 13px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.tree-toggle { display: inline-block; width: 14px; cursor: pointer; font-size: 12px; color: #8c8c8c; text-align: center; }
.tree-toggle:hover { color: #1677ff; }
.table-wrapper { flex: 1; overflow: auto; padding: 8px 16px; }
.drag-handle { cursor: grab; font-size: 16px; color: #bfbfbf; user-select: none; }
.drag-handle:active { cursor: grabbing; }
.row-descendant td { background-color: #f6f8fa !important; }
:deep(.draggable-row) { cursor: grab; }
:deep(.draggable-row:active) { cursor: grabbing; opacity: 0.7; }
:deep(.composite-group-header) { background: #fafafa; border-top: 2px solid #e8e8e8; }
</style>
