import json
from pathlib import Path

import boto3
import numpy as np
import faiss

from chunk import chunk_hierarchical

script_dir = Path(__file__).resolve().parent.parent
processed_dir = script_dir / "data" / "processed"

# boto3.client talks to AWS services over HTTP -- this one specifically
# talks to Bedrock's model-invocation endpoint. It reuses whatever
# credentials/region are already configured (same ones `aws configure`
# or env vars set up -- nothing new to set here).
bedrock = boto3.client("bedrock-runtime")


def embed_texts(texts, input_type):
    # Cohere's "texts" field accepts a LIST of texts, not just one --
    # sending many at once in a single API call is why this is called
    # "batching". Doing this instead of one call per chunk is what avoids
    # hitting Bedrock's rate limit (we hit ThrottlingException firing 600
    # back-to-back single-text calls before this fix).
    body = json.dumps({
        "texts": texts,
        "input_type": input_type,
    })

    response = bedrock.invoke_model(
        modelId="cohere.embed-v4:0",
        body=body,
        contentType="application/json",
        accept="application/json",
    )

    # response["body"] is a stream (like a file), not a string -- you have
    # to .read() it before you can parse it as JSON.
    result = json.loads(response["body"].read())

    # one embedding vector comes back per text we sent in, in the same order.
    return result["embeddings"]["float"]


def get_embedding(text, input_type):
    # convenience wrapper for embedding a single piece of text (used for
    # the user's query at search time) -- reuses embed_texts with a
    # one-item list, then pulls out that one result.
    return embed_texts([text], input_type)[0]


def embed_chunks(chunks, batch_size=90):
    # every chunk here is going INTO the index, so input_type is always
    # "search_document". We slice `chunks` into groups of `batch_size` and
    # send each group as one API call instead of one call per chunk.
    embeddings = []
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i + batch_size]
        embeddings.extend(embed_texts(batch, "search_document"))
        print(f"  embedded {min(i + batch_size, len(chunks))}/{len(chunks)} chunks")
    return embeddings


def build_faiss_index(embeddings):
    # FAISS wants a numpy array of 32-bit floats, not a plain Python list
    # of lists -- this is just a format conversion, no data changes.
    vectors = np.array(embeddings).astype("float32")

    # every embedding vector has the same length (Cohere v4 returns 1536
    # numbers per text) -- that length is the "dimension" FAISS needs to
    # know up front to set up its internal storage correctly.
    dimension = vectors.shape[1]

    # IndexFlatL2 is the simplest possible FAISS index: to search it, it
    # just measures the straight-line (L2/Euclidean) distance from your
    # query vector to every single vector stored, and returns the closest
    # ones. No approximation, no shortcuts -- which is exactly what "naive
    # top-k dense retrieval" means. Fine at 5 documents; wouldn't scale to
    # millions of chunks without a fancier index type.
    index = faiss.IndexFlatL2(dimension)
    index.add(vectors)
    return index


def search(query, index, chunks, k=5):
    # the question is going INTO a search, not INTO the index, so this is
    # the one place input_type is "search_query" instead of "search_document".
    query_vector = np.array([get_embedding(query, "search_query")]).astype("float32")

    # index.search returns two arrays: distances (how far each match is)
    # and indices (WHICH stored vector matched, by position). We only need
    # the positions here, to look the original text back up in `chunks`.
    distances, indices = index.search(query_vector, k)

    # indices[0] because we only searched with one query vector -- FAISS
    # supports searching many queries at once, so it always returns a
    # batch, even a batch of one.
    return [chunks[i] for i in indices[0]]


if __name__ == "__main__":
    # collect every chunk from every file into ONE list, so we build ONE
    # index across the whole corpus -- not five separate per-file indexes.
    all_chunks = []
    for md_path in processed_dir.glob("*.md"):
        text = md_path.read_text()
        all_chunks.extend(chunk_hierarchical(text))

    print(f"Total chunks across all files: {len(all_chunks)}")

    print("Embedding all chunks (one Bedrock call per chunk, this takes a while)...")
    embeddings = embed_chunks(all_chunks)

    print("Building FAISS index...")
    index = build_faiss_index(embeddings)

    query = "What is the maximum daily dose of metformin?"
    print(f"\nQuery: {query}")
    results = search(query, index, all_chunks, k=3)
    for i, result in enumerate(results):
        print(f"\n--- result {i + 1} ---")
        print(result[:400])
