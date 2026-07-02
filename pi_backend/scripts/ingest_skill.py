"""Generic skill-corpus ingestion.

Turns a skill folder (SKILL.md + references/*.md) into a chunks.jsonl corpus
that server.py loads at startup for a skill expert mode.

Usage:
    python pi_backend/scripts/ingest_skill.py skills/agility-sales-orders
    python pi_backend/scripts/ingest_skill.py <skill-dir> \
        --corpus-name my_skill_v1 --content-domain my_domain

Defaults derive from the skill folder name:
    skills/agility-sales-orders -> corpus agility_sales_orders_v1,
    content domain sales_orders, output
    pi_backend/ingest_output/agility_sales_orders_v1/chunks.jsonl

Each markdown file becomes a single chunk — skill corpora are small and are
sent to the LLM in full (no FAISS), so file-level chunks keep source
attribution simple.
"""

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def get_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def default_corpus_name(skill_dir: Path) -> str:
    return skill_dir.name.replace("-", "_") + "_v1"


def default_content_domain(skill_dir: Path) -> str:
    name = skill_dir.name
    if name.startswith("agility-"):
        name = name[len("agility-"):]
    return name.replace("-", "_")


def collect_skill_files(skill_dir: Path) -> list[Path]:
    files = []
    skill_md = skill_dir / "SKILL.md"
    if skill_md.exists():
        files.append(skill_md)
    ref_dir = skill_dir / "references"
    if ref_dir.exists():
        files.extend(sorted(ref_dir.glob("*.md")))
    return files


def relative_source_path(file_path: Path) -> str:
    try:
        return file_path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return str(file_path)


def ingest_skill(
    skill_dir: Path,
    corpus_name: str | None = None,
    content_domain: str | None = None,
    out_dir: Path | None = None,
) -> Path:
    skill_dir = Path(skill_dir)
    if not skill_dir.exists():
        raise SystemExit(f"Skill directory not found: {skill_dir}")

    corpus_name = corpus_name or default_corpus_name(skill_dir)
    content_domain = content_domain or default_content_domain(skill_dir)
    out_dir = Path(out_dir) if out_dir else REPO_ROOT / "pi_backend" / "ingest_output" / corpus_name
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "chunks.jsonl"

    files = collect_skill_files(skill_dir)
    if not files:
        raise SystemExit(f"No SKILL.md or references/*.md found in {skill_dir}")

    processed_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    chunks = []

    for file_path in files:
        text = file_path.read_text(encoding="utf-8")
        title = file_path.stem
        doc_id = f"{corpus_name}:{title.lower()}"
        source_path = relative_source_path(file_path)

        chunks.append(
            {
                "id": f"{doc_id}:chunk:0",
                "doc_id": doc_id,
                "chunk_id": 0,
                "chunk_hash": get_hash(f"{doc_id}\n{text}"),
                "title": file_path.name,
                "source_title": title,
                "doc_title": title,
                "corpus_name": corpus_name,
                "source_type": "skill_md",
                "source_format": "md",
                "doc_type": "skill",
                "content_domain": content_domain,
                "access_scope": "internal",
                "source_file": source_path,
                "source_path": source_path,
                "text": text,
                "last_processed_at": processed_at,
                "page_start": 1,
                "page_end": 1,
                "page_number": 1,
            }
        )

    with out_file.open("w", encoding="utf-8") as f:
        for chunk in chunks:
            f.write(json.dumps(chunk) + "\n")

    print(f"Ingested {len(chunks)} chunks from {skill_dir} -> {out_file}")
    return out_file


def main():
    parser = argparse.ArgumentParser(description="Ingest a skill folder into a chunks.jsonl corpus")
    parser.add_argument("skill_dir", type=Path, help="Skill folder containing SKILL.md and references/")
    parser.add_argument("--corpus-name", help="Corpus name (default: <folder>_v1 with dashes as underscores)")
    parser.add_argument("--content-domain", help="Content domain tag (default: derived from folder name)")
    parser.add_argument("--out-dir", type=Path, help="Output directory (default: pi_backend/ingest_output/<corpus-name>)")
    args = parser.parse_args()

    ingest_skill(
        skill_dir=args.skill_dir,
        corpus_name=args.corpus_name,
        content_domain=args.content_domain,
        out_dir=args.out_dir,
    )


if __name__ == "__main__":
    main()
