from dataclasses import dataclass


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    text: str
    section_path: str
    source_doc_id: str


def chunk_by_sections(
    text: str,
    source_doc_id: str,
    *,
    max_chars: int = 1500,
    overlap: int = 150,
) -> list[Chunk]:
    parts = text.split("\n\n")
    chunks: list[Chunk] = []
    buf: list[str] = []
    buf_len = 0
    section_idx = 0

    def flush() -> None:
        nonlocal buf, buf_len, section_idx
        if not buf:
            return
        body = "\n\n".join(buf)
        path = f"{source_doc_id}:sec{section_idx}"
        cid = f"{source_doc_id}_c{len(chunks)}"
        chunks.append(
            Chunk(chunk_id=cid, text=body, section_path=path, source_doc_id=source_doc_id)
        )
        buf = []
        buf_len = 0
        section_idx += 1

    for para in parts:
        p = para.strip()
        if not p:
            continue
        if buf_len + len(p) + 2 > max_chars and buf:
            flush()
            if overlap > 0 and chunks:
                tail = chunks[-1].text[-overlap:]
                buf = [tail]
                buf_len = len(tail)
        buf.append(p)
        buf_len += len(p) + 2
    flush()
    return chunks
