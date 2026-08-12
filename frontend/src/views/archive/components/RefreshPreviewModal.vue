<!--
  刷新预检弹窗（R-062：ArchiveList 与 ArchiveDetail 两处同构弹窗收敛为单组件，防 R-016/R-048 式分叉）
  职责：展示预检结果（schema 变化 + 数据试算 + 波及告警 + warnings），发出确认意图；
  确认后的执行逻辑（syncSchema/refreshData + stats 汇报 + 刷新页面）留在父组件——两处刷新对象不同。
-->
<template>
  <a-modal
    :open="open"
    :title="modalTitle"
    width="760px"
    okText="确认更新"
    cancelText="取消"
    :bodyStyle="{ maxHeight: '65vh', overflowY: 'auto' }"
    @update:open="(v: boolean) => emit('update:open', v)"
    @ok="emit('confirm')"
  >
    <template v-if="previewData">
      <!-- 结构变化 -->
      <template v-if="previewData.schema_changes?.has_changes">
        <a-alert type="warning" show-icon style="margin-bottom: 12px">
          <template #message>模型结构有变化，确认后将先同步结构再刷新数据（schema 版本 +1）</template>
        </a-alert>
        <div v-if="previewData.schema_changes.added?.length" style="margin-bottom: 8px">
          <b>新增字段：</b>
          <a-tag v-for="f in previewData.schema_changes.added" :key="f.code" color="green">{{ f.name }}</a-tag>
        </div>
        <div v-if="previewData.schema_changes.removed?.length" style="margin-bottom: 8px">
          <b>移除字段：</b>
          <a-tag v-for="f in previewData.schema_changes.removed" :key="f.code" color="red">{{ f.name }}</a-tag>
        </div>
        <div v-if="previewData.schema_changes.changed?.length" style="margin-bottom: 8px">
          <b>字段变更：</b>
          <div v-for="f in previewData.schema_changes.changed" :key="f.code" style="margin: 4px 0 0 12px">
            <span style="color: #1890ff">{{ f.name }}</span>
            <span v-for="(c, i) in f.changes" :key="i" style="margin-left: 8px; color: #666">
              {{ c.attr }}：<span style="color: #ff4d4f">{{ c.old ?? '-' }}</span> → <span style="color: #52c41a">{{ c.new ?? '-' }}</span>
            </span>
          </div>
        </div>
        <a-divider style="margin: 12px 0" />
      </template>
      <!-- 数据变化 -->
      <template v-if="previewData.data_changes?.has_changes">
        <div style="margin-bottom: 8px">
          <b>数据变化：</b>
          <a-tag v-if="previewData.data_changes.would_create" color="green">新增 {{ previewData.data_changes.would_create }} 条</a-tag>
          <a-tag v-if="previewData.data_changes.would_update" color="blue">更新 {{ previewData.data_changes.would_update }} 条</a-tag>
          <a-tag v-if="previewData.data_changes.would_deactivate" color="orange">源侧已删将停用 {{ previewData.data_changes.would_deactivate }} 条</a-tag>
        </div>
        <!-- v18：档案维护字段被源侧刷新波及告警（仅提醒，不阻断刷新） -->
        <a-alert
          v-if="previewData.data_changes.archive_owned_impact?.records"
          type="warning" show-icon style="margin-bottom: 8px"
        >
          <template #message>
            本次源侧刷新将波及 <b>{{ previewData.data_changes.archive_owned_impact.records }}</b> 条记录的<b>档案维护字段</b>（这些记录该字段无人工覆盖，值取自源侧）
          </template>
          <template #description>
            <a-tag v-for="f in previewData.data_changes.archive_owned_impact.fields" :key="f.code" color="orange" style="margin: 2px 4px 2px 0">{{ f.name }}（{{ f.records }} 条）</a-tag>
          </template>
        </a-alert>
        <a-table
          v-if="previewData.data_changes.changes_sample?.length"
          :dataSource="previewData.data_changes.changes_sample"
          :columns="[{ title: '记录标识', dataIndex: 'record_key', key: 'record_key', width: 140 }, { title: '字段变化', key: 'fields' }]"
          :pagination="false"
          rowKey="record_key"
          size="small"
          :scroll="{ y: 240 }"
        >
          <template #bodyCell="{ column, record: s }">
            <template v-if="column.key === 'fields'">
              <div v-for="(cf, i) in s.changed_fields" :key="i" style="line-height: 1.8">
                <span style="color: #1890ff">{{ cf.name }}</span>
                <span style="color: #999">：</span>
                <span style="color: #ff4d4f">{{ cf.old ?? '-' }}</span>
                <span style="color: #999"> → </span>
                <span style="color: #52c41a">{{ cf.new ?? '-' }}</span>
              </div>
            </template>
          </template>
        </a-table>
        <div v-if="(previewData.data_changes.would_update || 0) > (previewData.data_changes.changes_sample?.length || 0)" style="color: #999; margin-top: 4px">
          仅展示前 {{ previewData.data_changes.changes_sample?.length }} 条变化样本
        </div>
      </template>
      <a-alert v-if="previewData.data_changes?.errors?.length" type="error" show-icon style="margin-top: 8px">
        <template #message>试算遇到错误：{{ previewData.data_changes.errors.slice(0, 5).join('；') }}</template>
      </a-alert>
      <a-alert v-if="previewData.data_changes?.warnings?.length" type="warning" show-icon style="margin-top: 8px">
        <template #message>{{ previewData.data_changes.warnings.slice(0, 5).join('；') }}</template>
      </a-alert>
    </template>
  </a-modal>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(defineProps<{
  open: boolean
  previewData: any | null
  archiveName?: string
}>(), { archiveName: '' })

const emit = defineEmits<{
  (e: 'update:open', open: boolean): void
  (e: 'confirm'): void
}>()

const modalTitle = computed(() =>
  props.archiveName ? `刷新预检 — ${props.archiveName}` : '刷新预检：检测到以下变化'
)
</script>
