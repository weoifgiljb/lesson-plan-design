# -*- coding: utf-8 -*-
"""错误码目录：码 → HTTP 状态 + 中文说明 + 出现场景，是**唯一来源**。

新增/调整错误码只改这一个文件：
- 业务层抛 `AppError("<CODE>")`，HTTP 状态由本表推导；
- 路由的 `responses` 声明用 `app.api.responses.error_responses()` 从本表生成；
- `docs/api/contract.v1.json` 的 `errorCodes` 由 `scripts/sync_contract_errors.py` 按本表同步，
  `tests/test_errors_api.py` 会校验两边一致。
"""
from __future__ import annotations

CATALOG: dict[str, dict[str, object]] = {
    "AUTH_REQUIRED": {
        "http": 401,
        "zh": "未登录或登录已失效",
        "scene": "缺少/过期的会话 Cookie 或 Bearer 令牌、用户名口令错误",
    },
    "FORBIDDEN": {
        "http": 403,
        "zh": "无权限执行该操作",
        "scene": "角色不允许、归属校验失败、CSRF 校验失败、自助注册已关闭",
    },
    "USERNAME_TAKEN": {
        "http": 409,
        "zh": "用户名已被占用",
        "scene": "注册或建号时用户名重复",
    },
    "REGISTRATION_CLOSED": {
        "http": 403,
        "zh": "平台已关闭自助注册",
        "scene": "LPP_ALLOW_REGISTRATION=0 时的自助注册请求",
    },
    "PASSWORD_CHANGE_REQUIRED": {
        "http": 403,
        "zh": "请先修改初始口令",
        "scene": "账号 must_change_password=1 时访问改密以外的业务接口",
    },
    "NOT_FOUND": {
        "http": 404,
        "zh": "资源不存在",
        "scene": "id 无效或对象已软删除",
    },
    "CONFLICT_STALE": {
        "http": 409,
        "zh": "数据已变化，请刷新后重试",
        "scene": "乐观锁/唯一键冲突（重复导入、重复建课、用户名已存在）",
    },
    "CONFLICT_DELETED": {
        "http": 409,
        "zh": "对象已删除",
        "scene": "带 planId 推送时目标教案已软删除",
    },
    "HASH_MISMATCH": {
        "http": 422,
        "zh": "哈希校验不一致",
        "scene": "契约包/样例/产物的 planHash 或 sha256 与登记值不符",
    },
    "SCHEMA_UNSUPPORTED": {
        "http": 422,
        "zh": "不支持的结构版本",
        "scene": "schemaVersion / rubricVersion 超出支持范围",
    },
    "STRUCTURE_INVALID": {
        "http": 422,
        "zh": "结构校验未通过",
        "scene": "教案字段缺失或类型错误",
    },
    "REPORT_INCONSISTENT": {
        "http": 422,
        "zh": "审查报告与教案不一致",
        "scene": "轮次跳号、报告哈希与版本不匹配、证据链断裂",
    },
    "MEDIA_MISSING": {
        "http": 422,
        "zh": "引用的媒体文件缺失",
        "scene": "教案声明的截图/附件未随包上传或本地已丢失",
    },
    "PAYLOAD_REJECTED": {
        "http": 422,
        "zh": "请求内容不符合要求",
        "scene": "字段校验失败、口令强度不足、路径越界",
    },
    "UNSUPPORTED_MEDIA": {
        "http": 415,
        "zh": "不支持的上传类型",
        "scene": "上传文件不是 zip/json 等允许的类型",
    },
    "PAYLOAD_TOO_LARGE": {
        "http": 413,
        "zh": "上传内容超过大小上限",
        "scene": "契约包 50MB、样例 2MB 等限制",
    },
    "RATE_LIMITED": {
        "http": 429,
        "zh": "请求过于频繁",
        "scene": "登录连续失败锁定、后续可扩展的限流策略",
    },
    "SERVICE_UNAVAILABLE": {
        "http": 503,
        "zh": "服务暂不可用",
        "scene": "数据库结构未对齐（旧库需先运行 repair_schema.py）或磁盘不可写",
    },
    "INTERNAL": {
        "http": 500,
        "zh": "服务器内部错误",
        "scene": "未归类的异常（响应体不含堆栈与服务器路径）",
    },
}

#: 码 → HTTP 状态（闸门 BA-10/BC-05 要求模块级字面量表；
#: 与 CATALOG 的一致性由 tests/test_errors_api.py 断言）
ERROR_CODES = {
    "AUTH_REQUIRED": 401,
    "FORBIDDEN": 403,
    "USERNAME_TAKEN": 409,
    "REGISTRATION_CLOSED": 403,
    "PASSWORD_CHANGE_REQUIRED": 403,
    "NOT_FOUND": 404,
    "CONFLICT_STALE": 409,
    "CONFLICT_DELETED": 409,
    "HASH_MISMATCH": 422,
    "SCHEMA_UNSUPPORTED": 422,
    "STRUCTURE_INVALID": 422,
    "REPORT_INCONSISTENT": 422,
    "MEDIA_MISSING": 422,
    "PAYLOAD_REJECTED": 422,
    "UNSUPPORTED_MEDIA": 415,
    "PAYLOAD_TOO_LARGE": 413,
    "RATE_LIMITED": 429,
    "SERVICE_UNAVAILABLE": 503,
    "INTERNAL": 500,
}


def http_of(code: str) -> int:
    return int(CATALOG[code]["http"])


def description_of(code: str) -> str:
    return str(CATALOG[code]["zh"])
