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

## 可选配图 `mediaAssets`

不是结构校验必填。导出 Word 时按 `attachTo` 挂到对应字段（八步可用 `knowledgeLearning` 或 `activityFlow.knowledgeLearning`）。

长文本支持 Markdown 子集（`**粗体**`、`1. ` 列表、`#`–`###`、围栏代码、`![说明](相对路径)`），详见技能 `formatting-lesson-docx`。教材截图见 `capturing-ebook-pages`。

