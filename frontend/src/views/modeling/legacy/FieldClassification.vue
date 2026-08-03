<template>
  <div>
    <div class="page-header">
      <a-space>
        <a-button @click="goBack">← 返回字段配置</a-button>
        <h2 v-if="tableName">表：{{ tableName }} — AI字段分类与冗余检测</h2>
      </a-space>
    </div>

    <div v-if="!aiStarted" style="text-align: center; padding: 60px 0">
      <a-empty description="尚未进行AI分析">
        <a-button type="primary" size="large" :loading="aiLoading" @click="startAiAnalysis">
          开始AI分析
        </a-button>
      </a-empty>
      <p style="color: #999; margin-top: 8px">AI将自动对字段进行分类并检测可能的冗余字段</p>
    </div>

    <div v-else>
      <a-spin :spinning="aiLoading">
        <a-alert
          message="AI分析完成，请审核以下分类方案。您可以拖拽调整字段到不同分组，也可以合并/重命名分组。"
          type="success"
          show-icon
          style="margin-bottom: 16px"
        />

        <div v-for="group in groups" :key="group.name" style="margin-bottom: 24px">
          <a-card :title="group.name" :headStyle="{ fontWeight: 600 }">
            <template #extra>
              <a-space>
                <a-button size="small" @click="renameGroup(group)">重命名</a-button>
                <a-popconfirm title="确定删除该分组？字段将移至未分类" @confirm="deleteGroup(group)">
                  <a-button size="small" danger>删除</a-button>
                </a-popconfirm>
              </a-space>
            </template>
            <div class="field-chips">
              <a-tag
                v-for="field in group.fields"
                :key="field.code"
                closable
                :color="group.color || 'blue'"
                style="margin: 4px; padding: 4px 12px; font-size: 14px; cursor: move"
              >
                {{ field.name }} ({{ field.code }})
              </a-tag>
            </div>
          </a-card>
        </div>

        <div v-if="redundantFields.length > 0" style="margin-bottom: 16px">
          <a-card title="疑似冗余字段" :headStyle="{ fontWeight: 600, color: '#faad14' }">
            <template #extra>
              <a-button size="small" type="link" @click="markAllNonRedundant">全部标记为非冗余</a-button>
            </template>
            <div class="field-chips">
              <a-tag
                v-for="field in redundantFields"
                :key="field.code"
                closable
                color="orange"
                style="margin: 4px; padding: 4px 12px; font-size: 14px"
                @close="removeRedundant(field)"
              >
                {{ field.name }} ({{ field.code }})
              </a-tag>
            </div>
          </a-card>
        </div>

        <div style="text-align: center; margin-top: 24px">
          <a-space>
            <a-button @click="regenerate">重新分析</a-button>
            <a-button type="primary" :loading="confirming" @click="confirmClassification">
              确认分类方案
            </a-button>
          </a-space>
        </div>
      </a-spin>
    </div>

    <a-modal v-model:open="renameModal" title="重命名分组" @ok="doRename" okText="确定" cancelText="取消">
      <a-input v-model:value="renameValue" />
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { tableApi, fieldApi, fieldGroupApi } from '@/api/modeling'
import api from '@/api/index'

const route = useRoute()
const router = useRouter()
const tableId = Number(route.params.id)
const tableName = ref('')
const aiStarted = ref(false)
const aiLoading = ref(false)
const confirming = ref(false)
const groups = ref<any[]>([])
const redundantFields = ref<any[]>([])
const renameModal = ref(false)
const renameTarget = ref<any>(null)
const renameValue = ref('')

const colors = ['blue', 'green', 'purple', 'cyan', 'pink', 'orange']

async function loadData() {
  try {
    const res = await tableApi.get(tableId)
    tableName.value = res.data.name
  } catch (e: any) {
    message.error(e.message)
  }
}

async function startAiAnalysis() {
  aiLoading.value = true
  aiStarted.value = true
  try {
    const res = await api.post(`/fields/ai-analyze/?table=${tableId}`)
    groups.value = (res.data.groups || []).map((g: any, i: number) => ({
      ...g,
      color: colors[i % colors.length],
    }))
    redundantFields.value = res.data.redundant_fields || []
    message.success('AI分析完成')
  } catch (e: any) {
    message.error(e.message || 'AI分析失败')
    aiStarted.value = false
  } finally {
    aiLoading.value = false
  }
}

function renameGroup(group: any) {
  renameTarget.value = group
  renameValue.value = group.name
  renameModal.value = true
}

function doRename() {
  if (renameTarget.value && renameValue.value) {
    renameTarget.value.name = renameValue.value
    message.info('重命名已记录，请点击下方「确认分类方案」保存到后端')
  }
  renameModal.value = false
}

function deleteGroup(group: any) {
  const idx = groups.value.indexOf(group)
  if (idx > -1) groups.value.splice(idx, 1)
}

function removeRedundant(field: any) {
  const idx = redundantFields.value.indexOf(field)
  if (idx > -1) redundantFields.value.splice(idx, 1)
}

function markAllNonRedundant() {
  redundantFields.value = []
}

function regenerate() {
  groups.value = []
  redundantFields.value = []
  aiStarted.value = false
}

async function confirmClassification() {
  confirming.value = true
  try {
    const domainRes = await tableApi.get(tableId)
    const domainId = domainRes.data.domain
    // 保存分组方案
    for (const group of groups.value) {
      await fieldGroupApi.create({
        domain: domainId,
        name: group.name,
        sort_order: groups.value.indexOf(group),
      })
    }
    message.success('分类方案已确认保存，现在可以配置字段属性了')
  } catch (e: any) {
    message.error(e.message || '保存失败')
  } finally {
    confirming.value = false
  }
}

function goBack() {
  router.back()
}

onMounted(loadData)
</script>

<style scoped>
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}
.page-header h2 {
  margin: 0;
  font-size: 18px;
  display: inline;
}
.field-chips {
  min-height: 40px;
  padding: 8px;
}
</style>
