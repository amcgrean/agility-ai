import argparse
import json
import os
from pathlib import Path
from typing import Any

import faiss
import numpy as np
from openai import OpenAI

try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover - optional convenience dependency
    load_dotenv = None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a FAISS index and agility_meta.jsonl from chunked Agility docs."
    )
    parser.add_argument(
        "--chunks-file",
        required=True,
        help="Path to the chunk JSONL produced by ingest_agility_docs.py.",
    )
    parser.add_argument(
        "--out-dir",
        required=True,
        help="Directory where agility.index and agility_meta.jsonl will be written.",
    )
    parser.add_argument(
        "--env-file",
        default=None,
        help="Optional .env file to load before reading OPENAI_API_KEY and EMBED_MODEL.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=64,
        help="Embedding batch size.",
    )
    parser.add_argument(
        "--mcp-export-file",
        default=None,
        help="Optional JSONL file path for MCP-facing resource export.",
    )
    return parser.parse_args()


def load_chunks(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            text = (row.get("text") or "").strip()
            if not text:
                continue
            rows.append(row)
    return rows


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def batched(items: list[dict[str, Any]], size: int):
    for index in range(0, len(items), size):
        yield items[index : index + size]


def build_embedding_inputs(chunks: list[dict[str, Any]]) -> list[str]:
    inputs: list[str] = []
    for chunk in chunks:
        header_bits = [
            chunk.get("source_title") or chunk.get("doc_title") or "",
            chunk.get("section_title") or "",
            chunk.get("portal_section") or "",
            chunk.get("category") or "",
            chunk.get("article_number") or "",
            chunk.get("doc_type") or "",
            chunk.get("corpus_name") or "",
            chunk.get("content_domain") or "",
            chunk.get("access_scope") or "",
            (
                f"pages {chunk['page_start']}-{chunk['page_end']}"
                if chunk.get("page_start") and chunk.get("page_end") and chunk.get("page_start") != chunk.get("page_end")
                else f"page {chunk['page_start'] or chunk['page_number']}"
                if chunk.get("page_start") or chunk.get("page_number")
                else ""
            ),
        ]
        header = " | ".join(bit for bit in header_bits if bit)
        text = chunk.get("text", "")
        inputs.append(f"{header}\n\n{text}" if header else text)
    return inputs


def build_mcp_rows(chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for chunk in chunks:
        doc_id = chunk["doc_id"]
        chunk_id = chunk["chunk_id"]
        rows.append(
            {
                "uri": f"agility://docs/{doc_id}/chunk/{chunk_id}",
                "doc_id": doc_id,
                "chunk_id": chunk_id,
                "chunk_hash": chunk.get("chunk_hash"),
                "title": chunk.get("source_title") or chunk.get("doc_title"),
                "source_title": chunk.get("source_title") or chunk.get("doc_title"),
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


def main() -> None:
    args = parse_args()
    if args.env_file:
        if load_dotenv is None:
            raise SystemExit("python-dotenv is required when using --env-file.")
        load_dotenv(args.env_file)

    api_key = os.getenv("OPENAI_API_KEY")
    embed_model = os.getenv("EMBED_MODEL", "text-embedding-3-small")
    if not api_key:
        raise SystemExit("OPENAI_API_KEY is required to build the FAISS index.")

    chunks_file = Path(args.chunks_file).expanduser().resolve()
    out_dir = Path(args.out_dir).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    chunks = load_chunks(chunks_file)
    if not chunks:
        raise SystemExit(f"No chunks found in {chunks_file}")

    client = OpenAI(api_key=api_key)
    embedding_inputs = build_embedding_inputs(chunks)
    embeddings: list[list[float]] = []

    print(f"Generating embeddings for {len(chunks)} chunks...")
    for i, batch in enumerate(batched(embedding_inputs, args.batch_size)):
        print(f"  Processing batch {i+1}...")
        response = client.embeddings.create(model=embed_model, input=batch)
        embeddings.extend(item.embedding for item in response.data)

    print("Building FAISS index...")
    matrix = np.array(embeddings, dtype="float32")
    faiss.normalize_L2(matrix)
    index = faiss.IndexFlatIP(matrix.shape[1])
    index.add(matrix)

    print("Writing artifacts...")
    meta_path = out_dir / "agility_meta.jsonl"
    index_path = out_dir / "agility.index"
    write_jsonl(meta_path, chunks)
    faiss.write_index(index, str(index_path))

    if args.mcp_export_file:
        mcp_path = Path(args.mcp_export_file).expanduser().resolve()
        mcp_path.parent.mkdir(parents=True, exist_ok=True)
        write_jsonl(mcp_path, build_mcp_rows(chunks))

    summary = {
        "chunks_indexed": len(chunks),
        "embedding_model": embed_model,
        "index_path": str(index_path),
        "meta_path": str(meta_path),
        "mcp_export_path": str(Path(args.mcp_export_file).expanduser().resolve()) if args.mcp_export_file else None,
    }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
