# Week 1 Plan — ClinRAG

Hybrid-retrieval RAG over clinical drug labels + a RAGAS eval harness. Benchmark table is the deliverable.

- [x] **Mon** — Extraction: Docling on all 5 DailyMed PDFs, ACCURATE table mode, output in `data/processed/`. Known limitation logged: Table 4 renal-impairment table structurally corrupted in both FAST and ACCURATE modes (see NOTES.md).
- [x] **Wed** — Chunking: two chunkers (fixed-size w/ overlap, structure-aware on headings) over all 5 processed `.md` files. Spot-check chunks manually. Added a third hierarchical + table-aware chunker after spot-checking found Table 4 corruption bleeding into chunks with no header context (see Notes.md Day 2).
- [ ] **Fri (combined Thu+Fri)** — Embeddings + vector store baseline (pick embedding model, naive top-k dense retrieval working), then hybrid retrieval: BM25 + reciprocal rank fusion with dense, wire in a simple LLM call for generation. Plan slipped a day; Sat/Sun shift back accordingly.
- [ ] **Sat (3h)** — RAGAS eval harness: hand-verified question set, faithfulness/relevancy/precision/recall across dense-only vs. hybrid configs.
- [ ] **Sun (3h)** — Ship: README, architecture diagram, benchmark table, documented limitations, demo GIF, commit + push, LinkedIn post.

**If scope slips:** cut reranking first, then the structure-aware chunker (ship fixed-size only), then README polish depth. The RAGAS eval harness does not get cut — it's the identity of this project.
