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
import { useUiStore } from '@/stores/ui'
import type { DiffChange, EvidenceItem, Metric } from '@/api/models'

const ui = useUiStore()

const palettes = {
  ink: {
    title: 'A「墨蓝 · 麦金」',
    primary: '#1F3A5F',
    accent: '#B07A2A',
    bg: '#F7F8F5',
    surface: '#FFFFFF',
    text: '#1B2430',
    muted: '#5B6878',
    border: '#DDE3EA',
    success: '#2F6B4F',
    warning: '#A15C12',
    danger: '#A33A2B',
  },
  pine: {
    title: 'B「松绿 · 砂岩」',
    primary: '#2E5B52',
    accent: '#8C6A4A',
    bg: '#F5F4EF',
    surface: '#FFFFFF',
    text: '#1C2622',
    muted: '#5D6A63',
    border: '#D9DDD6',
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
  ['页面底', palette.value.bg],
  ['表面', palette.value.surface],
  ['主文字', palette.value.text],
  ['次文字', palette.value.muted],
  ['边框', palette.value.border],
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
const plans = [
  { id: 1, title: '一级考证辅导2', course: '信息技术', week: 2, session: 1, teacher: '张老师', status: 'passed', version: 2 },
  { id: 2, title: 'C 语言循环结构', course: '信息技术', week: 3, session: 2, teacher: '李老师', status: 'needs_repair', version: 1 },
  { id: 3, title: '网络安全意识', course: '信息技术', week: 4, session: 1, teacher: '张老师', status: 'pending_reviewer', version: 1 },
  { id: 4, title: 'Excel 数据透视表', course: '信息技术', week: 5, session: 2, teacher: '王组长', status: 'passed_with_override', version: 3 },
  { id: 5, title: 'Python 字典应用', course: '信息技术', week: 6, session: 1, teacher: '张老师', status: 'structure_invalid', version: 1 },
]

const dialogVisible = ref(false)

const uploadFiles = ref<{ name: string; size: number }[]>([])

function onFileChange(file: { name: string; size?: number }): void {
  uploadFiles.value = [{ name: file.name, size: file.size ?? 0 }]
}

const evidence: EvidenceItem[] = [
  { key: 'hash_match', label: '哈希匹配', ok: true, reason: '' },
  { key: 'round_continuous', label: '轮次连续', ok: true, reason: '' },
  { key: 'overrides_complete', label: '放行完整', ok: false, reason: 'waived 问题缺少对应放行记录：AR-2' },
  { key: 'independence_valid', label: '审校方式合规', ok: true, reason: '' },
  { key: 'status_consistent', label: '状态一致', ok: true, reason: '' },
]

const diffs: DiffChange[] = [
  { path: 'activityFlow.summary', before: '旧的小结', after: '第二次修订后的课堂小结' },
  { path: 'knowledgeGoals', before: '掌握基本操作', after: '掌握基本操作并能独立完成 2 个任务' },
]

const metrics: Metric[] = [
  ['structure_rate', '结构合规率', 3, 4],
  ['gold_standard', '金标准贴近分', 0, 0],
  ['defect_density', '闭环缺陷密度', 1, 4],
  ['evidence_rate', '证据链完整率', 4, 4],
  ['sync_consistency', '双端数据一致率', 8, 9],
  ['task_completion', '平台任务完成率', 12, 15],
  ['expert_score', '专家评分', 0, 0],
  ['export_seconds', '单份耗时', 62, 5],
  ['availability', '平台可用性', 0, 0],
].map(([key, label, numerator, denominator]) => ({
  key: String(key),
  label: String(label),
  numerator: Number(numerator),
  denominator: Number(denominator),
  value: Number(denominator) ? Number(numerator) / Number(denominator) : null,
  unit: key === 'export_seconds' ? '秒' : '',
  available: Number(denominator) > 0,
  filters: {},
}))

const chartOption = computed<EChartsOption>(() => ({
  grid: { left: 40, right: 16, top: 24, bottom: 32 },
  xAxis: {
    type: 'category',
    data: metrics.map((item) => item.label),
    axisLabel: { rotate: 25, fontSize: 10, color: palette.value.muted },
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
      barMaxWidth: 26,
      itemStyle: { color: palette.value.primary, borderRadius: [4, 4, 0, 0] },
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
  <div class="page styleguide">
    <div class="page-header">
      <div>
        <h1>风格验收 · {{ palette.title }}</h1>
        <p class="page-subtitle">
          真实 Element Plus 组件 + 项目令牌。请按 1440 / 1280 / 390 三档查看，确认后把结论写入
          <code>docs/frontend/review-notes.md</code>。
        </p>
      </div>
      <div class="row">
        <el-radio-group :model-value="ui.theme" size="small" @update:model-value="changeTheme">
          <el-radio-button value="ink">A 墨蓝</el-radio-button>
          <el-radio-button value="pine">B 松绿</el-radio-button>
        </el-radio-group>
      </div>
    </div>

    <section class="panel stack">
      <div class="section-title"><h2>色板与令牌</h2><span>切换主题会实时改 CSS 变量</span></div>
      <div class="grid-4">
        <div v-for="[label, color] in swatches" :key="label">
          <div class="swatch" :style="{ background: color }" />
          <div class="swatch-label"><span>{{ label }}</span><span class="mono">{{ color }}</span></div>
        </div>
      </div>
    </section>

    <section class="panel stack">
      <div class="section-title"><h2>排版</h2><span>系统中文字体，无外链</span></div>
      <div class="specimen"><span class="muted">页面标题 / 20 · 600</span><h1>教案库与版本链</h1></div>
      <div class="specimen"><span class="muted">小标题 / 16 · 600</span><h2>证据链与审查记录</h2></div>
      <div class="specimen"><span class="muted">正文 / 14 · 1.6</span><p>教师只能查看本人教案，组长查看本组；管理员可查看全部并审计关键操作。</p></div>
      <div class="specimen"><span class="muted">表格 / 13 · 1.45</span><p class="mono">planHash 8f2c…a91 · 2026-10-28 14:20</p></div>
    </section>

    <section class="panel stack">
      <div class="section-title"><h2>按钮</h2><span>高度 32，主按钮每屏一个</span></div>
      <div class="row">
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

    <section class="panel stack">
      <div class="section-title"><h2>表单与校验</h2><span>label 顶部，错误在下方</span></div>
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

    <section class="panel stack">
      <div class="section-title">
        <h2>表格、状态与分页</h2>
        <span>空态 / 加载 / 错误 / 正常</span>
      </div>
      <div class="toolbar">
        <el-input v-model="form.title" placeholder="按课题筛选" clearable style="width: 220px" />
        <el-select v-model="form.course" style="width: 140px">
          <el-option label="信息技术" value="信息技术" />
          <el-option label="英语" value="英语" />
        </el-select>
        <el-button type="primary">查询</el-button>
        <el-button @click="toggleLoading">模拟加载</el-button>
        <el-switch v-model="showEmpty" active-text="空态" />
      </div>
      <div class="table-scroll">
        <el-table v-loading="loading" :data="showEmpty ? [] : plans" border size="default">
          <el-table-column prop="title" label="课题" min-width="180" show-overflow-tooltip />
          <el-table-column prop="course" label="课程" width="120" />
          <el-table-column label="周/次" width="90">
            <template #default="{ row }">{{ row.week }} / {{ row.session }}</template>
          </el-table-column>
          <el-table-column prop="teacher" label="教师" width="100" />
          <el-table-column label="状态" width="120">
            <template #default="{ row }"><StatusTag :code="row.status" :status="row.status" /></template>
          </el-table-column>
          <el-table-column prop="version" label="版本" width="80" />
        </el-table>
      </div>
      <p class="muted mobile-hint">窄屏可左右滑动表格查看全部列</p>
      <el-empty v-if="showEmpty" description="没有匹配的教案，试试调整筛选条件">
        <el-button type="primary">上传契约包</el-button>
      </el-empty>
      <div class="page-footer">
        <el-pagination background layout="prev, pager, next, total" :total="42" :page-size="10" />
      </div>
    </section>

    <section class="panel stack">
      <div class="section-title"><h2>弹窗、上传与反馈</h2><span>遮罩、Esc、焦点回到触发元素</span></div>
      <div class="row">
        <el-button @click="dialogVisible = true">打开确认弹窗</el-button>
        <el-button @click="ElMessage.success('已保存')">成功提示</el-button>
        <el-button @click="ElMessage.error('保存失败（INTERNAL），traceId: demo')">失败提示</el-button>
        <el-upload :auto-upload="false" :show-file-list="false" accept=".zip" :on-change="onFileChange">
          <el-button>选择契约包</el-button>
        </el-upload>
        <span v-if="uploadFiles.length" class="muted">
          已选择：{{ uploadFiles[0].name }}（{{ Math.ceil(uploadFiles[0].size / 1024) }} KB）
        </span>
      </div>
      <el-dialog v-model="dialogVisible" title="删除这份教案？" width="420px">
        <p>软删除后教师与组长不可见，管理员仍可在审计中追溯。</p>
        <template #footer>
          <el-button @click="dialogVisible = false">取消</el-button>
          <el-button type="danger" @click="dialogVisible = false">确认删除</el-button>
        </template>
      </el-dialog>
    </section>

    <div class="grid-2">
      <EvidenceChain :items="evidence" :passed="4" :total="5" />
      <section class="panel stack">
        <div class="section-title"><h2>版本差异</h2><span>字段路径 + 前后值</span></div>
        <DiffViewer :changes="diffs" />
      </section>
    </div>

    <section class="stack">
      <div class="section-title"><h2>统计指标</h2><span>分子/分母同屏，空数据不显示 0</span></div>
      <div class="grid-3">
        <MetricCard v-for="metric in metrics" :key="metric.key" :metric="metric" />
      </div>
      <div class="panel">
        <ChartCard :option="chartOption" height="240px" />
      </div>
    </section>

    <section class="panel stack">
      <div class="section-title"><h2>页面四态</h2><span>loading / empty / error / 403</span></div>
      <div class="grid-2">
        <StatePanel state="loading" title="正在加载教案…" />
        <StatePanel state="empty" title="还没有教案" description="先上传一个契约包，或从样例库复制">
          <template #action><el-button type="primary">上传契约包</el-button></template>
        </StatePanel>
        <StatePanel state="error" title="读取失败（NOT_FOUND）" description="traceId: 4a77…c91" />
        <StatePanel state="forbidden" title="无权查看该教案" />
      </div>
    </section>

    <p class="muted styleguide-foot">
      验收提示：切到 1280 看侧栏折叠与筛选换行；切到 390 看导航收起与表格滚动。主题 A/B 只差令牌，不改布局。
    </p>
  </div>
</template>

<style scoped>
.styleguide {
  max-width: 1440px;
  margin: 0 auto;
  overflow-x: hidden;
}

.table-scroll {
  width: 100%;
  min-width: 0;
  overflow-x: auto;
}

.mobile-hint {
  display: none;
  margin-top: 8px;
  font-size: 12px;
}

@media (max-width: 767px) {
  .mobile-hint {
    display: block;
  }
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0 16px;
}

.styleguide-foot {
  padding-bottom: 24px;
  font-size: 12px;
}

@media (max-width: 767px) {
  .form-grid {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
