# -*- coding: utf-8 -*-
"""教案字段 Markdown 子集 → Word OOXML（仅标准库）。"""
from __future__ import annotations

import re
import struct
from dataclasses import dataclass, field
from pathlib import Path
from xml.sax.saxutils import escape

NS_W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS_R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
NS_WP = "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"
NS_A = "http://schemas.openxmlformats.org/drawingml/2006/main"
NS_PIC = "http://schemas.openxmlformats.org/drawingml/2006/picture"
NS_REL = "http://schemas.openxmlformats.org/package/2006/relationships"

IMAGE_EXTS = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".bmp": "image/bmp",
    ".webp": "image/webp",
}

HEADING_RE = re.compile(r"^(#{1,3})\s+(.+)$")
UL_RE = re.compile(r"^[-*]\s+(.+)$")
OL_RE = re.compile(r"^\d+\.\s+(.+)$")
FENCE_RE = re.compile(r"^```(\w*)\s*$")
IMAGE_LINE_RE = re.compile(r"^!\[([^\]]*)\]\(([^)]+)\)\s*$")
IMAGE_INLINE_RE = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
MAX_IMAGE_CX = 4680000
DEFAULT_IMAGE_CY = 3510000


def _xml_attr(text: str) -> str:
    return escape(text, {'"': "&quot;", "'": "&apos;"})


