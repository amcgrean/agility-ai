# PDF Ingestion Plan For Agility Documentation

## Goal

Process Agility PDF documentation into retrieval-ready chunks and publish that content into the Pi-hosted MCP stack so the chatbot and MCP clients can use the same source of truth.

## Recommended Pipeline

1. Collect source PDFs into a stable intake folder outside the repo.
   Example: `/home/amcgrean/agility-ai-data/pdf_sources`

2. Extract text and structure from each PDF.
   Preferred approach:
   - Start with `pymupdf` for reliable text extraction.
   - Fall back to OCR only for image-only pages.
   - Preserve page numbers, section headings, file name, and document version in metadata.

3. Normalize each document into JSONL records.
   Suggested schema per page or block:
   - `doc_id`
   - `doc_title`
   - `source_path`
   - `page_number`
   - `section_title`
   - `text`
   - `document_type`
   - `version`
   - `last_modified`

4. Chunk the normalized text for retrieval.
   Recommended starting point:
   - chunk size: 900 to 1200 characters
   - overlap: 150 to 250 characters
   - never split mid-heading when possible
   - carry forward page and section metadata into every chunk

5. Embed the chunks and merge them into the existing retrieval index.
   Store for each chunk:
   - embedding vector
   - chunk text
   - PDF metadata
   - synthetic URL or MCP resource URI

6. Publish the same normalized/chunked records to the MCP Pi server.
   Two practical options:
   - expose them as MCP resources such as `agility://docs/{doc_id}/{chunk_id}`
   - expose them through an MCP tool that searches the chunk store and returns top matches with metadata

7. Add incremental reprocessing.
   Rebuild only when a PDF hash changes.
   Keep a manifest with:
   - file path
   - SHA-256
   - ingestion timestamp
   - extraction status
   - last indexed version

## Repo Changes To Make Next

1. Add `pi_backend/scripts/ingest_pdfs.py`
   Responsibilities:
   - scan configured PDF source directory
   - extract text
   - normalize records
   - chunk text
   - write JSONL output
   - update a manifest file

2. Add `pi_backend/scripts/build_pdf_index.py`
   Responsibilities:
   - embed new/changed chunks
   - append or rebuild FAISS index
   - append metadata into `agility_meta.jsonl`

3. Add a dedicated metadata field for PDF-origin chunks.
   Suggested values:
   - `source_type: "pdf_docs"`
   - `doc_id`
   - `page_number`
   - `section_title`
   - `source_file`

4. Add a Pi-local config block in the env file.
   Suggested variables:
   - `AGILITY_PDF_SOURCE_DIR`
   - `AGILITY_PDF_NORMALIZED_DIR`
   - `AGILITY_PDF_MANIFEST`
   - `AGILITY_MCP_EXPORT_DIR`

## MCP Pi Server Integration Shape

The cleanest shared architecture is:

- Retrieval index remains optimized for chatbot answering.
- Normalized PDF records are exported separately for MCP consumption.
- MCP server reads the export directory and exposes:
  - resources for direct document browsing
  - a search tool for semantic or keyword lookup

That keeps the chatbot and MCP server aligned without forcing FAISS internals into the MCP layer.

## Quality Gates

- Reject PDFs with extraction coverage below a threshold.
- Log pages with very low text density for OCR review.
- Keep source-to-chunk traceability for every answer citation.
- Run a smoke test set of real Agility questions after each ingestion batch.

## Suggested First Milestone

1. Ingest 3 to 5 high-value PDFs.
2. Export normalized JSONL plus chunk JSONL.
3. Load those chunks into the existing FAISS index.
4. Expose the normalized records to the Pi MCP server as resources.
5. Validate citations, answer quality, and page traceability before bulk ingestion.
