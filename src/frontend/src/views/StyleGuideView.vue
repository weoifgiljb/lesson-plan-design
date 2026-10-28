<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import type { EChartsOption } from 'echarts'

import ChartCard from '@/components/ChartCard.vue'
import DiffViewer from '@/components/DiffViewer.vue'
import EvidenceChain from '@/components/EvidenceChain.vue'
import MetricCard from '@/components/MetricCard.vue'
import StatePanel from '@/components/StatePanel.vue'
import StatusTag from '@/components/StatusTag.vue'
import { DEMO_DIFFS, DEMO_EVIDENCE, DEMO_METRICS, DEMO_PLANS } from '@/dev/styleguide-fixtures'
import { useUiStore } from '@/stores/ui'

const ui = useUiStore()

const palettes = {
  ink: {
    title: 'A「墨蓝 · 麦金」',
    primary: '#1F3A5F',
    accent: '#B07A2A',
    canvas: '#F3F4F6',
    surface: '#FFFFFF',
    text: '#1B2430',
    muted: '#5B6878',
    border: '#E2E6EC',
    success: '#2F6B4F',
    warning: '#A15C12',
    danger: '#A33A2B',
  },
  pine: {
    title: 'B「松绿 · 砂岩」',
    primary: '#2E5B52',
    accent: '#8C6A4A',
    canvas: '#F2F3F0',
    surface: '#FFFFFF',
    text: '#1C2622',
    muted: '#5D6A63',
    border: '#E1E4DD',
    success: '#2E6B4F',
    warning: '#94641A',
    danger: '#A23F32',
  },
} as const

const palette = computed(() => palettes[ui.theme])

function changeTheme(value: string): void {
  if (value === 'ink' || value === 'pine') ui.setTheme(value)
}

const swatches = computed(() => [
  ['主色', palette.value.primary],
  ['强调色', palette.value.accent],
  ['画布', palette.value.canvas],
  ['表面', palette.value.surface],
  ['主文字', palette.value.text],
  ['次文字', palette.value.muted],
  ['描边', palette.value.border],
  ['成功', palette.value.success],
  ['警告', palette.value.warning],
  ['危险', palette.value.danger],
])

const formRef = ref<FormInstance>()
const form = reactive({ title: '', course: '信息技术', week: 2, note: '' })
const rules: FormRules = {
  title: [{ required: true, message: '请填写课题', trigger: 'blur' }],
  course: [{ required: true, message: '请选择课程', trigger: 'change' }],
  week: [{ required: true, message: '请填写周次', trigger: 'blur' }],
}

function submitForm(): void {
  formRef.value?.validate((valid) => {
    if (!valid) return
    ElMessage.success(`已保存：${form.course} 第 ${form.week} 周 / ${form.title}`)
  })
}

const loading = ref(false)
const showEmpty = ref(false)
const plans = DEMO_PLANS
const dialogVisible = ref(false)

const uploadFiles = ref<{ name: string; size: number }[]>([])

function onFileChange(file: { name: string; size?: number }): void {
  uploadFiles.value = [{ name: file.name, size: file.size ?? 0 }]
}

const evidence = DEMO_EVIDENCE
const diffs = DEMO_DIFFS
const metrics = DEMO_METRICS

const chartOption = computed<EChartsOption>(() => ({
  grid: { left: 40, right: 16, top: 20, bottom: 56 },
  xAxis: {
    type: 'category',
    data: metrics.map((item) => item.label),
    axisLabel: { rotate: 32, fontSize: 10, color: palette.value.muted, interval: 0 },
    axisLine: { lineStyle: { color: palette.value.border } },
  },
  yAxis: {
    type: 'value',
    max: 1,
    splitLine: { lineStyle: { color: palette.value.border } },
    axisLabel: { fontSize: 10, color: palette.value.muted },
  },
  series: [
    {
      type: 'bar',
      data: metrics.map((item) => item.value ?? 0),
      barMaxWidth: 22,
      itemStyle: { color: palette.value.primary, borderRadius: [3, 3, 0, 0] },
    },
  ],
  tooltip: { trigger: 'axis' },
}))

