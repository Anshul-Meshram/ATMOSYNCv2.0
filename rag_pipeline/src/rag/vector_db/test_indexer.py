
from pathlib import Path

from src.rag.ingestion.pdf_loader import process_pdf
from src.rag.ingestion.chunker import chunk_pages
from src.rag.vector_db.indexer import index_chunks


PROJECT_ROOT = Path(__file__).resolve().parents[3]

DOCUMENTS_DIR = PROJECT_ROOT / "src" / "rag" / "documents"


def main():

    print("=" * 60)
    print("MULTI-PDF RAG INDEXING TEST")
    print("=" * 60)

    pdf_files = list(DOCUMENTS_DIR.rglob("*.pdf"))

    if not pdf_files:
        print("No PDF documents found.")
        return

    print(f"\nPDF documents found: {len(pdf_files)}")

    total_indexed = 0

    for pdf_path in pdf_files:

        print("\n" + "-" * 60)
        print(f"Processing: {pdf_path.name}")
        print("-" * 60)

        print("\n1. Loading PDF...")

        pages = process_pdf(pdf_path)

        print(f"Pages loaded: {len(pages)}")

        print("\n2. Creating chunks...")

        chunks = chunk_pages(pages)

        print(f"Chunks created: {len(chunks)}")

        print("\n3. Generating embeddings and indexing...")

        indexed_count = index_chunks(
            chunks,
            pdf_path.name
        )

        print(f"Chunks indexed: {indexed_count}")

        total_indexed += indexed_count

    print("\n" + "=" * 60)
    print("MULTI-PDF INDEXING COMPLETED")
    print(f"Total PDFs processed: {len(pdf_files)}")
    print(f"Total chunks indexed: {total_indexed}")
    print("=" * 60)


if __name__ == "__main__":
    main()