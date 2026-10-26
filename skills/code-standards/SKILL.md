---
name: code-standards
description: >
  组件化拆分与代码规范执行：新增模块、拆分大文件、消除重复逻辑、重构前定边界时使用。
  约束绝对路径、if 链、跨层依赖、重复错误边界、状态判断、测试夹具与模块体量。
  用户说重构、拆分、组件化、代码规范、去重、模块太大时使用。
---

# 组件化与代码规范

硬约束见 `.cursor/rules/code-standards.mdc` 与根目录 `AGENTS.md`；完整方案与排期见 `docs/代码规范与重构计划.md`。

## 何时使用

- 新增模块或功能，需要决定放在 domain / application / adapter 哪一层；
- 拆分 `lib.py`、`export_docx.py`、`mcp_server.py` 等大文件；
- 发现重复的 if 链、错误处理、状态判断、文本格式化、测试搭建；
- 代码评审发现模块过大、跨层 import、绝对路径。

## 工作流

1. **分类**：判断改动属于 domain（纯业务）、application（编排）还是 adapter（CLI/MCP/DOCX/hooks）。
2. **定边界**：写出输入、输出、禁止事项；domain 不 print、不 `sys.exit`、不读写环境。
3. **先测后搬**：补一个能证明现有行为的测试；重构只搬家，不改输出。
4. **保留门面**：`lib.py` 继续 re-export 旧 API；`export_docx.py` 保留 `export_docx`/`_split_key_points` 兼容；`mcp_server.py` 保留 `call_tool`/`handle`。
5. **分小步**：每个 PR 只拆一个组件；先加新模块，再改调用方，最后删旧实现。
6. **跑门禁**：

```bash
py -3 scripts/run_all_tests.py
py -3 tests/fixtures/dual-end/run_plugin_fixtures.py
py -3 scripts/check_repo_hygiene.py
py -3 scripts/run_backend_gate.py      # 涉及平台端时
git diff --check
```

7. **提交**：`refactor(<id>): <摘要>`；PR 写清“只是搬家/行为不变/如何验证”。

## 组件地图

```text
domain:       lesson_plan/{model,validation,scoring,review,gate,examples,draft}.py
application:  docx_export/*、export_docx.py
adapters:     mcp_lesson/*、mcp_server.py、CLI、hooks
compat:       lib.py 仅 re-export
```

## 后端组件地图（src/backend）

```text
domain:       app/domain/{errors,roles,security,versions,manifest,hashing,ingest,evidence,versions_diff,stats}.py
application:  app/application/*_service.py（事务与编排）
adapters:     app/adapters/{db,archive,storage,engine,clock}（SQL 只在 db/repo.py）
api:          app/api/{deps,errors,schemas,routers}（只做协议适配）
gate:         scripts/check_backend_*.py + scripts/run_backend_gate.py
```

后端分层与闸门规则见 `docs/backend-review-gate.md`；写后端代码时按该文档的 8 组清单自查，合并前跑 `py -3 scripts/run_backend_gate.py`。

## 检查清单

- [ ] 没有本机绝对路径；
- [ ] 封闭集合用映射，没有新增长 if 链；
- [ ] domain 没有 import adapter，没有 print/`sys.exit`；
- [ ] 错误只在 adapter 边界捕获一次；
- [ ] 状态只由 `derive_review_status` 推导；
- [ ] 重复 3 次以上的测试搭建已抽夹具；
- [ ] 新测试已加入 `test/index.py`，全量 runner 通过；
- [ ] CLI/MCP/导出契约未变；
- [ ] 后端改动已跑 `scripts/run_backend_gate.py`，无 block（warning 已说明）。

## 反模式

- 为了行数把函数拆成大量一行包装；
- 在 domain 里直接 `print` 或读 `sys.argv`；
- 两个 adapter 各写一套工具异常处理；
- 用字符串字面量重复表示状态；
- 重构 PR 夹带新功能或契约变更。
