// openapi-sha256: fc8fb1112a70586dd2bfdfd6db75e90afa68119664f1c72c33520d00856f8b62
// 由 scripts/gen_frontend_types.py 生成，请勿手改。

export interface AuthMeOut {
  user: UserOut
  auth: string
}

export interface BodyCreateSampleApiV1SamplesPost {
  file: string
}

export interface BodyImportPlanApiV1PlansImportPost {
  file: string
}

export interface BodySyncPushApiV1SyncPushPost {
  file: string
  baseHash?: string
  planId?: number | null
}

export interface ExportRequest {
  planVersionIds: number[]
}

export interface HTTPValidationError {
  detail?: ValidationError[]
}

export interface LoginOut {
  accessToken: string
  tokenType: string
  expiresIn: number
  expiresAt: string
  user: UserOut
  csrfToken: string
}

export interface LoginPayload {
  username: string
  password: string
}

export interface MetricOut {
  key: string
  label: string
  numerator?: number
  denominator?: number
  value?: number | null
  unit?: string
  available?: boolean
  sampleInsufficient?: boolean
  basis?: Record<string, number> | null
}

export interface PasswordChange {
  oldPassword: string
  newPassword: string
}

export interface PlanDetailOut {
  plan: PlanListItem
  currentVersion?: PlanVersionOut | null
  latestReview?: Record<string, unknown> | null
}

export interface PlanListItem {
  planId: number
  contentTitle: string
  course: string
  week: number
  session: number
  ownerId: number
  teacher?: string | null
  versionNo?: number | null
  planHash?: string | null
  reviewStatus?: string | null
  reviewRound?: number | null
  versionCreatedAt?: string | null
}

export interface PlanPage {
  planId?: number | null
  items: PlanListItem[]
  page?: number
  pageSize?: number
  total: number
}

export interface PlanVersionOut {
  versionNo: number
  planHash: string
  engineVersion?: string | null
  createdAt?: string | null
  content?: Record<string, unknown> | null
  source?: string | null
  review?: Record<string, unknown> | null
}

export interface PlanVersionPage {
  planId?: number | null
  items: PlanVersionOut[]
  total: number
}

export interface RegisterPayload {
  username: string
  displayName: string
  password: string
}

export interface ReviewDetailOut {
  review?: ReviewRef | null
  report?: Record<string, unknown> | null
  findings?: Record<string, unknown>[]
  overrides?: Record<string, unknown>[]
  evidence?: ReviewEvidence | null
}

export interface ReviewEvidence {
  complete?: boolean
  passed?: number
  total?: number
  gaps?: unknown[]
  items?: Record<string, unknown>[]
}

export interface ReviewItem {
  reviewId: number
  planId: number
  versionNo?: number | null
  round?: number | null
  status: string
  reviewerMode?: string | null
  reportSha256?: string | null
  reviewedAt?: string | null
  teacher?: string | null
  contentTitle?: string | null
  course?: string | null
  week?: number | null
  session?: number | null
  evidence?: ReviewEvidence | null
}

export interface ReviewPage {
  items: ReviewItem[]
  page?: number
  pageSize?: number
  total: number
}

export interface ReviewRef {
  reviewId?: number | null
  planId?: number | null
  versionNo?: number | null
  round?: number | null
  status?: string | null
  reviewedAt?: string | null
  reportSha256?: string | null
  teacher?: string | null
  contentTitle?: string | null
}

export interface StatRecordOut {
  planId: number
  reviewId?: number | null
  contentTitle?: string | null
  course?: string | null
  week?: number | null
  session?: number | null
  teacher?: string | null
  versionNo?: number | null
  reviewStatus?: string | null
  structureOk?: boolean | null
  evidenceOk?: boolean | null
  openBlocking?: number | null
  createdAt?: string | null
}

export interface StatRecordPage {
  items: StatRecordOut[]
  page?: number
  pageSize?: number
  total: number
  filters?: Record<string, unknown>
  scope?: string
}

export interface StatsSummaryOut {
  metrics: MetricOut[]
  filters?: Record<string, unknown>
  scope?: string
}

export interface TaskBoard {
  items: TaskItem[]
  total: number
  counts: Record<string, number>
  generatedAt: string
}

export interface TaskCreate {
  course: string
  week: number
  session: number
  title: string
  className?: string
  dueDate?: string | null
  status?: string | null
  quadrant?: string | null
}

export interface TaskItem {
  taskId: number
  course: string
  week: number
  session: number
  title: string
  className?: string
  dueDate?: string | null
  status: "draft" | "exported" | "passed" | "reviewing"
  ownerId: number
  teacher?: string | null
  overdue?: boolean
  createdAt?: string | null
  quadrant: "important_not_urgent" | "not_urgent_not_important" | "urgent_important" | "urgent_not_important"
  boardPosition?: number
  boardVersion?: number
  discardedAt?: string | null
  discarded?: boolean
  canEdit?: boolean
}

