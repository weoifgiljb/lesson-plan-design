# Pull Request

## 关联

- 需求：FR-xx / BS-xx
- 测试用例：TC-xx-yy
- 分支：`feature/<id>-<slug>`

## 变更内容

<!-- 一句话说明改了什么；插件端/平台端/契约分别列 -->

## 测试

- [ ] 本需求对应用例通过
- [ ] 插件端测试套件通过（`py -3 plugins/lesson-plan-design/skills/lesson-plan-design/test/index.py`）
- [ ] 双端样例脚本通过（`py -3 tests/fixtures/dual-end/run_plugin_fixtures.py`，联调前必须全绿）
- [ ] P0 手工冒烟通过（列出 TC 编号）

## 契约影响

- [ ] 无
- [ ] 有：schema、黄金样例、错误码已同批更新

## 代码组织

- [ ] 没有新增本机绝对路径
- [ ] 没有跨层 import、重复状态判断或重复错误边界
- [ ] 新测试已加入 `test/index.py`，全量 runner 通过
- [ ] 重构未改变 CLI/MCP/导出契约

## 风险与未关闭项

<!-- 没有就写"无"；有则写影响范围、临时绕行、计划关闭时间 -->

## 自审记录

- 自审人：
- 自审时间：
- 结论：通过 / 需修改
- 导师抽查（节点评审时填写）：
