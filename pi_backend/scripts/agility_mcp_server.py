import argparse
import json
import os
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

from mcp.server import FastMCP

try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover - optional convenience dependency
    load_dotenv = None


TOKEN_PATTERN = re.compile(r"[a-z0-9]+")
DEFAULT_EXPORT_GLOB = "ingest_output/*/mcp_resources.jsonl"


def tokenize(text: str) -> list[str]:
    return TOKEN_PATTERN.findall((text or "").lower())


def text_preview(text: str, limit: int = 280) -> str:
    compact = " ".join((text or "").split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 3].rstrip() + "..."


def normalize_value(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


class MCPDocStore:
    def __init__(self, export_files: list[Path]):
        self.export_files = export_files
        self.rows: list[dict[str, Any]] = []
        self.by_uri: dict[str, dict[str, Any]] = {}
        self.by_doc_id: dict[str, list[dict[str, Any]]] = defaultdict(list)
        self._load()

    def _load(self) -> None:
        for export_file in self.export_files:
            with export_file.open("r", encoding="utf-8") as handle:
                for line in handle:
                    line = line.strip()
                    if not line:
                        continue
                    row = json.loads(line)
                    row["corpus_file"] = export_file.name
                    tokens = tokenize(
                        " ".join(
                            filter(
                                None,
                                [
                    row.get("title", ""),
                    row.get("source_title", ""),
                    row.get("section_title", ""),
                    row.get("portal_section", ""),
                    row.get("category", ""),
                    row.get("article_number", ""),
                                    row.get("text", ""),
                                ],
                            )
                        )
                    )
                    row["_token_set"] = set(tokens)
                    row["_title_tokens"] = set(tokenize(row.get("title", "")))
                    uri = row["uri"]
                    self.rows.append(row)
                    self.by_uri[uri] = row
                    self.by_doc_id[row["doc_id"]].append(row)

        for doc_rows in self.by_doc_id.values():
            doc_rows.sort(key=lambda item: int(item.get("chunk_id", 0)))

    def corpus_summary(self) -> dict[str, Any]:
        return {
            "export_files": [str(path) for path in self.export_files],
            "chunk_count": len(self.rows),
            "doc_count": len(self.by_doc_id),
            "corpora": sorted({row.get("corpus_name") for row in self.rows if row.get("corpus_name")}),
            "source_types": sorted({row.get("source_type") for row in self.rows if row.get("source_type")}),
            "content_domains": sorted({row.get("content_domain") for row in self.rows if row.get("content_domain")}),
            "access_scopes": sorted({row.get("access_scope") for row in self.rows if row.get("access_scope")}),
            "portal_sections": sorted({row.get("portal_section") for row in self.rows if row.get("portal_section")}),
        }

    def search(
        self,
        query: str,
        top_k: int = 5,
        corpus_name: str | None = None,
        source_type: str | None = None,
        content_domain: str | None = None,
        access_scope: str | None = None,
        portal_section: str | None = None,
        source_file_contains: str | None = None,
    ) -> list[dict[str, Any]]:
        query_tokens = set(tokenize(query))
        if not query_tokens:
            return []

        desired_corpus = normalize_value(corpus_name)
        desired_source_type = normalize_value(source_type)
        desired_domain = normalize_value(content_domain)
        desired_access_scope = normalize_value(access_scope)
        desired_section = normalize_value(portal_section)
        desired_file = normalize_value(source_file_contains)

        scored: list[tuple[float, dict[str, Any]]] = []
        for row in self.rows:
            if desired_corpus and row.get("corpus_name") != desired_corpus:
                continue
            if desired_source_type and row.get("source_type") != desired_source_type:
                continue
            if desired_domain and row.get("content_domain") != desired_domain:
                continue
            if desired_access_scope and row.get("access_scope") != desired_access_scope:
                continue
            if desired_section and (row.get("portal_section") or "").lower() != desired_section.lower():
                continue
            if desired_file and desired_file.lower() not in (row.get("source_file") or "").lower():
                continue

            overlap = query_tokens & row["_token_set"]
            if not overlap:
                continue

            title_overlap = query_tokens & row["_title_tokens"]
            score = float(len(overlap)) + (2.5 * len(title_overlap))

            title = (row.get("title") or "").lower()
            text = (row.get("text") or "").lower()
            lowered_query = query.lower()
            if lowered_query and lowered_query in title:
                score += 4.0
            elif lowered_query and lowered_query in text:
                score += 2.0

            if row.get("article_number") and row["article_number"].lower() in lowered_query:
                score += 3.0

            scored.append((score, row))

        scored.sort(
            key=lambda item: (
                item[0],
                item[1].get("title") or "",
                -(int(item[1].get("chunk_id", 0))),
            ),
            reverse=True,
        )

        results: list[dict[str, Any]] = []
        for score, row in scored[: max(1, min(top_k, 20))]:
            results.append(
                {
                    "uri": row["uri"],
                    "doc_id": row["doc_id"],
                    "chunk_id": row["chunk_id"],
                    "title": row.get("title"),
                    "source_title": row.get("source_title"),
                    "corpus_name": row.get("corpus_name"),
                    "section_title": row.get("section_title"),
                    "source_type": row.get("source_type"),
                    "source_format": row.get("source_format"),
                    "doc_type": row.get("doc_type"),
                    "content_domain": row.get("content_domain"),
                    "access_scope": row.get("access_scope"),
                    "portal_section": row.get("portal_section"),
                    "category": row.get("category"),
                    "article_number": row.get("article_number"),
                    "page_start": row.get("page_start"),
                    "page_end": row.get("page_end"),
                    "page_number": row.get("page_number"),
                    "source_file": row.get("source_file"),
                    "source_url": row.get("source_url"),
                    "deep_link": row.get("deep_link"),
                    "url": row.get("url"),
                    "score": round(score, 3),
                    "preview": text_preview(row.get("text", "")),
                }
            )
        return results

    def get_resource_text(self, uri: str) -> str:
        row = self.by_uri.get(uri)
        if not row:
            raise KeyError(uri)

        header_lines = [
            f"Title: {row.get('title') or 'Untitled'}",
            f"Section Title: {row.get('section_title') or 'N/A'}",
            f"URI: {row['uri']}",
            f"Doc ID: {row.get('doc_id')}",
            f"Chunk ID: {row.get('chunk_id')}",
        ]
        optional_pairs = [
            ("Source Type", row.get("source_type")),
            ("Source Format", row.get("source_format")),
            ("Doc Type", row.get("doc_type")),
            ("Corpus", row.get("corpus_name")),
            ("Content Domain", row.get("content_domain")),
            ("Access Scope", row.get("access_scope")),
            ("Portal Section", row.get("portal_section")),
            ("Category", row.get("category")),
            ("Article Number", row.get("article_number")),
            ("Page Start", row.get("page_start")),
            ("Page End", row.get("page_end")),
            ("Page Number", row.get("page_number")),
            ("Source File", row.get("source_file")),
            ("Source Path", row.get("source_path")),
            ("Source URL", row.get("source_url")),
            ("Deep Link", row.get("deep_link")),
            ("URL", row.get("url")),
        ]
        for label, value in optional_pairs:
            if value not in (None, ""):
                header_lines.append(f"{label}: {value}")

        return "\n".join(header_lines) + "\n\nText:\n" + (row.get("text") or "")

    def get_document_chunks(self, doc_id: str, limit: int = 20) -> list[dict[str, Any]]:
        rows = self.by_doc_id.get(doc_id, [])
        return [
            {
                "uri": row["uri"],
                "chunk_id": row["chunk_id"],
                "page_number": row.get("page_number"),
                "preview": text_preview(row.get("text", ""), limit=220),
            }
            for row in rows[: max(1, min(limit, 100))]
        ]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run an MCP server over exported Agility doc resources.")
    parser.add_argument("--env-file", default=None, help="Optional env file to load first.")
    parser.add_argument(
        "--export-file",
        action="append",
        default=[],
        help="Explicit MCP export JSONL file. Can be passed multiple times.",
    )
    parser.add_argument(
        "--transport",
        choices=["stdio", "streamable-http", "sse"],
        default="stdio",
        help="FastMCP transport to use.",
    )
    return parser.parse_args()


def resolve_export_files(explicit_files: list[str]) -> list[Path]:
    candidates = [Path(path).expanduser().resolve() for path in explicit_files if path]
    env_value = os.getenv("AGILITY_MCP_EXPORT_FILE", "")
    if env_value:
        for piece in env_value.split(","):
            piece = piece.strip()
            if piece:
                candidates.append(Path(piece).expanduser().resolve())

    if not candidates:
        base = Path(__file__).resolve().parent.parent
        candidates.extend(sorted(base.glob(DEFAULT_EXPORT_GLOB)))

    unique: list[Path] = []
    seen = set()
    for candidate in candidates:
        key = str(candidate).lower()
        if key in seen or not candidate.exists():
            continue
        seen.add(key)
        unique.append(candidate)
    return unique


def build_server(store: MCPDocStore) -> FastMCP:
    mcp = FastMCP("Agility Docs MCP")

    @mcp.tool(description="Search Agility documentation chunks across exported corpora.")
    def search_docs(
        query: str,
        top_k: int = 5,
        corpus_name: str | None = None,
        source_type: str | None = None,
        content_domain: str | None = None,
        access_scope: str | None = None,
        portal_section: str | None = None,
        source_file_contains: str | None = None,
    ) -> dict[str, Any]:
        return {
            "query": query,
            "results": store.search(
                query=query,
                top_k=top_k,
                corpus_name=corpus_name,
                source_type=source_type,
                content_domain=content_domain,
                access_scope=access_scope,
                portal_section=portal_section,
                source_file_contains=source_file_contains,
            ),
        }

    @mcp.tool(description="Read one exported Agility doc chunk by its agility:// URI.")
    def get_doc_chunk(uri: str) -> dict[str, Any]:
        row = store.by_uri.get(uri)
        if not row:
            return {"found": False, "uri": uri}
        return {
            "found": True,
            "uri": uri,
            "doc_id": row.get("doc_id"),
                "chunk_id": row.get("chunk_id"),
                "title": row.get("title"),
                "corpus_name": row.get("corpus_name"),
                "section_title": row.get("section_title"),
                "page_number": row.get("page_number"),
                "page_start": row.get("page_start"),
                "page_end": row.get("page_end"),
                "content_domain": row.get("content_domain"),
                "access_scope": row.get("access_scope"),
                "source_file": row.get("source_file"),
                "source_url": row.get("source_url"),
                "deep_link": row.get("deep_link"),
                "url": row.get("url"),
                "text": row.get("text"),
            }

    @mcp.tool(description="List chunk URIs for a document id so callers can browse a document sequentially.")
    def list_doc_chunks(doc_id: str, limit: int = 20) -> dict[str, Any]:
        return {"doc_id": doc_id, "chunks": store.get_document_chunks(doc_id, limit=limit)}

    @mcp.tool(description="Return corpus-level stats and source coverage for this Agility doc server.")
    def corpus_stats() -> dict[str, Any]:
        return store.corpus_summary()

    @mcp.resource(
        "agility://docs/{doc_id}/chunk/{chunk_id}",
        name="Agility Doc Chunk",
        mime_type="text/plain",
        description="Read a specific Agility documentation chunk by URI.",
    )
    def resource_doc_chunk(doc_id: str, chunk_id: str) -> str:
        uri = f"agility://docs/{doc_id}/chunk/{chunk_id}"
        return store.get_resource_text(uri)

    return mcp


def main() -> None:
    args = parse_args()
    if args.env_file:
        if load_dotenv is None:
            raise SystemExit("python-dotenv is required when using --env-file.")
        load_dotenv(args.env_file)

    export_files = resolve_export_files(args.export_file)
    if not export_files:
        raise SystemExit("No MCP export JSONL files were found.")

    store = MCPDocStore(export_files)
    server = build_server(store)
    server.run(args.transport)


if __name__ == "__main__":
    main()
