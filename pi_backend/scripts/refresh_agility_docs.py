import argparse
import os
import subprocess
import sys
from pathlib import Path

try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover - optional convenience dependency
    load_dotenv = None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the Agility doc ingestion pipeline end-to-end when environment dependencies are available."
    )
    parser.add_argument("--env-file", default=None, help="Optional env file to load first.")
    parser.add_argument("--source-dir", default=None, help="Override AGILITY_DOC_SOURCE_DIR.")
    parser.add_argument("--output-dir", default=None, help="Override AGILITY_DOC_OUTPUT_DIR.")
    parser.add_argument("--chunks-file", default=None, help="Override AGILITY_DOC_CHUNKS_FILE.")
    parser.add_argument("--mcp-export-file", default=None, help="Override AGILITY_MCP_EXPORT_FILE.")
    parser.add_argument("--corpus-name", default=None, help="Stable corpus name override for ingestion output.")
    parser.add_argument("--chunk-size", type=int, default=1100, help="Target chunk size for ingestion.")
    parser.add_argument("--chunk-overlap", type=int, default=200, help="Chunk overlap for ingestion.")
    parser.add_argument("--batch-size", type=int, default=64, help="Embedding batch size for index building.")
    parser.add_argument(
        "--skip-unchanged",
        action="store_true",
        help="Skip files whose content hash matches the previous ingestion manifest.",
    )
    parser.add_argument(
        "--skip-index",
        action="store_true",
        help="Only run ingestion, even if OPENAI_API_KEY and faiss are available.",
    )
    return parser.parse_args()


def run_command(args: list[str]) -> int:
    print("Running:", " ".join(f'"{arg}"' if " " in arg else arg for arg in args))
    completed = subprocess.run(args, check=False)
    return completed.returncode


def main() -> None:
    args = parse_args()
    if args.env_file:
        if load_dotenv is None:
            raise SystemExit("python-dotenv is required when using --env-file.")
        load_dotenv(args.env_file)

    base_dir = Path(__file__).resolve().parent
    source_dir = args.source_dir or os.getenv("AGILITY_DOC_SOURCE_DIR")
    output_dir = args.output_dir or os.getenv("AGILITY_DOC_OUTPUT_DIR")

    if not source_dir or not output_dir:
        raise SystemExit("AGILITY_DOC_SOURCE_DIR and AGILITY_DOC_OUTPUT_DIR are required.")

    chunks_file = args.chunks_file or os.getenv("AGILITY_DOC_CHUNKS_FILE") or str(Path(output_dir) / "doc_chunks.jsonl")
    mcp_export_file = args.mcp_export_file or os.getenv("AGILITY_MCP_EXPORT_FILE") or str(Path(output_dir) / "mcp_resources.jsonl")

    ingest_script = str(base_dir / "ingest_agility_docs.py")
    build_script = str(base_dir / "build_doc_index.py")

    ingest_cmd = [
        sys.executable,
        ingest_script,
        "--source-dir",
        str(source_dir),
        "--out-dir",
        str(output_dir),
        "--chunk-size",
        str(args.chunk_size),
        "--chunk-overlap",
        str(args.chunk_overlap),
    ]
    if args.skip_unchanged:
        ingest_cmd.append("--skip-unchanged")
    if args.corpus_name:
        ingest_cmd.extend(["--corpus-name", args.corpus_name])
    if run_command(ingest_cmd) != 0:
        raise SystemExit(1)

    if args.skip_index:
        print("Skipping index build by request.")
        return

    try:
        import faiss  # noqa: F401
    except Exception:
        print("Skipping index build because faiss is not installed in this Python environment.")
        return

    if not os.getenv("OPENAI_API_KEY"):
        print("Skipping index build because OPENAI_API_KEY is not set.")
        return

    build_cmd = [
        sys.executable,
        build_script,
        "--chunks-file",
        str(chunks_file),
        "--out-dir",
        str(base_dir.parent),
        "--batch-size",
        str(args.batch_size),
        "--mcp-export-file",
        str(mcp_export_file),
    ]
    if args.env_file:
        build_cmd.extend(["--env-file", args.env_file])
    if run_command(build_cmd) != 0:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
