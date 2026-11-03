<script setup lang="ts">
import { computed, onUnmounted, reactive, ref } from 'vue'

import { createExports, downloadExport, getExport } from '@/api/exports'
import { getStatsSummary, listStatRecords } from '@/api/stats'
import type { ExportJob } from '@/api/models'
import { saveBlob } from '@/utils/download'

const versionInput = ref('')
const jobs = ref<ExportJob[]>([])
const creating = ref(false)
const message = ref('')
const error = ref('')

const summary = reactive({ loading: false })

let timer: number | undefined

const pending = computed(() => jobs.value.filter((job) => job.status !== 'succeeded' && job.status !== 'failed'))

function parseIds(text: string): number[] {
  return text
    .split(/[,，\s]+/)
    .map((item) => Number(item.trim()))
    .filter((item) => Number.isInteger(item) && item > 0)
}

async function submit(): Promise<void> {
  const ids = parseIds(versionInput.value)
  error.value = ''
  message.value = ''
  if (ids.length === 0) {
    error.value = '请填写教案版本 ID（逗号分隔）'
    return
  }
  creating.value = true
  try {
    const result = await createExports(ids)
    const items: ExportJob[] = ((result as unknown as { items?: ExportJob[] }).items ?? []) as ExportJob[]
    if (items.length) jobs.value = [...items, ...jobs.value.filter((job) => !items.some((it) => it.exportId === job.exportId))]
    message.value = `已提交 ${result.items?.length ?? ids.length} 个导出任务`
    startPolling()
  } catch (caught) {
    error.value = caught instanceof Error ? caught.message : '创建导出任务失败'
  } finally {
    creating.value = false
  }
}

async function refresh(): Promise<void> {
  const active = pending.value
  if (active.length === 0) return
  for (const job of active) {
    try {
      const fresh = await getExport(job.exportId)
      jobs.value = jobs.value.map((item) => (item.exportId === fresh.exportId ? fresh : item))
    } catch {
      /* 单个任务失败不打断轮询 */
    }
  }
}

function startPolling(): void {
  if (timer !== undefined) return
  timer = window.setInterval(() => {
    void refresh()
    if (pending.value.length === 0) stopPolling()
  }, 4000)
}

function stopPolling(): void {
  if (timer !== undefined) {
    window.clearInterval(timer)
    timer = undefined
  }
}

onUnmounted(stopPolling)

async function download(job: ExportJob): Promise<void> {
  error.value = ''
  try {
    const blob = await downloadExport(job.exportId)
    saveBlob(blob, `plan-${job.planId}-v${job.versionNo}.docx`)
  } catch (caught) {
    error.value = caught instanceof Error ? caught.message : '下载失败'
  }
}

async function loadCandidates(): Promise<void> {
  summary.loading = true
  error.value = ''
  try {
    await getStatsSummary({})
    const page = await listStatRecords({ pageSize: 20 })
    message.value = `可在统计页下钻查看候选教案；本次载入 ${page.items.length} 条记录`
  } catch (caught) {
    error.value = caught instanceof Error ? caught.message : '加载候选失败'
  } finally {
    summary.loading = false
  }
}

const statusLabel: Record<string, string> = {
  queued: '排队中',
  running: '生成中',
  succeeded: '已完成',
  failed: '失败',
}
</script>

<template>
  <section class="exports">
    <header class="head">
      <div>
        <h1>导出中心</h1>
        <p class="lead">按教案版本批量导出 DOCX；同一版本 + 引擎 + 报告哈希只会生成一次。</p>
      </div>
      <el-button :loading="summary.loading" @click="loadCandidates">载入候选版本</el-button>
    </header>

    <el-alert v-if="error" type="error" :closable="false" show-icon :title="error" />
    <el-alert v-if="message" type="success" :closable="false" show-icon :title="message" />

    <div class="form">
      <el-input
        v-model="versionInput"
        class="ids"
        placeholder="教案版本 ID，逗号分隔，例如 12,15"
        aria-label="教案版本 ID"
      />
      <el-button type="primary" :loading="creating" @click="submit">创建导出</el-button>
    </div>

    <div class="table-wrap">
      <el-table v-if="jobs.length" :data="jobs" row-key="exportId" stripe>
        <el-table-column prop="exportId" label="任务" width="80" />
        <el-table-column prop="contentTitle" label="课题" min-width="200" />
        <el-table-column label="版本" width="90">
          <template #default="{ row }">v{{ row.versionNo }}</template>
        </el-table-column>
        <el-table-column label="状态" width="120">
          <template #default="{ row }">
            <el-tag
              :type="row.status === 'succeeded' ? 'success' : row.status === 'failed' ? 'danger' : 'warning'"
              disable-transitions
            >
              {{ statusLabel[row.status] ?? row.status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="engineVersion" label="引擎" width="110" />
        <el-table-column prop="reportHash" label="报告哈希" min-width="180" />
        <el-table-column label="操作" width="110" fixed="right">
          <template #default="{ row }">
            <el-button
              link
              type="primary"
              :disabled="row.status !== 'succeeded'"
              @click="download(row)"
            >
              下载
            </el-button>
          </template>
        </el-table-column>
      </el-table>
      <div v-else class="empty">还没有导出任务</div>
    </div>

    <p v-if="pending.length" class="hint">有 {{ pending.length }} 个任务进行中，每 4 秒自动刷新…</p>
  </section>
</template>

<style scoped>
.exports {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.head {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: flex-end;
  justify-content: space-between;
}

.head h1 {
  margin: 0 0 4px;
  font-size: 20px;
}

.lead {
  margin: 0;
  font-size: 13px;
  color: var(--lpp-text-muted);
}

.form {
  display: flex;
  gap: 8px;
}

.ids {
  max-width: 420px;
}

.table-wrap {
  min-height: 220px;
  border: 1px solid var(--lpp-border);
  border-radius: var(--lpp-radius-card);
  background: var(--lpp-surface);
}

.empty {
  display: grid;
  place-content: center;
  min-height: 200px;
  color: var(--lpp-text-muted);
  font-size: 13px;
}

.hint {
  margin: 0;
  font-size: 12px;
  color: var(--lpp-text-muted);
}
</style>
