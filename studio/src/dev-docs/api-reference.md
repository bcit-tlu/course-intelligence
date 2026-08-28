# API Reference

The Course Intelligence API is a FastAPI application (`course_intelligence/api.py`)
that provides an asynchronous job interface for processing course materials.

## Base URL

In local development: `http://localhost:8000`
In production: `https://course-intelligence.<env>.ltc.bcit.ca/api`

## Endpoints

### Health Check

```
GET /health
```

Returns service status and whether the LLM is in mock mode.

**Response:**

```json
{
  "status": "ok",
  "mock_llm": false
}
```

### Create Job

```
POST /jobs
```

Accept a course upload, store it in object storage, and queue it for processing.
Returns `202 Accepted`.

**Request:** `multipart/form-data`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `file` | File | Yes | The course material file (PDF, DOCX, HTML, TXT, MD, or ZIP) |
| `learning_objectives` | string | No | Instructor-provided learning objectives |
| `X-Tenant-Id` | header | No | Optional tenant identifier for isolation |

**Response:**

```json
{
  "job_id": "uuid-string",
  "status": "queued"
}
```

**Errors:**

| Status | Cause |
|--------|-------|
| 400 | Unsupported file type |
| 500 | Job creation failed (storage or database error) |

### List Jobs

```
GET /jobs
```

List jobs, optionally filtered by status and/or tenant.

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `limit` | int | 50 | Maximum number of jobs to return |
| `status` | string | — | Filter by status: `queued`, `processing`, `completed`, `failed` |

**Headers:**

| Header | Description |
|--------|-------------|
| `X-Tenant-Id` | Optional — filter to jobs for a specific tenant |

**Response:**

```json
{
  "jobs": [
    {
      "job_id": "uuid-string",
      "status": "completed",
      "filename": "module.pdf",
      "created_at": "2025-01-15T10:30:00+00:00",
      "updated_at": "2025-01-15T10:35:00+00:00",
      "error": null,
      "current_step": null,
      "tenant_id": null
    }
  ]
}
```

### Get Job Status

```
GET /jobs/{job_id}
```

Return the current status of a job.

**Response:**

```json
{
  "job_id": "uuid-string",
  "status": "processing",
  "filename": "module.pdf",
  "created_at": "2025-01-15T10:30:00+00:00",
  "updated_at": "2025-01-15T10:32:00+00:00",
  "error": null,
  "current_step": "classifying",
  "tenant_id": null
}
```

**Errors:**

| Status | Cause |
|--------|-------|
| 404 | Job not found |

### Get Job Results

```
GET /jobs/{job_id}/results
```

Return the learning elements for a completed job.

**Response:**

```json
{
  "job_id": "uuid-string",
  "filename": "module.pdf",
  "elements": [
    {
      "id": "uuid-string",
      "topic": "Introduction to Sepsis",
      "content": "Sepsis is a life-threatening condition...",
      "blooms_level": "Understand",
      "blooms_rationale": "The element asks the learner to explain a concept.",
      "source_page": "Page 1",
      "page_number": 1
    }
  ]
}
```

**Errors:**

| Status | Cause |
|--------|-------|
| 404 | Job not found |
| 409 | Job is not completed (includes current status in message) |

## Async Flow

Processing is asynchronous. The typical client flow is:

1. **POST** `/jobs` — upload file, receive `job_id`
2. **Poll** `GET /jobs/{job_id}` — check status (`queued` → `processing` → `completed`)
3. **GET** `/jobs/{job_id}/results` — fetch learning elements once `completed`

## Supported File Types

| Extension | Format |
|-----------|--------|
| `.pdf` | PDF |
| `.docx` | Word |
| `.html`, `.htm` | HTML |
| `.txt` | Text |
| `.md` | Markdown |
| `.zip` | Zip (D2L export or collection of supported files) |
