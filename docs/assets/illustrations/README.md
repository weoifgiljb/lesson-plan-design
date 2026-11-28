# 插图资产台账（LPP-UI-001）

所有插图均为本地资产，**不请求外部图片或字体**。未落盘的文件一律使用 CSS/SVG 降级，不得出现破图；接入新图后在此登记 ID、文件、提示词来源、模型、日期与 alt。

| ID | 文件 | 用途 | 比例 | 当前状态 | 降级 |
|---|---|---|---|---|---|
| A1 | `login-desk.webp` | 登录案头装裱画 | 4:5 | 槽位预留 | 登录页内联 SVG 教案本/朱笔/印章 |
| A2 | `empty-plans.webp` | 教案库/概览空态 | 4:3 | 槽位预留 | `StatePanel` 纸色插画 |
| A3 | `empty-tasks.webp` | 任务空态 | 4:3 | 槽位预留 | `StatePanel` 纸色插画 |
| A4 | `empty-reviews.webp` | 审查空态 | 4:3 | 槽位预留 | `StatePanel` 纸色插画 |
| A5 | `empty-exports.webp` | 导出空态 | 4:3 | 槽位预留 | 文件袋空态纸卡 |
| A6 | `error.webp` | 错误态 | 4:3 | 槽位预留 | `StatePanel` 裂纹/红章 |
| A7 | `forbidden.webp` | 无权限 | 4:3 | 槽位预留 | `StatePanel` 锁/钥匙 |
| A8 | `sample-cover-c.webp` | C 语言样例封面 | 3:2 | 槽位预留 | 课程首字 + 纸色块 |
| A9 | `sample-cover-it.webp` | 信息技术样例封面 | 3:2 | 槽位预留 | 课程首字 + 纸色块 |
| A10 | `sample-cover-generic.webp` | 通用样例封面 | 3:2 | 槽位预留 | 课程首字 + 纸色块 |
| A11 | `paper-grain.webp` | 纸纹（可选） | 1:1 | 槽位预留 | CSS `feTurbulence` 纸纹 |

## 提示词

生成提示词见 [界面风格优化需求](../../requirements/界面风格优化需求.md) 附录 A。统一锚点：暖米纸 `#F3EEE4`、松绿 `#245A4C`、朱砂 `#B0432F`、细墨线、平涂、轻纸纹、大留白、无文字/人物/品牌。

## 接入规则

1. 首屏图片总量 ≤120KB；A1 可预加载，其余懒加载。
2. 装饰性图片 `aria-hidden="true"`；承载信息时必须写 `alt`，且旁边保留等价文字。
3. 缺图/加载失败时用当前 CSS 降级，不允许改变布局高度（CLS <0.1）。
4. 新增资产同批更新本台账与 `界面风格优化需求.md`。
