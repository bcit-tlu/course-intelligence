"""D2L course module folder parser.

Walks a D2L export directory, parses the Table of Contents for page ordering,
extracts text from HTML pages and PDF assets, and returns a CourseModule.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

from bs4 import BeautifulSoup

from course_intelligence.engine.agents.utils.agent_states import ContentPage, CourseModule


def parse_d2l_folder(folder_path: str) -> CourseModule:
    """Parse a D2L export folder into a CourseModule.

    Args:
        folder_path: Absolute path to the D2L export directory.

    Returns:
        CourseModule with ordered content pages.

    Raises:
        ValueError: If the folder doesn't contain a valid D2L structure.
    """
    folder = Path(folder_path)
    toc_file = folder / "Table of Contents.html"

    if not toc_file.exists():
        raise ValueError(
            f"Not a valid D2L export: missing 'Table of Contents.html' in {folder}"
        )

    # Parse metadata from folder name
    course_name, module_id = _parse_folder_name(folder.name)

    # Parse ToC for ordered page list
    toc_entries = _parse_toc(toc_file)

    # Extract content from each page
    pages: list[ContentPage] = []
    page_number = 1

    for title, href in toc_entries:
        page_path = folder / href
        if not page_path.exists():
            continue

        text = _extract_page(page_path)
        pages.append(
            ContentPage(
                page_number=page_number,
                title=title,
                source_file=href,
                content_type="html_page",
                text=text,
            )
        )
        page_number += 1

    # Extract PDF assets
    pdf_pages = _extract_pdf_assets(folder)
    for pdf_page in pdf_pages:
        pdf_page["page_number"] = page_number
        pages.append(pdf_page)
        page_number += 1

    return CourseModule(
        course_name=course_name,
        module_id=module_id,
        source_folder=str(folder),
        pages=pages,
    )


def _parse_folder_name(name: str) -> tuple[str, str]:
    """Extract course name and module ID from the D2L folder name.

    Expected format: 'NSER-7410-NET - Emergency Nursing Theory 3 - 59439 - ...'
    """
    parts = name.split(" - ")
    if len(parts) >= 2:
        course_name = f"{parts[0].strip()} - {parts[1].strip()}"
    else:
        course_name = name

    # Try to find module number from the modules/ subdirectory
    module_id = "01"  # default
    return course_name, module_id


def _parse_toc(toc_path: Path) -> list[tuple[str, str]]:
    """Parse Table of Contents.html and return ordered (title, href) pairs.

    D2L ToC links are often empty anchors with the title as a sibling
    text node: <p><a href="..."></a>1. Module Overview</p>
    Falls back to parent text, then filename, when link text is empty.
    """
    with open(toc_path, "r", encoding="utf-8") as f:
        html = f.read()

    soup = BeautifulSoup(html, "html.parser")
    entries: list[tuple[str, str]] = []

    for link in soup.find_all("a"):
        href = link.get("href", "")
        if not href:
            continue

        # 1. Try the link's own text
        title = link.get_text(strip=True)

        # 2. Fall back to the parent element's text (D2L pattern)
        if not title and link.parent is not None:
            title = link.parent.get_text(strip=True)

        # 3. Fall back to a cleaned-up filename
        if not title:
            stem = Path(href).stem
            # Strip leading page number prefix like "01_"
            title = re.sub(r"^\d+_", "", stem).replace("-", " ")

        entries.append((title, href))

    return entries


def _extract_page(page_path: Path) -> str:
    """Extract text from a single HTML content page."""
    from course_intelligence.engine.dataflows.html_parser import extract_html

    return extract_html(str(page_path))


def _extract_pdf_assets(folder: Path) -> list[ContentPage]:
    """Find and extract all PDF files in assets/ subdirectories."""
    from course_intelligence.engine.dataflows.pdf_parser import extract_pdf

    pdf_pages: list[ContentPage] = []

    # Walk all assets/ directories
    for assets_dir in folder.rglob("assets"):
        if not assets_dir.is_dir():
            continue
        for pdf_file in sorted(assets_dir.glob("*.pdf")):
            try:
                text = extract_pdf(str(pdf_file))
                relative_path = str(pdf_file.relative_to(folder))
                pdf_pages.append(
                    ContentPage(
                        page_number=0,  # will be set by caller
                        title=pdf_file.stem,
                        source_file=relative_path,
                        content_type="pdf_asset",
                        text=text,
                    )
                )
            except Exception as e:
                # Log warning but don't fail the whole job for one bad PDF
                import logging
                logging.warning(f"Failed to extract PDF asset {pdf_file}: {e}")
                continue

    return pdf_pages
