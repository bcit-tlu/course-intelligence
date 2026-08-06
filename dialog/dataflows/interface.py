"""Data source abstraction — format dispatcher.

Routes parsing by file type or directory structure. All paths return
a CourseModule for uniform downstream processing.
"""

from __future__ import annotations

import logging
import os
import re
import tempfile
import zipfile
from pathlib import Path

logger = logging.getLogger(__name__)

# Only extract these file types from zip archives.
# Everything else (images, video, audio) is skipped to save disk space.
_EXTRACTABLE_EXTENSIONS = {".html", ".htm", ".pdf"}

from dialog.agents.utils.agent_states import (
    AgentState,
    ContentPage,
    CourseModule,
)


SUPPORTED_EXTENSIONS = {".zip", ".pdf", ".docx", ".txt", ".md"}

_SUPPORTED_CONTENT_EXTENSIONS = {".html", ".htm", ".pdf", ".txt", ".md", ".docx"}


def parse_document(state: AgentState) -> dict:
    """Dispatch to the correct parser and return a CourseModule.

    This is a graph node. It detects the input format and routes to
    the appropriate parser. All parsers return the same CourseModule
    structure.

    Also sets raw_text as the concatenation of all page texts for
    backward compatibility with the semantic_chunker.
    """
    source = state.get("source_path", "")
    if not source:
        return {"error": "No source_path provided"}

    try:
        course_module = dispatch(source)
    except (ValueError, OSError) as e:
        return {"error": str(e)}

    # Build raw_text from all pages for backward compatibility
    raw_text = "\n\n".join(
        f"## {page['title']}\n\n{page['text']}" for page in course_module["pages"]
    )

    return {"course_module": course_module, "raw_text": raw_text}


def dispatch(source: str) -> CourseModule:
    """Detect format and route to the correct parser.

    Args:
        source: Path to a file or directory.

    Returns:
        CourseModule structure.

    Raises:
        ValueError: If the format is unsupported.
    """
    path = Path(source)

    # Directory input
    if path.is_dir():
        return _dispatch_directory(path)

    # File input
    if not path.is_file():
        raise ValueError(f"Source path does not exist: {source}")

    ext = path.suffix.lower()

    if ext == ".zip":
        return _dispatch_zip(path)
    elif ext == ".pdf":
        return _dispatch_pdf(path)
    elif ext == ".docx":
        return _dispatch_docx(path)
    elif ext in (".txt", ".md"):
        return _dispatch_text(path)
    else:
        raise ValueError(
            f"Unsupported file format: '{ext}'. "
            f"Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
        )


def _dispatch_directory(path: Path) -> CourseModule:
    """Handle directory input — D2L structure or generic content collection.

    Tier 1: Search for D2L 'Table of Contents.html' anywhere in the tree.
    Tier 2: Fall back to generic directory parsing (collect all supported files).
    """
    toc_files = list(path.rglob("Table of Contents.html"))
    if toc_files:
        from .d2l_parser import parse_d2l_folder
        return parse_d2l_folder(str(toc_files[0].parent))

    return _parse_generic_directory(path)


def _natural_sort_key(path: Path, root: Path) -> list:
    """Sort key that handles numeric prefixes naturally.

    Ensures 01_intro.html comes before 10_conclusion.html
    rather than 01 before 10 alphabetically (which would put 10 first).
    """
    rel = str(path.relative_to(root))
    return [
        int(part) if part.isdigit() else part.lower()
        for part in re.split(r'(\d+)', rel)
    ]


