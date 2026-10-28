<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import type { EChartsOption } from 'echarts'

import ChartCard from '@/components/ChartCard.vue'
import DataTable from '@/components/DataTable.vue'
import DiffViewer from '@/components/DiffViewer.vue'
import EvidenceChain from '@/components/EvidenceChain.vue'
import MetricCard from '@/components/MetricCard.vue'
import MetricLedger from '@/components/MetricLedger.vue'
import PageHeader from '@/components/PageHeader.vue'
import SectionHeader from '@/components/SectionHeader.vue'
import StatePanel from '@/components/StatePanel.vue'
import StatusTag from '@/components/StatusTag.vue'
import StructurePanel from '@/components/StructurePanel.vue'
import type { TableColumn } from '@/components/table-types'
import { DEMO_DIFFS, DEMO_EVIDENCE, DEMO_LEDGER_KEYS, DEMO_METRICS, DEMO_PLANS, DEMO_STRUCTURE } from '@/dev/overview-fixtures'
import { CHART_TOKENS, PALETTE } from '@/styles/palette'
import { contrastRatio } from '@/utils/color'

const router = useRouter()
const isDev = import.meta.env.DEV

const tabs = [
  { id: 'principles', label: '方向' },
  { id: 'color', label: '色彩' },
  { id: 'type', label: '排版' },
  { id: 'components', label: '控件' },
  { id: 'data', label: '数据' },
  { id: 'structure', label: '结构剖面' },
  { id: 'states', label: '四态' },
  { id: 'responsive', label: '响应式' },
]

const swatches = [
  { label: '主色', value: PALETTE.primary },
  { label: '主色悬停', value: PALETTE.primaryHover },
  { label: '强调（黄铜）', value: PALETTE.brass },
  { label: '画布', value: PALETTE.canvas },
  { label: '层 / 侧栏', value: PALETTE.layer },
  { label: '表面', value: PALETTE.surface },
  { label: '主文字', value: PALETTE.text },
  { label: '次文字', value: PALETTE.textMuted },
  { label: '描边', value: PALETTE.border },
  { label: '成功', value: PALETTE.success },
  { label: '警告', value: PALETTE.warning },
  { label: '危险', value: PALETTE.danger },
]

const contrastRows = computed(() => [
  { label: '主文字 / 表面', pair: `${PALETTE.text} / ${PALETTE.surface}`, ratio: contrastRatio(PALETTE.text, PALETTE.surface) },
  { label: '次文字 / 表面', pair: `${PALETTE.textMuted} / ${PALETTE.surface}`, ratio: contrastRatio(PALETTE.textMuted, PALETTE.surface) },
  { label: '次文字 / 画布', pair: `${PALETTE.textMuted} / ${PALETTE.canvas}`, ratio: contrastRatio(PALETTE.textMuted, PALETTE.canvas) },
  { label: '主色 / 表面', pair: `${PALETTE.primary} / ${PALETTE.surface}`, ratio: contrastRatio(PALETTE.primary, PALETTE.surface) },
  { label: '危险 / 表面', pair: `${PALETTE.danger} / ${PALETTE.surface}`, ratio: contrastRatio(PALETTE.danger, PALETTE.surface) },
  { label: '身份牌文字 / 身份牌', pair: `${PALETTE.nameplateText} / ${PALETTE.nameplate}`, ratio: contrastRatio(PALETTE.nameplateText, PALETTE.nameplate) },
])

const spaces = [
  ['--lpp-space-1', '4', '图标与文字'],
  ['--lpp-space-2', '8', '按钮组、行内'],
  ['--lpp-space-3', '12', '表单、表格单元'],
  ['--lpp-space-4', '16', '区块内边距'],
  ['--lpp-space-6', '24', '区块间距'],
  ['--lpp-space-8', '32', '页面分节'],
]

const radii = [
  ['--lpp-radius-tag', '4', '状态标签'],
  ['--lpp-radius-control', '6', '按钮 / 输入 / 导航'],
  ['--lpp-radius-card', '10', '表格 / 面板'],
  ['--lpp-radius-window', '14', '弹窗'],
]

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