function toggleLoading(): void {
  loading.value = true
  window.setTimeout(() => {
    loading.value = false
  }, 800)
}
</script>

<template>
  <div class="review">
    <header class="review-head">
      <div class="review-title">
        <p class="kicker">Design review · 2026-10</p>
        <h1>视觉与组件验收</h1>
        <p class="review-lead">
          参考 Windows 11 Fluent 的导航与命令栏、macOS Finder 的内容优先、GNOME Settings 的分段结构。
          B「松绿 · 砂岩」已选，布局待确认。
        </p>
        <div class="chips">
          <span class="chip">主题 B 松绿</span>
          <span class="chip">Fluent / Finder / GNOME</span>
          <span class="chip chip--accent">待确认</span>
        </div>
      </div>
      <div class="review-summary" aria-label="验收摘要">
        <div><span>参考系统</span><strong>3</strong><small>Windows / macOS / GNOME</small></div>
        <div><span>覆盖</span><strong>4 / 4</strong><small>令牌 · 组件 · 四态 · 响应式</small></div>
        <div><span>状态</span><strong>待验收</strong><small>通过后冻结 v1.0</small></div>
      </div>
    </header>

    <nav class="tabs" aria-label="验收章节">
      <a href="#tokens">色板与令牌</a>
      <a href="#type">排版</a>
      <a href="#buttons">按钮</a>
      <a href="#forms">表单</a>
      <a href="#table">列表与状态</a>
      <a href="#overlays">弹窗与上传</a>
      <a href="#data">证据与指标</a>
      <a href="#states">页面四态</a>
      <span class="tabs-spacer" />
      <el-radio-group :model-value="ui.theme" size="small" @update:model-value="changeTheme">
        <el-radio-button value="ink">A 墨蓝</el-radio-button>
        <el-radio-button value="pine">B 松绿</el-radio-button>
      </el-radio-group>
    </nav>

    <div class="review-body">
      <section id="tokens" class="review-section">
        <header class="section-head">
          <div>
            <h2>色板与令牌</h2>
            <p class="muted">画布、表面、描边三层关系；颜色只通过令牌引用。</p>
          </div>
          <span class="section-meta">CSS variables</span>
        </header>
        <div class="swatch-grid">
          <div v-for="[label, color] in swatches" :key="label">
            <div class="swatch" :style="{ background: color }" />
            <div class="swatch-label"><span>{{ label }}</span><span class="mono">{{ color }}</span></div>
          </div>
        </div>
      </section>

      <div class="pair">
        <section id="type" class="review-section">
          <header class="section-head">
            <div>
              <h2>排版</h2>
              <p class="muted">Segoe UI + 系统中文字体；正文 14、表格 13、标题 20。</p>
            </div>
            <span class="section-meta">无外链字体</span>
          </header>
          <div class="type-specimens">
            <div><span class="spec-label">页面标题 / 20 · 600</span><h1>教案库与版本链</h1></div>
            <div><span class="spec-label">小标题 / 16 · 600</span><h2>证据链与审查记录</h2></div>
            <div><span class="spec-label">正文 / 14 · 1.6</span><p>教师只能查看本人教案，组长查看本组；管理员可查看全部并审计关键操作。</p></div>
            <div><span class="spec-label">表格 / 13 · 1.45</span><p class="mono">planHash 8f2c…a91 · 2026-10-28 14:20</p></div>
          </div>
        </section>

        <section id="buttons" class="review-section">
          <header class="section-head">
            <div>
              <h2>按钮</h2>
              <p class="muted">控件高 32、圆角 6；一屏一个主按钮。</p>
            </div>
            <span class="section-meta">Fluent 尺度</span>
          </header>
          <div class="demo-surface row">
            <el-button type="primary">上传契约包</el-button>
            <el-button>取消</el-button>
            <el-button type="success">通过</el-button>
            <el-button type="warning">放行</el-button>
            <el-button type="danger">删除</el-button>
            <el-button text>文字按钮</el-button>
            <el-button disabled>禁用</el-button>
            <el-button type="primary" loading>提交中</el-button>
          </div>
        </section>
      </div>

      <div class="pair">
        <section id="forms" class="review-section">
          <header class="section-head">
            <div>
              <h2>表单</h2>
              <p class="muted">标签在字段上方，错误在下方；窄屏自动一列。</p>
            </div>
            <span class="section-meta">Element Plus Form</span>
          </header>
          <el-form ref="formRef" :model="form" :rules="rules" label-position="top" class="form-grid">
            <el-form-item label="课题" prop="title">
              <el-input v-model="form.title" placeholder="例如：一级考证辅导2" />
            </el-form-item>
            <el-form-item label="课程" prop="course">
              <el-select v-model="form.course" style="width: 100%">
                <el-option label="信息技术" value="信息技术" />
                <el-option label="英语" value="英语" />
              </el-select>
            </el-form-item>
            <el-form-item label="周次" prop="week">
              <el-input-number v-model="form.week" :min="1" :max="20" />
            </el-form-item>
            <el-form-item label="备注">
              <el-input v-model="form.note" type="textarea" :rows="2" placeholder="选填" />
            </el-form-item>
          </el-form>
          <div class="row">
            <el-button type="primary" @click="submitForm">保存</el-button>
            <el-button @click="formRef?.resetFields()">重置</el-button>
          </div>
        </section>

        <section id="overlays" class="review-section">
          <header class="section-head">
            <div>
              <h2>弹窗与上传</h2>
              <p class="muted">Esc 关闭、焦点归位；上传只接受 .zip。</p>
            </div>
            <span class="section-meta">Dialog / Upload</span>
          </header>
          <div class="demo-surface row">
            <el-button @click="dialogVisible = true">打开弹窗</el-button>
            <el-button @click="ElMessage.success('已保存')">成功提示</el-button>
            <el-button @click="ElMessage.error('保存失败（INTERNAL）')">失败提示</el-button>
            <el-upload :auto-upload="false" :show-file-list="false" accept=".zip" :on-change="onFileChange">
              <el-button>选择契约包</el-button>
            </el-upload>
          </div>
          <p v-if="uploadFiles.length" class="muted selected-file">
            {{ uploadFiles[0].name }}（{{ Math.ceil(uploadFiles[0].size / 1024) }} KB）
          </p>
          <el-dialog v-model="dialogVisible" title="删除这份教案？" width="420px">
            <p>软删除后教师与组长不可见，管理员仍可在审计中追溯。</p>
            <template #footer>
              <el-button @click="dialogVisible = false">取消</el-button>
              <el-button type="danger" @click="dialogVisible = false">确认删除</el-button>
            </template>
          </el-dialog>
        </section>
      </div>

      <section id="table" class="review-section">
        <header class="section-head">
          <div>
            <h2>列表与状态</h2>
            <p class="muted">表格是主内容，筛选条与表格共用一条内容表面；表头透明、底部细线。</p>
          </div>
          <span class="section-meta">空态 / 加载 / 正常</span>
        </header>
        <div class="table-surface">
          <div class="table-toolbar">
            <div class="row">
              <el-input v-model="form.title" placeholder="按课题筛选" clearable style="width: 220px" />
              <el-select v-model="form.course" style="width: 140px">
                <el-option label="信息技术" value="信息技术" />
                <el-option label="英语" value="英语" />
              </el-select>
              <el-button type="primary">查询</el-button>
            </div>
            <div class="row">
              <el-button @click="toggleLoading">模拟加载</el-button>
              <el-switch v-model="showEmpty" active-text="空态" />
            </div>
          </div>
          <div class="table-scroll">
            <el-table v-loading="loading" :data="showEmpty ? [] : plans" size="default">
              <el-table-column prop="title" label="课题" min-width="180" show-overflow-tooltip />
              <el-table-column prop="course" label="课程" width="110" />
              <el-table-column label="周/次" width="80">
                <template #default="{ row }">{{ row.week }} / {{ row.session }}</template>
              </el-table-column>
              <el-table-column prop="teacher" label="教师" width="100" />
              <el-table-column label="状态" width="110">
                <template #default="{ row }"><StatusTag :code="row.status" :status="row.status" /></template>
              </el-table-column>
              <el-table-column prop="version" label="版本" width="70" />
            </el-table>
          </div>
          <p class="muted mobile-hint">窄屏可左右滑动表格查看全部列</p>
          <el-empty v-if="showEmpty" description="没有匹配的教案，试试调整筛选条件">
            <el-button type="primary">上传契约包</el-button>
          </el-empty>
          <div class="page-footer">
            <el-pagination background layout="prev, pager, next, total" :total="42" :page-size="10" />
          </div>
        </div>
      </section>

      <section id="data" class="review-section">
        <header class="section-head">
          <div>
            <h2>证据、差异与指标</h2>
            <p class="muted">证据链五项与版本差异并排；指标卡必须同屏显示分子/分母。</p>
          </div>
          <span class="section-meta">业务展示组件</span>
        </header>
        <div class="data-grid">
          <EvidenceChain :items="evidence" :passed="4" :total="5" />
          <div class="demo-surface stack">
            <div class="section-title"><h3>版本差异</h3><span>字段路径 + 前后值</span></div>
            <DiffViewer :changes="diffs" />
          </div>
        </div>
        <div class="metrics-grid">
          <MetricCard v-for="metric in metrics" :key="metric.key" :metric="metric" />
        </div>
        <div class="chart-surface">
          <ChartCard :option="chartOption" height="220px" />
        </div>
      </section>

      <section id="states" class="review-section">
        <header class="section-head">
          <div>
            <h2>页面四态</h2>
            <p class="muted">loading 用骨架，empty 给动作，error 带 code/traceId，403 说明原因。</p>
          </div>
          <span class="section-meta">每页必备</span>
        </header>
        <div class="state-grid">
          <div class="demo-surface"><StatePanel state="loading" title="正在加载教案…" /></div>
          <div class="demo-surface">
            <StatePanel state="empty" title="还没有教案" description="先上传一个契约包，或从样例库复制">
              <template #action><el-button type="primary">上传契约包</el-button></template>
            </StatePanel>
          </div>
          <div class="demo-surface">
            <StatePanel state="error" title="读取失败（NOT_FOUND）" description="traceId: 4a77…c91" />
          </div>
          <div class="demo-surface"><StatePanel state="forbidden" title="无权查看该教案" /></div>
        </div>
      </section>
    </div>
  </div>
