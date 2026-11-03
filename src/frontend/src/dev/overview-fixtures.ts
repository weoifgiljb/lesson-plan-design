/**
 * 仅 `/styleguide` 与结构组件测试使用的演示数据；真实系统页面不得引用本文件。
 *
 * 约束：
 * - 不参与业务页面、不发请求、不写入 store；
 * - 路由只在 DEV 注册，生产构建不会包含本文件；
 * - 教师姓名与队列均为虚构；课程标题来自校标样例，不含学生信息；
 * - 指标只展示当前口径，不编造环比、趋势与排名。
 */
import type { DiffChange, EvidenceItem, Metric } from '@/api/models'
import type { LessonStructure } from '@/components/structure/model'

export interface DemoPlan {
  id: number
  title: string
  course: string
  week: number
  session: number
  teacher: string
  version: number
  evidencePassed: number
  evidenceTotal: number
  status: string
  updatedAt: string
  scope: 'mine' | 'review'
}

export interface DemoTodo {
  id: string
  kind: '审查' | '导出' | '任务'
  title: string
  detail: string
  due: string
  overdue?: boolean
}

export interface DemoActivity {
  id: string
  time: string
  text: string
  meta: string
  tone: 'success' | 'warning' | 'muted'
}

export const DEMO_EVIDENCE: EvidenceItem[] = [
  { key: 'hash_match', label: '哈希匹配', ok: true, reason: '' },
  { key: 'round_continuous', label: '轮次连续', ok: true, reason: '' },
  {
    key: 'overrides_complete',
    label: '放行完整',
    ok: false,
    reason: 'waived 问题缺少对应放行记录：AR-2',
  },
  { key: 'independence_valid', label: '审校方式合规', ok: true, reason: '' },
  { key: 'status_consistent', label: '状态一致', ok: true, reason: '' },
]

export const DEMO_STRUCTURE: LessonStructure = {
  title: 'C 语言概述',
  course: '信息技术',
  week: 2,
  session: 1,
  planHash: '8f2c4d7a91e3',
  plannedHours: 1,
  goals: {
    knowledge: '了解 C 语言的产生、发展与特点',
    ability: '能说出 C 语言在典型任务中的适用范围',
    quality: '建立自主探究与规范书写意识',
  },
  steps: [
    {
      key: 'introduction',
      order: 1,
      title: '复习与导入新课',
      minutes: 5,
      group: 'opening',
      evidence: '课前任务单完成率',
    },
    {
      key: 'learningGoals',
      order: 2,
      title: '明确学习目标',
      minutes: 3,
      group: 'opening',
    },
    {
      key: 'knowledgeLearning',
      order: 3,
      title: '知识学习',
      minutes: 12,
      group: 'learning',
      evidence: '课堂提问记录',
    },
    {
      key: 'taskImplementation',
      order: 4,
      title: '工作任务实施',
      minutes: 15,
      group: 'practice',
      evidence: '提交 C04_学号.c 与运行截图',
    },
    {
      key: 'assessment',
      order: 5,
      title: '课程考核',
      minutes: 5,
      group: 'assessment',
      evidence: '随堂测验',
    },
    {
      key: 'summary',
      order: 6,
      title: '课堂小结',
      minutes: 3,
      group: 'closing',
    },
    {
      key: 'homework',
      order: 7,
      title: '布置作业',
      minutes: 2,
      group: 'closing',
    },
    {
      key: 'reflection',
      order: 8,
      title: '教学反思',
      minutes: 0,
      group: 'closing',
    },
  ],
  evidence: DEMO_EVIDENCE,
}