const dialogVisible = ref(false)
const uploadFiles = ref<{ name: string; size: number }[]>([])

function onFileChange(file: { name: string; size?: number }): void {
  uploadFiles.value = [{ name: file.name, size: file.size ?? 0 }]
}

const tablePage = ref(1)
const tablePageSize = 5
const tableRows = computed(() =>
  DEMO_PLANS.slice((tablePage.value - 1) * tablePageSize, tablePage.value * tablePageSize),
)
const planColumns: TableColumn[] = [
  { key: 'title', label: '课题', minWidth: 200 },
  { key: 'course', label: '课程', width: 100 },
  { key: 'week', label: '周 / 次', width: 84 },
  { key: 'teacher', label: '教师', width: 92 },
  { key: 'version', label: '版本', width: 60, align: 'right' },
  { key: 'evidence', label: '证据', width: 68 },
  { key: 'status', label: '状态', width: 104 },
]

const ledgerMetrics = computed(() =>
  DEMO_LEDGER_KEYS.map((key) => DEMO_METRICS.find((metric) => metric.key === key)).filter(
    (metric): metric is (typeof DEMO_METRICS)[number] => Boolean(metric),
  ),
)

const rateMetrics = computed(() =>
  DEMO_METRICS.filter((metric) =>
    ['structure_rate', 'evidence_rate', 'sync_consistency', 'task_completion'].includes(metric.key),
  ),
)

const chartOption = computed<EChartsOption>(() => ({
  animation: false,
  grid: { left: 96, right: 36, top: 22, bottom: 32 },
  textStyle: { fontFamily: CHART_TOKENS.fontFamily },
  xAxis: {
    type: 'value',
    min: 0,
    max: 1,
    axisLabel: { formatter: (value: number) => `${Math.round(value * 100)}%`, color: CHART_TOKENS.text, fontSize: 12 },
    splitLine: { lineStyle: { color: CHART_TOKENS.grid } },
    axisLine: { show: false },
    axisTick: { show: false },
  },
  yAxis: {
    type: 'category',
    data: rateMetrics.value.map((metric) => metric.label),
    axisLabel: { color: CHART_TOKENS.text, fontSize: 12 },
    axisLine: { show: false },
    axisTick: { show: false },
  },
  tooltip: {
    trigger: 'item',
    formatter: (params: unknown) => {
      const index = (params as { dataIndex: number }).dataIndex
      const metric = rateMetrics.value[index]
      return `${metric.label}<br/>${Math.round((metric.value ?? 0) * 100)}% / ${metric.numerator}/${metric.denominator}`
    },
  },
  series: [
    {
      type: 'scatter',
      symbolSize: 10,
      itemStyle: { color: CHART_TOKENS.primary },
      data: rateMetrics.value.map((metric, index) => [metric.value ?? 0, index]),
      markLine: {
        silent: true,
        symbol: 'none',
        label: { formatter: '目标 90%', color: CHART_TOKENS.text, fontSize: 11 },
        lineStyle: { color: CHART_TOKENS.accent, type: 'dashed', width: 1 },
        data: [{ xAxis: 0.9 }],
      },
    },
  ],
}))

const chartSummary = computed(
  () =>
    `四项比率指标：${rateMetrics.value
      .map((metric) => `${metric.label} ${Math.round((metric.value ?? 0) * 100)}%`)
      .join('；')}。虚线为目标 90%。`,
)

const force2d = ref(false)
const showEmpty = ref(false)
const loading = ref(false)

function toggleLoading(): void {
  loading.value = true
  window.setTimeout(() => {
    loading.value = false
  }, 800)
}

const statuses = ['passed', 'passed_with_override', 'needs_repair', 'pending_reviewer', 'structure_invalid', 'failed']
</script>