</template>

<style scoped>
.review {
  max-width: 1360px;
  margin: 0 auto;
}

.review-head {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(300px, 380px);
  gap: 32px;
  padding: 4px 0 18px;
  border-bottom: 1px solid var(--lpp-border);
}

.kicker {
  color: var(--lpp-text-muted);
  font-size: 11px;
  margin-bottom: 4px;
}

.review-title h1 {
  font-size: 22px;
  letter-spacing: -0.01em;
}

.review-lead {
  max-width: 640px;
  margin-top: 6px;
  color: var(--lpp-text-muted);
  font-size: 12px;
}

.chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 12px;
}

.chip {
  padding: 2px 8px;
  border: 1px solid var(--lpp-border);
  border-radius: 999px;
  background: var(--lpp-surface);
  color: var(--lpp-text-muted);
  font-size: 11px;
}

.chip--accent {
  border-color: color-mix(in srgb, var(--lpp-accent) 40%, var(--lpp-border));
  background: color-mix(in srgb, var(--lpp-accent) 8%, white);
  color: color-mix(in srgb, var(--lpp-accent) 70%, var(--lpp-text));
}

.review-summary {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0;
  align-self: end;
  border: 1px solid var(--lpp-border);
  border-radius: var(--lpp-radius-card);
  background: var(--lpp-surface);
  overflow: hidden;
}

