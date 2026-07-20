# Day 1 — Extraction experiment notes (Docling, `metformin.pdf`)

## 1. What did Docling get right / wrong?

**Right:**
- Section headings detected correctly and in order (DOSAGE AND ADMINISTRATION, CONTRAINDICATIONS, WARNINGS AND PRECAUTIONS, etc.)
- One multi-column patient-info checklist reconstructed cleanly into a readable 2-column markdown table

**Wrong:**
- A second multi-column checklist merged multiple bullet items into single table cells instead of splitting them (e.g. `o headache o drowsiness o weakness...` all in one cell)
- OCR on embedded images (barcode / pill-imprint graphics) produced garbage text fragments (e.g. `Sm 3 5 3 2694 6789 8`) mixed into the output
- Bullet/point sequence is out of order in multiple places
- Stray/misplaced characters showing up at random points in the text
- The WARNINGS AND PRECAUTIONS section came out broken/fragmented
- Repetition in multiple places — e.g. "USE IN SPECIFIC POPULATIONS" appears twice back to back (some of this is inherent to the FDA label format itself — Highlights section vs. Full Prescribing Information repeat section names — but not all of it; needs a closer look to separate "expected duplication" from "actual parsing bug")
- **Table 4 (renal impairment pharmacokinetics)** lost structural integrity — the Mild/Moderate/Severe row categories are missing or misaligned. This is the most serious finding: it's clinically load-bearing data (dose adjustment by renal function), and a scrambled table here could feed a wrong answer to a dosing question later.

**Tested:** ran the same file with `TableFormerMode.ACCURATE` instead of the default. Table 4 came out corrupted the same way — Mild/Moderate/Severe rows still missing/misaligned. So this is a genuine structural limitation on this table shape (multi-level spanning header + footnote-letter superscripts), not a fast-mode laziness artifact. Decision: document as a known limitation and move forward rather than chase a fix now — this specific complexity is out of scope for Day 1.

## 2. What's the chunking approach going to group by?

Plan default (from the original build plan): implement **two** chunkers behind one interface —
- Fixed-size with overlap (500 tokens / 50 overlap)
- Structure-aware, splitting on the headings Docling already detected

Both get benchmarked later (Day 5) rather than picking one now.

## 3. What's the smallest thing to build first?

Plan default: extraction working on **all** files first (not just this one) → then chunking → then validation. Don't build chunking until extraction is confirmed trustworthy across the whole sample set, not just `metformin.pdf`.

## 4. What could silently go wrong, and how do I catch it?

- **OCR garbage chunks**: a chunk made entirely of barcode-OCR noise could end up embedded and retrieved as if it were real content. Need a way to flag/filter chunks with an abnormal ratio of non-alphanumeric characters or very low readability before they go into the vector store.
- **Corrupted tables silently degrading answers**: Table 4's scrambled Mild/Moderate/Severe rows wouldn't throw an error — the pipeline would happily embed and retrieve it, and the LLM might answer confidently off broken data. Needs some form of spot-check on table-heavy chunks, not just an automated coverage-percentage check.
- **Duplicate/near-duplicate sections** (Highlights vs. Full Prescribing Info repeating the same section): not wrong exactly, but wastes chunk budget and could cause redundant near-identical hits in retrieval. Worth deciding whether to dedupe.