<template>
  <div class="styleguide page">
    <PageHeader
      title="设计验收"
      description="单一「松绿 · 砂岩」主题；用规则线、留白和数字层级建立秩序，3D 结构剖面是唯一的重音。"
    >
      <template #meta>
        <p class="styleguide-meta">
          候选稿 v1.1 / 2026-10-28 / 待用户确认后冻结
        </p>
      </template>
      <template #actions>
        <el-button @click="router.push('/preview/overview')">查看概览预览</el-button>
      </template>
    </PageHeader>

    <nav class="style-tabs" aria-label="验收章节">
      <a v-for="tab in tabs" :key="tab.id" :href="`#${tab.id}`">{{ tab.label }}</a>
      <span class="style-tabs__spacer" />
      <span class="style-tabs__note">1440 / 1280 / 390</span>
    </nav>

    <section id="principles" class="style-section">
      <SectionHeader
        title="方向：教案校样台"
        description="像编辑校样一样看教案：规则线、页边、批注、版本号与审查印记。"
        meta="不套后台模板"
      />
      <div class="principle-grid">
        <article>
          <h3>结构优先</h3>
          <p>先把三维目标、八步流程与证据链排清楚，再谈装饰。表格是主内容，不是卡片堆。</p>
        </article>
        <article>
          <h3>状态有文字</h3>
          <p>审查、导出、逾期、证据缺项都给出文字结论；颜色只做辅助，不承担唯一信息。</p>
        </article>
        <article>
          <h3>一处重音</h3>
          <p>结构剖面是唯一的高投入视觉；其余区域保持安静、低对比、可长时间阅读。</p>
        </article>
      </div>

      <table class="ref-table">
        <caption class="sr-only">设计参考与取舍</caption>
        <thead>
          <tr><th scope="col">参考</th><th scope="col">借用</th><th scope="col">不照搬</th></tr>
        </thead>
        <tbody>
          <tr><td>Linear</td><td>命令优先、紧凑但不拥挤、键盘可达</td><td>全暗色、紫色光晕</td></tr>
          <tr><td>Stripe Dashboard</td><td>指标排版、表格数字、克制的分隔线</td><td>营销式大数字堆叠</td></tr>
          <tr><td>Figma</td><td>工作台感：工具归工具，内容归内容</td><td>深色侧栏本身</td></tr>
          <tr><td>瑞士国际主义排版</td><td>网格、规则线、对齐、层级</td><td>无圆角报纸栏密度</td></tr>
        </tbody>
      </table>
    </section>

    <section id="color" class="style-section">
      <SectionHeader title="色彩" description="唯一的行动色是松绿；黄铜只做规则线、选中小标记与印章。" meta="CSS variables" />
      <div class="swatch-grid">
        <div v-for="swatch in swatches" :key="swatch.label">
          <div class="swatch" :style="{ background: swatch.value }" />
          <div class="swatch-label"><span>{{ swatch.label }}</span><span class="mono">{{ swatch.value }}</span></div>
        </div>
      </div>

      <div class="contrast-table">
        <div class="contrast-head"><span>文字组合</span><span>色值</span><span>对比度</span></div>
        <div v-for="row in contrastRows" :key="row.label" class="contrast-row">
          <span>{{ row.label }}</span>
          <span class="mono">{{ row.pair }}</span>
          <span class="numeric" :class="{ 'is-pass': row.ratio >= 4.5 }">{{ row.ratio.toFixed(2) }}:1</span>
        </div>
      </div>
    </section>

    <section id="type" class="style-section">
      <SectionHeader title="排版与尺度" description="中文系统无衬线 + Bahnschrift 数字；信息文字不小于 12px，不请求外部字体。" meta="12 → 36" />
      <div class="type-grid">
        <div class="type-specimens">
          <div><span class="spec-label">页面标题 / 28 / 600</span><h1>教案库与版本链</h1></div>
          <div><span class="spec-label">小标题 / 16 / 600</span><h2>证据链与审查记录</h2></div>
          <div><span class="spec-label">正文 / 14 / 1.65</span><p>教师只能查看本人教案，组长查看本组；管理员可查看全部并审计关键操作。</p></div>
          <div><span class="spec-label">表格 / 13 / 1.5</span><p class="numeric">planHash 8f2c…a91 / 2026-10-28 14:20</p></div>
          <div><span class="spec-label">辅助 / 12 / 1.4</span><p class="muted">当前范围 / 不含已删除教案</p></div>
        </div>
        <div class="scale-tables">
          <table class="scale-table">
            <caption class="sr-only">间距令牌</caption>
            <thead><tr><th scope="col">间距</th><th scope="col">px</th><th scope="col">用途</th></tr></thead>
            <tbody>
              <tr v-for="row in spaces" :key="row[0]"><td class="mono">{{ row[0] }}</td><td class="numeric">{{ row[1] }}</td><td>{{ row[2] }}</td></tr>
            </tbody>
          </table>
          <table class="scale-table">
            <caption class="sr-only">圆角令牌</caption>
            <thead><tr><th scope="col">圆角</th><th scope="col">px</th><th scope="col">用途</th></tr></thead>
            <tbody>
              <tr v-for="row in radii" :key="row[0]"><td class="mono">{{ row[0] }}</td><td class="numeric">{{ row[1] }}</td><td>{{ row[2] }}</td></tr>
            </tbody>
          </table>
        </div>
      </div>
    </section>

    <section id="components" class="style-section">
      <SectionHeader title="控件" description="主按钮每屏一个；成功/警告/危险使用轻色调，不把整屏染成红绿。" meta="Element Plus 映射" />
      <div class="demo-grid">
        <div class="demo-surface">
          <h3>按钮</h3>
          <div class="row">
            <el-button type="primary">上传契约包</el-button>
            <el-button>取消</el-button>
            <el-button plain type="success">通过</el-button>
            <el-button plain type="warning">放行</el-button>
            <el-button plain type="danger">退回修复</el-button>
            <el-button text>文字按钮</el-button>
            <el-button disabled>禁用</el-button>
            <el-button type="primary" loading>提交中</el-button>
          </div>
        </div>

        <div class="demo-surface">
          <h3>状态标签</h3>
          <div class="row">
            <StatusTag v-for="status in statuses" :key="status" :code="status" :status="status" />
          </div>
        </div>

        <div class="demo-surface demo-surface--wide">
          <h3>表单</h3>
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
        </div>

        <div class="demo-surface">
          <h3>弹层与上传</h3>
          <div class="row">
            <el-button @click="dialogVisible = true">打开弹窗</el-button>
            <el-button @click="ElMessage.success('已保存')">成功提示</el-button>
            <el-button @click="ElMessage.error('保存失败（INTERNAL）')">失败提示</el-button>
          </div>
          <el-upload :auto-upload="false" :show-file-list="false" accept=".zip" :on-change="onFileChange">
            <el-button>选择契约包</el-button>
          </el-upload>
          <p v-if="uploadFiles.length" class="upload-note mono">
            {{ uploadFiles[0].name }}（{{ Math.ceil(uploadFiles[0].size / 1024) }} KB）
          </p>
        </div>

        <el-dialog v-model="dialogVisible" title="删除这份教案？" width="420px">
          <p>软删除后教师与组长不可见，管理员仍可在审计中追溯。</p>
          <template #footer>
            <el-button @click="dialogVisible = false">取消</el-button>
            <el-button type="danger" @click="dialogVisible = false">确认删除</el-button>
          </template>
        </el-dialog>
      </div>
    </section>

    <section id="data" class="style-section">
      <SectionHeader title="数据展示" description="表格、指标、证据链与差异必须同屏给出分子/分母、状态文字与原因。" meta="业务展示组件" />

      <div class="demo-toolbar">
        <el-button @click="toggleLoading">模拟加载</el-button>
        <el-switch v-model="showEmpty" active-text="空态" />
      </div>

      <DataTable
        :rows="showEmpty ? [] : tableRows"
        :columns="planColumns"
        :state="loading ? 'loading' : 'ready'"
        :page="tablePage"
        :page-size="tablePageSize"
        :total="DEMO_PLANS.length"
        show-pagination
        aria-label="示例教案列表"
        empty-text="没有匹配的教案，试试调整筛选条件"
        @update:page="tablePage = $event"
      >
        <template #cell-title="{ row }">
          <strong class="table-title">{{ row.title }}</strong>
        </template>
        <template #cell-week="{ row }">{{ row.week }} / {{ row.session }}</template>
        <template #cell-evidence="{ row }">{{ row.evidencePassed }}/{{ row.evidenceTotal }}</template>
        <template #cell-status="{ row }">
          <StatusTag :code="String(row.status)" :status="String(row.status)" />
        </template>
        <template #empty>
          <el-button @click="showEmpty = false">清除筛选</el-button>
        </template>
      </DataTable>

      <div class="ledger-demo">
        <MetricLedger :metrics="ledgerMetrics" />
      </div>

      <div class="metric-grid">
        <MetricCard v-for="metric in DEMO_METRICS" :key="metric.key" :metric="metric" />
      </div>

      <div class="data-grid">
        <EvidenceChain :items="DEMO_EVIDENCE" :passed="4" :total="5" />
        <div class="demo-surface stack">
          <div class="section-title"><h3>版本差异</h3><span>字段路径 + 前后值</span></div>
          <DiffViewer :changes="DEMO_DIFFS" />
        </div>
      </div>

      <div class="chart-surface">
        <ChartCard
          :option="chartOption"
          height="230px"
          label="四项比率指标与 90% 目标线"
          :summary="chartSummary"
        />
      </div>
    </section>

    <section id="structure" class="style-section">
      <SectionHeader
        title="结构剖面"
        description="3D 只承载一个信息：三维目标、八步流程、五项证据的三层剖面。所有信息在结构清单中同样可得。"
        meta="three.js + 2D 兜底"
      />
      <div class="structure-toolbar">
        <el-switch v-model="force2d" active-text="强制简化视图" />
        <span class="muted">无 WebGL、窄屏、chunk 失败或上下文丢失时自动降级为 SVG。</span>
      </div>
      <StructurePanel :structure="DEMO_STRUCTURE" :force-fallback="force2d" height="400px" />
      <p class="muted structure-note">
        3D 在 `prefers-reduced-motion` 下静止；离开视口暂停；卸载时释放几何、材质与 WebGL 上下文。
      </p>
    </section>

    <section id="states" class="style-section">
      <SectionHeader title="页面四态" description="loading 不闪白；empty 给一个可执行动作；error 带 code 与 traceId；403 说明原因。" meta="每页必备" />
      <div class="state-grid">
        <div class="demo-surface"><StatePanel state="loading" title="正在加载教案…" /></div>
        <div class="demo-surface">
          <StatePanel state="empty" title="还没有教案" description="先上传一个契约包，或从样例库复制。">
            <template #action><el-button type="primary">上传契约包</el-button></template>
          </StatePanel>
        </div>
        <div class="demo-surface">
          <StatePanel state="error" title="NOT_FOUND" description="资源不存在或已被删除。" trace-id="4a77c91" />
        </div>
        <div class="demo-surface"><StatePanel state="forbidden" title="无权查看该教案" /></div>
      </div>
    </section>

    <section id="responsive" class="style-section">
      <SectionHeader title="响应式与无障碍" description="断点与检查项；焦点、对比度与 reduced-motion 都有自动化或人工证据。" meta="1440 / 1280 / 390" />
      <div class="responsive-grid">
        <table class="scale-table">
          <caption class="sr-only">断点</caption>
          <thead><tr><th scope="col">视口</th><th scope="col">行为</th></tr></thead>
          <tbody>
            <tr><td>≥1100</td><td>228px 侧栏展开；3D 与右侧栏并排</td></tr>
            <tr><td>900–1099</td><td>侧栏抽屉；3D 降级为 2D 剖面</td></tr>
            <tr><td>640–899</td><td>单列；表格容器内横向滚动</td></tr>
            <tr><td>&lt;640</td><td>抽屉 280px；按钮不重叠；隐藏次要元信息</td></tr>
          </tbody>
        </table>
        <ul class="a11y-list">
          <li>正文与次文字对比度 ≥4.5:1，单测锁定。</li>
          <li>焦点环 2px 实色松绿；Tab 顺序从跳过链接开始。</li>
          <li>图标按钮有 aria-label；状态不只靠颜色。</li>
          <li>3D canvas 不承载唯一信息，结构清单可键盘阅读。</li>
          <li>reduced-motion 下关闭自动旋转、入场与图表动画。</li>
        </ul>
      </div>
    </section>

    <section class="style-section style-section--last">
      <SectionHeader title="验收记录" description="反馈写入 docs/frontend/review-notes.md；通过后由用户签字冻结 v1.1。" meta="待确认" />
      <div class="review-links">
        <p><span class="mono">docs/frontend/ui-style-spec.md</span> 设计令牌与 3D 规范</p>
        <p><span class="mono">docs/frontend/component-acceptance.md</span> 组件与四态清单</p>
        <p><span class="mono">docs/frontend/review-notes.md</span> 本轮反馈表</p>
      </div>
      <p v-if="isDev" class="dev-note">本页只在 DEV 注册，生产构建不包含演示数据与预览路由。</p>
    </section>
  </div>
