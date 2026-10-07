from src.rag.ingestion.pdf_loader import process_pdf
from src.rag.ingestion.chunker import chunk_pages


PDF_PATH = "M:/sem7/Major Project/AtmoSync/src/rag/documents/Climate_Intelligence_System_Project_Report.pdf"


if __name__ == "__main__":

    # Step 1: Extract and clean PDF
    pages = process_pdf(PDF_PATH)

    print(f"Pages processed: {len(pages)}")

    # Step 2: Create chunks
    chunks = chunk_pages(pages)

    print(f"Total chunks created: {len(chunks)}")

    # Step 3: Display first few chunks
    print("\nFirst 3 chunks:")
    print("=" * 70)

    for chunk in chunks[:3]:

        print(f"\nChunk ID: {chunk['chunk_id']}")
        print(f"Page: {chunk['page']}")
        print(f"Characters: {chunk['char_count']}")
        print("-" * 70)
        print(chunk["text"][:500])