export interface TaskMove {
  quadrant: string
  position: number
  boardVersion: number
}

export interface TaskPage {
  items: TaskItem[]
  page: number
  pageSize: number
  total: number
}

export interface TokenOut {
  accessToken: string
  tokenType: string
  expiresIn: number
  expiresAt: string
  user: UserOut
}

export interface TokenPayload {
  username: string
  password: string
}

export interface UserCreate {
  username: string
  displayName: string
  role: string
  password: string
  group?: string
}

export interface UserOut {
  id: number
  username: string
  displayName: string
  role: string
  roleLabel: string
  mustChangePassword?: boolean
  group?: string
}

export interface ValidationError {
  loc: string | number[]
  msg: string
  type: string
  input?: unknown
  ctx?: Record<string, unknown>
}

export type ListAuditApiV1AuditGetResponse = Record<string, unknown>
export type ExportAuditApiV1AuditExportGetResponse = Record<string, unknown>
export type LoginApiV1AuthLoginPostResponse = Record<string, unknown>
export type LogoutApiV1AuthLogoutPostResponse = Record<string, unknown>
export type WhoamiApiV1AuthMeGetResponse = Record<string, unknown>
export type RegisterApiV1AuthRegisterPostResponse = Record<string, unknown>
export type TokenApiV1AuthTokenPostResponse = Record<string, unknown>
export type CreateExportsApiV1ExportsPostResponse = Record<string, unknown>
export type ExportDetailApiV1ExportsExportIdGetResponse = Record<string, unknown>
export type DownloadExportApiV1ExportsExportIdDownloadGetResponse = Record<string, unknown>
export type HealthApiV1HealthGetResponse = Record<string, unknown>
export type MeApiV1MeGetResponse = Record<string, unknown>
export type ChangePasswordApiV1MePasswordPostResponse = Record<string, unknown>
export type MetaApiV1MetaGetResponse = Record<string, unknown>
export type ListPlansApiV1PlansGetResponse = Record<string, unknown>
export type ImportPlanApiV1PlansImportPostResponse = Record<string, unknown>
export type DeletePlanApiV1PlansPlanIdDeleteResponse = Record<string, unknown>
export type PlanDetailApiV1PlansPlanIdGetResponse = Record<string, unknown>
export type PlanDiffApiV1PlansPlanIdDiffGetResponse = Record<string, unknown>
export type PlanVersionsApiV1PlansPlanIdVersionsGetResponse = Record<string, unknown>
export type ListReviewsApiV1ReviewsGetResponse = Record<string, unknown>
export type ReviewDetailApiV1ReviewsReviewIdGetResponse = Record<string, unknown>
export type ListSamplesApiV1SamplesGetResponse = Record<string, unknown>
export type CreateSampleApiV1SamplesPostResponse = Record<string, unknown>
export type SampleDetailApiV1SamplesSampleIdGetResponse = Record<string, unknown>
export type SampleDownloadApiV1SamplesSampleIdDownloadGetResponse = Record<string, unknown>
export type EngineInfoApiV1SettingsEngineGetResponse = Record<string, unknown>
export type StatsExportCsvApiV1StatsExportCsvGetResponse = Record<string, unknown>
export type StatsRecordsApiV1StatsRecordsGetResponse = Record<string, unknown>
export type StatsSummaryApiV1StatsSummaryGetResponse = Record<string, unknown>
export type SyncHeadApiV1SyncHeadGetResponse = Record<string, unknown>
export type SyncPullApiV1SyncPullGetResponse = Record<string, unknown>
export type SyncPushApiV1SyncPushPostResponse = Record<string, unknown>
export type ListTasksApiV1TasksGetResponse = Record<string, unknown>
export type CreateTaskApiV1TasksPostResponse = Record<string, unknown>
export type TaskBoardApiV1TasksBoardGetResponse = Record<string, unknown>
export type MoveTaskApiV1TasksTaskIdBoardPatchResponse = Record<string, unknown>
export type DiscardTaskApiV1TasksTaskIdDiscardPostResponse = Record<string, unknown>
export type TaskPackageApiV1TasksTaskIdPackageGetResponse = Record<string, unknown>
export type RestoreTaskApiV1TasksTaskIdRestorePostResponse = Record<string, unknown>
export type RollbackTaskApiV1TasksTaskIdRollbackPostResponse = Record<string, unknown>
export type ListUsersApiV1UsersGetResponse = Record<string, unknown>
export type CreateUserApiV1UsersPostResponse = Record<string, unknown>
