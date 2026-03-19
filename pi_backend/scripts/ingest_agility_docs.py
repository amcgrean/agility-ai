import argparse
import json
from collections import Counter
from pathlib import Path

from doc_ingest_chunk import build_mcp_rows, chunk_counts_by_doc, chunk_units
from doc_ingest_extract import build_docx_units, extract_html_units, extract_pdf_units
from doc_ingest_utils import (
    load_manifest_map,
    now_iso,
    read_previous_manifest,
    sha256_file,
    slugify,
    write_jsonl,
)


SUPPORTED_EXTENSIONS = {".html", ".pdf", ".docx"}
SKIPPED_EXTENSIONS = {".doc", ".dotx", ".pptx"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Normalize Agility HTML, PDF, and DOCX content into retrieval-ready JSONL outputs."
    )
    parser.add_argument("--source-dir", required=True, help="Root directory containing source docs.")
    parser.add_argument("--out-dir", required=True, help="Directory for normalized outputs and manifest.")
    parser.add_argument("--corpus-name", default=None, help="Stable corpus name for segmentation/filtering.")
    parser.add_argument("--chunk-size", type=int, default=1100, help="Target chunk size in characters.")
    parser.add_argument("--chunk-overlap", type=int, default=200, help="Chunk overlap in characters.")
    parser.add_argument(
        "--skip-unchanged",
        action="store_true",
        help="Reuse prior manifest hashes to skip unchanged files during reruns.",
    )
    return parser.parse_args()


def build_source_entry(source_path: str, source_file: str, extension: str, file_sha: str, previous: dict, processed_at: str) -> dict:
    return {
        "source_path": source_path,
        "source_file": source_file,
        "extension": extension,
        "sha256": file_sha,
        "previous_sha256": previous.get("sha256"),
        "changed": previous.get("sha256") != file_sha if previous else True,
        "status": "skipped",
        "reason": None,
        "doc_id": None,
        "doc_type": None,
        "normalized_units": 0,
        "chunks": 0,
        "last_processed_at": processed_at,
    }


