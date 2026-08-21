# CivicLens — Project Source of Truth

> **Rule #1: Every meaningful update gets committed and pushed to GitHub.**

## 1. Project Overview

**Project Name:** CivicLens  
**Tagline:** AI-powered urban infrastructure intelligence platform.

CivicLens allows citizens or operators to submit photos of urban infrastructure problems such as potholes, garbage accumulation, damaged signs, fallen trees, blocked drains, and similar issues.

The system will use AI, geospatial information, real-world APIs, retrieval, and a prioritization engine to:

1. Analyze the submitted image.
2. Identify the type of infrastructure issue.
3. Estimate severity and risk.
4. Use location and surrounding context.
5. Check for duplicate reports.
6. Retrieve relevant procedures/documents.
7. Generate an evidence-backed incident report.
8. Help operators prioritize what should be fixed first.

---

# 2. Core Product Vision

This is **not** just an "upload an image and get an AI prediction" demo.

CivicLens should demonstrate real software engineering:

- Frontend application
- Backend APIs
- Database design
- Authentication
- Object storage
- Background processing
- Caching
- Message/job queues
- AI model inference
- Vector search
- Retrieval-Augmented Generation
- External APIs
- Geospatial queries
- Error handling and retries
- Logging and observability
- Docker and deployment
- Scalable architecture

The goal is to build an end-to-end, production-oriented system that is portfolio-worthy for software engineering and AI/ML-oriented roles.

---

# 3. Planned AI Capabilities

We will focus on a small number of tasks and integrate them deeply.

## 3.1 Object Detection

Potential uses:

- Potholes
- Garbage piles
- Damaged signs
- Vehicles
- Fallen trees
- Barriers
- Other infrastructure objects

Output should include:

- Detected class
- Confidence
- Bounding boxes

## 3.2 Image Segmentation

Potential uses:

- Estimate affected road area
- Segment potholes or damaged regions
- Support severity calculations

## 3.3 Visual Question Answering

The system may ask targeted questions such as:

- Is the road wet?
- Is standing water visible?
- Is the issue in a driving lane?
- Is a pedestrian nearby?
- Is a warning sign present?

## 3.4 Image-to-Text

Generate structured descriptions that can be used for:

- Incident reports
- Search
- Embeddings
- Duplicate detection
- Accessibility
- Audit logs

## 3.5 Visual Document Retrieval

Retrieve relevant pages from municipal or infrastructure documents, including documents containing:

- Text
- Tables
- Images
- Layout information

## 3.6 Document Question Answering

Answer questions using retrieved document pages and relevant layout/context.

---

# 4. Core System Features

## Phase 1 — Incident Reporting

A user should be able to:

- Create an account
- Upload an incident image
- Add or capture a location
- Add an optional description
- Submit a report
- Track report status

## Phase 2 — AI Analysis

The backend should:

1. Store the image.
2. Create an incident record.
3. Send analysis to a background job.
4. Run AI inference.
5. Store structured results.
6. Update the incident status.

## Phase 3 — Context Enrichment

Use external APIs and geospatial data to determine:

- Nearby roads
- Road importance/type
- Schools
- Hospitals
- Bus stops
- Intersections
- Weather conditions
- Recent rainfall
- Other relevant infrastructure

## Phase 4 — Duplicate Detection

Multiple reports may describe the same physical issue.

The system should attempt to identify duplicates using combinations of:

- Geographic proximity
- Time proximity
- Image similarity
- Text embeddings
- Incident type

Duplicate reports should be linked to a master incident where appropriate.

## Phase 5 — Priority Engine

A proposed priority formula:

Priority Score =
    visual_severity
  + road_importance
  + pedestrian_risk
  + weather_factor
  + report_frequency
  + nearby_critical_infrastructure

The exact formula and weights should be designed, tested, and versioned during development.

## Phase 6 — Document Intelligence

Retrieve relevant maintenance procedures or municipal documents and generate evidence-backed recommendations.

## Phase 7 — Operator Dashboard

Operators should be able to:

- View incidents on a map
- Filter by status and severity
- See AI analysis
- Review duplicate reports
- Inspect supporting evidence
- Prioritize incidents
- Update incident status

---

# 5. Proposed Architecture

```text
                         Next.js Frontend
                                |
                                v
                          FastAPI Backend
                                |
              +-----------------+------------------+
              |                 |                  |
              v                 v                  v
        PostgreSQL +         Redis             Object Storage
          PostGIS              |                 S3/MinIO
              |                 |
              |                 v
              |          Background Queue
              |                 |
              |          Celery / Worker
              |                 |
              +--------+--------+---------+
                       |                  |
                       v                  v
                 AI Inference       Retrieval Service
                       |                  |
                       v                  v
               Hugging Face Models   Vector Search / RAG
```

