# -*- coding: utf-8 -*-
"""请求/响应 DTO：只做字段形状，不做业务判断。"""
from __future__ import annotations

from typing import Any

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.domain import report_rules, roles, task_rules, user_rules

#: 查询参数/响应里可用的枚举：从 domain 常量派生，避免路由里再写字符串字面量
TaskStatus = Literal[tuple(sorted(task_rules.TASK_RANK))]
TaskQuadrant = Literal[tuple(sorted(task_rules.QUADRANTS))]
ReviewStatus = Literal[tuple(sorted(report_rules.ALLOWED_STATUS))]
RoleName = Literal[tuple(roles.ROLES)]
Severity = Literal[tuple(sorted(report_rules.ALLOWED_SEVERITY))]


class LoginPayload(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=128)


class RegisterPayload(BaseModel):
    # 长度取 domain 常量：契约/OpenAPI 与 user_rules.validate 必须同一口径（R4-10）
    username: str = Field(
        min_length=user_rules.USERNAME_MIN,
        max_length=user_rules.USERNAME_MAX,
        pattern=r"^[A-Za-z0-9_.-]+$",
    )
    displayName: str = Field(min_length=1, max_length=user_rules.DISPLAY_NAME_MAX)
    password: str = Field(min_length=8, max_length=128)


class TokenPayload(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=128)


class UserOut(BaseModel):
    id: int
    username: str
    displayName: str
    role: str
    roleLabel: str
    # /me 与登录响应还要带这两个字段，缺了前端会拿不到"待改密/教研组"
    mustChangePassword: bool = False
    group: str = ""


class TokenOut(BaseModel):
    accessToken: str
    tokenType: str
    expiresIn: int
    expiresAt: str
    user: UserOut


class LoginOut(TokenOut):
    """网页登录比换令牌多一个 CSRF token（Cookie 会话要用）。"""

    csrfToken: str


class AuthMeOut(BaseModel):
    user: UserOut
    auth: str



def user_payload(user: dict[str, Any]) -> dict[str, Any]:
    role = str(user.get("role") or "")
    return {
        "id": int(user.get("id") or 0),
        "username": str(user.get("username") or ""),
        "displayName": str(user.get("display_name") or ""),
        "role": role,
        "roleLabel": roles.ROLE_LABELS.get(role, role),
        # 建号/重置后为 True：前端应强制先改密（BS-05）
        "mustChangePassword": bool(user.get("must_change_password")),
        # 教研组：组长/组内可见范围依赖它，缺了前端只能显示空
        "group": str(user.get("group_name") or ""),
    }


class TaskItem(BaseModel):
    taskId: int
    course: str
    week: int
    session: int
    title: str
    className: str = ""
    dueDate: str | None = None
    status: TaskStatus
    ownerId: int
    teacher: str | None = None
    overdue: bool = False
    createdAt: str | None = None
    quadrant: TaskQuadrant
    boardPosition: int = 0
    boardVersion: int = 0
    discardedAt: str | None = None
    discarded: bool = False
    canEdit: bool = False


class TaskPage(BaseModel):
    items: list[TaskItem]
    page: int
    pageSize: int
    total: int


class TaskBoard(BaseModel):
    items: list[TaskItem]
    total: int
    counts: dict[str, int]
    generatedAt: str


class PlanListItem(BaseModel):
    planId: int
    contentTitle: str
    course: str
    week: int
    session: int
    ownerId: int
    teacher: str | None = None
    versionNo: int | None = None
    planHash: str | None = None
    reviewStatus: str | None = None
    reviewRound: int | None = None
    versionCreatedAt: str | None = None


class PlanPage(BaseModel):
    # 列表不产出 planId（R4-08）：之前模型给默认值，响应里恒为 null，是噪声字段
    items: list[PlanListItem]
    page: int = 1
    pageSize: int = 20
    total: int


class PlanVersionOut(BaseModel):
    # 版本链里还带 status/round/reportSha256 等字段；先保留额外键，避免 response_model 静默吞字段
    model_config = ConfigDict(extra="allow")

    versionNo: int
    planHash: str
    engineVersion: str | None = None
    createdAt: str | None = None
    # 详情接口带完整 content；版本链只有元信息，所以这里可空
    content: dict[str, Any] | None = None
    source: str | None = None
    review: dict[str, Any] | None = None
    # 版本链（GET /plans/{id}/versions）每项都带这三个键；详情 currentVersion 没有则落 null
    round: int | None = None
    status: str | None = None
    reportSha256: str | None = None


