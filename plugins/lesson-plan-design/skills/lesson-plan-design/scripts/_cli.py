# -*- coding: utf-8 -*-
"""CLI 统一错误边界：stdout 只放结果，stderr 统一 JSON，退出码 0/1/2。"""
from __future__ import annotations

import argparse
import json
import sys


class CliError(Exception):
    def __init__(self, code: str, message: str, hint: str = "", exit_code: int = 1):
        super().__init__(message)
        self.code = code
        self.message = message
        self.hint = hint
        self.exit_code = exit_code


class JsonArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:  # type: ignore[override]
        raise CliError("USAGE", message, "运行 --help 查看参数", 2)


def emit_error(error: CliError) -> int:
    payload = {
        "ok": False,
        "error": {
            "code": error.code,
            "message": error.message,
            "hint": error.hint,
        },
    }
    print(json.dumps(payload, ensure_ascii=False), file=sys.stderr)
    return error.exit_code


def run_cli(main) -> int:
    try:
        return main()
    except CliError as exc:
        return emit_error(exc)
    except FileNotFoundError as exc:
        name = exc.filename or "指定文件"
        return emit_error(CliError("FILE_NOT_FOUND", f"文件不存在：{name}", "检查路径后重试"))
    except json.JSONDecodeError as exc:
        return emit_error(
            CliError("INVALID_JSON", f"JSON 解析失败：{exc.msg}", "检查 JSON 语法与编码")
        )
    except ValueError as exc:
        return emit_error(CliError("INVALID_INPUT", str(exc), "检查输入字段与取值"))
    except OSError as exc:
        return emit_error(CliError("IO_ERROR", str(exc), "检查文件或目录权限"))
    except Exception as exc:  # noqa: BLE001 - CLI 边界必须给稳定 JSON，不能抛 traceback
        return emit_error(CliError("INTERNAL", str(exc), "请把该错误反馈给维护者"))