</template>

<style scoped>
.styleguide {
  gap: 30px;
  max-width: 1400px;
}

.styleguide-meta {
  margin-top: 6px;
  color: var(--lpp-text-muted);
  font-size: var(--lpp-font-xs);
}

.style-tabs {
  position: sticky;
  top: var(--lpp-commandbar);
  z-index: 10;
  display: flex;
  align-items: center;
  gap: 2px;
  padding: 7px 0;
  margin: 0 -4px;
  border-bottom: 1px solid var(--lpp-border);
  background: var(--lpp-canvas);
  overflow-x: auto;
}

.style-tabs a {
  padding: 5px 9px;
  border-radius: var(--lpp-radius-control);
  color: var(--lpp-text-muted);
  font-size: var(--lpp-font-xs);
  text-decoration: none;
  white-space: nowrap;
}

.style-tabs a:hover {
  background: var(--lpp-nav-hover);
  color: var(--lpp-text);
  text-decoration: none;
}

.style-tabs__spacer {
  flex: 1;
}

.style-tabs__note {
  color: var(--lpp-text-muted);
  font-family: var(--lpp-mono);
  font-size: 12px;
  white-space: nowrap;
}

.style-section {
  scroll-margin-top: calc(var(--lpp-commandbar) + 12px);
}

