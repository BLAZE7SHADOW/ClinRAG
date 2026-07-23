# ClinRAG

A hybrid-retrieval RAG system over clinical drug labels (DailyMed FDA labels), with a RAGAS evaluation harness as the actual deliverable — not just a demo.

**Status: in progress.** See `WEEK1_PLAN.md` for the day-by-day build plan and what's done vs. pending.

## What's built so far

1. **Extraction** (`notebook/extract.py`) — Docling converts DailyMed PDFs to markdown, ACCURATE table mode.
2. **Chunking** (`notebook/chunk.py`) — three strategies: fixed-size w/ token overlap, structure-aware on markdown headers, and a hierarchical combination with table-aware splitting (keeps markdown tables intact instead of cutting through them).
3. **Embeddings + dense retrieval** (`notebook/embed.py`) — Cohere Embed v4 via AWS Bedrock, FAISS (`IndexFlatL2`) for nearest-neighbor search. Naive top-k dense retrieval baseline.

## Not built yet

- Hybrid retrieval (BM25 + reciprocal rank fusion with dense)
- LLM generation step
- RAGAS evaluation (faithfulness, answer relevancy, context precision/recall)

## Known limitations

Logged in `Notes.md` as they're found, not hidden. Notable one: a renal-impairment dosing table in one source PDF is structurally corrupted by Docling's extraction (row/header misalignment) — chunking mitigates part of this (keeps table rows atomic) but can't fully repair it, since the damage happens upstream.

## Setup

```
uv sync
```

Embeddings require AWS credentials with Bedrock access to `cohere.embed-v4:0` (region `us-east-1`), configured via `aws configure` or environment variables.

## Running the pipeline

```
cd notebook
uv run python extract.py   # data/raw/*.pdf -> data/processed/*.md
uv run python chunk.py     # prints chunk counts/samples for all three strategies
uv run python embed.py     # builds a FAISS index over all chunks, runs a test query
```
