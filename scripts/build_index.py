import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from regcomply.chunking.split import chunk_by_sections
from regcomply.index.build import build_policy_index
from regcomply.ingest.normalize import normalize_text

POLICY_DIR = Path(__file__).parent.parent / "data" / "raw" / "policies"
INDEX_DIR = Path(__file__).parent.parent / "chroma_db"


def main() -> None:
    policy_files = list(POLICY_DIR.glob("*.txt"))
    if not policy_files:
        print(f"No policy files found in {POLICY_DIR}")
        return

    all_chunks = []
    for path in policy_files:
        raw = path.read_text(encoding="utf-8")
        normalized = normalize_text(raw)
        doc_id = path.stem
        chunks = chunk_by_sections(normalized, doc_id, max_chars=1500, overlap=150)
        print(f"  {path.name}: {len(chunks)} chunks")
        all_chunks.extend(chunks)

    print(f"\nTotal chunks: {len(all_chunks)}")
    print(f"Building index at: {INDEX_DIR}")
    build_policy_index(all_chunks, INDEX_DIR)
    print("Index built successfully.")


if __name__ == "__main__":
    main()
