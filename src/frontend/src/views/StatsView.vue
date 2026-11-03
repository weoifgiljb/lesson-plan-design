<script setup lang="ts">
import { computed, reactive, ref } from 'vue'

import {
  downloadStatsCsv,
  getStatsSummary,
  listStatRecords,
  type StatsQuery,
} from '@/api/stats'
import type { Metric, StatRecord } from '@/api/models'
import { useApiRequest } from '@/composables/useApiRequest'
import { buildBarOption, buildStatusOption } from '@/composables/useStatsCharts'
import ChartCard from '@/components/ChartCard.vue'
import { UNAVAILABLE_TEXT } from '@/utils/labels'
import { saveBlob } from '@/utils/download'

const filters = reactive({ course: '', week: '', page: 1, pageSize: 10 })

const query = computed<StatsQuery>(() => {
  const payload: StatsQuery = {}
  if (filters.course.trim()) payload.course = filters.course.trim()
  if (filters.week.trim()) payload.week = Number(filters.week)
  return payload
})

const summary = useApiRequest(() => getStatsSummary(query.value), { immediate: true })
const metrics = computed<Metric[]>(() => summary.data.value?.metrics ?? [])

const records = useApiRequest(
  () => listStatRecords({ ...query.value, page: filters.page, pageSize: filters.pageSize }),
  { immediate: false },
)
const rows = computed<StatRecord[]>(() => records.data.value?.items ?? [])
const total = computed(() => records.data.value?.total ?? 0)
const expanded = ref(false)

const barOption = computed(() => buildBarOption(metrics.value))
const statusOption = computed(() => buildStatusOption(rows.value))

const exportError = ref('')

function formatValue(metric: Metric): string {
  if (metric.value === null || metric.value === undefined) return UNAVAILABLE_TEXT
  // 比率型指标后端不给 unit（0–1），其余指标带单位（如"分钟"/"条"）：
  // 不能一律 ×100，否则缺陷密度与单份耗时会变成荒谬的百分比。
  if (!metric.unit) return `${(metric.value * 100).toFixed(1)}%`
  const rounded = Number.isInteger(metric.value) ? String(metric.value) : metric.value.toFixed(1)
  return `${rounded} ${metric.unit}`
}

async function toggleRecords(): Promise<void> {
  expanded.value = !expanded.value
  if (expanded.value && !records.data.value) await records.load()
}

async function download(): Promise<void> {
  exportError.value = ''
  try {
    const blob = await downloadStatsCsv()
    saveBlob(blob, 'stats-summary.csv')
  } catch (caught) {
    exportError.value = caught instanceof Error ? caught.message : '导出失败'
  }
}

const scopeLabel: Record<string, string> = { own: '本人', group: '本组', all: '全校' }
</script>

