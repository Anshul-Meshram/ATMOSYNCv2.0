import re 

def clean_text(text:str)->str:
    """
    Clean Extracted PDF text

    Operations:
    -Normalise whitespace
    -Remove excessive blank lines
    -Fix spaces around line breaks
    """

    if not text:
        return ""
    # Replace multiple spaces/tabs with a single space.
    text = re.sub(r"[ \t]+", " ", text)

    # Remove spaces before and after newlines.
    text = re.sub(r" *\n *", "\n", text)

    # Replace three or more newlines with two newlines.
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()

if __name__ == "__main__":
    sample_text = """" 
    This is a sample text extracted from a PDF document. It contains multiple spaces, tabs, and excessive blank lines.
    """
    cleaned_text = clean_text(sample_text)

    print("Original Text:")
    print(sample_text)

    print("\nCleaned Text:")
    print(cleaned_text)