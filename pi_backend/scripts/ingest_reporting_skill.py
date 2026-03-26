import json
import os
import hashlib
from datetime import datetime, timezone
from pathlib import Path

def get_hash(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()

def main():
    skill_dir = Path(r"C:\Users\indha\OneDrive - Beisser Lumber\ai\skills\agility-reporting")
    out_dir = Path(r"C:\Users\indha\python\agility ai\pi_backend\ingest_output\agility_reporting_v1")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "chunks.jsonl"
    
    chunks = []
    
    files_to_process = [skill_dir / "SKILL.md"]
    ref_dir = skill_dir / "references"
    if ref_dir.exists():
        files_to_process.extend(ref_dir.glob("*.md"))
        
    processed_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    
    for file_path in files_to_process:
        if not file_path.exists():
            continue
            
        text = file_path.read_text(encoding="utf-8")
        title = file_path.name.replace(".md", "")
        doc_id = f"reporting-skill-{title.lower()}"
        chunk_id = 0
        
        chunk_hash = get_hash(f"{doc_id}\n{text}")
        
        chunk = {
            "id": f"{doc_id}:chunk:{chunk_id}",
            "doc_id": doc_id,
            "chunk_id": chunk_id,
            "chunk_hash": chunk_hash,
            "title": file_path.name,
            "source_title": title,
            "doc_title": title,
            "corpus_name": "agility_reporting_v1",
            "source_type": "skill_md",
            "source_format": "md",
            "doc_type": "skill",
            "content_domain": "reporting",
            "access_scope": "internal",
            "source_file": str(file_path),
            "source_path": str(file_path),
            "text": text,
            "last_processed_at": processed_at,
            "page_start": 1,
            "page_end": 1,
            "page_number": 1,
        }
        chunks.append(chunk)

    with out_file.open("w", encoding="utf-8") as f:
        for chunk in chunks:
            f.write(json.dumps(chunk) + "\n")
            
    print(f"Generated {len(chunks)} chunks in {out_file}")

if __name__ == "__main__":
    main()