Architecture decisions may evolve, but major changes should be documented.

---

# 6. Proposed Technology Stack

## Frontend

- Next.js
- TypeScript
- Tailwind CSS
- React Query or equivalent
- MapLibre or Mapbox

## Backend

- Python
- FastAPI
- Pydantic

## Database

- PostgreSQL
- PostGIS
- pgvector (if appropriate)

## Caching / Jobs

- Redis
- Celery or another background worker system

## Object Storage

- S3-compatible storage
- MinIO for local development

## AI

- Hugging Face Transformers
- Vision models
- Embedding models
- Visual retrieval models
- LLM for report generation/RAG where appropriate

## Infrastructure

- Docker
- Docker Compose
- GitHub Actions later
- Cloud deployment later

---

# 7. External Data Sources

Potential integrations:

- OpenStreetMap / Overpass
- Weather API
- Geocoding API
- Street-level imagery APIs where suitable
- Public municipal/open-data APIs where available

Every external API integration should document:

- Purpose
- Authentication requirements
- Rate limits
- Failure handling
- Caching strategy
- Cost/free-tier limitations

---

# 8. Development Roadmap

## Milestone 0 — Project Foundation

- [ ] Create GitHub repository
- [ ] Create project README
- [ ] Create initial project structure
- [ ] Add this source-of-truth document
- [ ] Configure `.gitignore`
- [ ] Make first commit
- [ ] Push first commit to GitHub

## Milestone 1 — Backend Foundation

- [ ] Set up FastAPI
- [ ] Add health endpoint
- [ ] Set up environment configuration
- [ ] Connect PostgreSQL
- [ ] Design initial database schema
- [ ] Add Docker setup
- [ ] Add basic API documentation

## Milestone 2 — Incident Reporting

- [ ] Create incident database model
- [ ] Implement image upload
- [ ] Add object storage
- [ ] Create incident API endpoints
- [ ] Validate requests
- [ ] Handle errors

## Milestone 3 — AI Pipeline

- [ ] Select first model
- [ ] Create inference service abstraction
- [ ] Add asynchronous processing
- [ ] Store AI results
- [ ] Add retries and failure states

## Milestone 4 — Geospatial Intelligence

- [ ] Add PostGIS
- [ ] Store geographic coordinates
- [ ] Query nearby infrastructure
- [ ] Integrate map data
- [ ] Add weather enrichment

## Milestone 5 — Duplicate Detection

- [ ] Define duplicate criteria
- [ ] Add embeddings/similarity search
- [ ] Add geographic clustering
- [ ] Create master incident logic

## Milestone 6 — Priority Engine

- [ ] Define severity model
- [ ] Implement priority scoring
- [ ] Make weights configurable
- [ ] Store score explanations

## Milestone 7 — Retrieval and Document Intelligence

- [ ] Collect relevant documents
- [ ] Build ingestion pipeline
- [ ] Add retrieval
- [ ] Add document QA/RAG
- [ ] Link recommendations to evidence

## Milestone 8 — Frontend

- [ ] Build incident submission flow
- [ ] Build incident status view
- [ ] Build map
- [ ] Build operator dashboard
- [ ] Add loading/error states

## Milestone 9 — Production Engineering

- [ ] Redis caching
- [ ] Background jobs
- [ ] Rate limiting
- [ ] Structured logging
- [ ] Monitoring/observability
- [ ] Security review
- [ ] Automated tests

## Milestone 10 — Deployment

- [ ] Production Docker configuration
- [ ] CI/CD
- [ ] Deploy backend
- [ ] Deploy frontend
- [ ] Configure production database/storage
- [ ] Add monitoring

---

# 9. GitHub Is Mandatory

## Our Development Rule

**We do not treat GitHub as something to update at the end of the project.**

GitHub will be maintained from Day 1.

Every meaningful completed unit of work should follow:

```text
Plan
  ↓
Create a branch if appropriate
  ↓
Implement
  ↓
Run/test
  ↓
Review changes
  ↓
git status
  ↓
git add
  ↓
git commit
  ↓
git push
  ↓
Verify GitHub
```

## Commit Rule

Commit after a meaningful, working change.

Good examples:

- Set up FastAPI project
- Add PostgreSQL connection
- Add incident database model
- Implement image upload endpoint
- Add Redis caching
- Integrate weather service
- Fix authentication bug

Avoid one huge commit containing several unrelated features.

