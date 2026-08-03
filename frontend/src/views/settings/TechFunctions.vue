<template>
  <div>
    <div class="page-header">
      <h2>系统设置 — 技术函数</h2>
      <a-space>
        <a-button @click="loadTemplate">下载模板</a-button>
        <a-button :loading="listLoading" @click="loadPlugins">刷新</a-button>
      </a-space>
    </div>

    <a-alert
      type="info"
      show-icon
      style="margin-bottom: 16px"
    >
      <template #message>
        <div>
          技术函数允许通过上传 <code>.py</code> 脚本动态扩展公式引擎，无需重启服务。
          插件内使用 <code>@register_function(name, min_args, max_args, description, category='技术函数')</code> 注册函数，
          自动纳入公式校验/求值/前端函数库/AI 生成表达式全链路。
        </div>
        <div style="color:#888;font-size:12px;margin-top:4px">
          安全策略：白名单导入（re / hashlib / math / datetime / apps.modeling.formula_engine），禁止 os / sys / subprocess / open / eval / exec 等危险操作。
        </div>
      </template>
    </a-alert>

    <!-- 上传区 -->
    <a-card size="small" title="上传插件" style="margin-bottom: 16px">
      <a-upload-dragger
        name="file"
        :multiple="false"
        :accept="'.py'"
        :show-upload-list="false"
        :custom-request="handleUpload"
        :disabled="uploading"
      >
        <p class="ant-upload-drag-icon">
          <inbox-outlined v-if="!uploading" />
          <a-spin v-else />
        </p>
        <p class="ant-upload-text">点击或拖拽 .py 文件到此区域上传</p>
        <p class="ant-upload-hint">
          文件名仅允许字母、数字、下划线、点、连字符。上传后自动进行 AST 安全校验并加载。
        </p>
      </a-upload-dragger>
    </a-card>

    <!-- 已加载插件列表 -->
    <a-card size="small" :title="`已加载插件（${plugins.length}）`">
      <template #extra>
        <a-tag color="blue">共 {{ totalFunctions }} 个函数</a-tag>
      </template>
      <a-empty v-if="plugins.length === 0 && !listLoading" description="暂无已加载插件" />
      <a-list v-else item-layout="horizontal" :data-source="plugins">
        <template #renderItem="{ item }">
          <a-list-item>
            <a-list-item-meta>
              <template #title>
                <span style="font-family: monospace">{{ item.filename }}</span>
                <a-tag color="green" style="margin-left: 8px">{{ item.function_count }} 函数</a-tag>
              </template>
              <template #description>
                <div v-if="item.functions.length > 0" style="margin-top: 4px">
                  <a-tag v-for="fn in item.functions" :key="fn.name" style="margin: 2px 4px 2px 0">
                    {{ fn.name }}
                    <span style="color:#888;font-size:11px">（{{ fn.category }}）</span>
                  </a-tag>
                </div>
                <div v-else style="color:#999;font-size:12px">（无函数注册）</div>
              </template>
            </a-list-item-meta>
            <template #actions>
              <a-button size="small" :loading="reloadingMap[item.filename]" @click="handleReload(item.filename)">重载</a-button>
              <a-popconfirm
                :title="`确认卸载插件 ${item.filename}？卸载后其注册的函数将从公式引擎移除。`"
                ok-text="确认卸载"
                cancel-text="取消"
                @confirm="handleUnload(item.filename)"
              >
                <a-button size="small" danger :loading="unloadingMap[item.filename]">卸载</a-button>
              </a-popconfirm>
            </template>
          </a-list-item>
        </template>
      </a-list>
    </a-card>

    <!-- 模板弹窗 -->
    <a-modal
      v-model:open="templateVisible"
      title="插件模板代码"
      width="760px"
      okText="复制代码"
      cancelText="关闭"
      @ok="copyTemplate"
    >
      <a-alert
        type="success"
        show-icon
        style="margin-bottom: 12px"
        message="复制下方代码保存为 .py 文件，修改函数实现后上传即可加载。"
      />
      <a-typography-paragraph>
        <pre style="background:#f6f8fa;padding:12px;border-radius:4px;max-height:500px;overflow:auto;font-size:12px;line-height:1.5">{{ templateCode }}</pre>
      </a-typography-paragraph>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, reactive } from 'vue'
import { message } from 'ant-design-vue'
import { InboxOutlined } from '@ant-design/icons-vue'
import { computedFieldApi, type PluginInfo } from '@/api/modeling'
import { extractApiError } from '@/utils/apiError'

const plugins = ref<PluginInfo[]>([])
const listLoading = ref(false)
const uploading = ref(false)
const reloadingMap = reactive<Record<string, boolean>>({})
const unloadingMap = reactive<Record<string, boolean>>({})

const templateVisible = ref(false)
const templateCode = ref('')

const totalFunctions = computed(() => plugins.value.reduce((sum, p) => sum + p.function_count, 0))

async function loadPlugins() {
  listLoading.value = true
  try {
    const res = await computedFieldApi.pluginList()
    plugins.value = res.data.plugins || []
  } catch (e: any) {
    message.error(extractApiError(e) || '加载插件列表失败')
  } finally {
    listLoading.value = false
  }
}

async function handleUpload(options: any) {
  const file = options.file as File
  if (!file.name.endsWith('.py')) {
    message.error('仅支持 .py 文件')
    options.onError?.(new Error('only .py'))
    return
  }
  uploading.value = true
  try {
    const res = await computedFieldApi.pluginUpload(file)
    const info = res.data
    message.success(`插件 ${info.filename} 上传成功，注册 ${info.functions.length} 个函数`)
    options.onSuccess?.(info)
    await loadPlugins()
  } catch (e: any) {
    const data = e.response?.data
    let errMsg = data?.error || '上传失败'
    if (data?.details && Array.isArray(data.details)) {
      errMsg += '\n' + data.details.slice(0, 5).join('\n')
    }
    message.error({ content: errMsg, duration: 6 })
    options.onError?.(e)
  } finally {
    uploading.value = false
  }
}

async function handleReload(filename: string) {
  reloadingMap[filename] = true
  try {
    const res = await computedFieldApi.pluginReload(filename)
    message.success(`插件 ${filename} 已重载，注册 ${res.data.functions.length} 个函数`)
    await loadPlugins()
  } catch (e: any) {
    message.error(extractApiError(e) || '重载失败')
  } finally {
    reloadingMap[filename] = false
  }
}

async function handleUnload(filename: string) {
  unloadingMap[filename] = true
  try {
    await computedFieldApi.pluginUnload(filename)
    message.success(`插件 ${filename} 已卸载`)
    await loadPlugins()
  } catch (e: any) {
    message.error(extractApiError(e) || '卸载失败')
  } finally {
    unloadingMap[filename] = false
  }
}

async function loadTemplate() {
  try {
    const res = await computedFieldApi.pluginTemplate()
    templateCode.value = res.data.template
    templateVisible.value = true
  } catch (e: any) {
    message.error('获取模板失败')
  }
}

async function copyTemplate() {
  try {
    await navigator.clipboard.writeText(templateCode.value)
    message.success('模板代码已复制到剪贴板')
  } catch {
    message.error('复制失败，请手动选择复制')
  }
}

onMounted(() => {
  loadPlugins()
})
</script>

<style scoped>
.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}
.page-header h2 {
  margin: 0;
  font-size: 18px;
}
.ant-upload-drag-icon {
  font-size: 32px;
  color: #1890ff;
  margin-bottom: 8px;
}
</style>
