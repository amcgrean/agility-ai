import io
import os
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any
from urllib.parse import urljoin
from zipfile import BadZipFile, ZipFile

import fitz
from bs4 import BeautifulSoup

try:
    import pytesseract
except Exception:  # pragma: no cover - optional OCR dependency
    pytesseract = None

try:
    from PIL import Image
except Exception:  # pragma: no cover - optional OCR dependency
    Image = None

try:
    import numpy as np
    from rapidocr_onnxruntime import RapidOCR
except Exception:  # pragma: no cover - optional OCR dependency
    np = None
    RapidOCR = None

from doc_ingest_utils import (
    ARTICLE_NUMBER_PATTERN,
    HEADING_ONLY_PATTERN,
    classify_doc_type,
    clean_text,
    detect_repeated_margin_lines,
    doc_deep_link,
    infer_access_scope,
    infer_content_domain,
    infer_section_title,
    is_heading_candidate,
    make_doc_id,
    remove_margin_noise,
    sha256_file,
    sha256_text,
    split_paragraphs,
    strip_pdf_artifacts,
)


DOCX_NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
OCR_DPI = int(os.getenv("AGILITY_PDF_OCR_DPI", "200"))
rapidocr_engine = RapidOCR() if RapidOCR is not None else None


def _text_from_detail_cell(node: Any) -> str:
    return clean_text(node.get_text("\n", strip=True))


def _maybe_ocr_pdf_page(page: fitz.Page) -> str:
    try:
        matrix = fitz.Matrix(OCR_DPI / 72.0, OCR_DPI / 72.0)
        pixmap = page.get_pixmap(matrix=matrix, alpha=False)
        image = Image.open(io.BytesIO(pixmap.tobytes("png")))
        if pytesseract is not None and Image is not None:
            ocr_text = clean_text(pytesseract.image_to_string(image))
            if ocr_text:
                return ocr_text
        if rapidocr_engine is not None and np is not None:
            result, _ = rapidocr_engine(np.array(image))
            if result:
                return clean_text("\n".join(item[1] for item in result if len(item) > 1 and item[1]))
        return ""
    except Exception:
        return ""


def _with_common_metadata(base: dict[str, Any], relative_path: Path, title: str | None, source_format: str) -> dict[str, Any]:
    base["doc_type"] = classify_doc_type(relative_path, title, source_format)
    base["content_domain"] = infer_content_domain(relative_path, title, source_format)
    base["access_scope"] = infer_access_scope(relative_path, title, source_format)
    return base


