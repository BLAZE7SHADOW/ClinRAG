from pathlib import Path
import tiktoken
from langchain_text_splitters import RecursiveCharacterTextSplitter, MarkdownHeaderTextSplitter

script_dir = Path(__file__).resolve().parent.parent
processed_dir = script_dir / "data" / "processed"


def chunk_fixed(text, chunk_size=500, chunk_overlap=50):
    # from_tiktoken_encoder measures chunk_size/chunk_overlap in TOKENS (using
    # tiktoken, the tokenizer family OpenAI models use) instead of raw characters
    # -- this targets what actually limits an embedding model's input, not an
    # approximation of it.
    splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )
    return splitter.split_text(text)


def chunk_by_headers(text):
    # split at the markdown headers Docling's export already produced.
    # each tuple is (the markdown symbol to split on, a label used in the
    # returned chunk's metadata -- not used further here, but it's how the
    # splitter tracks which section a chunk came from)
    headers_to_split_on = [
        ("#", "header_1"),
        ("##", "header_2"),
        ("###", "header_3"),
    ]
    splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)
    docs = splitter.split_text(text)
    # MarkdownHeaderTextSplitter returns Document objects (text + metadata),
    # not plain strings. Pull out just the text so both chunkers return the
    # same shape -- a list[str] -- and are easy to compare side by side.
    return [doc.page_content for doc in docs]


def split_into_table_and_prose(text):
    # generic markdown convention: every line of a table (including the
    # |---|---| separator row) starts with "|". Group consecutive lines of
    # the same kind together so a table block and the prose around it come
    # out as separate segments -- this has nothing document-specific about
    # it, so it works on any markdown table, not just Table 4.
    segments = []
    current_type = None
    current_lines = []

    for line in text.split("\n"):
        line_type = "table" if line.strip().startswith("|") else "prose"

        if line_type != current_type and current_lines:
            segments.append((current_type, "\n".join(current_lines)))
            current_lines = []

        current_type = line_type
        current_lines.append(line)

    if current_lines:
        segments.append((current_type, "\n".join(current_lines)))

    return segments


def chunk_hierarchical(text, chunk_size=500, chunk_overlap=50):
    # "gpt2" matches the default encoding_name that chunk_fixed's
    # from_tiktoken_encoder call uses -- if we counted tokens with a
    # different encoding here, a section could pass this size check but
    # still come out oversized (or vice versa) once chunk_fixed re-splits it.
    encoding = tiktoken.get_encoding("gpt2")

    # step 1: split by structure first, same as chunk_by_headers
    header_chunks = chunk_by_headers(text)

    hierarchical_chunks = []
    for section in header_chunks:
        token_count = len(encoding.encode(section))
        if token_count <= chunk_size:
            # section already fits inside the token budget -- keep it whole,
            # no need to split further and lose the clean section boundary
            hierarchical_chunks.append(section)
            continue

        # section is too big for one chunk -- but a plain fixed-size split
        # here would happily cut a table in half. Split into table/prose
        # segments first so tables stay intact, then only size-split prose.
        for segment_type, segment_text in split_into_table_and_prose(section):
            if segment_type == "table":
                # keep the whole table as one chunk even if it's over
                # chunk_size -- a table missing its header row is worse
                # than one long chunk
                hierarchical_chunks.append(segment_text)
            else:
                segment_tokens = len(encoding.encode(segment_text))
                if segment_tokens > chunk_size:
                    hierarchical_chunks.extend(chunk_fixed(segment_text, chunk_size, chunk_overlap))
                else:
                    hierarchical_chunks.append(segment_text)

    return hierarchical_chunks


if __name__ == "__main__":
    # only runs when this file is executed directly, not on import
    for md_path in processed_dir.glob("*.md"):
        text = md_path.read_text()
        fixed_chunks = chunk_fixed(text)
        header_chunks = chunk_by_headers(text)
        hierarchical_chunks = chunk_hierarchical(text)

        print(f"\n=== {md_path.name} ===")
        print(f"fixed:        {len(fixed_chunks)} chunks")
        print(f"headers:      {len(header_chunks)} chunks")
        print(f"hierarchical: {len(hierarchical_chunks)} chunks")
        print(f"--- first fixed chunk ---\n{fixed_chunks[0][:300]}")
        print(f"--- first header chunk ---\n{header_chunks[0][:300]}")
        print(f"--- first hierarchical chunk ---\n{hierarchical_chunks[0][:300]}")
