export type Role = 'teacher' | 'lead' | 'admin'

export interface User {
  id: number
  username: string
  displayName: string
  role: Role
  roleLabel?: string
  group?: string
}

export interface LoginResult {
  user: User
  csrfToken: string
}

export interface Paged<T> {
  items: T[]
  page: number
  pageSize: number
  total: number
}

export interface PlanListItem {
  planId: number
  contentTitle: string
  course: string
  week: number
  session: number
  ownerId: number
  teacher: string
  versionNo: number
  planHash: string
  reviewStatus: string
  reviewRound: number
  versionCreatedAt: string
}

export interface PlanVersion {
  versionNo: number
  planHash: string
  engineVersion?: string
  createdAt: string
  content?: Record<string, unknown>
  round?: number
  status?: string
  reportSha256?: string
}

export interface PlanDetail {
  plan: PlanListItem
  currentVersion: PlanVersion | null
  latestReview: {
    round: number
    status: string
    reviewerMode?: string | null
    reportSha256: string
  } | null
}

export interface DiffChange {
  path: string
  before: unknown
  after: unknown
}

export interface DiffResult {
  planId: number
  fromVersion: number
  toVersion: number
  changes: DiffChange[]
  count: number
}

export interface EvidenceItem {
  key: string
  label: string
  ok: boolean
  reason: string
}

export interface Evidence {
  items: EvidenceItem[]
  complete: boolean
  passed: number
  total: number
  gaps: string[]
}

export interface ReviewHeader {
  reviewId: number
  planId: number
  versionNo: number
  round: number
  status: string
  reviewerMode: string
  reportSha256: string
  reviewedAt: string
  teacher: string
  contentTitle: string
  course: string
  week: number
  session: number
}

export interface ReviewListItem extends ReviewHeader {
  evidence: Pick<Evidence, 'complete' | 'passed' | 'total' | 'gaps'>
}

export interface Finding {
  id: string
  severity: 'blocker' | 'major' | 'minor' | string
  status: 'open' | 'waived' | 'accepted' | string
  hypothesis?: string
  evidence?: string[]
  affectedPaths?: string[]
  repair?: string
}

export interface ReviewDetail {
  review: ReviewHeader
  report: Record<string, unknown>
  findings: Finding[]
  overrides: Record<string, unknown>[]
  repairHistory: Record<string, unknown>[]
  evidence: Evidence
}

export interface ExportItem {
  planVersionId: number
  exportId?: number
  status: 'succeeded' | 'failed'
  code?: string
  message?: string
  engineVersion?: string
  docxSha256?: string
  planHash?: string
  reportHash?: string
}

export interface ExportJob {
  exportId: number
  planVersionId: number
  planId: number
  versionNo: number
  contentTitle: string
  status: string
  engineVersion: string
  docxSha256: string
  planHash: string
  reportHash: string
  createdAt: string
}

export interface Metric {
  key: string
  label: string
  numerator: number
  denominator: number
  value: number | null
  unit: string
  available: boolean
  filters: Record<string, unknown>
}

export interface StatsSummary {
  metrics: Metric[]
  filters: Record<string, unknown>
  scope: 'own' | 'group' | 'all'
}

export type TaskQuadrant =
  | 'urgent_important'
  | 'important_not_urgent'
  | 'urgent_not_important'
  | 'not_urgent_not_important'

export interface TaskItem {
  taskId: number
  course: string
  week: number
  session: number
  title: string
  className: string
  dueDate: string | null
  status: 'draft' | 'reviewing' | 'passed' | 'exported' | string
  ownerId: number
  teacher?: string
  quadrant: TaskQuadrant
  boardPosition: number
  boardVersion: number
  discarded: boolean
  discardedAt: string | null
  canEdit: boolean
  overdue: boolean
  createdAt: string
}

export interface TaskBoard {
  items: TaskItem[]
  total: number
  counts: Record<TaskQuadrant, number>
  generatedAt: string
}

export interface SampleItem {
  sampleId: number
  course: string
  week: number
  session: number
  title: string
  planHash: string
  valid: boolean
  ruleVersion: string
  complete: boolean
}

export interface AuditItem {
  id: number
  actor: { id: number | null; name: string; role: string; group: string }
  action: string
  targetType: string
  targetId: string
  detail: Record<string, unknown>
  ip: string
  traceId: string
  beforeHash: string
  afterHash: string
  createdAt: string
}

export interface UserItem {
  userId: number
  username: string
  displayName: string
  group: string
  role: Role
  active: boolean
  mustChangePassword: boolean
  createdAt: string
}

export interface EngineInfo {
  engineAvailable: boolean
  versions: {
    engineVersion?: string
    rulesVersion?: string
    rubricVersion?: string
    reviewSchemaVersion?: string
    exampleCount?: number
    status?: string
  }
  contractVersion: string
  supportedContractVersions: string[]
}
