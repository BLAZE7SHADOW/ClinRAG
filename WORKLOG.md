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
