<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

import { RequestError, toApiError } from '@/api/client-error'
import { getPlan, importPlan } from '@/api/plans'
import MarkdownView from '@/components/MarkdownView.vue'
import PageHeader from '@/components/PageHeader.vue'
import StatePanel from '@/components/StatePanel.vue'
import { useApiRequest } from '@/composables/useApiRequest'
import { useSessionStore } from '@/stores/session'
import { saveBlob } from '@/utils/download'
import { buildPlanMarkdown } from '@/utils/plan-markdown'

const route = useRoute()
const router = useRouter()
const session = useSessionStore()
const planId = Number(route.params.id)
const canImport = computed(() => session.role === 'teacher' || session.role === 'lead')

const detail = useApiRequest(() => getPlan(planId))
const booting = ref(true)
const sourceMode = ref(false)
const importing = ref(false)
const fileInput = ref<HTMLInputElement | null>(null)

const plan = computed(() => detail.data.value?.plan ?? null)
const markdown = computed(() => (detail.data.value ? buildPlanMarkdown(detail.data.value) : ''))

function handleError(caught: unknown, fallback: string): RequestError {
  const requestError = caught instanceof RequestError ? caught : toApiError(caught)
  if (requestError.status === 401) {
    void router.replace({ path: '/login', query: { redirect: route.fullPath } })
  } else if (requestError.status === 403) {
    void router.replace('/403')
  } else {
    ElMessage.error(`${requestError.message || fallback}（${requestError.code}）`)
  }
  return requestError
}

async function load(): Promise<void> {
  booting.value = true
  try {
    await detail.load()
  } finally {
    booting.value = false
  }
}

function openDetail(): void {
  void router.push(`/plans/${planId}`)
}

function downloadMarkdown(): void {
  if (!plan.value) return
  saveBlob(
    new Blob([markdown.value], { type: 'text/markdown;charset=utf-8' }),
    `plan-${plan.value.planId}-v${plan.value.versionNo}.md`,
  )
  ElMessage.success('Markdown 已下载')
}

function openVersionPicker(): void {
  fileInput.value?.click()
}

async function onVersionFile(event: Event): Promise<void> {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  if (!file.name.toLowerCase().endsWith('.zip')) {
    ElMessage.error('只接受 .zip 契约包')
    input.value = ''
    return
  }
  importing.value = true
  try {
    const result = await importPlan(file)
    ElMessage.success(
      result.duplicate
        ? `契约包已存在，当前为第 ${result.versionNo} 版`
        : `新版本 v${result.versionNo} 已入库`,
    )
    if (result.planId === planId) await load()
    else await router.push(`/plans/${result.planId}/content`)
  } catch (caught) {
    handleError(caught, '上传新版本失败')
  } finally {
    importing.value = false
    input.value = ''
  }
}

onMounted(() => {
  if (!Number.isFinite(planId)) {
    void router.replace('/plans')
    return
  }
  void load()
})
</script>

<template>
  <div class="plan-content-page page">
    <PageHeader
      title="教案正文"
      :description="
        plan
          ? `${plan.contentTitle} · ${plan.course} · 第 ${plan.week} 周第 ${plan.session} 次课`
          : 'Markdown 渲染的教案正文'
      "
    >
      <template #meta>
        <p v-if="plan" class="muted">
          v{{ plan.versionNo }} · Markdown · 只读
        </p>
      </template>
      <template #actions>
        <input
          ref="fileInput"
          class="hidden-file"
          type="file"
          accept=".zip,application/zip"
          aria-label="上传新版本"
          @change="onVersionFile"
        />
        <el-button @click="openDetail">返回详情</el-button>
        <el-button @click="sourceMode = !sourceMode">{{ sourceMode ? '预览' : '源码' }}</el-button>
        <el-button :disabled="!markdown" @click="downloadMarkdown">下载 Markdown</el-button>
        <el-button v-if="plan && canImport" :loading="importing" @click="openVersionPicker">
          上传新版本
        </el-button>
      </template>
    </PageHeader>

    <StatePanel
      v-if="booting"
      state="loading"
      title="正在读取教案正文…"
      description="正文、目标与八步流程会从当前版本生成 Markdown。"
    />

    <StatePanel
      v-else-if="detail.error.value"
      state="error"
      :title="detail.error.value.code"
      :description="detail.error.value.message"
      :trace-id="detail.error.value.traceId"
    >
      <template #action>
        <el-button @click="openDetail">返回详情</el-button>
        <el-button type="primary" @click="load">重试</el-button>
      </template>
    </StatePanel>

    <template v-else-if="plan">
      <p class="notice">
        平台 v1.0 只读；修订在插件端完成后上传新版本，不会覆盖旧版本。
      </p>

      <article v-if="!sourceMode" class="markdown-card" aria-label="教案正文">
        <MarkdownView :markdown="markdown" />
      </article>
      <pre v-else class="source-card" aria-label="Markdown 源码"><code>{{ markdown }}</code></pre>
    </template>
  </div>
</template>

<style scoped>
.plan-content-page {
  gap: 16px;
}

.hidden-file {
  display: none;
}

.notice {
  padding: 8px 10px;
  border-left: 2px solid var(--lpp-accent);
  background: var(--lpp-layer);
  color: var(--lpp-text-muted);
  font-size: var(--lpp-font-xs);
  line-height: 1.6;
}

.markdown-card {
  padding: 28px 32px;
  border: 1px solid var(--lpp-border);
  border-radius: var(--lpp-radius-card);
  background: var(--lpp-surface);
}

.source-card {
  margin: 0;
  padding: 18px;
  border: 1px solid var(--lpp-border);
  border-radius: var(--lpp-radius-card);
  background: var(--lpp-layer);
  color: var(--lpp-text);
  font-family: var(--lpp-font-numeric);
  font-size: 12px;
  line-height: 1.65;
  overflow: auto;
  white-space: pre-wrap;
}

@media (max-width: 767px) {
  .markdown-card {
    padding: 18px 16px;
  }
}
</style>
