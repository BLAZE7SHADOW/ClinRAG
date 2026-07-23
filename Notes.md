# Day 1 — Extraction notes (Docling, metformin.pdf)

## What Docling got right
- Section headings detected in the right order (DOSAGE, CONTRAINDICATIONS, WARNINGS, etc.)
- One patient-info checklist table came out clean, 2 columns, readable

## What Docling got wrong
- Another checklist merged multiple bullets into one cell (`o headache o drowsiness o weakness` all mashed together)
- OCR garbage from barcode/pill images leaked into the text (`Sm 3 5 3 2694 6789 8`)
- Bullet order scrambled in a few places
- Random stray characters showing up
- WARNINGS AND PRECAUTIONS section came out broken/fragmented
- Some duplication — "USE IN SPECIFIC POPULATIONS" appears twice back to back. Partly expected (Highlights vs Full Prescribing Info repeat section names) but didn't dig into whether all of it is expected.
- **Table 4 (renal impairment dosing)** — the bad one. Mild/Moderate/Severe rows missing or scrambled. This is dosing data, so a broken table here isn't cosmetic — it's the kind of thing that could feed a wrong dosing answer.

Tried ACCURATE mode instead of default — same corruption. Not a fast-mode shortcut, it's this table shape (multi-level header + footnote letters) Docling can't handle. Logging it, not chasing a fix today.

## Chunking plan
Two chunkers: fixed-size w/ overlap (500 tokens / 50 overlap), and structure-aware on headings. Compare both later, don't pick a winner yet.

## Build order
Extraction on all 5 files first. Don't touch chunking until extraction is trustworthy across the whole set, not just metformin.

## Risks to watch
- OCR-garbage chunks could get embedded and retrieved like real content. Need some kind of filter before they hit the vector store.
- Corrupted tables (Table 4) won't throw an error — they'll just get embedded and retrieved as-is, and the LLM could answer confidently off broken data.
- Duplicate sections waste chunk budget, could cause redundant near-identical hits. Maybe dedupe later.

# Day 2 — Chunking (chunk.py)

Built 3 chunkers, ran all of them on all 5 processed files:
- `chunk_fixed` — fixed-size, token-based, with overlap
- `chunk_by_headers` — splits on markdown headers
- `chunk_hierarchical` — headers first, then sub-splits anything still too big

## Bug: empty first chunk
3 of 5 files (amlodipine, lisinopril, amoxicillin) — the first chunk from `chunk_by_headers` is just `"----------"`. Nothing else. Docling puts a separator line before the first real header, and the splitter treats everything before the first header as its own chunk — here that's just the separator.

Not fixing today, logging it. Real fix later: drop any chunk under some minimum length before it reaches the vector store.

## Hierarchical is actually doing something
Chunk counts are higher for hierarchical than for headers-only in every file (amlodipine: 139 → 155). Real sections were over the token limit and got sub-split, not just passed through untouched.

## Table 4 bug shows up again, worse
Spot-checked a middle `chunk_fixed` chunk on metformin.md (36 of 72) — landed right inside Table 4. Just raw numbers, no column labels, no idea what they mean. Confirms the Day 1 corruption isn't just cosmetic — it can produce a chunk that's flat-out useless on its own.

**Fix:** added table-aware splitting to `chunk_hierarchical`. Detects table rows generically (any line starting with `|`) and keeps the whole table as one chunk instead of letting the size-based splitter cut through the middle of it. Not hardcoded to Table 4 or metformin — works on any markdown table.

Result: the Mild/Moderate/Severe rows now stay together in one chunk. That specific bug (numbers with no row context) is gone.

Still broken: the actual column header (Cmax, Tmax, Renal Clearance) landed in the *previous* chunk as plain text, not inside the table block — because Docling's export dropped it outside the `|...|` syntax in the first place. No amount of chunking logic can glue that back on. It's an extraction bug, not a chunking one. Logged, not fixing today.

# Day 3 — Embeddings + dense retrieval (embed.py)

## Model choice
Checked what's actually available and invokable through Bedrock (not just listed) — Amazon Titan v1/v2, Cohere Embed v3/v4, TwelveLabs (video, not relevant). Anthropic has no embedding models at all, on any platform. OpenAI and Qwen have embedding models but aren't on Bedrock — using them would mean a separate account/API key or self-hosting, outside the AWS setup already working.

Picked **Cohere Embed v4** — newest, strongest text option actually available, verified working with a real `invoke-model` call before committing to it (1536-dim vectors came back). Cohere's third-party, so Bedrock required an AWS Marketplace subscription step first (confirmed $0 purchase amount — usage is billed separately, per token, not the subscription itself).

## Bug: throttled after ~1 request
First version called the API once per chunk — 600 chunks, 600 sequential calls, hit `ThrottlingException` almost immediately. Fix: Cohere's API accepts a batch of texts in a single call. Rewrote to send chunks in batches of 90 instead of one at a time — collapsed ~600 calls down to 7, no more throttling.

## First real test
Built one FAISS index (`IndexFlatL2`, brute-force nearest-neighbor — the naive baseline) across all 600 chunks from all 5 files. Asked: "What is the maximum daily dose of metformin?" Got back the actual FDA max-dose language (2,000 mg) plus real dosing/bioavailability passages — no keyword matching, pure vector similarity, and it found the right answer. Working end-to-end dense retrieval baseline.

## Known gap, not fixed yet
This is dense-only — pure "meaning" search, no keyword matching. Weak spot: exact drug names, dose numbers, product codes sometimes match better on literal text than on semantic similarity. That's what hybrid retrieval (BM25 + dense, next) is meant to cover.

# Day 4 — Hybrid retrieval (hybrid.py)

Added BM25 keyword search (`rank_bm25`) alongside the existing dense/FAISS search, combined with reciprocal rank fusion (RRF) — merges two ranked lists using rank *position* only, not raw scores, since BM25 scores and vector distances aren't on the same scale and can't just be added together.

## Test: dense-only vs hybrid, same query
"What is the maximum daily dose of metformin?" — top-3 from each, same 600 chunks.

Real difference: hybrid promoted a chunk dense-only didn't surface in its top-3 at all — a dosing-initiation passage with a specific starting dose. Likely BM25 catching an exact keyword match ("dose"/"metformin"/"daily") that dense search ranked lower on pure meaning similarity.

Confirms the Day 3 theory: dense-only can miss chunks that match well on literal words but less well on "meaning" alone. One query, one anecdote though — not proof hybrid is better overall. That's what Saturday's RAGAS harness is for: measuring this across a real question set instead of eyeballing one example.

## Known inefficiency, not fixed
`hybrid.py` re-embeds all 600 chunks every time it's run standalone (~7 Bedrock calls). Fine for a baseline, worth fixing later with saved/cached embeddings once we're not just proving the pipeline works.

## Reranking
Not added today. Decided to wait for Saturday's RAGAS numbers before adding it — only worth the complexity if the measured results actually show a gap it would close.
