# -*- coding: utf-8 -*-
"""将本地 PDF/DOCX/PPT(X) 转为浏览器可渲染页面并用 Playwright 截图。"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import zlib
from dataclasses import dataclass
from pathlib import Path
from xml.sax.saxutils import escape as html_escape

INSTALL_HINT = "pip install playwright && python -m playwright install chromium"
PDF_INFLATE_MAX_BYTES = 256 * 1024


class CaptureError(Exception):
    """截图失败（缺依赖、不支持的格式、页码越界等）。"""


def dump(data: dict) -> str:
    return json.dumps(data, ensure_ascii=False)


def detect_kind(path: Path) -> str:
    ext = path.suffix.lower()
    mapping = {".pdf": "pdf", ".docx": "docx", ".pptx": "pptx", ".ppt": "ppt"}
    kind = mapping.get(ext)
    if kind is None:
        raise CaptureError(f"不支持的文件类型：{path.suffix or '(无扩展名)'}，仅支持 pdf/docx/pptx/ppt")
    return kind


def parse_pages(spec: str | None, total: int) -> list[int]:
    if total < 1:
        raise CaptureError("文档没有可截取的页面")
    if not spec or not str(spec).strip():
        return list(range(1, total + 1))
    selected: list[int] = []
    for part in str(spec).split(","):
        token = part.strip()
        if not token:
            continue
        if "-" in token:
            start_s, end_s = token.split("-", 1)
            try:
                start, end = int(start_s), int(end_s)
            except ValueError as exc:
                raise CaptureError(f"无法解析页码：{token}") from exc
            if start > end:
                start, end = end, start
            selected.extend(range(start, end + 1))
        else:
            try:
                selected.append(int(token))
            except ValueError as exc:
                raise CaptureError(f"无法解析页码：{token}") from exc
    unique = sorted(set(selected))
    bad = [n for n in unique if n < 1 or n > total]
    if bad:
        raise CaptureError(f"页码超出范围 1-{total}：{bad}")
    return unique


def pdf_page_count(path: Path) -> int:
    data = path.read_bytes()
    best = 0
    for blob in _pdf_search_blobs(data):
        counted = _pages_count_in(blob)
        if counted and counted > best:
            best = counted
    if best:
        return best
    pages = re.findall(rb"/Type\s*/Page\b", data)
    return max(1, len(pages))


def _should_inflate_pdf_stream(data: bytes, stream_at: int, raw: bytes) -> bool:
    if len(raw) > PDF_INFLATE_MAX_BYTES:
        return False
    header = data[max(0, stream_at - 400) : stream_at]
    return re.search(rb"/Subtype\s*/Image\b", header) is None


def _pdf_search_blobs(data: bytes) -> list[bytes]:
    blobs = [data]
    for match in re.finditer(rb"stream\r?\n(.+?)\r?\nendstream", data, re.DOTALL):
        raw = match.group(1).strip(b"\r\n")
        if not _should_inflate_pdf_stream(data, match.start(), raw):
            continue
        for wbits in (zlib.MAX_WBITS, -zlib.MAX_WBITS):
            try:
                blobs.append(zlib.decompress(raw, wbits))
                break
            except zlib.error:
                continue
    return blobs


def _pages_count_in(blob: bytes) -> int | None:
    best = None
    for match in re.finditer(rb"<<(?:(?!<<).)*?>>", blob, re.DOTALL):
        block = match.group(0)
        if not re.search(rb"/Type\s*/Pages\b", block):
            continue
        counted = re.search(rb"/Count\s+(\d+)", block)
        if counted:
            value = int(counted.group(1))
            if best is None or value > best:
                best = value
    if best is not None:
        return best
    for pattern in (
        rb"/Type\s*/Pages\b.{0,800}?/Count\s+(\d+)",
        rb"/Count\s+(\d+).{0,800}?/Type\s*/Pages\b",
    ):
        counted = re.search(pattern, blob, re.DOTALL)
        if counted:
            return int(counted.group(1))
    return None


def write_minimal_pdf(path: Path, text: str = "Hello ebook") -> Path:
    safe = "".join(ch if 32 <= ord(ch) < 127 and ch not in "()\\" else " " for ch in text)
    stream = f"BT /F1 24 Tf 72 720 Td ({safe}) Tj ET\n".encode("latin-1")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n" + stream + b"endstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    body = b"%PDF-1.4\n"
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(body))
        body += f"{index} 0 obj\n".encode("ascii") + obj + b"\nendobj\n"
    xref_start = len(body)
    xref = f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode("ascii")
    for offset in offsets[1:]:
        xref += f"{offset:010d} 00000 n \n".encode("ascii")
    trailer = (
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_start}\n%%EOF\n"
    ).encode("ascii")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(body + xref + trailer)
    return path


def find_soffice() -> Path | None:
    for name in ("soffice", "soffice.exe", "libreoffice"):
        found = shutil.which(name)
        if found:
            return Path(found)
    for candidate in (
        Path(r"C:\Program Files\LibreOffice\program\soffice.exe"),
        Path(r"C:\Program Files (x86)\LibreOffice\program\soffice.exe"),
        Path("/usr/bin/soffice"),
        Path("/usr/bin/libreoffice"),
    ):
        if candidate.is_file():
            return candidate
    return None


def convert_with_libreoffice(src: Path, work: Path, soffice: Path) -> Path:
    work.mkdir(parents=True, exist_ok=True)
    try:
        subprocess.run(
            [str(soffice), "--headless", "--convert-to", "pdf", "--outdir", str(work), str(src)],
            check=True,
            capture_output=True,
            timeout=180,
        )
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        raise CaptureError(f"LibreOffice 转换失败：{src.name}") from exc
    pdf = work / f"{src.stem}.pdf"
    if not pdf.is_file():
        raise CaptureError(f"LibreOffice 未生成 PDF：{pdf.as_posix()}")
    return pdf


def docx_to_html(src: Path, dest: Path) -> Path:
    try:
        import mammoth
    except ImportError as exc:
        raise CaptureError("截取 .docx 需要安装 mammoth：pip install mammoth") from exc
    result = mammoth.convert_to_html(str(src))
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(
        "<!DOCTYPE html><html><head><meta charset='utf-8'/>"
        "<style>body{font-family:'宋体',serif;max-width:800px;margin:32px auto;line-height:1.6;}</style>"
        f"</head><body>{result.value}</body></html>",
        encoding="utf-8",
    )
    return dest


def pptx_to_html_pages(src: Path, dest_dir: Path) -> list[Path]:
    try:
        from pptx import Presentation
    except ImportError as exc:
        raise CaptureError("无 LibreOffice 时截取 .pptx 需要 python-pptx：pip install python-pptx") from exc
    presentation = Presentation(str(src))
    dest_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for index, slide in enumerate(presentation.slides, start=1):
        texts: list[str] = []
        for shape in slide.shapes:
            if getattr(shape, "has_text_frame", False):
                texts.append(shape.text_frame.text)
        body = "".join(f"<p>{html_escape(item)}</p>" for item in texts if item and item.strip())
        path = dest_dir / f"slide-{index:03d}.html"
        path.write_text(
            "<!DOCTYPE html><html><head><meta charset='utf-8'/>"
            "<style>body{font-family:sans-serif;padding:48px;width:1280px;min-height:720px;background:#fff;}</style>"
            f"</head><body><h1>幻灯片 {index}</h1>{body}</body></html>",
            encoding="utf-8",
        )
        paths.append(path)
    if not paths:
        raise CaptureError("PPTX 中没有可截取的幻灯片")
    return paths


@dataclass
class RenderJob:
    page: int
    path: Path
    kind: str


def screenshot_full_page(job: RenderJob) -> bool:
    """HTML 长页需要整页；PDF 阅读器整本可滚，必须按视口截当前页。"""
    return job.kind != "pdf"


def prepare_jobs(src: Path, work: Path, *, soffice: Path | None | object = ...) -> list[RenderJob]:
    kind = detect_kind(src)
    if soffice is ...:
        soffice = find_soffice()
    if kind == "ppt" and soffice is None:
        raise CaptureError("旧版 .ppt 需要本机安装 LibreOffice（soffice），未找到则无法截图")
    if kind in {"docx", "pptx", "ppt"} and soffice is not None:
        pdf = convert_with_libreoffice(src, work / "converted", soffice)
        return prepare_jobs(pdf, work, soffice=None)
    if kind == "pdf":
        total = pdf_page_count(src)
        return [RenderJob(page=i, path=src, kind="pdf") for i in range(1, total + 1)]
    if kind == "docx":
        html = docx_to_html(src, work / "doc.html")
        return [RenderJob(page=1, path=html, kind="html")]
    if kind == "pptx":
        slides = pptx_to_html_pages(src, work / "slides")
        return [RenderJob(page=i, path=path, kind="html") for i, path in enumerate(slides, start=1)]
    raise CaptureError(f"无法准备截图任务：{kind}")


def chromium_available() -> bool:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return False
    try:
        with sync_playwright() as playwright:
            executable = playwright.chromium.executable_path
        return bool(executable) and Path(executable).is_file()
    except Exception:
        return False


def _screenshot_jobs(jobs: list[RenderJob], out_dir: Path) -> list[dict]:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise CaptureError(f"未安装 Playwright。请运行：{INSTALL_HINT}") from exc
    if not chromium_available():
        raise CaptureError(f"未找到 Chromium。请运行：{INSTALL_HINT}")
    out_dir.mkdir(parents=True, exist_ok=True)
    pages: list[dict] = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        context = browser.new_context(viewport={"width": 1280, "height": 1600})
        page = context.new_page()
        try:
            for job in jobs:
                dest = out_dir / f"page-{job.page:03d}.png"
                uri = job.path.resolve().as_uri()
                if job.kind == "pdf":
                    uri = f"{uri}#page={job.page}"
                page.goto(uri, wait_until="load", timeout=30000)
                page.wait_for_timeout(800)
                page.screenshot(path=str(dest), full_page=screenshot_full_page(job))
                pages.append(
                    {
                        "page": job.page,
                        "png": dest.as_posix(),
                        "caption": f"第{job.page}页",
                    }
                )
        finally:
            browser.close()
    return pages


def capture_ebook(src: Path, out_dir: Path, *, pages: str | None = None) -> dict:
    src = src.resolve()
    if not src.is_file():
        raise CaptureError(f"找不到文件：{src.as_posix()}")
    work = out_dir / ".work"
    work.mkdir(parents=True, exist_ok=True)
    jobs = prepare_jobs(src, work)
    selected = set(parse_pages(pages, jobs[-1].page if jobs else 0))
    jobs = [job for job in jobs if job.page in selected]
    captured = _screenshot_jobs(jobs, out_dir)
    manifest = {
        "ok": True,
        "source": str(src),
        "pages": captured,
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="用 Playwright 截取本地教材 PDF/DOCX/PPT")
    parser.add_argument("path", help="本地 pdf/docx/pptx/ppt 路径")
    parser.add_argument("-o", "--out", help="输出目录，默认 output/ebook-captures/<文件名>")
    parser.add_argument("--pages", help="页码，如 3-7 或 1,3,5")
    args = parser.parse_args()
    src = Path(args.path)
    out = Path(args.out) if args.out else Path("output") / "ebook-captures" / src.stem
    try:
        manifest = capture_ebook(src, out, pages=args.pages)
    except CaptureError as exc:
        print(dump({"ok": False, "error": str(exc)}), file=sys.stderr)
        return 1
    print(dump({"ok": True, "source": manifest["source"], "pages": manifest["pages"], "out": out.as_posix()}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