.style-section--last {
  padding-bottom: 12px;
}

.principle-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0;
  border-top: 1px solid var(--lpp-border);
  border-bottom: 1px solid var(--lpp-border);
}

.principle-grid article {
  padding: 14px 18px;
  border-right: 1px solid var(--lpp-border);
}

.principle-grid article:first-child {
  padding-left: 0;
}

.principle-grid article:last-child {
  border-right: 0;
}

.principle-grid h3 {
  font-size: var(--lpp-font-sm);
  font-weight: 600;
}

.principle-grid p {
  margin-top: 4px;
  color: var(--lpp-text-muted);
  font-size: var(--lpp-font-xs);
  line-height: 1.6;
}

.ref-table,
.scale-table {
  width: 100%;
  border-collapse: collapse;
  font-size: var(--lpp-font-xs);
  text-align: left;
}

.ref-table {
  margin-top: 16px;
}

.ref-table th,
.ref-table td,
.scale-table th,
.scale-table td {
  padding: 7px 10px;
  border-bottom: 1px solid var(--lpp-border);
  vertical-align: top;
}

.ref-table th,
.scale-table th {
  color: var(--lpp-text-muted);
  font-weight: 600;
  border-bottom-color: var(--lpp-border-strong);
}

.ref-table td:first-child {
  color: var(--lpp-text);
  font-weight: 600;
  white-space: nowrap;
}

