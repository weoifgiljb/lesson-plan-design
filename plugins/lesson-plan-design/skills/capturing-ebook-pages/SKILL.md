---
name: capturing-ebook-pages
description: >
  用 Playwright 把本地教材 PDF、DOCX、PPT、PPTX 截成 PNG 并写出 manifest（Office 文件先转为 PDF 或 HTML）。
  用户提到电子书截图、教材截图、截 PDF/PPT/DOCX 页面、给教案配图时使用。
compatibility: Requires Python 3 and Playwright Chromium. Optional LibreOffice, mammoth, and python-pptx.
---

# Capturing Ebook Pages

## Instructions

1. 只要本机文件路径。不要去登录网页、DRM 阅读器或在线书城。
2. 依赖写在本技能说明里，不要在 `lesson-plan-design` 的校验脚本里 import Playwright：

```bash
pip install playwright mammoth python-pptx
python -m playwright install chromium
```

3. 在本技能根目录运行：

```bash
python scripts/capture_ebook.py <book.pdf> -o output/ebook-captures/<stem> --pages 3-7
```

   省略 `--pages` 则截全部页。`--pages` 支持 `3-7` 或 `1,3,5`。
4. 读 `manifest.json`（`source`、`page`、`png`、`caption`），把选用页写入教案 `mediaAssets`，再按 `formatting-lesson-docx` / `lesson-plan-design` 导出 Word。
5. 适配规则：
   - PDF：Chromium 打开 `file://…#page=N`
   - DOCX / PPTX：有 LibreOffice（`soffice`）则转 PDF；否则 mammoth / python-pptx 转 HTML（无 soffice 时 .docx 整份算 1 页；复杂 PPTX 会失真）
   - `.ppt`：必须有 LibreOffice；没有就失败并说明原因，禁止假装成功
6. 缺少 Chromium 时退出码非 0，并提示 `pip install playwright && python -m playwright install chromium`。截图失败不得跳过教案审查。

## Examples

用户：把 `教材/C语言.pdf` 第 3 到 5 页截下来，挂到知识学习。

```bash
python scripts/capture_ebook.py 教材/C语言.pdf -o output/ebook-captures/C语言 --pages 3-5
```

然后写入：

```json
"mediaAssets": [
  {"path": "output/ebook-captures/C语言/page-003.png", "caption": "教材第3页", "attachTo": "knowledgeLearning"}
]
```

用户：截这份 `旧版.ppt`。若本机没有 LibreOffice，应明确报「旧版 .ppt 需要 soffice」，不要输出空白 PNG。

## Additional Resources

- 脚本：[scripts/capture_ebook.py](scripts/capture_ebook.py)
- 测试：[test/index.py](test/index.py)
- Word 嵌图：`formatting-lesson-docx`
- 教案门禁：`lesson-plan-design`