def _png_pixel_size(data: bytes) -> tuple[int, int] | None:
    if len(data) < 24 or data[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    width, height = struct.unpack(">II", data[16:24])
    if width < 1 or height < 1:
        return None
    return width, height


def _gif_pixel_size(data: bytes) -> tuple[int, int] | None:
    if len(data) < 10 or data[:6] not in (b"GIF87a", b"GIF89a"):
        return None
    width, height = struct.unpack("<HH", data[6:10])
    return (width, height) if width > 0 and height > 0 else None


def _bmp_pixel_size(data: bytes) -> tuple[int, int] | None:
    if len(data) < 26 or data[:2] != b"BM":
        return None
    width, height = struct.unpack("<ii", data[18:26])
    width, height = abs(width), abs(height)
    return (width, height) if width > 0 and height > 0 else None


def _jpeg_pixel_size(data: bytes) -> tuple[int, int] | None:
    if len(data) < 4 or data[:2] != b"\xff\xd8":
        return None
    index = 2
    while index + 9 < len(data):
        if data[index] != 0xFF:
            index += 1
            continue
        marker = data[index + 1]
        index += 2
        if marker in (0xD8, 0xD9):
            continue
        if index + 2 > len(data):
            break
        length = struct.unpack(">H", data[index:index + 2])[0]
        if length < 2 or index + length > len(data):
            break
        if marker in range(0xC0, 0xC4) or marker in range(0xC5, 0xC8) or marker in range(0xC9, 0xCC) or marker in range(0xCD, 0xD0):
            if length >= 7:
                height, width = struct.unpack(">HH", data[index + 3:index + 7])
                return (width, height) if width > 0 and height > 0 else None
        index += length
    return None


def _image_extent(path: Path) -> tuple[int, int]:
    try:
        data = path.read_bytes()
        size = (
            _png_pixel_size(data)
            or _gif_pixel_size(data)
            or _bmp_pixel_size(data)
            or _jpeg_pixel_size(data)
        )
    except OSError:
        size = None
    if size is None:
        return MAX_IMAGE_CX, DEFAULT_IMAGE_CY
    width, height = size
    return MAX_IMAGE_CX, max(1, round(MAX_IMAGE_CX * height / width))


@dataclass
class Inline:
    kind: str
    text: str = ""
    src: str = ""


@dataclass
class Block:
    kind: str
    inlines: list[Inline] = field(default_factory=list)
    level: int = 1
    text: str = ""
    lang: str = ""
    alt: str = ""
    src: str = ""


def _next_markup(text: str, start: int) -> int:
    hits = [pos for pos in (text.find("![", start), text.find("`", start), text.find("**", start), text.find("*", start)) if pos != -1]
    return min(hits) if hits else len(text)


def _ascii_ident_char(char: str) -> bool:
    return char.isascii() and (char.isalnum() or char == "_")


def _looks_like_c_pointers(text: str, open_at: int, close_at: int) -> bool:
    after_open = open_at + 1 < len(text) and _ascii_ident_char(text[open_at + 1])
    after_close = close_at + 1 < len(text) and _ascii_ident_char(text[close_at + 1])
    return after_open and after_close


def parse_inlines(text: str) -> list[Inline]:
    result: list[Inline] = []
    i = 0
    n = len(text)
    while i < n:
        if text.startswith("![", i):
            match = IMAGE_INLINE_RE.match(text, i)
            if match:
                result.append(Inline("image", text=match.group(1), src=match.group(2)))
                i = match.end()
                continue
        if text[i] == "`":
            close = text.find("`", i + 1)
            if close != -1:
                result.append(Inline("code", text[i + 1 : close]))
                i = close + 1
                continue
        if text.startswith("**", i):
            close = text.find("**", i + 2)
            if close != -1:
                result.append(Inline("bold", text[i + 2 : close]))
                i = close + 2
                continue
        if text[i] == "*":
            close = text.find("*", i + 1)
            if close != -1 and not _looks_like_c_pointers(text, i, close):
                result.append(Inline("italic", text[i + 1 : close]))
                i = close + 1
                continue
        nxt = _next_markup(text, i + 1)
        result.append(Inline("text", text[i:nxt]))
        i = nxt
    return result


def parse_markdown(source: str | None) -> list[Block]:
    text = "" if source is None else str(source)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = text.split("\n")
    blocks: list[Block] = []
    index = 0
    total = len(lines)
    while index < total:
        line = lines[index]
        fence = FENCE_RE.match(line)
        if fence:
            lang = fence.group(1) or ""
            index += 1
            body: list[str] = []
            while index < total and not lines[index].startswith("```"):
                body.append(lines[index])
                index += 1
            if index < total:
                index += 1
            blocks.append(Block(kind="code", text="\n".join(body), lang=lang))
            continue
        if not line.strip():
            index += 1
            continue
        heading = HEADING_RE.match(line)
        if heading:
            blocks.append(
                Block(
                    kind="heading",
                    level=len(heading.group(1)),
                    inlines=parse_inlines(heading.group(2).strip()),
                )
            )
            index += 1
            continue
        unordered = UL_RE.match(line)
        if unordered:
            blocks.append(Block(kind="ul_item", inlines=parse_inlines(unordered.group(1))))
            index += 1
            continue
        ordered = OL_RE.match(line)
        if ordered:
            blocks.append(Block(kind="ol_item", inlines=parse_inlines(ordered.group(1))))
            index += 1
            continue
        image = IMAGE_LINE_RE.match(line.strip())
        if image:
            blocks.append(Block(kind="image", alt=image.group(1), src=image.group(2)))
            index += 1
            continue
        para_lines = [line]
        index += 1
        while index < total:
            nxt = lines[index]
            if not nxt.strip():
                break
            if (
                FENCE_RE.match(nxt)
                or HEADING_RE.match(nxt)
                or UL_RE.match(nxt)
                or OL_RE.match(nxt)
                or IMAGE_LINE_RE.match(nxt.strip())
            ):
                break
            para_lines.append(nxt)
            index += 1
        inlines: list[Inline] = []
        for offset, para_line in enumerate(para_lines):
            if offset:
                inlines.append(Inline("break"))
            inlines.extend(parse_inlines(para_line))
        blocks.append(Block(kind="paragraph", inlines=inlines))
    return blocks


def _run(text: str, *, bold: bool = False, italic: bool = False, code: bool = False) -> str:
    fonts = (
        '<w:rFonts w:ascii="Consolas" w:hAnsi="Consolas" w:eastAsia="宋体"/>'
        if code
        else '<w:rFonts w:ascii="宋体" w:eastAsia="宋体" w:hAnsi="宋体"/>'
    )
    extras = ""
    if bold:
        extras += "<w:b/>"
    if italic:
        extras += "<w:i/>"
    if code:
        extras += '<w:shd w:val="clear" w:fill="F2F2F2"/><w:sz w:val="21"/>'
    return (
        f"<w:r><w:rPr>{fonts}{extras}</w:rPr>"
        f'<w:t xml:space="preserve">{escape(text)}</w:t></w:r>'
    )


def _runs(inlines: list[Inline], package: "DocxPackage") -> str:
    parts: list[str] = []
    for item in inlines:
        if item.kind == "break":
            parts.append("<w:r><w:br/></w:r>")
        elif item.kind == "bold":
            parts.append(_run(item.text, bold=True))
        elif item.kind == "italic":
            parts.append(_run(item.text, italic=True))
        elif item.kind == "code":
            parts.append(_run(item.text, code=True))
        elif item.kind == "image":
            parts.append(package.image_drawing(item.src, alt=item.text))
        else:
            parts.append(_run(item.text))
    return "".join(parts) or _run("")


STYLES_XML = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="{NS_W}">
  <w:docDefaults>
    <w:rPrDefault>
      <w:rPr>
        <w:rFonts w:ascii="宋体" w:eastAsia="宋体" w:hAnsi="宋体"/>
        <w:sz w:val="24"/>
        <w:szCs w:val="24"/>
      </w:rPr>
    </w:rPrDefault>
    <w:pPrDefault>
      <w:pPr>
        <w:spacing w:line="360" w:lineRule="auto"/>
      </w:pPr>
    </w:pPrDefault>
  </w:docDefaults>
  <w:style w:type="paragraph" w:default="1" w:styleId="Normal">
    <w:name w:val="Normal"/>
    <w:qFormat/>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Heading1">
    <w:name w:val="heading 1"/>
    <w:basedOn w:val="Normal"/>
    <w:pPr><w:spacing w:before="240" w:after="80"/></w:pPr>
    <w:rPr><w:b/><w:sz w:val="32"/><w:rFonts w:ascii="黑体" w:eastAsia="黑体"/></w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Heading2">
    <w:name w:val="heading 2"/>
    <w:basedOn w:val="Normal"/>
    <w:pPr><w:spacing w:before="160" w:after="80"/></w:pPr>
    <w:rPr><w:b/><w:sz w:val="28"/><w:rFonts w:ascii="黑体" w:eastAsia="黑体"/></w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Heading3">
    <w:name w:val="heading 3"/>
    <w:basedOn w:val="Normal"/>
    <w:pPr><w:spacing w:before="120" w:after="60"/></w:pPr>
    <w:rPr><w:b/><w:sz w:val="26"/><w:rFonts w:ascii="黑体" w:eastAsia="黑体"/></w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="CodeBlock">
    <w:name w:val="Code Block"/>
    <w:pPr>
      <w:shd w:val="clear" w:fill="F2F2F2"/>
      <w:spacing w:before="40" w:after="40"/>
    </w:pPr>
    <w:rPr>
      <w:rFonts w:ascii="Consolas" w:hAnsi="Consolas" w:eastAsia="宋体"/>
      <w:sz w:val="20"/>
    </w:rPr>
  </w:style>
</w:styles>
"""

NUMBERING_XML = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:numbering xmlns:w="{NS_W}">
  <w:abstractNum w:abstractNumId="0">
    <w:multiLevelType w:val="hybridMultilevel"/>
    <w:lvl w:ilvl="0">
      <w:start w:val="1"/>
      <w:numFmt w:val="bullet"/>
      <w:lvlText w:val="•"/>
      <w:lvlJc w:val="left"/>
      <w:pPr><w:ind w:left="720" w:hanging="360"/></w:pPr>
    </w:lvl>
  </w:abstractNum>
  <w:abstractNum w:abstractNumId="1">
    <w:multiLevelType w:val="hybridMultilevel"/>
    <w:lvl w:ilvl="0">
      <w:start w:val="1"/>
      <w:numFmt w:val="decimal"/>
      <w:lvlText w:val="%1."/>
      <w:lvlJc w:val="left"/>
      <w:pPr><w:ind w:left="720" w:hanging="360"/></w:pPr>
    </w:lvl>
  </w:abstractNum>
  <w:num w:numId="1"><w:abstractNumId w:val="0"/></w:num>
  PLACEHOLDER_NUMS
</w:numbering>
"""


class DocxPackage:
    def __init__(self, *, base_dir: Path | None = None) -> None:
        self.base_dir = base_dir
        self._images: list[tuple[str, str, Path]] = []
        self._image_index = 0
        self._ordered_ids: list[int] = []
        self._next_num_id = 10
        self._docpr_id = 1

    def new_ordered_num(self) -> int:
        num_id = self._next_num_id
        self._next_num_id += 1
        self._ordered_ids.append(num_id)
        return num_id

    def _resolve(self, src: str) -> Path | None:
        path = Path(src)
        if not path.is_absolute() and self.base_dir is not None:
            path = self.base_dir / src
        return path if path.is_file() else None

    def register_image(self, src: str) -> str | None:
        path = self._resolve(src)
        if path is None:
            return None
        self._image_index += 1
        rid = f"rIdImg{self._image_index}"
        ext = path.suffix.lower() if path.suffix.lower() in IMAGE_EXTS else ".png"
        dest = f"word/media/image{self._image_index}{ext}"
        self._images.append((rid, dest, path))
        return rid

    def image_drawing(self, src: str, *, alt: str = "") -> str:
        path = self._resolve(src)
        rid = self.register_image(src)
        if rid is None or path is None:
            return _run(alt or src)
        doc_id = self._docpr_id
        self._docpr_id += 1
        cx, cy = _image_extent(path)
        name = _xml_attr(alt or path.name)
        return (
            "<w:r><w:drawing>"
            f'<wp:inline distT="0" distB="0" distL="0" distR="0" xmlns:wp="{NS_WP}">'
            f'<wp:extent cx="{cx}" cy="{cy}"/>'
            f'<wp:docPr id="{doc_id}" name="{name}"/>'
            f'<a:graphic xmlns:a="{NS_A}">'
            f'<a:graphicData uri="{NS_PIC}">'
            f'<pic:pic xmlns:pic="{NS_PIC}">'
            "<pic:nvPicPr>"
            f'<pic:cNvPr id="{doc_id}" name="{name}"/>'
            "<pic:cNvPicPr/>"
            "</pic:nvPicPr>"
            "<pic:blipFill>"
            f'<a:blip r:embed="{rid}" xmlns:r="{NS_R}"/>'
            "<a:stretch><a:fillRect/></a:stretch>"
            "</pic:blipFill>"
            "<pic:spPr>"
            f'<a:xfrm><a:off x="0" y="0"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm>'
            '<a:prstGeom prst="rect"><a:avLst/></a:prstGeom>'
            "</pic:spPr>"
            "</pic:pic></a:graphicData></a:graphic></wp:inline></w:drawing></w:r>"
        )

    def _paragraph(self, inner_runs: str, *, style: str | None = None, num_id: int | None = None) -> str:
        ppr = ""
        if style:
            ppr += f'<w:pStyle w:val="{style}"/>'
        if num_id is not None:
            ppr += (
                "<w:numPr>"
                '<w:ilvl w:val="0"/>'
                f'<w:numId w:val="{num_id}"/>'
                "</w:numPr>"
            )
        return f"<w:p><w:pPr>{ppr}</w:pPr>{inner_runs}</w:p>"

    def empty_paragraph(self) -> str:
        return self._paragraph(_run(""))

    def label_paragraph(self, text: str, *, center: bool = False) -> str:
        align = '<w:jc w:val="center"/>' if center else ""
        return (
            f"<w:p><w:pPr>{align}</w:pPr>"
            f"{_run(text, bold=True)}"
            "</w:p>"
        )

    def title_paragraph(self, text: str) -> str:
        """Render a centered, larger black title using the built-in heading style."""
        return (
            '<w:p><w:pPr><w:pStyle w:val="Heading1"/><w:jc w:val="center"/></w:pPr>'
            f"{_run(text, bold=True)}</w:p>"
        )

    def render_markdown(self, source: str | None) -> str:
        blocks = parse_markdown(source)
        if not blocks:
            return self.empty_paragraph()
        parts: list[str] = []
        index = 0
        while index < len(blocks):
            block = blocks[index]
            if block.kind == "ol_item":
                num_id = self.new_ordered_num()
                while index < len(blocks) and blocks[index].kind == "ol_item":
                    parts.append(
                        self._paragraph(_runs(blocks[index].inlines, self), num_id=num_id)
                    )
                    index += 1
                continue
            if block.kind == "ul_item":
                parts.append(self._paragraph(_runs(block.inlines, self), num_id=1))
            elif block.kind == "heading":
                style = f"Heading{min(max(block.level, 1), 3)}"
                parts.append(self._paragraph(_runs(block.inlines, self), style=style))
            elif block.kind == "code":
                lines = block.text.split("\n") or [""]
                for line in lines:
                    parts.append(self._paragraph(_run(line, code=True), style="CodeBlock"))
            elif block.kind == "image":
                drawing = self.image_drawing(block.src, alt=block.alt)
                parts.append(self._paragraph(drawing))
                if block.alt:
                    parts.append(self._paragraph(_run(block.alt, italic=True)))
            else:
                parts.append(self._paragraph(_runs(block.inlines, self)))
            index += 1
        return "".join(parts)

    def render_image_asset(self, asset: dict) -> str:
        src = str(asset.get("path") or "")
        caption = str(asset.get("caption") or "")
        xml = self._paragraph(self.image_drawing(src, alt=caption))
        if caption:
            xml += self._paragraph(_run(caption, italic=True))
        return xml

    def numbering_xml(self) -> str:
        extras = []
        for num_id in self._ordered_ids:
            extras.append(f'<w:num w:numId="{num_id}"><w:abstractNumId w:val="1"/></w:num>')
        return NUMBERING_XML.replace("PLACEHOLDER_NUMS", "".join(extras))

    def document_rels(self) -> str:
        rels = [
            f'<Relationship Id="rIdStyles" Type="{NS_R}/styles" Target="styles.xml"/>',
            f'<Relationship Id="rIdNumbering" Type="{NS_R}/numbering" Target="numbering.xml"/>',
        ]
        for rid, dest, _path in self._images:
            target = dest.split("/", 1)[1]
            rels.append(
                f'<Relationship Id="{rid}" Type="{NS_R}/image" Target="{target}"/>'
            )
        return (
            f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            f'<Relationships xmlns="{NS_REL}">'
            + "".join(rels)
            + "</Relationships>"
        )

    def content_types(self) -> str:
        defaults = [
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>',
            '<Default Extension="xml" ContentType="application/xml"/>',
        ]
        used_exts = {Path(dest).suffix.lower() for _rid, dest, _path in self._images}
        for ext in sorted(used_exts):
            mime = IMAGE_EXTS.get(ext, "application/octet-stream")
            defaults.append(f'<Default Extension="{ext.lstrip(".")}" ContentType="{mime}"/>')
        overrides = [
            '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>',
            '<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>',
            '<Override PartName="/word/numbering.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.numbering+xml"/>',
        ]
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            + "".join(defaults)
            + "".join(overrides)
            + "</Types>"
        )

    def zip_parts(self, document_xml: str) -> dict[str, bytes]:
        package_rels = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="{NS_REL}">
  <Relationship Id="rId1" Type="{NS_R}/officeDocument" Target="word/document.xml"/>
</Relationships>
"""
        parts: dict[str, bytes] = {
            "[Content_Types].xml": self.content_types().encode("utf-8"),
            "_rels/.rels": package_rels.encode("utf-8"),
            "word/_rels/document.xml.rels": self.document_rels().encode("utf-8"),
            "word/document.xml": document_xml.encode("utf-8"),
            "word/styles.xml": STYLES_XML.encode("utf-8"),
            "word/numbering.xml": self.numbering_xml().encode("utf-8"),
        }
        for _rid, dest, path in self._images:
            parts[dest] = path.read_bytes()
        return parts
