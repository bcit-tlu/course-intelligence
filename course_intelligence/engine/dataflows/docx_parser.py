"""Word document parser — extract text from .docx files."""

from __future__ import annotations


def extract_docx(path: str) -> str:
    """Extract plain text from a Word (.docx) file.

    Preserves paragraph breaks. Headings are converted to
    markdown-style markers based on their style name.
    """
    from docx import Document

    doc = Document(path)
    lines: list[str] = []

    for para in doc.paragraphs:
        text = para.text.strip()
        if not text:
            continue

        style_name = (para.style.name or "").lower()

        if "heading 1" in style_name:
            lines.append(f"# {text}")
            lines.append("")
        elif "heading 2" in style_name:
            lines.append(f"## {text}")
            lines.append("")
        elif "heading 3" in style_name:
            lines.append(f"### {text}")
            lines.append("")
        elif "heading 4" in style_name:
            lines.append(f"#### {text}")
            lines.append("")
        else:
            lines.append(text)
            lines.append("")

    return "\n".join(lines).strip()
