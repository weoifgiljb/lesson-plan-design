// openapi-sha256: 286b9ffd20e5c9738b9dd806a738d06d88b58af0e4025163859c58098874f1c2
// 由 scripts/gen_frontend_types.py 生成，请勿手改。

export interface BodyCreateSampleApiV1SamplesPost {
  file: string
}

export interface BodyImportPlanApiV1PlansImportPost {
  file: string
}

export interface BodySyncPushApiV1SyncPushPost {
  file: string
  baseHash?: string
}

export interface ExportRequest {
  planVersionIds: number[]
}

export interface HTTPValidationError {
  detail?: ValidationError[]
}

export interface LoginPayload {
  username: string
  password: string
}

export interface TaskCreate {
  course: string
  week: number
  session: number
  title: string
  className?: string
  dueDate?: string | null
}

export interface UserCreate {
  username: string
  displayName: string
  role: string
  password: string
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
export type LoginApiV1AuthLoginPostResponse = Record<string, unknown>
export type LogoutApiV1AuthLogoutPostResponse = Record<string, unknown>
export type CreateExportsApiV1ExportsPostResponse = Record<string, unknown>
export type ExportDetailApiV1ExportsExportIdGetResponse = Record<string, unknown>
export type DownloadExportApiV1ExportsExportIdDownloadGetResponse = Record<string, unknown>
export type HealthApiV1HealthGetResponse = Record<string, unknown>
export type MeApiV1MeGetResponse = Record<string, unknown>
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
export type EngineInfoApiV1SettingsEngineGetResponse = Record<string, unknown>
export type StatsSummaryApiV1StatsSummaryGetResponse = Record<string, unknown>
export type SyncHeadApiV1SyncHeadGetResponse = Record<string, unknown>
export type SyncPullApiV1SyncPullGetResponse = Record<string, unknown>
export type SyncPushApiV1SyncPushPostResponse = Record<string, unknown>
export type ListTasksApiV1TasksGetResponse = Record<string, unknown>
export type CreateTaskApiV1TasksPostResponse = Record<string, unknown>
export type TaskPackageApiV1TasksTaskIdPackageGetResponse = Record<string, unknown>
export type ListUsersApiV1UsersGetResponse = Record<string, unknown>
export type CreateUserApiV1UsersPostResponse = Record<string, unknown>
