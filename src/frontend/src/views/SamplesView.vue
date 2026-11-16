<script setup lang="ts">
import { computed, reactive, ref } from 'vue'

import {
  createSample,
  downloadSample,
  getSample,
  listSamples,
  type SampleQuery,
} from '@/api/samples'
import type { SampleDetail, SampleItem } from '@/api/models'
import { useApiRequest } from '@/composables/useApiRequest'
import { saveBlob } from '@/utils/download'

const filters = reactive({ course: '', week: '', page: 1, pageSize: 20 })

const query = computed<SampleQuery>(() => {
  const payload: SampleQuery = { page: filters.page, pageSize: filters.pageSize }
  if (filters.course.trim()) payload.course = filters.course.trim()
  if (filters.week.trim()) payload.week = Number(filters.week)
  return payload
})

const { data, loading, error, load } = useApiRequest(() => listSamples(query.value), {
  immediate: true,
})

const rows = computed<SampleItem[]>(() => data.value?.items ?? [])
const total = computed(() => data.value?.total ?? 0)

const uploadError = ref('')
const uploading = ref(false)
const detail = ref<SampleDetail | null>(null)
const detailError = ref('')
const detailOpen = ref(false)

async function onUpload(event: Event): Promise<void> {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  uploading.value = true
  uploadError.value = ''
  try {
    await createSample(file)
    await load()
  } catch (caught) {
    uploadError.value = caught instanceof Error ? caught.message : '上传失败'
  } finally {
    uploading.value = false
    input.value = ''
  }
}

async function openDetail(row: SampleItem): Promise<void> {
  detailOpen.value = true
  detail.value = null
  detailError.value = ''
  try {
    detail.value = await getSample(row.sampleId)
  } catch (caught) {
    detailError.value = caught instanceof Error ? caught.message : '详情加载失败'
  }
}

async function download(row: SampleItem): Promise<void> {
  try {
    const blob = await downloadSample(row.sampleId)
    saveBlob(blob, `sample-${row.sampleId}.json`)
  } catch (caught) {
    detailError.value = caught instanceof Error ? caught.message : '下载失败'
    detailOpen.value = true
  }
}
</script>

<template>
  <section class="samples">
    <header class="head">
      <div>
        <h1>样例库</h1>
        <p class="lead">合格的黄金样例，插件端可直接下载使用；被篡改的样例会拒绝下载。</p>
      </div>
      <div class="actions">
        <el-input v-model="filters.course" class="filter" placeholder="课程" clearable />
        <el-input v-model="filters.week" class="filter-sm" placeholder="周次" clearable />
        <label class="upload">
          <input type="file" accept="application/json,.json" :disabled="uploading" @change="onUpload" />
          <el-button type="primary" :loading="uploading">上传样例</el-button>
        </label>
      </div>
    </header>

    <el-alert v-if="uploadError" type="error" :closable="false" show-icon :title="uploadError" />
    <el-alert
      v-if="error"
      type="error"
      :closable="false"
      show-icon
      :title="error.message"
      :description="error.traceId ? `traceId: ${error.traceId}` : ''"
    />

    <div class="shelf" v-loading="loading">
      <article
        v-for="row in rows"
        :key="row.sampleId"
        class="sample-card"
        tabindex="0"
        @click="openDetail(row)"
        @keyup.enter="openDetail(row)"
      >
        <div class="sample-cover" :class="{ 'is-incomplete': !row.complete || !row.valid }">
          <span class="cover-initial">{{ row.course?.slice(0, 1) || '课' }}</span>
          <span class="cover-week">第 {{ row.week }} 周</span>
        </div>
        <div class="sample-body">
          <h2>{{ row.title }}</h2>
          <p>{{ row.course }} · 第 {{ row.week }} 周第 {{ row.session }} 次</p>
          <div class="sample-meta">
            <el-tag :type="row.complete && row.valid ? 'success' : 'warning'" disable-transitions>
              {{ row.complete && row.valid ? '可用' : '不完整' }}
            </el-tag>
            <span>规则 {{ row.ruleVersion }}</span>
          </div>
        </div>
        <div class="sample-actions">
          <el-button link type="primary" @click.stop="openDetail(row)">预览</el-button>
          <el-button link type="primary" @click.stop="download(row)">下载</el-button>
        </div>
      </article>

      <div v-if="!rows.length && !loading" class="empty">
        <p class="empty-title">样例库还是空的</p>
        <p class="empty-desc">上传一份通过结构校验的教案 JSON，或运行 scripts/seed_samples.py 导入插件样例。</p>
      </div>
    </div>

    <footer v-if="total > filters.pageSize" class="pager">
      <el-pagination
        v-model:current-page="filters.page"
        :page-size="filters.pageSize"
        :total="total"
        layout="prev, pager, next"
        background
        @current-change="load()"
      />
    </footer>

    <el-drawer v-model="detailOpen" title="样例详情" size="46%">
      <el-alert v-if="detailError" type="error" :closable="false" show-icon :title="detailError" />
      <template v-if="detail">
        <dl class="meta">
          <dt>课题</dt><dd>{{ detail.title }}</dd>
          <dt>课程</dt><dd>{{ detail.course }}</dd>
          <dt>位置</dt><dd>第 {{ detail.week }} 周 · 第 {{ detail.session }} 次</dd>
          <dt>planHash</dt><dd class="mono">{{ detail.planHash }}</dd>
          <dt>完整性</dt>
          <dd>
            {{ detail.complete ? '完整' : '不完整' }}
            <span v-if="detail.assetsOk === false" class="warn">（资产哈希不一致）</span>
          </dd>
        </dl>
        <pre class="json">{{ JSON.stringify(detail.content ?? {}, null, 2) }}</pre>
      </template>
      <p v-else-if="!detailError" class="loading">加载中…</p>
    </el-drawer>
  </section>
