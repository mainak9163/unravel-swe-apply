# Unravel SWE Application Agent

This repository contains the agent I built for the Unravel SWE application flow.

## What This Agent Does

The agent automates the application-email task end-to-end:

1. Searches for founder information about Unravel.tech using multiple web providers.
2. Collects source-backed evidence from search results and fetched pages.
3. Uses Gemini to identify the founder whose name contains `pr`.
4. Constructs the founder email as `<first_name>@unravel.tech`.
5. Generates a professional application email in a strict output format.

The API returns a single final email draft ready to send.

It also supports a follow-up mode that finds the founder email and sends the reply directly over SMTP.

## Why This Exists

I initially sent my first outreach email with assistance from tool-based web search while validating the task expectations.

This version is the implemented agent system itself, with explicit search, evidence collection, founder extraction, and final email generation wired together as code.

## Tech Stack

- Python
- FastAPI
- Uvicorn
- Requests
- DDGS (DuckDuckGo search)
- Gemini API (`gemini-2.5-flash` by default)

Optional search-provider integrations:

- Serper (`SERPER_API_KEY`)
- Tavily (`TAVILY_API_KEY`)

## Project Structure

```text
main.py
src/
  app/
    api.py            # FastAPI endpoint (/apply)
    agent.py          # Orchestration, prompt + output validation
    gemini.py         # Gemini API call + founder extraction helper
    search.py         # Multi-provider search + page fetch + evidence builder
    config.py         # Environment config
    logging_setup.py  # Logging setup
```

## API Flow

1. `POST /apply` accepts applicant details (`name`, `bio`, `skills`, `role`, `resume_path`, `rhyming_word`).
2. `run_agent()` gathers search context with source snippets and fetched page excerpts.
3. `identify_target_founder()` extracts founder candidates from evidence and picks the `pr` match.
4. Agent computes recipient email from founder first name.
5. Gemini produces final output in required template:

```text
To: ...
Subject: ...
Body:
...
Attachment: ...
```

6. Response is returned as JSON:

```json
{
  "email_draft": "..."
}
```

## Setup

### Prerequisites

- Python 3.10+
- A valid Gemini API key

### Install

```bash
pip install fastapi uvicorn requests ddgs
```

### Environment Variables

Required:

- `GEMINI_API_KEY`

Optional:

- `GEMINI_MODEL` (default: `gemini-2.5-flash`)
- `SERPER_API_KEY`
- `TAVILY_API_KEY`
- `LOG_LEVEL` (default: `INFO`)
- `SMTP_HOST` (required for send flow)
- `SMTP_PORT` (default: `587`)
- `SMTP_USERNAME`
- `SMTP_PASSWORD`
- `SMTP_FROM_EMAIL` (defaults to `SMTP_USERNAME`)
- `SMTP_USE_TLS` (default: `true`)

### Run

```bash
python main.py
```

Server starts at:

- `http://0.0.0.0:8000`

### Example Request

```bash
curl -X POST "http://127.0.0.1:8000/apply" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Mainak Mukherjee",
    "bio": "Software engineer with internship experience and interest in AI agents.",
    "skills": "Python, TypeScript, backend systems",
    "role": "SDE-1",
    "resume_path": "resume.pdf",
    "rhyming_word": "Why"
  }'
```

### Follow-up Send Request

Use this endpoint to have the agent identify the founder email and send your follow-up automatically:

```bash
curl -X POST "http://127.0.0.1:8000/followup/send" \
  -H "Content-Type: application/json" \
  -d '{
    "applicant_name": "Mainak Mukherjee",
    "sender_email": "mainakcollege8967@gmail.com",
    "repo_url": "https://github.com/mainak9163/unravel-swe-apply",
    "video_note": "I will add a process walkthrough video link in the repository shortly.",
    "subject": "Re: Application - Agent Code Repository"
  }'
```

## Design Notes

- Search is source-first and provider-agnostic (Serper, Tavily, DDG fallback).
- URL deduping and domain-priority ranking improve relevance.
- Founder extraction uses structured JSON parsing and retry logic.
- Final email output is validated for strict formatting before returning.
- Logging is enabled across all major steps for traceability.

## Limitations

- Search quality depends on public web indexing and provider availability.
- Founder identification depends on evidence quality in retrieved pages.
- This implementation targets the specified Unravel application workflow and output format.

## Process Video

A walkthrough video demonstrating the full process (setup, run, and live output) will be added here:

- [`VIDEO_LINK_HERE`](https://streamable.com/4l9f7k)

## Author

- Mainak Mukherjee
- Email: `mainakcollege8967@gmail.com`