def _extract_training_page_units(
    soup: BeautifulSoup,
    path: Path,
    source_dir: Path,
    manifest_entry: dict[str, Any] | None,
    processed_at: str,
) -> tuple[dict[str, Any], list[dict[str, Any]]] | None:
    video_info = soup.find(attrs={"name": "Video Info"})
    main_col_box = soup.find(id="mainColBox")
    if video_info is None and main_col_box is None:
        return None

    relative_path = path.relative_to(source_dir)
    page_title = None
    if main_col_box is not None:
        header = main_col_box.find(class_="col-box-header")
        if header is not None:
            page_title = clean_text(header.get_text(" ", strip=True))
    if not page_title:
        page_title = clean_text((soup.title.get_text(" ", strip=True) if soup.title else "") or path.stem)

    field_map: dict[str, str] = {}
    if video_info is not None:
        for row in video_info.select("tr"):
            cells = row.find_all("td", recursive=False)
            for index in range(0, len(cells) - 1, 2):
                label = _text_from_detail_cell(cells[index]).rstrip(":")
                value = _text_from_detail_cell(cells[index + 1])
                if label:
                    field_map[label] = value

    instructions_block = soup.find(attrs={"name": "Instructions"})
    instruction_text = None
    if instructions_block is not None:
        instruction_bits = []
        for paragraph in instructions_block.find_all(["p", "li"], recursive=True):
            text = clean_text(paragraph.get_text(" ", strip=True))
            if text and "right-click 'view' button" not in text.lower() and "copy link" not in text.lower():
                instruction_bits.append(text)
        instruction_text = "\n\n".join(instruction_bits).strip() or None

    source_url = None
    portal_section = "Uncategorized"
    if manifest_entry:
        source_url = manifest_entry.get("final_url") or manifest_entry.get("url")
        portal_section = manifest_entry.get("section") or portal_section

    article_number = None
    article_match = ARTICLE_NUMBER_PATTERN.search(page_title)
    if article_match:
        article_number = article_match.group(0).upper()

    subject = field_map.get("Subject") or page_title
    view_link = None
    if video_info is not None:
        view_anchor = video_info.find("a", href=True, string=re.compile(r"view", re.IGNORECASE))
        if view_anchor is not None:
            view_link = urljoin(source_url or "", view_anchor["href"])

    doc_id = make_doc_id("html", relative_path, subject)
    base = _with_common_metadata(
        {
            "doc_id": doc_id,
            "source_title": subject,
            "doc_title": subject,
            "source_type": "html_training",
            "source_format": "html",
            "source_path": str(relative_path).replace("\\", "/"),
            "source_file": path.name,
            "source_url": source_url,
            "deep_link": source_url,
            "portal_section": portal_section,
            "article_number": article_number,
            "product": field_map.get("Product") or None,
            "category": field_map.get("Category") or field_map.get("Subcategory") or None,
            "attachments": ([{"name": "View Video", "href": view_link, "is_file": False}] if view_link else []),
            "last_processed_at": processed_at,
            "source_file_sha256": sha256_file(path),
            "ocr_applied": False,
        },
        relative_path,
        subject,
        "html",
    )

    units: list[dict[str, Any]] = []
    unit_index = 0
    summary_lines = []
    for label in ("Available with Release", "Duration", "Product", "Category", "Subcategory"):
        value = field_map.get(label)
        if value:
            summary_lines.append(f"{label}: {value}")
    if field_map.get("Segment Description"):
        summary_lines.append(f"Segment Description: {field_map['Segment Description']}")
    if view_link:
        summary_lines.append(f"View Link: {view_link}")

    if summary_lines:
        unit_text = "\n\n".join(summary_lines)
        units.append(
            {
                **base,
                "record_id": f"{doc_id}:unit:{unit_index}",
                "section_title": "Training Summary",
                "page_start": None,
                "page_end": None,
                "text": unit_text,
                "text_hash": sha256_text(unit_text),
            }
        )
        unit_index += 1

    if instruction_text:
        units.append(
            {
                **base,
                "record_id": f"{doc_id}:unit:{unit_index}",
                "section_title": "Instructions",
                "page_start": None,
                "page_end": None,
                "text": instruction_text,
                "text_hash": sha256_text(instruction_text),
            }
        )

    if units:
        return base, units
    return None


def parse_docx_paragraphs(path: Path) -> list[dict[str, Any]]:
    paragraphs: list[dict[str, Any]] = []
    try:
        with ZipFile(path) as archive:
            xml_bytes = archive.read("word/document.xml")
    except (BadZipFile, KeyError) as exc:
        raise ValueError(f"Unable to read DOCX structure: {exc}") from exc

    root = ET.fromstring(xml_bytes)
    for paragraph in root.findall(".//w:p", DOCX_NS):
        runs = []
        for node in paragraph.findall(".//w:t", DOCX_NS):
            if node.text:
                runs.append(node.text)
        text = clean_text("".join(runs))
        if not text:
            continue
        style_node = paragraph.find(".//w:pStyle", DOCX_NS)
        style_value = style_node.attrib.get(f"{{{DOCX_NS['w']}}}val") if style_node is not None else ""
        paragraphs.append({"text": text, "style": style_value})
    return paragraphs


