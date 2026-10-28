# 校标字段

默认学校：东莞经贸学校；课程：信息技术；教研组：计算机。

## 元信息

| 字段 | 说明 |
|------|------|
| school | 学校 |
| academicYear | 学年，如 2024-2025 |
| semester | 学期，1 或 2 |
| course | 课程 |
| planNumber | 教案编号，可空 |
| teachingGroup | 教研组 |
| teacher | 任课教师 |
| teachingObject | 教学对象 / 班级 |
| teachDate | 授课日期 |
| week | 周次，正整数 |
| session | 课次，正整数 |
| contentTitle | 教学内容标题 |
| contentDetail | 补充，如练习套别 |
| plannedHours | 计划学时，正数 |

## 三维目标与教法资源

| 字段 | 说明 |
|------|------|
| teachingPurpose | 教学目的 |
| knowledgeGoals | 知识目标 |
| abilityGoals | 能力目标 |
| qualityGoals | 素质目标 |
| keyPoints | 重点与难点 |
| teachingMethods | 教学方法 |
| teachingResources | 教学资源（默认机房） |

### 写法（质检）

- `knowledgeGoals`：**学生会什么**（可陈述的知识），用可观察动词（说出、列出、区分、说明等）。
- `abilityGoals`：**学生能干什么**（可完成的操作/任务），须能对上任务实施与考核证据。
- `qualityGoals`：表头仍是素质目标，内容回答**达成什么素养**；写可观察的规范、习惯、协作，禁止空泛「培养…精神」。
- 三维目标必须可评可测：下课前教师能用产出、演示或口头检查判断是否达成。
- `keyPoints` 固定分写两行：`重点：…（来自本课教学内容）` / `难点：…（来自学情，写清卡在哪里）`。重点由教学内容确定，难点由学情确定。
- `examples/` 只作字段与八步的结构对照，不要照抄样例中的课题清单式目标与未分写的重难点。

## 八步流程 `activityFlow`

| 键 | 标题 |
|----|------|
| introduction | 一、复习与导入新课 |
| learningGoals | 二、明确学习目标 |
| knowledgeLearning | 三、知识学习 |
| taskImplementation | 四、工作任务实施（须含必须完成/必做） |
| assessment | 五、课程考核 |
| summary | 六、课堂小结 |
| homework | 七、布置作业 |
| reflection | 八、教学反思（可空） |

### 结构化活动（可选）

八步字段默认继续支持字符串。需要分别呈现主要内容、教师活动和学生活动时，可将任一字段写成单个对象或对象数组：

```json
{
  "mainContent": "完成两数加法程序",
  "teacherActivity": "演示变量声明和调试",
  "studentActivity": "编写、运行并互查代码",
  "minutes": 20,
  "evidence": "提交 C04_学号.c 和运行截图"
}
```

`mainContent` 必填；`teacherActivity`、`studentActivity`、`minutes`、`evidence` 为可选字段。工作任务实施中的结构化活动应提供学生操作和可核验产出，便于课堂考核与导出排版。

## 可选配图 `mediaAssets`

不是结构校验必填。导出 Word 时按 `attachTo` 挂到对应字段（八步可用 `knowledgeLearning` 或 `activityFlow.knowledgeLearning`）。

长文本支持 Markdown 子集（`**粗体**`、`1. ` 列表、`#`–`###`、围栏代码、`![说明](相对路径)`），详见技能 `formatting-lesson-docx`。教材截图见 `capturing-ebook-pages`。

