// openapi-sha256: ed0c024db5f23dc9df0319b55c2d7b02341452af58447f42d6efdaec6ab2de6b
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
  planId?: number | null
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

export interface PasswordChange {
  oldPassword: string
  newPassword: string
}

export interface RegisterPayload {
  username: string
  displayName: string
  password: string
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

export interface TaskMove {
  quadrant: string
  position: number
  boardVersion: number
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
