"""Tests for the flexible directory layout parser."""

import tempfile
from pathlib import Path

import pytest

from dialog.dataflows.interface import (
    _dispatch_directory,
    _natural_sort_key,
    _parse_generic_directory,
    dispatch,
)


def _write_html(path: Path, title: str, body: str) -> None:
    """Write a minimal HTML file."""
    path.write_text(
        f"<html><body><div class='container'>"
        f"<h1>{title}</h1><p>{body}</p>"
        f"</div></body></html>"
    )


class TestNestedD2L:
    """Tier 1: D2L with Table of Contents nested in a subdirectory."""

    def test_nested_toc_found_via_rglob(self, tmp_path: Path):
        """ToC inside a subdirectory should be found and parsed."""
        course_dir = tmp_path / "Course Export"
        course_dir.mkdir()
        module_dir = course_dir / "01"
        module_dir.mkdir()

        _write_html(module_dir / "page1.html", "Overview", "Intro content")
        _write_html(module_dir / "page2.html", "Sepsis", "Sepsis content")

        toc = module_dir / "Table of Contents.html"
        toc.write_text(
            '<html><body>'
            '<a href="page1.html">Overview</a>'
            '<a href="page2.html">Sepsis</a>'
            '</body></html>'
        )

        result = _dispatch_directory(course_dir)
        assert result["course_name"] == "01"
        assert len(result["pages"]) == 2
        assert result["pages"][0]["title"] == "Overview"
        assert result["pages"][1]["title"] == "Sepsis"

    def test_toc_at_root_still_works(self, tmp_path: Path):
        """ToC at the top level should still work (backward compat)."""
        _write_html(tmp_path / "page1.html", "Intro", "Hello")
        toc = tmp_path / "Table of Contents.html"
        toc.write_text('<html><body><a href="page1.html">Intro</a></body></html>')

        result = _dispatch_directory(tmp_path)
        assert len(result["pages"]) == 1
        assert result["pages"][0]["title"] == "Intro"


class TestGenericDirectory:
    """Tier 2: No ToC — generic directory parsing."""

    def test_mixed_files_collected(self, tmp_path: Path):
        """HTML and text files at various nesting levels should all be found."""
        _write_html(tmp_path / "01_intro.html", "Intro", "Introduction text")
        (tmp_path / "notes.txt").write_text("Some notes here")

        sub = tmp_path / "subdir"
        sub.mkdir()
        _write_html(sub / "02_detail.html", "Detail", "Detail content")

        result = _parse_generic_directory(tmp_path)
        assert result["module_id"] == "generic"
        assert len(result["pages"]) == 3
        titles = [p["title"] for p in result["pages"]]
        assert "01_intro" in titles
        assert "notes" in titles
        assert "02_detail" in titles

    def test_natural_sort_ordering(self, tmp_path: Path):
        """01_foo should come before 10_bar."""
        _write_html(tmp_path / "10_conclusion.html", "End", "Conclusion")
        _write_html(tmp_path / "01_intro.html", "Start", "Intro")
        _write_html(tmp_path / "02_middle.html", "Mid", "Middle")

        result = _parse_generic_directory(tmp_path)
        titles = [p["title"] for p in result["pages"]]
        assert titles == ["01_intro", "02_middle", "10_conclusion"]

    def test_page_numbers_sequential(self, tmp_path: Path):
        """Pages should be numbered 1, 2, 3... in sorted order."""
        for i in [10, 1, 5]:
            _write_html(tmp_path / f"{i:02d}_page.html", f"Page{i}", f"Content {i}")

        result = _parse_generic_directory(tmp_path)
        page_numbers = [p["page_number"] for p in result["pages"]]
        assert page_numbers == [1, 2, 3]

    def test_empty_directory_raises(self, tmp_path: Path):
        """An empty directory should raise a clear ValueError."""
        with pytest.raises(ValueError, match="No supported content files found"):
            _parse_generic_directory(tmp_path)

    def test_no_supported_files_raises(self, tmp_path: Path):
        """Directory with only unsupported files should raise."""
        (tmp_path / "image.png").write_bytes(b"\x89PNG")
        (tmp_path / "video.mp4").write_bytes(b"\x00\x00")

        with pytest.raises(ValueError, match="No supported content files found"):
            _parse_generic_directory(tmp_path)

    def test_source_file_is_relative_path(self, tmp_path: Path):
        """source_file should be the path relative to the root."""
        sub = tmp_path / "chapter1"
        sub.mkdir()
        _write_html(sub / "page.html", "Page", "Content")

        result = _parse_generic_directory(tmp_path)
        assert result["pages"][0]["source_file"] == "chapter1/page.html"


class TestNaturalSortKey:
    """Unit tests for the _natural_sort_key helper."""

    def test_numeric_prefix(self, tmp_path: Path):
        root = tmp_path
        f1 = root / "01_intro.html"
        f10 = root / "10_conclusion.html"

        assert _natural_sort_key(f1, root) < _natural_sort_key(f10, root)

    def test_nested_numeric(self, tmp_path: Path):
        root = tmp_path
        f1 = root / "chapter01" / "01_page.html"
        f2 = root / "chapter01" / "10_page.html"

        assert _natural_sort_key(f1, root) < _natural_sort_key(f2, root)


class TestDispatchIntegration:
    """Integration: dispatch() routes directories correctly."""

    def test_dispatch_generic_directory(self, tmp_path: Path):
        """dispatch() should route a non-D2L directory to the generic parser."""
        _write_html(tmp_path / "content.html", "Test", "Test content")

        result = dispatch(str(tmp_path))
        assert len(result["pages"]) == 1
        assert result["pages"][0]["title"] == "content"

    def test_dispatch_empty_directory_raises(self, tmp_path: Path):
        """dispatch() should propagate the ValueError from the generic parser."""
        with pytest.raises(ValueError, match="No supported content files found"):
            dispatch(str(tmp_path))