Avoid committing broken code unless there is a deliberate reason.

## Commit Message Format

Use simple, descriptive commits:

```text
feat: add FastAPI application skeleton
feat: add incident creation endpoint
feat: integrate PostgreSQL database
feat: add image upload service
fix: handle invalid image uploads
fix: retry failed analysis jobs
docs: update architecture documentation
refactor: separate inference service
test: add incident API tests
chore: update Docker configuration
```

## Before Every Commit

Run:

```bash
git status
```

Check what changed.

Then:

```bash
git diff
```

Review the changes before committing.

## Basic Workflow

First time:

```bash
git init
git add .
git commit -m "chore: initialize CivicLens project"
git branch -M main
git remote add origin <YOUR_GITHUB_REPOSITORY_URL>
git push -u origin main
```

For normal updates:

```bash
git status
git add .
git commit -m "feat: describe the completed feature"
git push
```

Before starting work after a break:

```bash
git pull
```

## Important Git Rule

Never blindly use commands without understanding them.

As part of this project, Git and GitHub are learning objectives. Every time we use a new Git command, we should understand:

1. What it does.
2. Why we need it.
3. What state the repository is in before running it.
4. What changed after running it.

---

# 10. Repository Structure Target

The exact structure can evolve, but we should aim for something similar to:

```text
civiclens/
│
├── README.md
├── PROJECT.md
├── .gitignore
├── .env.example
├── docker-compose.yml
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── db/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── services/
│   │   ├── workers/
│   │   └── main.py
│   │
│   ├── tests/
│   ├── requirements.txt
│   └── Dockerfile
│
├── frontend/
│   ├── app/
│   ├── components/
│   ├── lib/
│   └── package.json
│
├── docs/
│   ├── architecture/
│   ├── api/
│   └── decisions/
│
└── scripts/
```

---

# 11. Documentation Requirements

Maintain documentation throughout development.

## README.md

Should eventually include:

- Project overview
- Problem statement
- Features
- Architecture
- Technology stack
- Screenshots
- Setup instructions
- API overview
- AI pipeline
- Deployment
- Future work

## PROJECT.md

This file is the detailed source of truth for:

- Vision
- Architecture
- Roadmap
- Features
- Engineering decisions
- GitHub workflow

## Architecture Documentation

Major architecture decisions should be recorded.

Example:

```text
Decision: Use background workers for AI analysis.

Reason:
AI inference may take several seconds and should not block the API request.

Trade-off:
Additional infrastructure complexity.

Decision Date:
YYYY-MM-DD
```

---

# 12. Definition of Done

A feature is not fully done just because the code was written.

A feature is considered done when appropriate items are complete:

- [ ] Implementation completed
- [ ] Manually tested
- [ ] Automated tests added where appropriate
- [ ] Errors handled
- [ ] API/schema updated if necessary
- [ ] Documentation updated if necessary
- [ ] Git changes reviewed
- [ ] Meaningful commit created
- [ ] Changes pushed to GitHub

---

# 13. Learning Goals

This project is also a structured learning vehicle.

By the end, the developer should understand:

- Git and GitHub
- REST APIs
- HTTP requests/responses
- Backend architecture
- Databases
- SQL
- PostgreSQL
- Redis
- Caching
- Background jobs
- Queues
- Docker
- Environment variables
- Authentication
- Object storage
- AI model inference
- RAG
- Vector search
- Geospatial databases
- External API integration
- System design fundamentals
- Deployment
- CI/CD
- Monitoring

---

# 14. Non-Negotiable Project Principles

1. **Build incrementally.**
2. **Do not overengineer early.**
3. **Get a small vertical slice working first.**
4. **Understand every major component we add.**
5. **Do not copy code blindly.**
6. **Use GitHub from Day 1.**
7. **Commit meaningful updates regularly.**
8. **Push completed updates regularly.**
9. **Document major decisions.**
10. **Measure real metrics instead of inventing impressive numbers.**
11. **Prefer a working end-to-end product over many disconnected AI features.**
12. **Every new technology should have a clear reason for being in the architecture.**

---

# 15. Current Status

**Project Stage:** Milestone 0 — Project Foundation

**Immediate next objective:**

Create the CivicLens repository locally, initialize Git, create the initial project structure, add this `PROJECT.md` file and a starter `README.md`, make the first commit, and push the project to GitHub.

---

## Change Log

### 2026-08-20
- Project concept established.
- Initial architecture and roadmap documented.
- GitHub-from-Day-1 workflow established as a core project requirement.
- Commit and push discipline marked as mandatory.
