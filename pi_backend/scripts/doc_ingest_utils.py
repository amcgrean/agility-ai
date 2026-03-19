import hashlib
import json
import re
import unicodedata
from collections import Counter
from datetime import datetime, timezone
from html import unescape
from pathlib import Path
from typing import Any


ARTICLE_NUMBER_PATTERN = re.compile(r"\b(?:AR|VR|V)\d{3,6}\b", re.IGNORECASE)
HEADING_ONLY_PATTERN = re.compile(r"^(article:?|article information|details|attachments?)$", re.IGNORECASE)
SENTENCE_END_PATTERN = re.compile(r"[.!?:)\]\"']$")
SECTION_SPLIT_PATTERN = re.compile(r"\n{2,}")
LIST_BULLET_PATTERN = re.compile(r"^\s*(?:[-*•]|[0-9]+[.)]|[A-Z][.)])\s+")
PAGE_NUMBER_ONLY_PATTERN = re.compile(r"^(?:page\s+)?\d{1,4}(?:\s+of\s+\d{1,4})?$", re.IGNORECASE)
PAGE_FOOTER_PATTERN = re.compile(r"^page\s+\d{1,4}\s+of\s+\d{1,4}$", re.IGNORECASE)


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    normalized = normalized.lower()
    normalized = re.sub(r"[^a-z0-9]+", "-", normalized).strip("-")
    return normalized or "document"