</template>

<style scoped>
.samples {
  display: flex;
  flex-direction: column;
  gap: 16px;
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
  font-family: var(--lpp-font-display);
  font-size: var(--lpp-font-xl);
  letter-spacing: 0.01em;
}

.lead {
  margin: 0;
  font-size: 13px;
  color: var(--lpp-text-muted);
}

.actions {
  display: flex;
  gap: 8px;
  align-items: center;
  padding: 8px 10px;
  border: 1px solid var(--lpp-border);
  border-radius: var(--lpp-radius-card);
  background: var(--lpp-surface-2);
}

.actions :deep(.el-input__wrapper) {
  min-height: 32px;
  background: var(--lpp-surface);
}

.filter {
  width: 130px;
}

.filter-sm {
  width: 90px;
}

.upload input {
  display: none;
}

.shelf {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
  min-height: 240px;
}

.sample-card {
  display: flex;
  flex-direction: column;
  min-width: 0;
  border: 1px solid var(--lpp-border);
  border-radius: var(--lpp-radius-card);
  background: var(--lpp-surface);
  box-shadow: var(--lpp-shadow-paper);
  cursor: pointer;
  overflow: hidden;
}

.sample-card:hover,
.sample-card:focus-visible {
  border-color: var(--lpp-primary);
}

.sample-cover {
  position: relative;
  display: flex;
  aspect-ratio: 3 / 2;
  align-items: center;
  justify-content: center;
  background:
    linear-gradient(135deg, transparent 49.5%, var(--lpp-paper-line) 50%, transparent 50.5%),
    var(--lpp-surface-2);
  border-bottom: 1px solid var(--lpp-border);
}

.sample-cover.is-incomplete {
  background: var(--lpp-warning-soft);
}

.cover-initial {
  color: var(--lpp-brass-ink);
  font-family: var(--lpp-font-display);
  font-size: 44px;
  opacity: 0.55;
}

.cover-week {
  position: absolute;
  right: 10px;
  bottom: 8px;
  color: var(--lpp-text-muted);
  font-family: var(--lpp-font-numeric);
  font-size: 11px;
}

.sample-body {
  display: grid;
  gap: 5px;
  padding: 12px 14px 8px;
}

.sample-body h2 {
  overflow: hidden;
  font-family: var(--lpp-font-display);
  font-size: var(--lpp-font-md);
  font-weight: 600;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.sample-body p {
  overflow: hidden;
  color: var(--lpp-text-muted);
  font-size: var(--lpp-font-xs);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.sample-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  color: var(--lpp-text-muted);
  font-size: 11px;
}

.sample-actions {
  display: flex;
  justify-content: flex-end;
  gap: 4px;
  margin-top: auto;
  padding: 4px 10px 10px;
}

.empty {
  grid-column: 1 / -1;
  display: grid;
  place-content: center;
  gap: 6px;
  min-height: 220px;
  padding: 24px;
  border: 1px dashed var(--lpp-border-strong);
  border-radius: var(--lpp-radius-card);
  background: var(--lpp-surface);
  text-align: center;
}

.empty-title {
  margin: 0;
  font-size: 15px;
}

.empty-desc {
  margin: 0;
  font-size: 13px;
  color: var(--lpp-text-muted);
}

.pager {
  display: flex;
  justify-content: flex-end;
}

.meta {
  display: grid;
  grid-template-columns: 90px 1fr;
  gap: 6px 12px;
  margin: 0 0 12px;
  font-size: 13px;
}

.meta dt {
  color: var(--lpp-text-muted);
}

.meta dd {
  margin: 0;
}

.mono {
  font-family: var(--lpp-font-mono, ui-monospace, monospace);
  word-break: break-all;
}

.warn {
  color: var(--lpp-warning);
}

.json {
  max-height: 60vh;
  overflow: auto;
  padding: 12px;
  border: 1px solid var(--lpp-border);
  border-radius: var(--lpp-radius-control);
  background: var(--lpp-layer);
  font-size: 12px;
}

.loading {
  color: var(--lpp-text-muted);
}

@media (max-width: 1100px) {
  .shelf {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 767px) {
  .head,
  .actions {
    align-items: stretch;
  }

  .actions {
    flex-wrap: wrap;
  }

  .shelf {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