def _parse_generic_directory(path: Path) -> CourseModule:
    """Parse a directory of content files without a Table of Contents.

    Recursively finds all supported files and builds a CourseModule
    with one page per file, sorted by relative path (natural sort).
    """
    files = sorted(
        (
            f for f in path.rglob("*")
            if f.is_file() and f.suffix.lower() in _SUPPORTED_CONTENT_EXTENSIONS
        ),
        key=lambda f: _natural_sort_key(f, path),
    )

    if not files:
        raise ValueError(
            f"No supported content files found in {path}. "
            f"Supported: {', '.join(sorted(_SUPPORTED_CONTENT_EXTENSIONS))}"
        )

    pages: list[ContentPage] = []
    for i, f in enumerate(files, 1):
        rel = str(f.relative_to(path))
        ext = f.suffix.lower()

        if ext in (".html", ".htm"):
            from .html_parser import extract_html
            text = extract_html(str(f))
            content_type = "html_page"
        elif ext == ".pdf":
            from .pdf_parser import extract_pdf
            text = extract_pdf(str(f))
            content_type = "pdf"
        elif ext == ".docx":
            from .docx_parser import extract_docx
            text = extract_docx(str(f))
            content_type = "docx"
        else:
            from .text_parser import extract_text
            text = extract_text(str(f))
            content_type = "text"

        pages.append(ContentPage(
            page_number=i,
            title=f.stem,
            source_file=rel,
            content_type=content_type,
            text=text,
        ))

    return CourseModule(
        course_name=path.name,
        module_id="generic",
        source_folder=str(path),
        pages=pages,
    )


def _dispatch_zip(path: Path) -> CourseModule:
    """Selectively extract from zip and re-dispatch as directory.

    Only extracts .html and .pdf files to minimize disk usage.
    A 2 GB D2L export with media typically shrinks to ~200 MB.
    """
    with tempfile.TemporaryDirectory() as tmp_dir:
        with zipfile.ZipFile(str(path), "r") as zf:
            members = zf.namelist()
            extracted = 0
            skipped = 0

            for member in members:
                # Skip macOS metadata (__MACOSX/, ._AppleDouble, .DS_Store)
                parts = Path(member).parts
                filename = Path(member).name
                if (
                    "__MACOSX" in parts
                    or filename.startswith("._")
                    or filename == ".DS_Store"
                ):
                    skipped += 1
                    continue

                member_ext = Path(member).suffix.lower()
                # Always extract directories (needed for structure)
                if member.endswith("/"):
                    zf.extract(member, tmp_dir)
                    continue
                if member_ext in _EXTRACTABLE_EXTENSIONS:
                    zf.extract(member, tmp_dir)
                    extracted += 1
                else:
                    skipped += 1

            logger.info(
                "Zip extraction: %d files extracted, %d skipped (from %s)",
                extracted, skipped, path.name,
            )

        # The zip might contain a single top-level folder or files directly
        contents = [c for c in os.listdir(tmp_dir) if not c.startswith((".", "__MACOSX"))]
        if len(contents) == 1 and (Path(tmp_dir) / contents[0]).is_dir():
            extract_root = str(Path(tmp_dir) / contents[0])
        else:
            extract_root = tmp_dir

        return dispatch(extract_root)


def _dispatch_pdf(path: Path) -> CourseModule:
    """Wrap a single PDF in a CourseModule."""
    from .pdf_parser import extract_pdf

    text = extract_pdf(str(path))
    return _wrap_single_file(path, text, "pdf")


def _dispatch_docx(path: Path) -> CourseModule:
    """Wrap a single Word doc in a CourseModule."""
    from .docx_parser import extract_docx

    text = extract_docx(str(path))
    return _wrap_single_file(path, text, "docx")


def _dispatch_text(path: Path) -> CourseModule:
    """Wrap a single text/markdown file in a CourseModule."""
    from .text_parser import extract_text

    text = extract_text(str(path))
    return _wrap_single_file(path, text, "text")


def _wrap_single_file(path: Path, text: str, content_type: str) -> CourseModule:
    """Wrap extracted text from a single file into a CourseModule."""
    page = ContentPage(
        page_number=1,
        title=path.stem,
        source_file=path.name,
        content_type=content_type,
        text=text,
    )
    return CourseModule(
        course_name=path.stem,
        module_id="single",
        source_folder=str(path.parent),
        pages=[page],
    )
