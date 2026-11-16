<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { sealSuccess } from '@/utils/seal-toast'

import { RequestError, toApiError } from '@/api/client-error'
import { getPlan, importPlan } from '@/api/plans'
import MarkdownView from '@/components/MarkdownView.vue'
import PageHeader from '@/components/PageHeader.vue'
import StatePanel from '@/components/StatePanel.vue'
import StatusTag from '@/components/StatusTag.vue'
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
const latestReview = computed(() => detail.data.value?.latestReview ?? null)
const reportHash = computed(() => latestReview.value?.reportSha256 ?? '')

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
  sealSuccess('Markdown 已下载')
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
    sealSuccess(
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
      <div class="proof-layout">
        <article class="proof-sheet" aria-label="教案正文">
          <span class="proof-binding" aria-hidden="true" />
          <p class="proof-kicker">第 {{ plan.versionNo }} 稿 · 只读校样</p>
          <p class="notice">
            平台只读；修订在插件端完成后上传新版本，不会覆盖旧版本。
          </p>
          <MarkdownView v-if="!sourceMode" :markdown="markdown" />
          <pre v-else class="source-card" aria-label="Markdown 源码"><code>{{ markdown }}</code></pre>
        </article>

        <aside class="proof-margin" aria-label="版本、审查与证据">
          <section class="margin-block">
            <h2>版本</h2>
            <dl>
              <div><dt>稿次</dt><dd>第 {{ plan.versionNo }} 稿</dd></div>
              <div><dt>课程</dt><dd>{{ plan.course }}</dd></div>
              <div><dt>周次</dt><dd>第 {{ plan.week }} 周第 {{ plan.session }} 次</dd></div>
              <div><dt>哈希</dt><dd class="mono">{{ plan.planHash.slice(0, 12) }}…</dd></div>
            </dl>
          </section>

          <section class="margin-block">
            <h2>审查</h2>
            <template v-if="latestReview">
              <StatusTag :code="latestReview.status" :status="latestReview.status" />
              <p class="margin-note">第 {{ latestReview.round }} 轮 · {{ latestReview.reviewerMode ?? '教师审查' }}</p>
            </template>
            <p v-else class="margin-note">这份教案还没有审查记录。</p>
          </section>

          <section class="margin-block">
            <h2>证据链</h2>
            <p v-if="latestReview" class="margin-note">
              报告哈希
              <span class="mono">{{ reportHash ? `${reportHash.slice(0, 12)}…` : '未记录' }}</span>
            </p>
            <p v-else class="margin-note">审查后会在这里留下报告哈希与轮次。</p>
            <el-button link type="primary" @click="openDetail">查看详情与版本历史</el-button>
          </section>
        </aside>
      </div>
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

.proof-layout {
  display: grid;
  grid-template-columns: minmax(0, 68ch) 280px;
  gap: 28px;
  align-items: start;
}

.proof-sheet {
  position: relative;
  min-width: 0;
  padding: 26px 32px 34px 44px;
  border: 1px solid var(--lpp-border);
  border-radius: var(--lpp-radius-card);
  background: var(--lpp-surface);
  box-shadow: var(--lpp-shadow-paper);
}

.proof-binding {
  position: absolute;
  top: 26px;
  bottom: 26px;
  left: 13px;
  width: 14px;
  background-image: radial-gradient(circle, var(--lpp-border-strong) 2px, transparent 2.5px);
  background-size: 14px 34px;
  opacity: 0.7;
}

.proof-sheet::before {
  content: '';
  position: absolute;
  top: 0;
  bottom: 0;
  left: 31px;
  width: 1px;
  background: var(--lpp-accent-soft);
}

.proof-kicker {
  margin-bottom: 8px;
  color: var(--lpp-accent-ink);
  font-family: var(--lpp-font-hand);
  font-size: var(--lpp-font-xs);
  letter-spacing: 0.08em;
}

.proof-sheet :deep(.markdown-body) {
  max-width: 68ch;
  font-size: var(--lpp-font-base);
  line-height: 1.75;
}

.proof-sheet :deep(.markdown-body h1) {
  font-family: var(--lpp-font-display);
  font-size: var(--lpp-font-xl);
  font-weight: 600;
  letter-spacing: 0.01em;
}

.proof-sheet :deep(.markdown-body h2) {
  font-family: var(--lpp-font-display);
  font-size: var(--lpp-font-md);
}

.proof-sheet :deep(.markdown-body table) {
  font-size: var(--lpp-font-sm);
  line-height: var(--lpp-line-table);
}

.notice {
  margin-bottom: 18px;
  padding: 8px 10px;
  border-left: 2px solid var(--lpp-accent);
  background: var(--lpp-layer);
  color: var(--lpp-text-muted);
  font-size: var(--lpp-font-xs);
  line-height: 1.6;
}

.proof-margin {
  position: sticky;
  top: 80px;
  display: grid;
  gap: 16px;
}

.margin-block {
  padding: 14px 14px 12px;
  border: 1px solid var(--lpp-border);
  border-radius: var(--lpp-radius-card);
  background: var(--lpp-surface-2);
}

.margin-block h2 {
  margin-bottom: 8px;
  color: var(--lpp-text-muted);
  font-family: var(--lpp-font-family);
  font-size: var(--lpp-font-xs);
  font-weight: 500;
  letter-spacing: 0.04em;
}

.margin-block dl {
  display: grid;
  gap: 6px;
  margin: 0;
}

.margin-block dl div {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  font-size: var(--lpp-font-xs);
}

.margin-block dt {
  color: var(--lpp-text-muted);
}

.margin-block dd {
  margin: 0;
  color: var(--lpp-text);
  text-align: right;
}

.margin-note {
  margin: 6px 0 8px;
  color: var(--lpp-text-muted);
  font-size: var(--lpp-font-xs);
  line-height: 1.55;
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

@media (max-width: 980px) {
  .proof-layout {
    grid-template-columns: minmax(0, 1fr);
  }

  .proof-margin {
    position: static;
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 767px) {
  .proof-sheet {
    padding: 20px 18px 24px 36px;
  }

  .proof-margin {
    grid-template-columns: minmax(0, 1fr);
  }

  .proof-binding {
    left: 10px;
  }

  .proof-sheet::before {
    left: 26px;
  }
}
</style>
