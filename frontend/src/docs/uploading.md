# Uploading a Module

## Supported file formats

Dialog accepts the following file types:

| Extension | Format | Notes |
|-----------|--------|-------|
| `.zip` | D2L export | Zipped course package from Desire2Learn/Brightspace |
| `.pdf` | PDF document | Text-based PDFs work best; scanned images may not extract cleanly |
| `.docx` | Word document | Microsoft Word (.docx) format |
| `.txt` | Plain text | UTF-8 encoded text file |
| `.md` | Markdown | Markdown source file |

## How to upload

1. Navigate to the **home page** (`/`)
2. **Drag and drop** a file onto the upload zone, or **click to browse** your file system
3. Optionally enter **learning objectives** (one per line) — these help guide the chunking process
4. Click **Process Module** to start

## Learning objectives (optional)

Learning objectives are free-text goals you provide to help the processor
understand what the course is trying to teach. Enter one per line, for example:

```
Describe the key principles of sepsis recognition
Explain the chain of survival for cardiac arrest
Demonstrate proper technique for IV insertion
```

Objectives are optional — the processor will work without them, but providing
them can improve the quality of the knowledge extraction.

## What happens after submit

- A **job** is created and you are redirected to the job status page
- The file is uploaded to the server and processing begins automatically
- You can monitor progress in real time on the job page
- Once complete, results appear on the same page — no refresh needed

See [Job Status](#job-status) for details on the processing lifecycle.