class PlanDetailOut(BaseModel):
    plan: PlanListItem
    currentVersion: PlanVersionOut | None = None
    latestReview: dict[str, Any] | None = None


class PlanVersionPage(BaseModel):
    planId: int | None = None
    items: list[PlanVersionOut]
    # 版本链不分页，total 与服务层同口径（曾因模型漏声明被 response_model 静默吞掉）
    total: int


class ReviewEvidence(BaseModel):
    model_config = ConfigDict(extra="allow")

    complete: bool = False
    passed: int = 0
    total: int = 0
    gaps: list[Any] = []
    # 详情响应里带逐项证据（key/ok/reason），列表只有汇总
    items: list[dict[str, Any]] = []


class ReviewItem(BaseModel):
    # 审查列表的真实键以 report_rules/derive_status 为准，额外键先保留
    model_config = ConfigDict(extra="allow")

    reviewId: int
    planId: int
    # 导出中心只接受教案版本 ID，列表必须把它带出来（列表与详情同源）
    planVersionId: int
    versionNo: int | None = None
    round: int | None = None
    # 状态不收紧成枚举：历史库与"报告异常"分支会产出白名单外状态，收紧会 500
    status: str
    reviewerMode: str | None = None
    reportSha256: str | None = None
    reviewedAt: str | None = None
    teacher: str | None = None
    contentTitle: str | None = None
    course: str | None = None
    week: int | None = None
    session: int | None = None
    evidence: ReviewEvidence | None = None
    # 乐观可导出判定，仅用于按钮默认态；最终门禁在 export_service
    exportable: bool = False


class ReviewPage(BaseModel):
    items: list[ReviewItem]
    page: int = 1
    pageSize: int = 20
    total: int


class ReviewRef(BaseModel):
    """详情里的 review 与列表项形状不同（少了派生字段、多了报告相关字段）。"""

    model_config = ConfigDict(extra="allow")

    reviewId: int | None = None
    planId: int | None = None
    planVersionId: int
    versionNo: int | None = None
    round: int | None = None
    status: str | None = None
    reviewedAt: str | None = None
    reportSha256: str | None = None
    teacher: str | None = None
    contentTitle: str | None = None
    # 详情响应实测带课程/周次/课次（此前靠 extra=allow 透传，生成类型里没有）
    course: str | None = None
    week: int | None = None
    session: int | None = None


class ReviewDetailOut(BaseModel):
    model_config = ConfigDict(extra="allow")

    review: ReviewRef | None = None
    # 坏报告时 report 为 None，evidence.gaps 会标 report_unreadable
    report: dict[str, Any] | None = None
    findings: list[dict[str, Any]] = []
    overrides: list[dict[str, Any]] = []
    # 修复历史此前只在 extra=allow 里透传，生成类型看不到（R4-15）
    repairHistory: list[dict[str, Any]] = []
    evidence: ReviewEvidence | None = None


class MetricOut(BaseModel):
    """统计指标：比率型无 unit（0–1），耗时等带 unit；sampleInsufficient 表示样本 <5。"""

    model_config = ConfigDict(extra="allow")

    key: str
    label: str
    # 耗时类指标的分子是分钟（可能是小数），所以用 float 而不是 int
    numerator: float = 0
    denominator: float = 0
    value: float | None = None
    unit: str = ""
    available: bool = True
    sampleInsufficient: bool = False
    basis: dict[str, int] | None = None
    # 每个指标自带生效筛选（list 或 summary 的 filters 是同一份口径），此前靠 extra=allow 透传
    filters: dict[str, Any] = {}


class StatsSummaryOut(BaseModel):
    model_config = ConfigDict(extra="allow")

    metrics: list[MetricOut]
    filters: dict[str, Any] = {}
    scope: str = "own"


class StatRecordOut(BaseModel):
    model_config = ConfigDict(extra="allow")

    planId: int
    reviewId: int | None = None
    contentTitle: str | None = None
    course: str | None = None
    week: int | None = None
    session: int | None = None
    teacher: str | None = None
    versionNo: int | None = None
    reviewStatus: str | None = None
    structureOk: bool | None = None
    evidenceOk: bool | None = None
    openBlocking: int | None = None
    createdAt: str | None = None


class StatRecordPage(BaseModel):
    items: list[StatRecordOut]
    page: int = 1
    pageSize: int = 20
    total: int
    # 与 /stats/summary 同口径：回显生效的筛选与范围，便于前端标注"当前看的是哪些数据"
    filters: dict[str, Any] = {}
    scope: str = ""
