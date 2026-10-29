# Job Status

## Job lifecycle

Every uploaded module creates a **job** that moves through the following states:

| State | Description |
|-------|-------------|
| **Queued** | The job has been created and is waiting to start processing |
| **Processing** | The pipeline is actively running on the file |
| **Completed** | Processing finished successfully — results are available |
| **Failed** | An error occurred during processing — the error message is shown |

## Processing steps

While a job is in the **Processing** state, it progresses through three stages:

1. **Extracting course content** — text is pulled from the uploaded file
2. **Identifying learning elements** — the text is split into individual knowledge elements
3. **Classifying cognitive levels** — each element is assigned a [Bloom's taxonomy](https://en.wikipedia.org/wiki/Bloom%27s_taxonomy) level

The job page shows a live progress indicator with the current step highlighted.
A timer displays elapsed time since the job was created.

> Processing can take several minutes for a full course module. The page
> updates automatically — no need to refresh.

## Job history

All jobs are listed on the **History** page (`/jobs`). Each entry shows:

- **Filename** of the uploaded module
- **Relative timestamp** (e.g. "5m ago", "2h ago")
- **Status badge** with an icon indicating the current state

Click any job to view its details, including processing progress or results.

## Deleting jobs

Completed, failed, and queued jobs can be removed from the history list.
Each job card has a **trash** button on its right edge; clicking it opens a
confirmation dialog. Confirming permanently deletes the job, its results,
and the uploaded file — this cannot be undone.

Jobs that are currently **Processing** cannot be deleted until they finish.
The trash button is hidden for those jobs; wait for the job to complete or
fail, then delete it.

## Error states

If a job fails, the job page displays:

- Which **step** the failure occurred in
- The **error message** describing what went wrong

Common causes of failure:

- Corrupted or password-protected PDF files
- Empty or unreadable documents
- Server-side processing errors

You can retry by uploading the file again from the home page.