def main() -> None:
    args = parse_args()
    source_dir = Path(args.source_dir).expanduser().resolve()
    out_dir = Path(args.out_dir).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    corpus_name = args.corpus_name or slugify(source_dir.name)

    processed_at = now_iso()
    manifest_map = load_manifest_map(source_dir)
    previous_manifest = read_previous_manifest(out_dir / "ingestion_manifest.json")

    normalized_units = []
    doc_records = []
    source_manifest = []
    seen_file_hashes: dict[str, str] = {}

    for path in sorted(source_dir.rglob("*")):
        if not path.is_file() or out_dir in path.parents:
            continue

        relative_path = path.relative_to(source_dir)
        source_path_str = str(relative_path).replace("\\", "/")
        extension = path.suffix.lower()
        file_sha = sha256_file(path)
        previous = previous_manifest.get(source_path_str, {})
        source_entry = build_source_entry(source_path_str, path.name, extension, file_sha, previous, processed_at)

        if any(part.startswith(".") for part in relative_path.parts):
            source_entry["reason"] = "hidden path"
            source_manifest.append(source_entry)
            continue
        if "scrape audit" in {part.lower() for part in relative_path.parts}:
            source_entry["reason"] = "audit artifacts"
            source_manifest.append(source_entry)
            continue
        if relative_path.as_posix() in {"site/index.html", "site/packet.html"}:
            source_entry["reason"] = "portal shell page"
            source_manifest.append(source_entry)
            continue
        if extension in SKIPPED_EXTENSIONS:
            source_entry["reason"] = "unsupported legacy office format"
            source_manifest.append(source_entry)
            continue
        if extension not in SUPPORTED_EXTENSIONS:
            source_entry["reason"] = "unsupported extension"
            source_manifest.append(source_entry)
            continue
        if file_sha in seen_file_hashes:
            source_entry["reason"] = f"duplicate file content of {seen_file_hashes[file_sha]}"
            source_manifest.append(source_entry)
            continue
        if args.skip_unchanged and previous.get("sha256") == file_sha and previous.get("status") == "processed":
            source_entry["reason"] = "unchanged since previous manifest"
            source_manifest.append(source_entry)
            seen_file_hashes[file_sha] = source_path_str
            continue

        try:
            if extension == ".html":
                manifest_key = str(relative_path).replace("/", "\\").lower()
                manifest_entry = manifest_map.get(manifest_key)
                try:
                    base_record, units = extract_html_units(path, source_dir, manifest_entry, processed_at)
                except ValueError as exc:
                    if str(exc).startswith("embedded_pdf::"):
                        embedded_pdf = Path(str(exc).split("::", 1)[1])
                        base_record, units = extract_pdf_units(embedded_pdf, source_dir, processed_at)
                        source_entry["reason"] = f"used embedded pdf: {embedded_pdf.name}"
                    else:
                        raise
            elif extension == ".pdf":
                base_record, units = extract_pdf_units(path, source_dir, processed_at)
            else:
                base_record, units = build_docx_units(path, source_dir, processed_at)

            base_record["corpus_name"] = corpus_name
            for unit in units:
                unit["corpus_name"] = corpus_name
            doc_records.append(base_record)
            normalized_units.extend(units)
            source_entry["status"] = "processed"
            source_entry["doc_id"] = base_record["doc_id"]
            source_entry["doc_type"] = base_record["doc_type"]
            source_entry["content_domain"] = base_record.get("content_domain")
            source_entry["access_scope"] = base_record.get("access_scope")
            source_entry["ocr_applied"] = bool(base_record.get("ocr_applied"))
            source_entry["normalized_units"] = len(units)
            source_entry["normalized_text_hashes"] = [unit["text_hash"] for unit in units[:5]]
            seen_file_hashes[file_sha] = source_path_str
        except Exception as exc:
            source_entry["status"] = "error"
            source_entry["reason"] = str(exc)

        source_manifest.append(source_entry)

    chunks = chunk_units(normalized_units, chunk_size=args.chunk_size, overlap=args.chunk_overlap, processed_at=processed_at)
    per_doc_chunk_counts: Counter = chunk_counts_by_doc(chunks)
    for source_entry in source_manifest:
        if source_entry.get("doc_id"):
            source_entry["chunks"] = int(per_doc_chunk_counts.get(source_entry["doc_id"], 0))

    normalized_path = out_dir / "normalized_docs.jsonl"
    chunks_path = out_dir / "doc_chunks.jsonl"
    mcp_export_path = out_dir / "mcp_resources.jsonl"
    manifest_path = out_dir / "ingestion_manifest.json"

    write_jsonl(normalized_path, normalized_units)
    write_jsonl(chunks_path, chunks)
    write_jsonl(mcp_export_path, build_mcp_rows(chunks))

    manifest_payload = {
        "source_dir": str(source_dir),
        "corpus_name": corpus_name,
        "raw_input_preserved": True,
        "normalized_path": str(normalized_path),
        "chunks_path": str(chunks_path),
        "mcp_export_path": str(mcp_export_path),
        "processed_at": processed_at,
        "stats": {
            "document_records": len(doc_records),
            "normalized_records": len(normalized_units),
            "chunk_records": len(chunks),
            "processed_sources": sum(1 for item in source_manifest if item["status"] == "processed"),
            "errored_sources": sum(1 for item in source_manifest if item["status"] == "error"),
            "skipped_sources": sum(1 for item in source_manifest if item["status"] == "skipped"),
            "deduped_sources": sum(1 for item in source_manifest if str(item.get("reason", "")).startswith("duplicate file content")),
        },
        "sources": source_manifest,
    }
    manifest_path.write_text(json.dumps(manifest_payload, indent=2), encoding="utf-8")

    print(json.dumps(manifest_payload["stats"], indent=2))
    print(f"Normalized records: {normalized_path}")
    print(f"Chunk records: {chunks_path}")
    print(f"MCP export: {mcp_export_path}")
    print(f"Manifest: {manifest_path}")


if __name__ == "__main__":
    main()
