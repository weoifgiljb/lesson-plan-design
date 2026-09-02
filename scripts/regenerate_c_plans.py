import json
import re
import sys
from pathlib import Path

ROOT = Path(r"C:\Users\17841\Desktop\毕业设计")
PLAN_DIR = ROOT / "output" / "c-language-plans"

sys.path.insert(0, str(ROOT / "plugins" / "lesson-plan-design" / "skills" / "lesson-plan-design" / "scripts"))
from lib import draft_plan

ASSETS = {
    "第1周第1次_认识C语言与Dev-C++开发环境.json": "项目一-dev环境.png",
    "第1周第2次_我的第一个C程序_输出与程序结构.json": "项目一-程序结构.png",
    "第2周第1次_数据类型变量与常量.json": "项目二-数据类型.png",
    "第2周第2次_运算符表达式与键盘输入输出.json": "项目二-运算符输入输出.png",
    "第3周第1次_if单分支与双分支.json": "项目三-if分支.png",
    "第3周第2次_多分支与switch选择结构.json": "项目三-switch.png",
    "第4周第1次_while与do_while循环.json": "项目四-循环.png",
    "第4周第2次_for循环_从重复计算到规律程序.json": "项目四-for.png",
}

PAGES = {
    "项目一-dev环境.png": "项目一课件第32页",
    "项目一-程序结构.png": "项目一课件第42页",
    "项目二-数据类型.png": "项目二课件第5页",
    "项目二-运算符输入输出.png": "项目二课件第110页",
    "项目三-if分支.png": "项目三课件第15页",
    "项目三-switch.png": "项目三课件第21页",
    "项目四-循环.png": "项目四教学设计第1页",
    "项目四-for.png": "项目四教学设计第1页",
}

CODE = {
    "第1周第1次_认识C语言与Dev-C++开发环境.json": "编辑 -> 保存 .c -> 编译 -> 运行",
    "第1周第2次_我的第一个C程序_输出与程序结构.json": '#include <stdio.h>\nint main(void) {\n    printf("Hello, C!\\n");\n    return 0;\n}',
    "第2周第1次_数据类型变量与常量.json": "int launchCount = 1;\nfloat fuel = 12.5f;\nchar grade = 'A';",
    "第2周第2次_运算符表达式与键盘输入输出.json": '#include <stdio.h>\nint main(void) {\n    int price, count;\n    scanf("%d%d", &price, &count);\n    printf("%d\\n", price * count);\n    return 0;\n}',
    "第3周第1次_if单分支与双分支.json": 'if (score >= 60) {\n    printf("通过");\n} else {\n    printf("继续努力");\n}',
    "第3周第2次_多分支与switch选择结构.json": 'switch (choice) {\ncase 1:\n    printf("米饭");\n    break;\ndefault:\n    printf("无此选项");\n}',
    "第4周第1次_while与do_while循环.json": "int i = 1, sum = 0;\nwhile (i <= 10) {\n    sum += i;\n    i++;\n}",
    "第4周第2次_for循环_从重复计算到规律程序.json": "int sum = 0;\nfor (int i = 1; i <= 100; i++) {\n    sum += i;\n}",
}


def markdownize(value: str) -> str:
    value = re.sub(r"(?<![A-Za-z0-9])(\d+)、", r"\n\1. ", value)
    value = re.sub(r"\n+", "\n", value).strip()
    return value


def normalize_activity(value):
    """Normalize legacy text without flattening structured activity rows."""
    if isinstance(value, dict):
        return {
            key: (markdownize(item) if isinstance(item, str) else item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [normalize_activity(item) for item in value]
    return markdownize(str(value))


def main() -> None:
    for name, asset_name in ASSETS.items():
        path = PLAN_DIR / name
        existing = json.loads(path.read_text(encoding="utf-8"))
        plan = draft_plan(
            int(existing["week"]),
            int(existing["session"]),
            str(existing["contentTitle"]),
            content_detail=str(existing.get("contentDetail") or ""),
            planned_hours=float(existing.get("plannedHours") or 2),
            academic_year=str(existing.get("academicYear") or "2024-2025"),
            semester=int(existing.get("semester") or 2),
            teacher=str(existing.get("teacher") or ""),
            teaching_object=str(existing.get("teachingObject") or ""),
            teach_date=str(existing.get("teachDate") or ""),
            plan_number=str(existing.get("planNumber") or ""),
        )
        plan["school"] = existing.get("school", plan["school"])
        plan["course"] = existing.get("course", plan["course"])
        plan["teachingGroup"] = existing.get("teachingGroup", plan["teachingGroup"])
        for field in ("knowledgeGoals", "abilityGoals", "qualityGoals", "keyPoints", "teachingMethods", "teachingResources"):
            plan[field] = markdownize(str(plan.get(field, "")))
        flow = plan["activityFlow"]
        for key, value in flow.items():
            flow[key] = normalize_activity(value)
        code = CODE[name]
        knowledge_value = flow["knowledgeLearning"]
        if isinstance(knowledge_value, list) and knowledge_value and isinstance(knowledge_value[0], dict):
            knowledge_value[0]["teacherActivity"] = (
                str(knowledge_value[0].get("teacherActivity") or "")
                + f"\n\n**教师演示代码：**\n```c\n{code}\n```"
            )
        elif "```" not in str(knowledge_value):
            flow["knowledgeLearning"] = str(knowledge_value) + f"\n\n**教师演示代码：**\n```c\n{code}\n```"
        plan["mediaAssets"] = [{
            "path": f"../ebook-captures/selected/{asset_name}",
            "caption": f"教材项目页：{asset_name.rsplit('.', 1)[0]}（{PAGES[asset_name]}）",
            "attachTo": "knowledgeLearning",
        }]
        path.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(path)


if __name__ == "__main__":
    main()
