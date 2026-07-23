from pathlib import Path

from rank_bm25 import BM25Okapi

from chunk import chunk_hierarchical
from embed import embed_chunks, build_faiss_index, get_embedding, search

script_dir = Path(__file__).resolve().parent.parent
processed_dir = script_dir / "data" / "processed"


def build_bm25_index(chunks):
    # BM25 is pure keyword matching -- it needs each chunk broken into
    # individual words (tokens), not one long string. ".lower().split()" is
    # the simplest possible tokenizer: lowercase everything (so "Metformin"
    # and "metformin" count as the same word) and split on whitespace.
    tokenized_chunks = [chunk.lower().split() for chunk in chunks]
    return BM25Okapi(tokenized_chunks)


def bm25_rank(query, bm25_index, k=20):
    # tokenize the query the same way the chunks were tokenized -- BM25
    # only works if both sides are broken into words the same way.
    tokenized_query = query.lower().split()

    # get_scores returns one relevance score per chunk, in the SAME order
    # the chunks were originally given to build_bm25_index -- so index 0
    # of this scores list is still chunk 0, index 1 is still chunk 1, etc.
    scores = bm25_index.get_scores(tokenized_query)

    # we want the top-k chunk POSITIONS (indices), ranked best-first, not
    # the scores themselves. argsort sorts ascending by default, so [::-1]
    # reverses it to descending (highest score = best match, first).
    ranked_indices = scores.argsort()[::-1][:k]
    return list(ranked_indices)


def dense_rank(query, faiss_index, k=20):
    # same embedding + search logic as embed.py's search() function, but
    # returning the ranked chunk POSITIONS instead of the chunk text --
    # we need positions here so reciprocal_rank_fusion can compare BM25's
    # and dense's rankings using the same chunk-identity system (their
    # shared index position in the `all_chunks` list).
    import numpy as np
    query_vector = np.array([get_embedding(query, "search_query")]).astype("float32")
    distances, indices = faiss_index.search(query_vector, k)
    return list(indices[0])


def reciprocal_rank_fusion(ranked_lists, k=60):
    # Each ranked_list is a list of chunk positions, best match first.
    # RRF's idea: don't trust either method's raw scores (BM25 scores and
    # vector distances aren't on comparable scales), only trust RANK
    # POSITION. A chunk ranked #1 by BOTH methods should beat a chunk
    # ranked #1 by only one method and unranked by the other.
    #
    # Formula: for every chunk, add up 1 / (k + rank) across every ranked
    # list it appears in (rank starts at 1, not 0). The constant k=60 is
    # the standard default from the original RRF paper -- it just softens
    # how much rank #1 is worth vs rank #2, rank #3, etc.
    scores = {}
    for ranked_list in ranked_lists:
        for rank, chunk_index in enumerate(ranked_list, start=1):
            scores[chunk_index] = scores.get(chunk_index, 0) + 1 / (k + rank)

    # sort chunk positions by their combined score, highest first
    fused_indices = sorted(scores, key=lambda i: scores[i], reverse=True)
    return fused_indices


def hybrid_search(query, faiss_index, bm25_index, chunks, k=5, candidate_pool=20):
    # get each method's own top candidates first (a wider pool than the
    # final k, so RRF has enough overlap between the two rankings to
    # actually combine), then fuse the two ranked lists into one.
    dense_indices = dense_rank(query, faiss_index, candidate_pool)
    bm25_indices = bm25_rank(query, bm25_index, candidate_pool)

    fused_indices = reciprocal_rank_fusion([dense_indices, bm25_indices])

    top_indices = fused_indices[:k]
    return [chunks[i] for i in top_indices]


if __name__ == "__main__":
    all_chunks = []
    for md_path in processed_dir.glob("*.md"):
        text = md_path.read_text()
        all_chunks.extend(chunk_hierarchical(text))

    print(f"Total chunks across all files: {len(all_chunks)}")

    # NOTE: this re-embeds every chunk each time hybrid.py is run standalone
    # -- fine for today's baseline, but a real inefficiency worth fixing
    # later (e.g. save/load embeddings to disk instead of recomputing them
    # every run) once we're not just proving the pipeline works.
    print("Embedding all chunks...")
    embeddings = embed_chunks(all_chunks)

    print("Building FAISS index (dense) and BM25 index (keyword)...")
    faiss_index = build_faiss_index(embeddings)
    bm25_index = build_bm25_index(all_chunks)

    query = "What is the maximum daily dose of metformin?"
    print(f"\nQuery: {query}")

    print("\n=== Dense-only results ===")
    dense_results = search(query, faiss_index, all_chunks, k=3)
    for i, result in enumerate(dense_results):
        print(f"--- dense result {i + 1} ---")
        print(result[:300])

    print("\n=== Hybrid (BM25 + dense, RRF) results ===")
    hybrid_results = hybrid_search(query, faiss_index, bm25_index, all_chunks, k=3)
    for i, result in enumerate(hybrid_results):
        print(f"--- hybrid result {i + 1} ---")
        print(result[:300])
