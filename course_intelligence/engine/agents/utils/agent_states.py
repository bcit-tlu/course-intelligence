"""AgentState — the single object that flows through every graph node."""

from __future__ import annotations

from typing import NotRequired, TypedDict


class ContentPage(TypedDict):
    page_number: int
    title: str
    source_file: str
    content_type: str          # "html_page" | "pdf_asset" | "pdf" | "docx" | "text"
    text: str


class CourseModule(TypedDict):
    course_name: str
    module_id: str
    source_folder: str
    pages: list[ContentPage]


class KnowledgeChunk(TypedDict):
    chunk_id: str
    topic: str
    content: str
    source_page: NotRequired[str]      # title of the page the chunk came from
    page_number: NotRequired[int]
    blooms_level: NotRequired[str]     # Bloom's taxonomy level (set by classifier)
    blooms_rationale: NotRequired[str]


class AgentState(TypedDict, total=False):
    # --- inputs ---
    source_path: str               # path to the uploaded file or directory
    learning_objectives: str       # raw instructor-provided objectives string
    raw_text: str                  # extracted plain text / markdown

    # --- set by content extractor ---
    course_module: CourseModule     # structured parsed content

    # --- set by semantic_chunker ---
    knowledge_map: list[KnowledgeChunk]

    # --- meta ---
    error: str | None
