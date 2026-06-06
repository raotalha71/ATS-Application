
import fitz                      # PyMuPDF — pip name: pymupdf
from docx import Document        # python-docx
from pathlib import Path
import io


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """
    Extract text from PDF bytes using PyMuPDF.
    Handles multi-page PDFs. Returns concatenated plain text.
    """
    text_parts = []
    # Open PDF from bytes (no temp file needed)
    with fitz.open(stream=file_bytes, filetype="pdf") as doc:
        for page in doc:
            text_parts.append(page.get_text("text"))  # "text" = plain text mode
    return "\n".join(text_parts).strip()


def extract_text_from_docx(file_bytes: bytes) -> str:
    """
    Extract text from DOCX bytes using python-docx.
    Reads all paragraphs and table cells.
    """
    doc = Document(io.BytesIO(file_bytes))
    parts = []

    # Extract paragraph text
    for para in doc.paragraphs:
        if para.text.strip():
            parts.append(para.text.strip())

    # Extract table cell text (often used for skills/experience layout)
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                if cell.text.strip():
                    parts.append(cell.text.strip())

    return "\n".join(parts).strip()


def extract_text(file_bytes: bytes, filename: str) -> str:
    """
    Router — picks extractor based on file extension.
    Raises ValueError for unsupported formats.
    """
    ext = Path(filename).suffix.lower()

    if ext == ".pdf":
        return extract_text_from_pdf(file_bytes)
    elif ext in (".docx", ".doc"):
        return extract_text_from_docx(file_bytes)
    else:
        raise ValueError(f"Unsupported file format: {ext}. Use PDF or DOCX.")
