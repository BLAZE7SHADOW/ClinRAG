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