def clean_text(value: str) -> str:
    text = unicodedata.normalize("NFKC", unescape(value or ""))
    replacements = {
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2013": "-",
        "\u2014": "-",
        "\u2022": "*",
        "\u00a0": " ",
        "â€¢": "*",
        "â€“": "-",
        "â€”": "-",
        "â€˜": "'",
        "â€™": "'",
        "â€œ": '"',
        "â€\x9d": '"',
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    text = text.replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def normalize_line(line: str) -> str:
    return clean_text(line)


def dedupe_preserve_order(items: list[str]) -> list[str]:
    seen = set()
    deduped: list[str] = []
    for item in items:
        key = item.lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


def is_heading_candidate(line: str) -> bool:
    stripped = normalize_line(line)
    if not stripped or HEADING_ONLY_PATTERN.match(stripped) or len(stripped) > 120:
        return False
    if stripped.endswith(".") and len(stripped.split()) > 6:
        return False
    if LIST_BULLET_PATTERN.match(stripped):
        return False

    alpha_chars = [char for char in stripped if char.isalpha()]
    if not alpha_chars:
        return False
    upper_ratio = sum(1 for char in alpha_chars if char.isupper()) / max(1, len(alpha_chars))
    if upper_ratio > 0.8 and len(stripped.split()) <= 10:
        return True

    words = stripped.split()
    title_case_words = sum(1 for word in words if word[:1].isupper())
    if len(words) <= 12 and title_case_words >= max(1, int(len(words) * 0.7)):
        return True

    return bool(ARTICLE_NUMBER_PATTERN.search(stripped))


def repair_wrapped_lines(text: str) -> str:
    lines = [line.rstrip() for line in clean_text(text).splitlines()]
    repaired: list[str] = []
    current = ""

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            if current:
                repaired.append(current)
                current = ""
            continue
        if not current:
            current = line
            continue

        should_join = (
            not SENTENCE_END_PATTERN.search(current)
            and not is_heading_candidate(line)
            and not LIST_BULLET_PATTERN.match(line)
            and line[:1].islower()
        )
        if should_join:
            current = f"{current} {line}"
        else:
            repaired.append(current)
            current = line

    if current:
        repaired.append(current)
    return "\n\n".join(repaired)


def split_paragraphs(text: str) -> list[str]:
    repaired = repair_wrapped_lines(text)
    return [paragraph.strip() for paragraph in SECTION_SPLIT_PATTERN.split(repaired) if paragraph.strip()]


def detect_repeated_margin_lines(page_texts: list[str]) -> tuple[set[str], set[str]]:
    top_counter: Counter[str] = Counter()
    bottom_counter: Counter[str] = Counter()
    populated_pages = 0

    for text in page_texts:
        lines = [normalize_line(line) for line in text.splitlines() if normalize_line(line)]
        if not lines:
            continue
        populated_pages += 1
        for line in dedupe_preserve_order(lines[:2]):
            top_counter[line] += 1
        for line in dedupe_preserve_order(lines[-2:]):
            bottom_counter[line] += 1

    if populated_pages < 3:
        return set(), set()

    threshold = max(3, int(populated_pages * 0.35))
    repeated_top = {line for line, count in top_counter.items() if count >= threshold and len(line) < 120}
    repeated_bottom = {line for line, count in bottom_counter.items() if count >= threshold and len(line) < 120}
    return repeated_top, repeated_bottom


def remove_margin_noise(text: str, repeated_top: set[str], repeated_bottom: set[str]) -> str:
    lines = [normalize_line(line) for line in text.splitlines()]
    while lines and (not lines[0] or lines[0] in repeated_top):
        lines.pop(0)
    while lines and (not lines[-1] or lines[-1] in repeated_bottom):
        lines.pop()
    return "\n".join(lines)


def strip_pdf_artifacts(text: str) -> str:
    cleaned_lines: list[str] = []
    lines = [normalize_line(line) for line in text.splitlines()]

    for index, line in enumerate(lines):
        if not line:
            cleaned_lines.append("")
            continue

        prev_line = lines[index - 1] if index > 0 else ""
        next_line = lines[index + 1] if index + 1 < len(lines) else ""
        if PAGE_FOOTER_PATTERN.match(line):
            continue
        if PAGE_NUMBER_ONLY_PATTERN.match(line) and prev_line == "" and next_line == "":
            continue
        if PAGE_NUMBER_ONLY_PATTERN.match(line) and (prev_line == "" or is_heading_candidate(next_line)):
            continue
        cleaned_lines.append(line)

    return clean_text("\n".join(cleaned_lines))


def infer_section_title(paragraphs: list[str], fallback: str) -> str:
    for paragraph in paragraphs:
        first_line = paragraph.splitlines()[0].strip()
        if is_heading_candidate(first_line):
            return first_line
    return fallback


def make_doc_id(source_type: str, relative_path: Path, title: str | None = None) -> str:
    stem = title or relative_path.stem
    return f"{source_type}-{slugify(stem)}-{sha256_text(str(relative_path).lower())[:10]}"


def doc_deep_link(doc_id: str, page_start: int | None = None, chunk_id: int | None = None) -> str:
    uri = f"agility://docs/{doc_id}"
    if page_start is not None:
        uri += f"/page/{page_start}"
    if chunk_id is not None:
        uri += f"/chunk/{chunk_id}"
    return uri


def classify_doc_type(relative_path: Path, title: str | None, source_format: str) -> str:
    title_text = f"{relative_path.as_posix()} {(title or '')}".lower()
    if "training" in title_text or "webinar" in title_text or "video" in title_text:
        return "training_video"
    if "faq" in title_text:
        return "faq"
    if "handbook" in title_text:
        return "handbook"
    if "quick reference" in title_text or "quick guide" in title_text:
        return "quick_reference"
    if "checklist" in title_text:
        return "checklist"
    if "mobile" in title_text:
        return "mobile_guide"
    if "policy" in title_text:
        return "policy"
    if "dashboard" in title_text:
        return "dashboard_guide"
    if source_format == "html":
        return "portal_article"
    if source_format == "docx":
        return "internal_guide"
    return "pdf_guide"


def infer_content_domain(relative_path: Path, title: str | None, source_format: str) -> str:
    haystack = f"{relative_path.as_posix()} {(title or '')}".lower()
    if source_format == "docx" or "internal" in haystack:
        return "internal_docs"
    if "building" in haystack or "jobsite" in haystack or "construction" in haystack:
        return "building_docs"
    if "training" in haystack or "video" in haystack or "webinar" in haystack:
        return "training_docs"
    return "product_docs"


def infer_access_scope(relative_path: Path, title: str | None, source_format: str) -> str:
    haystack = f"{relative_path.as_posix()} {(title or '')}".lower()
    restricted_markers = (
        "password",
        "payroll",
        "hr",
        "human resources",
        "salary",
        "finance",
        "financial",
        "security",
        "customer data",
    )
    if any(marker in haystack for marker in restricted_markers):
        return "restricted"
    if source_format == "docx" or "internal" in haystack or "building" in haystack:
        return "internal"
    return "standard"


def load_manifest_map(source_dir: Path) -> dict[str, dict[str, Any]]:
    manifest_path = source_dir / "site" / "manifest.json"
    if not manifest_path.exists():
        return {}
    data = json.loads(manifest_path.read_text(encoding="utf-8", errors="ignore"))
    manifest_map: dict[str, dict[str, Any]] = {}
    for entry in data:
        local_path = entry.get("local_path")
        if not local_path:
            continue
        normalized = local_path.replace("/", "\\").lower()
        manifest_map[normalized] = entry
        manifest_map[f"site\\{normalized}"] = entry
    return manifest_map


def read_previous_manifest(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    previous = {}
    for item in payload.get("sources", []):
        source_path = item.get("source_path")
        if source_path:
            previous[source_path] = item
    return previous


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
