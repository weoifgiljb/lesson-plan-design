/**
 * 仅 `/styleguide` 组件预览使用的演示数据。
 *
 * 约束：
 * - 不参与任何业务页面、不发请求、不写入 store；
 * - 路由只在 DEV 注册，生产构建不会包含本文件；
 * - 数值只用于展示组件状态（密度、颜色、空态），不代表真实统计。
 */
import type { DiffChange, EvidenceItem, Metric } from '@/api/models'

export interface DemoPlanRow {
  id: number
  title: string
  course: string
  week: number
  session: number
  teacher: string
  status: string
  version: number
}

export const DEMO_PLANS: DemoPlanRow[] = [
  { id: 1, title: '示例课题 1', course: '示例课程', week: 2, session: 1, teacher: '示例教师 A', status: 'passed', version: 2 },
  { id: 2, title: '示例课题 2', course: '示例课程', week: 3, session: 2, teacher: '示例教师 B', status: 'needs_repair', version: 1 },
  { id: 3, title: '示例课题 3', course: '示例课程', week: 4, session: 1, teacher: '示例教师 A', status: 'pending_reviewer', version: 1 },
  { id: 4, title: '示例课题 4', course: '示例课程', week: 5, session: 2, teacher: '示例教师 C', status: 'passed_with_override', version: 3 },
  { id: 5, title: '示例课题 5', course: '示例课程', week: 6, session: 1, teacher: '示例教师 A', status: 'structure_invalid', version: 1 },
]

export const DEMO_EVIDENCE: EvidenceItem[] = [
  { key: 'hash_match', label: '哈希匹配', ok: true, reason: '' },
  { key: 'round_continuous', label: '轮次连续', ok: true, reason: '' },
  { key: 'overrides_complete', label: '放行完整', ok: false, reason: 'waived 问题缺少对应放行记录：AR-2' },
  { key: 'independence_valid', label: '审校方式合规', ok: true, reason: '' },
  { key: 'status_consistent', label: '状态一致', ok: true, reason: '' },
]

export const DEMO_DIFFS: DiffChange[] = [
  { path: 'activityFlow.summary', before: '旧的小结', after: '修订后的课堂小结' },
  { path: 'knowledgeGoals', before: '掌握基本操作', after: '掌握基本操作并能独立完成 2 个任务' },
]

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