.review-summary > div {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 10px 12px;
  border-right: 1px solid var(--lpp-border);
}

.review-summary > div:last-child {
  border-right: 0;
}

.review-summary span {
  color: var(--lpp-text-muted);
  font-size: 10px;
}

.review-summary strong {
  font-size: 14px;
  font-variant-numeric: tabular-nums;
}

.review-summary small {
  color: var(--lpp-text-muted);
  font-size: 10px;
  line-height: 1.35;
}

.tabs {
  position: sticky;
  top: 0;
  z-index: 5;
  display: flex;
  align-items: center;
  gap: 2px;
  padding: 8px 0;
  margin-bottom: 4px;
  background: var(--lpp-canvas);
  border-bottom: 1px solid var(--lpp-border);
  overflow-x: auto;
}

.tabs a {
  padding: 5px 9px;
  border-radius: var(--lpp-radius-control);
  color: var(--lpp-text-muted);
  font-size: 12px;
  text-decoration: none;
  white-space: nowrap;
}

.tabs a:hover {
  background: var(--lpp-nav-hover);
  color: var(--lpp-text);
  text-decoration: none;
}

.tabs-spacer {
  flex: 1;
}

.review-section {
  padding: 18px 0 20px;
  border-bottom: 1px solid var(--lpp-border);
}

