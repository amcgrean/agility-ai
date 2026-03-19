from collections import Counter
from typing import Any

from doc_ingest_utils import doc_deep_link, sha256_text, split_paragraphs


def group_by_doc(units: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for unit in units:
        grouped.setdefault(unit["doc_id"], []).append(unit)
    for doc_units in grouped.values():
        doc_units.sort(
            key=lambda item: (
                item.get("page_start") if item.get("page_start") is not None else 10**9,
                item.get("record_id", ""),
            )
        )
    return grouped


def chunk_units(units: list[dict[str, Any]], chunk_size: int, overlap: int, processed_at: str) -> list[dict[str, Any]]:
    chunks: list[dict[str, Any]] = []
    seen_chunk_hashes: set[str] = set()

    for doc_id, doc_units in group_by_doc(units).items():
        active_texts: list[str] = []
        active_pages: list[int] = []
        active_section: str | None = None
        chunk_index = 0

        def overlap_paragraphs(paragraphs: list[str]) -> list[str]:
            if overlap <= 0 or not paragraphs:
                return []
            selected: list[str] = []
            total = 0
            for paragraph in reversed(paragraphs):
                paragraph = paragraph.strip()
                if not paragraph:
                    continue
                selected.insert(0, paragraph)
                total += len(paragraph) + 2
                if total >= overlap:
                    break
            return selected

        def flush_chunk() -> None:
            nonlocal active_texts, active_pages, active_section, chunk_index
            if not active_texts:
                return
            chunk_text = "\n\n".join(active_texts).strip()
            if not chunk_text:
                active_texts = []
                active_pages = []
                return

            base = doc_units[0]
            page_values = sorted({page for page in active_pages if page is not None})
            page_start = page_values[0] if page_values else None
            page_end = page_values[-1] if page_values else None
            chunk_hash = sha256_text(f"{doc_id}\n{chunk_text}")
            if chunk_hash in seen_chunk_hashes:
                active_texts = []
                active_pages = []
                return
            seen_chunk_hashes.add(chunk_hash)

            if page_start is not None:
                deep_link = doc_deep_link(doc_id, page_start=page_start, chunk_id=chunk_index)
            else:
                deep_link = base.get("source_url") or doc_deep_link(doc_id, chunk_id=chunk_index)

            chunks.append(
                {
                    "id": f"{doc_id}:chunk:{chunk_index}",
                    "chunk_id": chunk_index,
                    "chunk_hash": chunk_hash,
                    "doc_id": doc_id,
                    "source_title": base["source_title"],
                    "doc_title": base["doc_title"],
                    "corpus_name": base.get("corpus_name"),
                    "source_file": base["source_file"],
                    "source_path": base["source_path"],
                    "source_type": base["source_type"],
                    "source_format": base["source_format"],
                    "doc_type": base["doc_type"],
                    "content_domain": base.get("content_domain"),
                    "access_scope": base.get("access_scope"),
                    "ocr_applied": bool(base.get("ocr_applied")),
                    "source_url": base.get("source_url"),
                    "deep_link": deep_link,
                    "url": deep_link,
                    "portal_section": base.get("portal_section"),
                    "product": base.get("product"),
                    "category": base.get("category"),
                    "article_number": base.get("article_number"),
                    "section_title": active_section or base["source_title"],
                    "page_start": page_start,
                    "page_end": page_end,
                    "page_number": page_start if page_start == page_end else page_start,
                    "last_processed_at": processed_at,
                    "text": chunk_text,
                }
            )
            chunk_index += 1
            active_texts = overlap_paragraphs(active_texts)
            active_pages = []

        for unit in doc_units:
            unit_text = unit["text"]
            unit_section = unit.get("section_title") or unit["source_title"]
            unit_paragraphs = split_paragraphs(unit_text) or [unit_text]

            for paragraph in unit_paragraphs:
                proposed = "\n\n".join(active_texts + [paragraph]).strip()
                section_changed = active_section and unit_section != active_section and len("\n\n".join(active_texts)) > int(chunk_size * 0.45)
                if active_texts and (len(proposed) > chunk_size or section_changed):
                    flush_chunk()
                if not active_section or not active_texts:
                    active_section = unit_section
                active_texts.append(paragraph)
                if unit.get("page_start") is not None:
                    page_end = int(unit.get("page_end") or unit["page_start"])
                    active_pages.extend(range(int(unit["page_start"]), page_end + 1))
            if len("\n\n".join(active_texts)) >= chunk_size:
                flush_chunk()

        flush_chunk()

    return chunks


def build_mcp_rows(chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for chunk in chunks:
        rows.append(
            {
                "uri": f"agility://docs/{chunk['doc_id']}/chunk/{chunk['chunk_id']}",
                "doc_id": chunk["doc_id"],
                "chunk_id": chunk["chunk_id"],
                "chunk_hash": chunk["chunk_hash"],
                "title": chunk["source_title"],
                "source_title": chunk["source_title"],
                "corpus_name": chunk.get("corpus_name"),
                "section_title": chunk.get("section_title"),
                "source_type": chunk.get("source_type"),
                "source_format": chunk.get("source_format"),
                "doc_type": chunk.get("doc_type"),
                "content_domain": chunk.get("content_domain"),
                "access_scope": chunk.get("access_scope"),
                "ocr_applied": chunk.get("ocr_applied"),
                "source_path": chunk.get("source_path"),
                "source_file": chunk.get("source_file"),
                "source_url": chunk.get("source_url"),
                "deep_link": chunk.get("deep_link"),
                "url": chunk.get("url"),
                "portal_section": chunk.get("portal_section"),
                "category": chunk.get("category"),
                "article_number": chunk.get("article_number"),
                "page_start": chunk.get("page_start"),
                "page_end": chunk.get("page_end"),
                "page_number": chunk.get("page_number"),
                "last_processed_at": chunk.get("last_processed_at"),
                "text": chunk.get("text"),
            }
        )
    return rows


def chunk_counts_by_doc(chunks: list[dict[str, Any]]) -> Counter:
    return Counter(chunk["doc_id"] for chunk in chunks)