.swatch-grid {
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: 10px;
}

.swatch-grid .swatch {
  height: 62px;
}

.contrast-table {
  margin-top: 18px;
  border-top: 1px solid var(--lpp-border);
}

.contrast-head,
.contrast-row {
  display: grid;
  grid-template-columns: 180px minmax(0, 1fr) 90px;
  gap: 12px;
  padding: 6px 0;
  border-bottom: 1px solid var(--lpp-border);
  font-size: var(--lpp-font-xs);
}

.contrast-head {
  color: var(--lpp-text-muted);
  font-weight: 600;
  border-bottom-color: var(--lpp-border-strong);
}

.contrast-row .mono {
  color: var(--lpp-text-muted);
}

.contrast-row .is-pass {
  color: var(--lpp-success);
  font-weight: 600;
}

.type-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.2fr) minmax(0, 1fr);
  gap: 28px;
}

.type-specimens {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.type-specimens > div {
  padding-bottom: 8px;
  border-bottom: 1px dashed var(--lpp-border);
}

.type-specimens > div:last-child {
  border-bottom: 0;
}

.spec-label {
  color: var(--lpp-text-muted);
  font-size: var(--lpp-font-xs);
}

.scale-tables {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.demo-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.demo-surface {
  padding: 14px;
  border: 1px solid var(--lpp-border);
  border-radius: var(--lpp-radius-card);
  background: var(--lpp-surface);
}

.demo-surface h3 {
  margin-bottom: 10px;
  color: var(--lpp-text-muted);
  font-size: var(--lpp-font-xs);
  font-weight: 600;
}

.demo-surface--wide {
  grid-column: span 2;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0 16px;
}

.upload-note {
  margin-top: 8px;
}

.demo-toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: flex-end;
  gap: 12px;
  margin-bottom: 10px;
}

.table-title {
  color: var(--lpp-text);
  font-size: var(--lpp-font-sm);
  font-weight: 500;
}

.ledger-demo {
  margin-top: 18px;
}

.metric-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 10px;
  margin-top: 14px;
}

