# Overview

## What is Dialog?

Dialog is a course material processor for nursing education. It takes raw course
modules — PDFs, Word documents, text files, or D2L export zips — and transforms
them into structured **learning elements**, each tagged with a **Bloom's taxonomy
level**.

## Who is it for?

Dialog is designed for nursing educators and curriculum designers who need to:

- Break down course material into individual knowledge topics
- See how content is distributed across cognitive levels
- Identify gaps in coverage (e.g. too much "Remember", not enough "Analyze")

## How it works

The processing pipeline has three stages:

| Step | Description |
|------|-------------|
| **Extract** | Raw text is extracted from the uploaded file (PDF, DOCX, TXT, etc.) |
| **Chunk** | The text is split into individual knowledge elements, each with a topic and content |
| **Classify** | Each element is assigned a Bloom's taxonomy level with a rationale |

After processing completes, you can browse the results, filter by Bloom's level,
and review the distribution of cognitive levels across the module.

## What you get

Each learning element includes:

- **Topic** — a short title describing the knowledge area
- **Content** — the extracted text for that topic
- **Bloom's level** — one of Remember, Understand, Apply, Analyze, Evaluate, or Create
- **Rationale** — a brief explanation of why that level was assigned
- **Source page** — the page number in the original document (when available)

Ready to get started? See [Uploading a Module](#uploading-a-module).