.pair {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0 32px;
}

.section-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 12px;
}

.section-head h2 {
  margin-bottom: 2px;
}

.section-head p {
  font-size: 12px;
  max-width: 680px;
}

.section-meta {
  color: var(--lpp-text-muted);
  font-size: 11px;
  white-space: nowrap;
}

.swatch-grid {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 10px;
}

.swatch {
  height: 40px;
  border-radius: var(--lpp-radius-control);
  border: 1px solid rgba(0, 0, 0, 0.08);
}

.swatch-label {
  display: flex;
  justify-content: space-between;
  gap: 4px;
  margin-top: 4px;
  color: var(--lpp-text-muted);
  font-size: 11px;
}

.type-specimens {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.type-specimens > div {
  padding-bottom: 7px;
  border-bottom: 1px dashed var(--lpp-border);
}

.type-specimens > div:last-child {
  border-bottom: 0;
  padding-bottom: 0;
}

.spec-label {
  color: var(--lpp-text-muted);
  font-size: 11px;
}

.demo-surface,
.table-surface,
.chart-surface {
  background: var(--lpp-surface);
  border: 1px solid var(--lpp-border);
  border-radius: var(--lpp-radius-card);
  padding: 12px 14px;
}

.table-surface {
  padding: 0;
  overflow: hidden;
}

.table-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 9px 12px;
  border-bottom: 1px solid var(--lpp-border);
  background: var(--lpp-layer);
}

.table-scroll {
  width: 100%;
  min-width: 0;
  overflow-x: auto;
}

.table-surface :deep(.el-table) {
  border-radius: 0;
}

.table-surface .page-footer {
  padding: 8px 12px;
  border-top: 1px solid var(--lpp-border);
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0 16px;
}

.selected-file {
  margin-top: 8px;
  font-size: 11px;
}

.data-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
  margin-top: 12px;
}

.chart-surface {
  margin-top: 12px;
  padding: 6px 8px 0;
}

.state-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.state-grid .demo-surface {
  min-height: 170px;
}

.mobile-hint {
  display: none;
  padding: 6px 12px 0;
  font-size: 11px;
}

@media (max-width: 1100px) {
  .review-head {
    grid-template-columns: minmax(0, 1fr);
    gap: 16px;
  }

  .swatch-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

@media (max-width: 900px) {
  .pair {
    grid-template-columns: minmax(0, 1fr);
    gap: 0;
  }

  .metrics-grid,
  .state-grid,
  .data-grid {
    grid-template-columns: minmax(0, 1fr);
  }
}

@media (max-width: 767px) {
  .form-grid {
    grid-template-columns: minmax(0, 1fr);
  }

  .mobile-hint {
    display: block;
  }

  .swatch-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .tabs {
    margin: 0 -14px;
    padding: 8px 14px;
  }

  .review-summary {
    grid-template-columns: minmax(0, 1fr);
  }

  .review-summary > div {
    border-right: 0;
    border-bottom: 1px solid var(--lpp-border);
  }

  .review-summary > div:last-child {
    border-bottom: 0;
  }

  .table-toolbar {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>
