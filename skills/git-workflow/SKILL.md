---
name: git-workflow
description: >
  双端项目分支协作：开工从 develop 切 feature 子分支、完成后 PR 回合 develop、
  联调时切 test/integration 合并全部 feature、通过后经 develop 合 main。
  用户说开工、新建分支、联调、合并、发版、回滚时使用。
---

# 双端 Git 分支协作

硬约束见根目录 `AGENTS.md` 与 `.cursor/rules/git-workflow.mdc`；完整说明见 `docs/dev/git-workflow.md`。

## 分支模型

```text
main                         发布，只接受 develop 的 PR
└── develop                  集成，所有 feature 的回合目标
    ├── feature/fr-01-rules          插件端需求
    ├── feature/bs-01-ingest         平台端需求
    └── test/integration             联调时创建，合并全部待发 feature
```

## 开工

1. 确认需求编号（FR/BS）、验收标准、对应测试用例（TC）三样齐全；缺一项先补文档。
2. 执行：

```bash
git switch develop
git pull --ff-only origin develop
git switch -c feature/<id>-<slug>
```

3. 一个分支只做一个需求；需求过大时按验收点拆子分支，回合目标仍是 `develop`。

## 提交与回合

- 提交信息：`<type>(<id>): <摘要>`，`type` 取 `feat`、`fix`、`docs`、`test`、`refactor`、`chore`。
- 推分支并创建 PR，base 为 `develop`，按 `.github/pull_request_template.md` 填写。
- 合并前至少跑：本需求用例、插件端测试套件；契约变更加黄金测试。

```bash
git push -u origin feature/<id>-<slug>
```

## 联调

```bash
git switch develop
git switch -c test/integration
git merge --no-ff feature/<id>-<slug>   # 逐个合并全部待发 feature
```

测试顺序：

1. `py -3 plugins/lesson-plan-design/skills/lesson-plan-design/test/index.py`
2. `py -3 tests/fixtures/dual-end/run_plugin_fixtures.py`（必须全绿；FR-01 未合入前的 4 项基线失败不得带入联调）
3. `py -3 scripts/extract_test_schema.py`
4. 平台端实现后执行 `docs/testing/测试用例_markmap.md` 第 6—12 章与 P0 冒烟

缺陷处理：属于某个 feature 的回该分支修复，再回合 `develop` 并入 `test/integration`；只在集成分支出现的，切 `fix/integration-<slug>`，同时回 `test/integration` 与 `develop`。

## 发布

**先递增版本号**：把 `plugins/lesson-plan-design/.claude-plugin/plugin.json` 的 `version` 递增，五个宿主 manifest（`.claude-plugin` / `.cursor-plugin` / `.codex-plugin` / `.codebuddy-plugin` / `.qoder-plugin`）同步，标签版本号与 manifest 一致。版本号不动时，用户执行 `claude plugin update` 会得到「已是最新」而拿不到更新。

```bash
git switch develop
git merge --no-ff test/integration
git tag -a v<版本>-<阶段> -m "<说明>"
git push origin develop --tags
# 通过 PR 将 develop 合入 main，随后删除 test/integration
```

## 热修

从 `main` 切 `fix/<id>-<slug>`，修复后同时回合 `main` 与 `develop`，并补回归用例。

## 禁止

- 直接向 `main`、`develop` 提交业务代码。
- 用 `--ours`/`--theirs` 整体丢弃冲突改动。
- 把 `node_modules/`、`output/`、`.dsh/`、`.codex_audio_tmp/` 或个人临时文件提交进仓库。
- 用"未执行"冒充平台端用例通过；未实现的用例必须标 `待实现`。
