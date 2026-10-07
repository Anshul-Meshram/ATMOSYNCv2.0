import fitz
from pathlib import Path
from .text_cleaner import clean_text


def extract_pages_from_pdf(pdf_path: str) -> list[dict]:
    """
    Extract text from a PDF while preserving page information.

    Args:
        pdf_path: Path to the PDF file.

    Returns:
        List of dictionaries containing page number and page text.
    """

    pdf_path = Path(pdf_path)

    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    if pdf_path.suffix.lower() != ".pdf":
        raise ValueError(f"Expected a PDF file, got: {pdf_path.suffix}")

    document = fitz.open(pdf_path)

    pages = []

    for page_number, page in enumerate(document, start=1):

        text = page.get_text().strip()

        pages.append({
            "page": page_number,
            "text": text
        })

    document.close()

    return pages


def check_pdf_text(pages: list[dict]) -> bool:
    """
    Check whether the PDF contains extractable text.

    Returns:
        True if sufficient text is available, otherwise False.
    """

    total_characters = sum(len(page["text"]) for page in pages)

    if total_characters == 0:
        return False

    return True

def process_pdf(pdf_path: str) -> list[dict]:
    """
    Complete PDF ingestion pipeline

    steps:
    1. Extract pages
    2. Check whether text exists
    3. clean page text 
    4. Remove Empty Spaces 

    Args:
        pdf_path : Path to the PDF file.
    
    Returns:
        List of processed pages 
    """
    pages = extract_pages_from_pdf(pdf_path)

    if not check_pdf_text(pages):
        raise ValueError(
                         "No extraction text foung in the pdf."
                         "The pdf maybe scanned or image based ."
                         )
    processed_pages = []

    for page in pages:
        cleaned_text = clean_text(page["text"])

        #Ignore completely empty pages 
        if not cleaned_text:
            continue
        processed_pages.append({
            "page": page["page"],
            "text": cleaned_text
        })
    return processed_pages

    
        

if __name__ == "__main__":

    pdf_file = "M:/sem7/Major Project/AtmoSync/src/rag/documents/weather_report_2026-09-21.pdf"

    pages = process_pdf(pdf_file)

    has_text = check_pdf_text(pages)

    print("PDF ingestion completed successfully.")
    print(f"Pages with text: {len(pages)}")
    print(
        f"Total characters: "
        f"{sum(len(page['text']) for page in pages)}"
    )

    print("First page review:")
    print("-"*50)
    print(pages[0]["text"][:500])  # Print first 500 characters of the first page