def build_docx_units(path: Path, source_dir: Path, processed_at: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    relative_path = path.relative_to(source_dir)
    paragraphs = parse_docx_paragraphs(path)
    if not paragraphs:
        raise ValueError("DOCX did not contain extractable text")

    title = paragraphs[0]["text"]
    doc_id = make_doc_id("docx", relative_path, title)
    base = _with_common_metadata(
        {
            "doc_id": doc_id,
            "source_title": title,
            "doc_title": title,
            "source_type": "docx_guides",
            "source_format": "docx",
            "source_path": str(relative_path).replace("\\", "/"),
            "source_file": path.name,
            "source_url": None,
            "deep_link": None,
            "portal_section": relative_path.parts[0] if len(relative_path.parts) > 1 else None,
            "article_number": next((m.group(0).upper() for p in paragraphs if (m := ARTICLE_NUMBER_PATTERN.search(p["text"]))), None),
            "product": None,
            "category": None,
            "attachments": [],
            "last_processed_at": processed_at,
            "source_file_sha256": sha256_file(path),
            "ocr_applied": False,
        },
        relative_path,
        title,
        "docx",
    )

    units: list[dict[str, Any]] = []
    current_title = title
    current_paragraphs: list[str] = []
    unit_index = 0

    for paragraph in paragraphs:
        style = (paragraph.get("style") or "").lower()
        text = paragraph["text"]
        is_heading = style.startswith("heading") or is_heading_candidate(text)
        if is_heading:
            if current_paragraphs:
                unit_text = "\n\n".join(current_paragraphs)
                units.append(
                    {
                        **base,
                        "record_id": f"{doc_id}:unit:{unit_index}",
                        "section_title": current_title,
                        "page_start": None,
                        "page_end": None,
                        "text": unit_text,
                        "text_hash": sha256_text(unit_text),
                    }
                )
                unit_index += 1
                current_paragraphs = []
            current_title = text
            continue
        current_paragraphs.append(text)

    if current_paragraphs:
        unit_text = "\n\n".join(current_paragraphs)
        units.append(
            {
                **base,
                "record_id": f"{doc_id}:unit:{unit_index}",
                "section_title": current_title,
                "page_start": None,
                "page_end": None,
                "text": unit_text,
                "text_hash": sha256_text(unit_text),
            }
        )

    if not units:
        raise ValueError("DOCX did not produce normalized units")
    return base, units


def extract_pdf_units(path: Path, source_dir: Path, processed_at: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    relative_path = path.relative_to(source_dir)
    with fitz.open(path) as document:
        title = clean_text(document.metadata.get("title") or path.stem)
        page_texts: list[str] = []
        ocr_applied = False
        for index in range(document.page_count):
            page = document.load_page(index)
            page_text = clean_text(page.get_text("text"))
            if not page_text or len(page_text) < 40:
                ocr_text = _maybe_ocr_pdf_page(page)
                if len(ocr_text) > len(page_text):
                    page_text = ocr_text
                    ocr_applied = True
            page_texts.append(page_text)

    repeated_top, repeated_bottom = detect_repeated_margin_lines(page_texts)
    doc_id = make_doc_id("pdf", relative_path, title)
    base = _with_common_metadata(
        {
            "doc_id": doc_id,
            "source_title": title,
            "doc_title": title,
            "source_type": "pdf_docs",
            "source_format": "pdf",
            "source_path": str(relative_path).replace("\\", "/"),
            "source_file": path.name,
            "source_url": None,
            "deep_link": None,
            "portal_section": relative_path.parts[0] if len(relative_path.parts) > 1 else None,
            "article_number": None,
            "product": None,
            "category": None,
            "attachments": [],
            "last_processed_at": processed_at,
            "source_file_sha256": sha256_file(path),
            "ocr_applied": ocr_applied,
        },
        relative_path,
        title,
        "pdf",
    )

    units: list[dict[str, Any]] = []
    for page_number, raw_text in enumerate(page_texts, start=1):
        cleaned_page = strip_pdf_artifacts(remove_margin_noise(raw_text, repeated_top, repeated_bottom))
        if not cleaned_page:
            continue
        paragraphs = split_paragraphs(cleaned_page)
        if not paragraphs:
            continue
        section_title = infer_section_title(paragraphs, title)
        if base["article_number"] is None:
            for paragraph in paragraphs:
                match = ARTICLE_NUMBER_PATTERN.search(paragraph)
                if match:
                    base["article_number"] = match.group(0).upper()
                    break
        unit_text = "\n\n".join(paragraphs)
        units.append(
            {
                **base,
                "record_id": f"{doc_id}:page:{page_number}",
                "section_title": section_title,
                "page_start": page_number,
                "page_end": page_number,
                "text": unit_text,
                "text_hash": sha256_text(unit_text),
                "deep_link": doc_deep_link(doc_id, page_start=page_number),
            }
        )

    if not units:
        raise ValueError("No extractable PDF text found")
    return base, units


def extract_html_units(
    path: Path,
    source_dir: Path,
    manifest_entry: dict[str, Any] | None,
    processed_at: str,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    html = path.read_text(encoding="utf-8", errors="ignore")
    soup = BeautifulSoup(html, "html.parser")
    details_node = soup.find(attrs={"name": "Details"})
    embed_node = soup.find("embed", src=True)
    if details_node is None:
        training_result = _extract_training_page_units(soup, path, source_dir, manifest_entry, processed_at)
        if training_result is not None:
            return training_result
        if embed_node and ".pdf" in embed_node.get("src", "").lower():
            embedded_pdf = (path.parent / embed_node["src"]).resolve()
            if embedded_pdf.exists():
                raise ValueError(f"embedded_pdf::{embedded_pdf}")
        raise ValueError("No usable content container found")

    relative_path = path.relative_to(source_dir)
    full_text = clean_text(details_node.get_text("\n", strip=True))
    if not full_text:
        raise ValueError("HTML details area was empty")

    title = None
    for candidate in details_node.find_all(["h1", "h2", "h3", "strong"]):
        candidate_text = clean_text(candidate.get_text(" ", strip=True))
        if candidate_text and not HEADING_ONLY_PATTERN.match(candidate_text):
            title = candidate_text
            break
    if not title:
        title = clean_text((soup.title.get_text(" ", strip=True) if soup.title else "") or path.stem)

    lines = [line.strip() for line in full_text.splitlines() if line.strip()]
    product = next((lines[i + 1] for i, line in enumerate(lines[:-1]) if line.lower() == "product"), None)
    category = next((lines[i + 1] for i, line in enumerate(lines[:-1]) if line.lower() == "category"), None)
    article_match = ARTICLE_NUMBER_PATTERN.search(full_text)
    article_number = article_match.group(0).upper() if article_match else None

    attachments = []
    for link in details_node.find_all("a", href=True):
        href = link["href"].strip()
        name = clean_text(link.get_text(" ", strip=True))
        if href and name:
            attachments.append(
                {
                    "name": name,
                    "href": href,
                    "is_file": bool(re.search(r"\.(pdf|docx?|xlsx?|pptx?)($|\?)", href, re.IGNORECASE)),
                }
            )

    source_url = None
    portal_section = "Uncategorized"
    if manifest_entry:
        source_url = manifest_entry.get("final_url") or manifest_entry.get("url")
        portal_section = manifest_entry.get("section") or portal_section

    doc_id = make_doc_id("html", relative_path, title)
    base = _with_common_metadata(
        {
            "doc_id": doc_id,
            "source_title": title,
            "doc_title": title,
            "source_type": "html_article",
            "source_format": "html",
            "source_path": str(relative_path).replace("\\", "/"),
            "source_file": path.name,
            "source_url": source_url,
            "deep_link": source_url,
            "portal_section": portal_section,
            "article_number": article_number,
            "product": product,
            "category": category,
            "attachments": attachments,
            "last_processed_at": processed_at,
            "source_file_sha256": sha256_file(path),
            "ocr_applied": False,
        },
        relative_path,
        title,
        "html",
    )

    units: list[dict[str, Any]] = []
    current_heading = title
    current_paragraphs: list[str] = []
    unit_index = 0
    for child in details_node.find_all(["h1", "h2", "h3", "p", "li", "table"], recursive=True):
        text = clean_text(child.get_text("\n", strip=True))
        if not text:
            continue
        if child.name in {"h1", "h2", "h3"} and not HEADING_ONLY_PATTERN.match(text):
            if current_paragraphs:
                unit_text = "\n\n".join(current_paragraphs)
                units.append(
                    {
                        **base,
                        "record_id": f"{doc_id}:unit:{unit_index}",
                        "section_title": current_heading,
                        "page_start": None,
                        "page_end": None,
                        "text": unit_text,
                        "text_hash": sha256_text(unit_text),
                    }
                )
                unit_index += 1
                current_paragraphs = []
            current_heading = text
            continue
        if text not in current_paragraphs:
            current_paragraphs.append(text)

    if not units and not current_paragraphs:
        current_paragraphs = split_paragraphs(full_text)
    if current_paragraphs:
        unit_text = "\n\n".join(current_paragraphs)
        units.append(
            {
                **base,
                "record_id": f"{doc_id}:unit:{unit_index}",
                "section_title": current_heading,
                "page_start": None,
                "page_end": None,
                "text": unit_text,
                "text_hash": sha256_text(unit_text),
            }
        )

    if not units:
        raise ValueError("HTML did not produce normalized units")
    return base, units
