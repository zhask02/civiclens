# CivicLens

## Current v1 scope and operations

CivicLens v1 is a pothole-only platform: a citizen photo, location, and
description flow through visual detection, deterministic severity/priority,
duplicate assessment, internal routing, and an operator queue.

Copy `.env.example` to `.env`, start Redis with `docker compose up -d`, then
run `backend\.venv\Scripts\python.exe -m alembic upgrade head` from the
repository root. Run FastAPI from `backend/`, `npm run dev` from `frontend/`,
`npm run build` to verify the frontend, and
`backend\.venv\Scripts\python.exe -m pytest tests -q` to run backend tests.

Citizen reporting/tracking is public in v1 and does not offer private report
ownership. The `#/operator` console accepts an operator/admin bearer token
only for the current browser session; credentials are never compiled into the
frontend. Operators can assign work, add append-only notes, advance lifecycle
state, and view routing/status history.

A CivicLens route is an internal recommendation, not an official complaint.
No external GCC, NHAI, Tamil Nadu, or campus submission integration exists.
Nominatim cannot prove road ownership, so uncertain reports intentionally route
to `UNKNOWN` with manual review. The detector has imperfect recall, and visual
severity is not a physical danger measurement.

> AI-powered urban infrastructure intelligence platform.

CivicLens is a full-stack, AI-powered web application for reporting, analyzing, and prioritizing urban infrastructure issues such as potholes, garbage accumulation, damaged signs, fallen trees, and blocked drains.

## Project Status

🚧 Currently under active development.

## Core Idea

A user submits a photo of an urban infrastructure problem. CivicLens will eventually:

- Analyze the image using AI
- Identify the type of issue
- Estimate severity
- Use geospatial and real-world context
- Detect potential duplicate reports
- Retrieve relevant procedures and documents
- Generate evidence-backed incident reports
- Help operators prioritize incidents

## Planned Tech Stack

- **Frontend:** Next.js + TypeScript
- **Backend:** FastAPI + Python
- **Database:** PostgreSQL + PostGIS
- **Cache & Background Jobs:** Redis + Celery
- **Object Storage:** S3 / MinIO
- **AI:** Hugging Face models
- **Infrastructure:** Docker + Docker Compose

## Development

This project is being built incrementally with Git and GitHub maintained from Day 1.

Every meaningful, working update is reviewed, committed, and pushed to GitHub.

---

🚧 CivicLens is currently at the project foundation stage.