.data-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  margin-top: 16px;
}

.chart-surface {
  margin-top: 14px;
  padding: 8px 10px 2px;
  border: 1px solid var(--lpp-border);
  border-radius: var(--lpp-radius-card);
  background: var(--lpp-surface);
}

.structure-toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 10px;
}

.structure-toolbar .muted {
  font-size: var(--lpp-font-xs);
}

.structure-note {
  margin-top: 8px;
  font-size: var(--lpp-font-xs);
}

.state-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.state-grid .demo-surface {
  min-height: 200px;
}

.responsive-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  gap: 24px;
}

.a11y-list {
  margin: 0;
  padding: 0;
  list-style: none;
  font-size: var(--lpp-font-xs);
  line-height: 1.7;
}

.a11y-list li {
  padding: 6px 0;
  border-bottom: 1px dashed var(--lpp-border);
}

.a11y-list li::before {
  content: '✓';
  margin-right: 7px;
  color: var(--lpp-success);
  font-weight: 700;
}

.review-links {
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: var(--lpp-font-xs);
}

.review-links .mono {
  margin-right: 6px;
  color: var(--lpp-primary);
}

.dev-note {
  margin-top: 12px;
  color: var(--lpp-text-muted);
  font-size: 12px;
}

@media (max-width: 1100px) {
  .swatch-grid {
    grid-template-columns: repeat(4, minmax(0, 1fr));
  }

  .principle-grid,
  .type-grid,
  .responsive-grid {
    grid-template-columns: minmax(0, 1fr);
  }

  .principle-grid article {
    padding-left: 0;
    border-right: 0;
    border-bottom: 1px solid var(--lpp-border);
  }

  .principle-grid article:last-child {
    border-bottom: 0;
  }
}

@media (max-width: 900px) {
  .demo-grid,
  .data-grid,
  .state-grid {
    grid-template-columns: minmax(0, 1fr);
  }

  .demo-surface--wide {
    grid-column: auto;
  }

  .form-grid {
    grid-template-columns: minmax(0, 1fr);
  }
}

@media (max-width: 767px) {
  .style-tabs {
    flex-wrap: wrap;
    row-gap: 2px;
    margin: 0 -14px;
    padding: 7px 14px;
    overflow: visible;
  }

  .style-tabs__spacer,
  .style-tabs__note {
    display: none;
  }

  .swatch-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .contrast-head,
  .contrast-row {
    grid-template-columns: minmax(0, 1fr) 70px;
  }

  .contrast-head span:nth-child(2),
  .contrast-row span:nth-child(2) {
    display: none;
  }
}
</style>