export const DEMO_METRICS: Metric[] = [
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

export const DEMO_LEDGER_KEYS = [
  'evidence_rate',
  'structure_rate',
  'defect_density',
  'export_seconds',
]

export const DEMO_PLANS: DemoPlan[] = [
  {
    id: 1,
    title: 'C 语言概述',
    course: '信息技术',
    week: 2,
    session: 1,
    teacher: '林晓岚',
    version: 2,
    evidencePassed: 4,
    evidenceTotal: 5,
    status: 'pending_reviewer',
    updatedAt: '10:24',
    scope: 'review',
  },
  {
    id: 2,
    title: '变量与数据类型',
    course: '信息技术',
    week: 3,
    session: 2,
    teacher: '周予安',
    version: 1,
    evidencePassed: 3,
    evidenceTotal: 5,
    status: 'needs_repair',
    updatedAt: '09:58',
    scope: 'mine',
  },
  {
    id: 3,
    title: '循环结构',
    course: '信息技术',
    week: 4,
    session: 1,
    teacher: '陈嘉禾',
    version: 3,
    evidencePassed: 5,
    evidenceTotal: 5,
    status: 'passed',
    updatedAt: '昨天',
    scope: 'review',
  },
  {
    id: 4,
    title: '数组',
    course: '信息技术',
    week: 5,
    session: 2,
    teacher: '许知远',
    version: 1,
    evidencePassed: 4,
    evidenceTotal: 5,
    status: 'pending_reviewer',
    updatedAt: '昨天',
    scope: 'review',
  },
  {
    id: 5,
    title: '函数与模块化',
    course: '信息技术',
    week: 6,
    session: 1,
    teacher: '林晓岚',
    version: 2,
    evidencePassed: 5,
    evidenceTotal: 5,
    status: 'passed_with_override',
    updatedAt: '10-26',
    scope: 'mine',
  },
  {
    id: 6,
    title: '指针初步',
    course: '信息技术',
    week: 7,
    session: 2,
    teacher: '周予安',
    version: 1,
    evidencePassed: 2,
    evidenceTotal: 5,
    status: 'structure_invalid',
    updatedAt: '10-26',
    scope: 'mine',
  },
  {
    id: 7,
    title: '结构体与链表',
    course: '信息技术',
    week: 8,
    session: 1,
    teacher: '陈嘉禾',
    version: 2,
    evidencePassed: 5,
    evidenceTotal: 5,
    status: 'passed',
    updatedAt: '10-25',
    scope: 'review',
  },
  {
    id: 8,
    title: '文件读写',
    course: '信息技术',
    week: 9,
    session: 2,
    teacher: '许知远',
    version: 1,
    evidencePassed: 3,
    evidenceTotal: 5,
    status: 'needs_repair',
    updatedAt: '10-25',
    scope: 'mine',
  },
]

export const DEMO_TODOS: DemoTodo[] = [
  {
    id: 'review-loop',
    kind: '审查',
    title: '循环结构 · 第 2 轮',
    detail: '证据 5/5，等待教研组长确认',
    due: '今天 16:00',
  },
  {
    id: 'export-c',
    kind: '导出',
    title: 'C 语言概述 · 第 2 版',
    detail: '门禁通过，产物哈希已生成',
    due: '今天 14:30',
  },
  {
    id: 'task-array',
    kind: '任务',
    title: '数组 · 第 8 周',
    detail: '任务包尚未提交',
    due: '已逾期 2 天',
    overdue: true,
  },
]

export const DEMO_ACTIVITIES: DemoActivity[] = [
  {
    id: 'a1',
    time: '10:24',
    text: '审查通过《C 语言概述》第 2 轮',
    meta: 'planHash 8f2c…a91',
    tone: 'success',
  },
  {
    id: 'a2',
    time: '09:58',
    text: '导出完成 2024-C语言概述-v2.docx',
    meta: 'SHA-256 3a91…c07',
    tone: 'success',
  },
  {
    id: 'a3',
    time: '08:40',
    text: '契约包入库《数组》',
    meta: '结构校验 · 哈希匹配',
    tone: 'muted',
  },
  {
    id: 'a4',
    time: '昨天',
    text: '《指针初步》结构校验未通过',
    meta: '缺「知识目标」与第 4 步活动',
    tone: 'warning',
  },
]

export const DEMO_DIFFS: DiffChange[] = [
  { path: 'activityFlow.summary', before: '旧的小结', after: '修订后的课堂小结' },
  {
    path: 'knowledgeGoals',
    before: '掌握基本操作',
    after: '掌握基本操作并能独立完成 2 个任务',
  },
]

export const DEMO_REVIEW_DETAIL = {
  round: 2,
  status: 'pending_reviewer',
  reviewerMode: 'adversarial',
  reportSha256: 'c41d8e0b7a2f',
}
