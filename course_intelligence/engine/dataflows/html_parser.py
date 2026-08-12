"""HTML-to-text parser — converts D2L course HTML pages to clean plain text."""

from __future__ import annotations

from bs4 import BeautifulSoup


def extract_html(path: str) -> str:
    """Extract text from an HTML file, preserving heading structure.

    Targets the <div class="container"> body used by BCIT/D2L templates.
    Strips scripts, styles, and navigation. Converts headings to
    markdown-style markers for downstream processing.
    """
    with open(path, "r", encoding="utf-8") as f:
        html = f.read()

    return html_to_text(html)


def html_to_text(html: str) -> str:
    """Convert raw HTML string to structured plain text.

    Heading levels are preserved as markdown markers (# ## ###).
    Lists are converted to bullet/numbered text.
    Tables are preserved as pipe-delimited rows.
    Scripts, styles, and boilerplate are stripped.
    """
    soup = BeautifulSoup(html, "html.parser")

    # Remove unwanted elements
    for tag in soup.find_all(["script", "style", "link", "meta", "nav"]):
        tag.decompose()

    # Try to find the main content container (BCIT D2L template)
    container = soup.find("div", class_="container")
    if container is None:
        # Fallback: use the whole body
        container = soup.find("body")
    if container is None:
        container = soup

    lines: list[str] = []
    _walk(container, lines)

    # Clean up excessive blank lines
    text = "\n".join(lines)
    while "\n\n\n" in text:
        text = text.replace("\n\n\n", "\n\n")
    return text.strip()


def _walk(element, lines: list[str]) -> None:
    """Recursively walk the DOM and build plain text output."""
    from bs4 import NavigableString, Tag

    for child in element.children:
        if isinstance(child, NavigableString):
            text = child.strip()
            if text:
                lines.append(text)
        elif isinstance(child, Tag):
            tag_name = child.name

            # Headings → markdown markers
            if tag_name == "h1":
                lines.append("")
                lines.append(f"# {child.get_text(strip=True)}")
                lines.append("")
            elif tag_name == "h2":
                lines.append("")
                lines.append(f"## {child.get_text(strip=True)}")
                lines.append("")
            elif tag_name == "h3":
                lines.append("")
                lines.append(f"### {child.get_text(strip=True)}")
                lines.append("")
            elif tag_name == "h4":
                lines.append("")
                lines.append(f"#### {child.get_text(strip=True)}")
                lines.append("")
            elif tag_name == "h5":
                lines.append(f"##### {child.get_text(strip=True)}")

            # Paragraphs
            elif tag_name == "p":
                text = child.get_text(strip=True)
                if text:
                    lines.append(text)
                    lines.append("")

            # Unordered lists
            elif tag_name == "ul":
                for li in child.find_all("li", recursive=False):
                    li_text = li.get_text(strip=True)
                    if li_text:
                        lines.append(f"- {li_text}")
                lines.append("")

            # Ordered lists
            elif tag_name == "ol":
                for i, li in enumerate(child.find_all("li", recursive=False), 1):
                    li_text = li.get_text(strip=True)
                    if li_text:
                        lines.append(f"{i}. {li_text}")
                lines.append("")

            # Tables
            elif tag_name == "table":
                _extract_table(child, lines)
                lines.append("")

            # Figures / images — extract caption text only
            elif tag_name == "figure":
                caption = child.find("figcaption")
                if caption:
                    cap_text = caption.get_text(strip=True)
                    if cap_text:
                        lines.append(f"[Figure: {cap_text}]")
                        lines.append("")

            # Divs and other containers — recurse
            else:
                _walk(child, lines)


def _extract_table(table_tag, lines: list[str]) -> None:
    """Convert an HTML table to pipe-delimited plain text rows."""
    rows = table_tag.find_all("tr")
    for row in rows:
        cells = row.find_all(["th", "td"])
        cell_texts = [c.get_text(strip=True) for c in cells]
        if any(cell_texts):
            lines.append("| " + " | ".join(cell_texts) + " |")
