"""PDF parser — extract text from PDF files using PyMuPDF."""

from __future__ import annotations


def extract_pdf(path: str) -> str:
    """Extract plain text from a PDF file."""
    import fitz  # PyMuPDF

    doc = fitz.open(path)
    pages: list[str] = []
    for page in doc:
        pages.append(page.get_text("text"))
    doc.close()
    return "\n\n".join(pages)
