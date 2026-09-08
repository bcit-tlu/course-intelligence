"""Shared LLM message construction with instructor learning objectives."""

from __future__ import annotations

OBJECTIVES_LABEL = "Learning objectives for this course:"


def build_messages(
    system_prompt: str,
    learning_objectives: str | None,
    content: str,
) -> list[dict]:
    """Build the message list for an LLM call.

    When learning_objectives is non-blank, a user message carrying the
    objectives is inserted between the system prompt and the content so
    chunks and classifications reflect the instructor's intent. When
    blank, the list is exactly [system, content] — identical to the
    pre-objectives behavior.
    """
    messages: list[dict] = [{"role": "system", "content": system_prompt}]
    if learning_objectives and learning_objectives.strip():
        messages.append({
            "role": "user",
            "content": f"{OBJECTIVES_LABEL}\n{learning_objectives.strip()}",
        })
    messages.append({"role": "user", "content": content})
    return messages
