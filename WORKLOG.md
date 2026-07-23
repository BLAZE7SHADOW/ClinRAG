  ## 2026-07-20

  - Set up the ClinRAG repo and ran a real Docling extraction pipeline test on a sample
    clinical document (metformin.pdf from DailyMed) to evaluate extraction/parsing quality
    before building anything further.
  - Tested Docling's two table-structure recognition modes, FAST and ACCURATE, on the same
    file to compare output quality rather than assume one was better.
  - Manually reviewed both outputs and found the same structural bug in both modes: a
    multi-level-header pharmacokinetics table (Mild/Moderate/Severe renal impairment dosing)
    lost its row structure. Logged in NOTES.md.
  - Decided to default to ACCURATE mode going forward. Reasoning: this one hard table being
    equally broken in both modes doesn't prove FAST is safe on the *other* tables in the
    corpus — and given this is medical dosing data, the risk of a silently wrong table
    outweighs the (currently unmeasured) speed cost. Will benchmark actual speed difference
    once running the full corpus, not before.

  ## 2026-07-22

  - Built and ran three chunkers (`chunk.py`) across all 5 processed markdown files:
    fixed-size w/ token overlap, structure-aware on markdown headers, and a hierarchical
    combination of the two.
  - Spot-checked chunk output manually (first/middle/last chunks, plus a targeted check
    around the known Table 4 corruption). Found two real issues: an empty separator-only
    first chunk in 3/5 files, and Table 4's corrupted rows landing in a chunk with zero
    header context.
  - Added generic table-aware splitting to the hierarchical chunker (detects any markdown
    table by its `|` rows, keeps it as one atomic chunk instead of letting size-based
    splitting cut through it). Confirmed it fixed the Table 4 row-splitting issue, though
    the column header itself is still detached (an upstream Docling export bug, not
    fixable at the chunking layer). Both findings logged in Notes.md.

  ## 2026-07-23

  - Built embeddings + dense retrieval baseline (`embed.py`): compared Amazon Titan vs
    Cohere on Bedrock, verified real invoke access (not just listing) before picking
    Cohere Embed v4. Hit a rate limit embedding 600 chunks one at a time; fixed by
    batching 90 texts per API call. FAISS `IndexFlatL2` as the naive baseline index.
    Test query returned the correct FDA max-dose passage.
  - Built hybrid retrieval (`hybrid.py`): added BM25 keyword search alongside dense
    search, combined via reciprocal rank fusion. Compared dense-only vs hybrid on the
    same test query — hybrid surfaced a real dosing chunk that dense-only missed
    entirely, confirming the theory that pure semantic search can lose exact-keyword
    matches. One example only; Saturday's RAGAS harness will measure this properly.
  - Decided not to add reranking today (it was flagged as out of scope) — revisit after
    RAGAS gives real numbers to justify it, instead of assuming it's needed.
  - Added README.md and ARCHITECTURE.md reflecting current pipeline state.
  - Wired in LLM generation (`generate.py`) using Claude Haiku 4.5 via Bedrock, completing
    the full retrieve-then-generate loop. Had to use a cross-region inference profile ID
    instead of the plain model ID (newer Anthropic models on Bedrock require it for
    on-demand calls). Prompt explicitly restricts the model to answering only from
    retrieved excerpts. End-to-end test on the metformin max-dose question produced a
    correct, grounded answer. This completes Friday's full planned scope.
