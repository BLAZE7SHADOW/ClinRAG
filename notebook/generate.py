import json
from pathlib import Path

import boto3

from chunk import chunk_hierarchical
from embed import embed_chunks, build_faiss_index
from hybrid import build_bm25_index, hybrid_search

script_dir = Path(__file__).resolve().parent.parent
processed_dir = script_dir / "data" / "processed"

bedrock = boto3.client("bedrock-runtime")

# Newer Anthropic models on Bedrock don't accept the plain model ID for
# on-demand calls -- they require an "inference profile" ID instead
# (confirmed by testing; the plain ID gave a ValidationException asking
# for this exact profile ID). Fast + cheap model, since this will get
# called many times during tomorrow's RAGAS eval across many questions.
MODEL_ID = "us.anthropic.claude-haiku-4-5-20251001-v1:0"


def generate_answer(query, context_chunks):
    # glue the retrieved chunks into one block of text, clearly separated,
    # so the prompt can point at "the following excerpts" as one unit.
    context = "\n\n---\n\n".join(context_chunks)

    # the whole point of RAG: explicitly tell the model to answer ONLY
    # from the provided excerpts, not from whatever it remembers about
    # this drug from training. Also tell it to say so if the excerpts
    # don't actually contain the answer, instead of guessing -- a
    # confident guess is worse than an honest "not in this context".
    prompt = f"""Answer the question using ONLY the excerpts below. If the excerpts don't contain the answer, say so instead of guessing.

Excerpts:
{context}

Question: {query}

Answer:"""

    body = json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 300,
        "messages": [
            {"role": "user", "content": prompt}
        ],
    })

    response = bedrock.invoke_model(
        modelId=MODEL_ID,
        body=body,
        contentType="application/json",
        accept="application/json",
    )

    result = json.loads(response["body"].read())

    # Claude's response text is nested under content -> a list of blocks
    # -> the first block's "text" field (a message can have multiple
    # content blocks, but a plain text answer is just one block).
    return result["content"][0]["text"]


def answer_question(query, faiss_index, bm25_index, chunks, k=5):
    # this is the full pipeline in one call: retrieve, then generate --
    # exactly what tomorrow's RAGAS harness will call once per question,
    # once per config (dense-only vs hybrid).
    retrieved_chunks = hybrid_search(query, faiss_index, bm25_index, chunks, k=k)
    answer = generate_answer(query, retrieved_chunks)
    return answer, retrieved_chunks


if __name__ == "__main__":
    all_chunks = []
    for md_path in processed_dir.glob("*.md"):
        text = md_path.read_text()
        all_chunks.extend(chunk_hierarchical(text))

    print(f"Total chunks across all files: {len(all_chunks)}")

    print("Embedding all chunks...")
    embeddings = embed_chunks(all_chunks)

    print("Building indices...")
    faiss_index = build_faiss_index(embeddings)
    bm25_index = build_bm25_index(all_chunks)

    query = "What is the maximum daily dose of metformin?"
    print(f"\nQuery: {query}")

    answer, retrieved_chunks = answer_question(query, faiss_index, bm25_index, all_chunks)

    print(f"\n=== Retrieved {len(retrieved_chunks)} chunks ===")
    for i, chunk in enumerate(retrieved_chunks):
        print(f"--- chunk {i + 1} ---\n{chunk[:200]}\n")

    print("=== Generated answer ===")
    print(answer)