<template>
  <section class="stats">
    <header class="head">
      <div>
        <h1>统计</h1>
        <p class="lead">
          9 项指标均带分子/分母；样本少于 5 份只提示"样本不足"，不做跨教师结论。
        </p>
      </div>
      <div class="actions">
        <el-input v-model="filters.course" class="filter" placeholder="课程" clearable @change="summary.load()" />
        <el-input v-model="filters.week" class="filter-sm" placeholder="周次" clearable @change="summary.load()" />
        <el-button @click="download">导出 CSV</el-button>
        <el-button type="primary" @click="toggleRecords">
          {{ expanded ? '收起明细' : '查看明细' }}
        </el-button>
      </div>
    </header>

    <el-alert v-if="exportError" type="error" :closable="false" show-icon :title="exportError" />
    <el-alert
      v-if="summary.error.value"
      type="error"
      :closable="false"
      show-icon
      :title="summary.error.value.message"
      :description="summary.error.value.traceId ? `traceId: ${summary.error.value.traceId}` : ''"
    />

    <p v-if="summary.data.value" class="scope">
      统计范围：{{ scopeLabel[summary.data.value.scope] ?? summary.data.value.scope }}
    </p>

    <div class="cards" v-loading="summary.loading.value">
      <article v-for="metric in metrics" :key="metric.key" class="card">
        <header class="card-head">
          <span class="card-label">{{ metric.label }}</span>
          <el-tag v-if="metric.sampleInsufficient" size="small" type="warning" disable-transitions>
            样本不足
          </el-tag>
          <el-tag v-else-if="metric.available === false" size="small" type="info" disable-transitions>
            不可用
          </el-tag>
        </header>
        <p class="card-value">{{ formatValue(metric) }}</p>
        <p class="card-sub">
          {{ metric.numerator }} / {{ metric.denominator }}
          <span v-if="metric.unit">· {{ metric.unit }}</span>
          <span v-if="metric.basis"> · 口径：任务 {{ metric.basis.task }} / 教案 {{ metric.basis.plan }}</span>
        </p>
      </article>
    </div>

    <section class="charts">
      <ChartCard
        label="指标达成度"
        summary="比率型指标的达成度，括号内为分子/分母；样本不足的指标用警示色标注。"
        :option="barOption"
      />
      <ChartCard
        label="审查状态分布"
        :summary="`按下钻明细统计，共 ${total} 份教案`"
        :option="statusOption"
      />
    </section>

    <section v-if="expanded" class="records">
      <h2>下钻明细（{{ total }} 条）</h2>
      <div class="table-wrap" v-loading="records.loading.value">
        <el-table v-if="rows.length" :data="rows" row-key="planId" stripe>
          <el-table-column prop="planId" label="教案" width="90" />
          <el-table-column prop="contentTitle" label="课题" min-width="200" />
          <el-table-column prop="teacher" label="教师" width="120" />
          <el-table-column label="位置" width="150">
            <template #default="{ row }">第 {{ row.week }} 周 · 第 {{ row.session }} 次</template>
          </el-table-column>
          <el-table-column label="结构" width="90">
            <template #default="{ row }">{{ row.structureOk ? '合规' : '不合规' }}</template>
          </el-table-column>
          <el-table-column label="证据链" width="100">
            <template #default="{ row }">{{ row.evidenceOk ? '完整' : '不完整' }}</template>
          </el-table-column>
          <el-table-column prop="openBlocking" label="未闭环" width="90" />
          <el-table-column prop="reviewStatus" label="审查状态" width="130" />
        </el-table>
        <div v-else-if="!records.loading.value" class="empty">暂无明细</div>
      </div>
      <footer v-if="total > filters.pageSize" class="pager">
        <el-pagination
          v-model:current-page="filters.page"
          :page-size="filters.pageSize"
          :total="total"
          layout="prev, pager, next"
          background
          @current-change="records.load()"
        />
      </footer>
    </section>
  </section>
</template>

<style scoped>
.stats {
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

.actions {
  display: flex;
  gap: 8px;
  align-items: center;
}

.filter {
  width: 130px;
}

.filter-sm {
  width: 90px;
}

.scope {
  margin: 0;
  font-size: 12px;
  color: var(--lpp-text-muted);
}

.cards {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(210px, 1fr));
  gap: 10px;
}

.card {
  padding: 12px 14px;
  border: 1px solid var(--lpp-border);
  border-radius: var(--lpp-radius-card);
  background: var(--lpp-surface);
}

.card-head {
  display: flex;
  gap: 8px;
  align-items: center;
  justify-content: space-between;
}

.card-label {
  font-size: 13px;
  color: var(--lpp-text-muted);
}

.card-value {
  margin: 8px 0 4px;
  font-size: 22px;
  font-variant-numeric: tabular-nums;
}

.card-sub {
  margin: 0;
  font-size: 12px;
  color: var(--lpp-text-muted);
}

.charts {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(360px, 1fr));
  gap: 12px;
}

.records h2 {
  margin: 8px 0;
  font-size: 15px;
}

.table-wrap {
  min-height: 200px;
  border: 1px solid var(--lpp-border);
  border-radius: var(--lpp-radius-card);
  background: var(--lpp-surface);
}

.empty {
  display: grid;
  place-content: center;
  min-height: 180px;
  color: var(--lpp-text-muted);
  font-size: 13px;
}

.pager {
  display: flex;
  justify-content: flex-end;
  margin-top: 10px;
}
</style>
