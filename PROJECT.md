# CivicLens — Project Source of Truth

> **Rule #1: Every meaningful update gets committed and pushed to GitHub.**

## 1. Project Overview

**Project Name:** CivicLens  
**Tagline:** AI-powered pothole intelligence platform.

CivicLens v1 is a focused, end-to-end platform for reporting, analyzing,
prioritizing, and managing **pothole incidents**.

The project deliberately starts with one civic issue instead of attempting
to solve every infrastructure problem at once. Other categories such as
garbage, drainage, streetlights, and water leaks are future extensions.

The goal is to demonstrate real AI/backend engineering rather than a simple
image-classification demo.

---

# 2. V1 Product Scope

CivicLens v1 should provide:

1. Pothole incident reporting
2. Image/evidence upload
3. Location capture and enrichment
4. Local pothole detection
5. Structured visual predictions
6. Explainable severity estimation
7. Duplicate/related report detection
8. Deterministic priority scoring
9. Incident lifecycle management
10. Operator/admin dashboard
11. Geographic visualization
12. Deployment
13. Testing and demonstration polish

Incident lifecycle:

```text
SUBMITTED → ANALYZED → ASSIGNED → IN_PROGRESS → RESOLVED
```

### Deferred from v1

- Garbage detection
- Streetlight detection
- Drainage detection
- Water-leak detection
- Generic multi-class civic issue detection
- Large multimodal LLM pipeline
- Full RAG/document intelligence
- Vector database infrastructure
- Multiple specialized CV models

These may be added after the pothole product is complete.

---

# 3. Core Architecture Principle

CivicLens separates **visual facts**, **business reasoning**, and
**application infrastructure**.

```text
Image
  ↓
PotholeDetector
  ↓
VisualPrediction
  ↓
SeverityEngine
  ↓
SeverityAssessment
  ↓
Location enrichment
  ↓
PriorityEngine
  ↓
PriorityResult
```

Duplicate detection is a separate workflow:

```text
New Incident
  ↓
Candidate Retrieval
  ↓
DuplicateService
  ├── Location similarity
  ├── Time similarity
  └── Visual similarity
  ↓
DUPLICATE / RELATED / SEPARATE
```

The important architectural rule is:

> **Pure domain logic should not directly depend on databases, APIs,
> storage, Redis, or FastAPI.**

Infrastructure prepares the data; domain services make deterministic
decisions from that data.

This keeps the system easier to test, explain, replace, and deploy.

---

# 4. Current Repository Structure

```text
civiclens/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   └── incidents.py
│   │   ├── clients/
│   │   │   ├── supabase.py
│   │   │   ├── redis.py
│   │   │   └── geocoding.py
│   │   ├── config.py
│   │   ├── db/
│   │   │   ├── database.py
│   │   │   ├── dependencies.py
│   │   │   └── models.py
│   │   ├── enums/
│   │   │   └── incident.py
│   │   ├── models/
│   │   │   ├── incident.py
│   │   │   ├── evidence.py
│   │   │   └── analysis.py
│   │   ├── schemas/
│   │   │   ├── incident.py
│   │   │   ├── evidence.py
│   │   │   ├── analysis.py
│   │   │   ├── vision.py
│   │   │   └── location.py
│   │   └── services/
│   │       ├── incident.py
│   │       ├── storage.py
│   │       ├── analysis.py
│   │       ├── vision.py
│   │       ├── pothole_detector.py
│   │       ├── severity.py
│   │       ├── location.py
│   │       ├── location_context.py
│   │       ├── priority.py
│   │       ├── duplicate.py
│   │       └── visual_embedding.py
│   ├── tests/
│   └── scripts/
├── evaluation/
├── ml/
│   └── weights/
│       └── yolo26_best.pt
├── test_images/
├── .env
├── .gitignore
├── compose.yaml
├── PROJECT.md
└── README.md
```

`backend/app/models/` contains SQLAlchemy database models.

`backend/app/schemas/` contains Pydantic API/data contracts.

`ml/weights/` contains model weights.

This separation prevents database models, API contracts, and ML artifacts
from becoming mixed together.

---

# 5. Technology Stack and Why

## Python

Used for the backend and AI components because the project needs strong
support for FastAPI, SQLAlchemy, PyTorch, Ultralytics, NumPy, PIL, and ML
libraries.

## FastAPI

Used as the backend API framework because it provides typed request/response
validation, automatic OpenAPI documentation, and good integration with
Python AI services.

## Pydantic

Used for structured contracts between services and API boundaries.

This prevents loosely structured dictionaries from becoming the default
communication mechanism between components.

## PostgreSQL / Supabase

PostgreSQL is the persistent relational database.

Supabase is used for managed PostgreSQL and object storage, reducing
infrastructure overhead while still using standard PostgreSQL concepts.

## SQLAlchemy

SQLAlchemy provides the database abstraction and ORM layer.

The application keeps database session creation in `database.py` and the
FastAPI session lifecycle in `dependencies.py`.

## Alembic

Alembic manages versioned database schema changes.

This is preferable to manually changing production database schemas because
each schema evolution becomes reproducible and reviewable.

## Supabase Storage

Incident images are stored as objects rather than directly inside database
rows.

The database stores metadata and the storage path.

This keeps large binary evidence separate from relational incident data.

## Redis

Redis is used as infrastructure for caching geospatial lookups and can later
support other short-lived application state.

The reason for adding Redis is performance and external-API protection, not
because every feature requires a cache.

## OpenStreetMap / Nominatim

Nominatim provides reverse geocoding and geographic context.

CivicLens preserves useful OSM vocabulary such as highway, amenity, road,
and place information rather than forcing everything into a tiny custom
road-type enum.

Nominatim requests are cached and the provider is kept behind a client
abstraction because public geocoding services have rate limits and usage
policies.

## Docker / Docker Compose

Docker provides reproducible local infrastructure.

Redis currently runs through Docker Compose, allowing the application to use
the same service boundary locally without installing Redis directly on the
host.

## Ultralytics / YOLO

YOLO is used for local pothole object detection because CivicLens needs
bounding boxes and confidence values, not merely image-level classification.

Local inference avoids requiring an external vision API for every submitted
image.

## Hugging Face model weights

The selected pothole detector is:

`DanielsStulpe/pothole-detection`

Its local weights are stored as:

`ml/weights/yolo26_best.pt`

The model is used locally so inference is controllable and reproducible.

## MobileNetV3 Small / timm

MobileNetV3 Small is used as a lightweight visual feature extractor for
duplicate detection.

A benchmark showed strong separation on the selected pothole dataset while
remaining fast and lightweight enough for CPU inference.

It is used as an embedding model, not as the pothole detector.

## NumPy

NumPy is used for numerical operations including embedding normalization and
cosine similarity.

---

# 6. AI Architecture

## 6.1 Pothole Detection

The detector is abstracted behind:

```text
VisionModel
    ↓
PotholeDetector
```

The abstraction means the rest of CivicLens does not need to know the
specific implementation of the current detector.

The detector:

- validates image bytes
- runs YOLO inference
- filters detections at the current provisional confidence threshold
- returns structured bounding boxes
- returns the highest accepted confidence
- identifies the incident category as pothole when detections exist

Current detector threshold:

`0.40`

This threshold is an engineering choice for the application and is not
claimed to be the globally optimal model threshold.

---

# 7. Model Evaluation

The selected detector was evaluated against the IIT Madras Pothole Detection
dataset v2.

Dataset:

- 2,722 total images
- 1,906 train
- 542 validation
- 274 test
- 3 classes
- pothole class ID 2

At IoU 0.50 and confidence 0.19:

### Validation

- Precision: 0.676
- Recall: 0.374
- F1: 0.481
- TP: 540
- FP: 259
- FN: 904

### Test

- Precision: 0.664
- Recall: 0.335
- F1: 0.446
- TP: 227
- FP: 115
- FN: 450

The major weakness is missed potholes rather than catastrophic false-positive
behavior.

These measurements are retained as project evidence instead of presenting
unverified model-performance claims.

---

# 8. Severity Engine

Severity is deliberately separated from object detection.

The detector answers:

> "What visual object was detected and where?"

The severity engine answers:

> "How visually significant does this detected issue appear?"

The current deterministic heuristic uses:

- largest bounding-box area ratio
- number of detected potholes
- highest detector confidence as a small supporting signal

Severity levels:

```text
LOW
MEDIUM
HIGH
CRITICAL
```

The system explicitly does **not** claim that image bounding-box size measures
physical pothole depth or exact real-world dimensions.

Detector confidence is treated as reliability evidence, not physical danger.

No detection returns no severity rather than incorrectly treating the issue
as a low-severity pothole.

---

# 9. Location Intelligence

CivicLens enriches incident coordinates using reverse geocoding.

Current structured location information includes:

- latitude
- longitude
- OSM category
- OSM type
- OSM highway
- OSM amenity
- OSM name
- OSM road
- neighbourhood
- suburb
- city
- state
- postcode
- country
- CivicLens civic context

CivicLens-specific contexts currently include:

```text
CAMPUS
PARKING
UNKNOWN
```

The system does not guess a context solely from a place name or coordinate.

For example, explicit OSM evidence for a university/college can produce
`CAMPUS`.

This separation lets CivicLens preserve provider data while adding its own
operational interpretation.

---

# 10. Priority Engine

Priority is separate from severity.

Severity represents:

> apparent visual seriousness.

Priority represents:

> how urgently CivicLens should surface the incident.

Current deterministic model:

```text
Priority Score =
    Base Severity Score
    × Location Multiplier
    × Confidence Factor
```

Severity base scores:

```text
LOW       25
MEDIUM    50
HIGH      75
CRITICAL  100
```

Location multipliers:

```text
UNKNOWN   0.8
PARKING   0.9
CAMPUS    1.0
```

Confidence acts as a reliability dampener rather than a danger score.

Scores map to:

```text
LOW
MEDIUM
HIGH
CRITICAL
```

Low-confidence predictions are additionally marked for review.

This deterministic approach was chosen for v1 because it is transparent,
testable, and explainable. More complex learned prioritization can be
evaluated later once CivicLens has real incident data.

---

# 11. End-to-End Analysis Pipeline

The current analysis service orchestrates:

```text
Evidence
   ↓
Download image
   ↓
PotholeDetector
   ↓
SeverityEngine
   ↓
Location enrichment
   ↓
PriorityEngine
   ↓
AnalysisResult
   ↓
EvidenceAnalysis persistence
```

The orchestration layer is separate from the individual domain services.

This makes each component independently testable while allowing the API to
run the complete workflow.

The pipeline rejects cases where no pothole is detected instead of producing
a misleading low-priority pothole record.

---

# 12. Duplicate Detection

Duplicate detection determines whether two reports may describe the same
physical pothole.

Architecture:

```text
New Incident
    ↓
Candidate Retrieval
    ↓
DuplicateService
    ├── Location similarity
    ├── Time similarity
    └── Visual similarity
    ↓
Combined Score
    ↓
DUPLICATE / RELATED / SEPARATE
```

## 12.1 Geographic similarity

Haversine distance is used because latitude and longitude are spherical
coordinates rather than ordinary Cartesian x/y values.

Current location scoring:

```text
≤ 20m     → 100
≤ 50m     → 70
≤ 100m    → 30
> 100m    → 0
```

These are initial engineering thresholds and will be recalibrated using real
CivicLens reports.

## 12.2 Temporal similarity

Current time scoring:

```text
≤ 1 hour   → 100
≤ 6 hours  → 75
≤ 24 hours → 50
≤ 72 hours → 20
> 72 hours → 0
```

## 12.3 Visual similarity

MobileNetV3 Small generates normalized image embeddings.

Cosine similarity compares two embeddings.

The benchmark produced:

### Full-image benchmark

- 270 pothole test images
- 50 synthetic same-image positive pairs
- 200 negative pairs
- Positive mean: 0.9311
- Positive minimum: 0.8577
- Negative mean: 0.3185
- Negative maximum: 0.8109
- Initial benchmark threshold: 0.82

The benchmark achieved perfect separation on those sampled pairs.

**Important limitation:** positive pairs were synthetic transformations of
the same image, not independent photographs of the same physical pothole.
Therefore the 0.82 threshold is provisional and must not be presented as
real-world duplicate accuracy.

A crop-based benchmark was also tested but produced worse negative separation,
so CivicLens currently uses the full image.

## 12.4 Combined duplicate score

When visual evidence is available:

```text
Location  45%
Time      20%
Visual    35%
```

When visual evidence is unavailable, the service falls back to:

```text
Location  60%
Time      40%
```

If only one embedding is provided, the service rejects the comparison
explicitly rather than silently ignoring incomplete visual evidence.

---

# 13. Candidate Retrieval — Next Architecture Layer

`DuplicateService` deliberately does not access the database.

The next layer will retrieve plausible existing incidents before comparison.

Conceptually:

```text
New Incident
     ↓
Candidate Retrieval
     ├── geographic window
     └── temporal window
     ↓
Potential existing incidents
     ↓
DuplicateService
```

Initial candidate bounds will align with the duplicate engine:

- within 100 metres
- within 72 hours
- appropriate incident category/status filtering where useful

The candidate retrieval component answers:

> "Which incidents are worth comparing?"

The `DuplicateService` answers:

> "How similar are these two incidents?"

This separation prevents database queries from contaminating pure duplicate
scoring logic.

---

# 14. Database Architecture

Current database models include:

## Incident

Stores:

- description
- latitude
- longitude
- category
- severity
- status
- confidence
- created_at

## IncidentEvidence

Stores:

- incident_id
- storage_path
- file_type
- created_at

## EvidenceAnalysis

Stores:

- evidence_id
- category
- severity
- confidence
- model_name
- severity_score
- priority_score
- priority_level
- requires_review
- created_at

Database sessions are managed through:

```text
database.py
    ↓
SessionLocal

FastAPI dependency
    ↓
get_db()
    ↓
request-scoped Session
```

We will reuse this mechanism rather than creating feature-specific database
connections.

---

# 15. External API Principles

Every external service should be isolated behind a client.

Current examples:

```text
Supabase client
Redis client
Geocoding client
```

Reasons:

1. External APIs can fail.
2. External providers can change.
3. Tests should not require live network access.
4. Production providers may differ from development providers.
5. Rate limits and authentication should not leak into domain logic.

External API integrations should document:

- purpose
- authentication
- rate limits
- caching
- failure handling
- cost/free-tier limitations

---

# 16. Redis Strategy

Redis is not currently the source of truth for incidents.

PostgreSQL remains authoritative.

Redis is intended for short-lived/cacheable information such as geocoding
results.

This avoids repeatedly calling external geocoding services for the same
coordinates and helps respect provider rate limits.

Redis may later support:

- background-job infrastructure
- frequently accessed incident data
- rate limiting
- other temporary application state

Only add these uses when the actual architecture needs them.

---

# 17. Testing Strategy

Tests are required for meaningful domain behavior.

Current backend test suite:

**47 tests passing**

Important tested areas include:

- vision model behavior
- pothole detector
- severity engine
- priority engine
- location interpretation
- analysis orchestration
- Haversine distance
- time similarity
- duplicate assessment
- cosine similarity
- visual embedding service
- visual duplicate behavior
- missing/partial visual evidence

The preferred workflow is:

```text
Implement
   ↓
Test focused feature
   ↓
Run full suite
   ↓
Review diff
   ↓
Update PROJECT.md
   ↓
Commit
   ↓
Push
```

---

# 18. GitHub Development Rule

GitHub is maintained from Day 1.

Every meaningful working checkpoint should be:

```text
Implement
→ Test
→ Review diff
→ Update PROJECT.md
→ git status
→ git add
→ git commit
→ git push
→ verify clean working tree
```

We do not accumulate weeks of undocumented changes.

Git commits should represent meaningful working units.

Examples:

```text
feat(cv): add vision model abstraction
feat(severity): add severity engine
feat(duplicate): add haversine distance
feat(duplicate): add time similarity
feat(duplicate): add duplicate assessment service
feat(duplicate): add visual embedding service
feat(duplicate): add visual similarity
```

Before committing:

```text
git status
git diff
```

Git is also a learning objective. New Git commands should be understood
before being used.

---

# 19. Architecture Decision Log

## Decision 1 — Focus v1 on potholes

**Why:** A complete single-domain product is more valuable than many
half-finished civic categories.

**Trade-off:** The first release has narrower functionality.

**Status:** Chosen for v1.

---

## Decision 2 — Separate detection from severity

**Why:** Object detection should report visual facts, while severity is an
application-level interpretation.

**Trade-off:** More components than putting everything inside the detector.

**Benefit:** Easier testing, explainability, and future model replacement.

**Status:** Implemented.

---

## Decision 3 — Use deterministic severity scoring for v1

**Why:** There is not yet enough CivicLens-specific labeled data to justify a
learned severity model.

**Trade-off:** Less sophisticated than a trained model.

**Benefit:** Transparent and auditable behavior.

**Status:** Implemented.

---

## Decision 4 — Use deterministic priority scoring for v1

**Why:** Priority is a business decision, not simply a model prediction.

**Trade-off:** Hand-designed weights require later calibration.

**Benefit:** Operators can understand why a score was produced.

**Status:** Implemented.

---

## Decision 5 — Preserve native OSM vocabulary

**Why:** OSM provides useful geographic classifications that would be lost
if everything were compressed into a tiny custom road taxonomy.

**Trade-off:** The resulting schema has more fields.

**Status:** Implemented.

---

## Decision 6 — Use Redis for geospatial caching

**Why:** Reverse geocoding is an external operation with rate limits and
latency.

**Trade-off:** Adds infrastructure.

**Benefit:** Lower repeated API usage and faster repeated lookups.

**Status:** Implemented.

---

## Decision 7 — Use MobileNetV3 Small for visual embeddings

**Why:** It provides lightweight CPU-friendly embeddings and performed well
on our initial duplicate-similarity benchmark.

**Alternatives considered:**

- pHash
- SSIM
- ORB/SIFT
- YOLO internal features
- larger embedding models
- Siamese/metric-learning models
- multimodal APIs
- vector databases

**Trade-off:** The model is not specifically trained for pothole identity
matching.

**Important limitation:** The benchmark used synthetic same-image
transformations, so real-world duplicate performance remains unvalidated.

**Status:** Chosen for v1.

---

## Decision 8 — Keep DuplicateService independent of the database

**Why:** Duplicate scoring should remain deterministic and unit-testable.

**Trade-off:** A separate candidate retrieval layer is required.

**Benefit:** Database concerns do not leak into domain logic.

**Status:** Implemented.

---

## Decision 9 — Use Haversine distance for geographic comparison

**Why:** Latitude/longitude are spherical geographic coordinates.

**Trade-off:** Slightly more computation than simple coordinate subtraction.

**Benefit:** Distances are expressed correctly in metres.

**Status:** Implemented.

---

## Decision 10 — Use full-image embeddings instead of pothole crops

**Why:** Crop benchmarking improved positive-pair stability slightly but made
negative pairs substantially more similar.

**Trade-off:** Full images include more irrelevant visual information.

**Benefit:** Better separation in the current benchmark.

**Status:** Chosen for v1.

---

# 20. Completed Milestones

## Foundation

- [x] GitHub repository
- [x] Project source-of-truth document
- [x] Backend structure
- [x] Environment configuration
- [x] PostgreSQL/Supabase integration
- [x] Redis infrastructure
- [x] Docker Compose Redis setup

## Computer Vision

- [x] Vision model abstraction
- [x] Pothole detector
- [x] Model weights
- [x] Image validation
- [x] Detector evaluation
- [x] Detector tests

## Severity

- [x] Severity engine
- [x] Explainable severity reasons
- [x] Severity tests

## Location

- [x] Reverse geocoding client
- [x] Redis geocoding cache
- [x] Structured location schema
- [x] Civic context interpretation
- [x] Location tests

## Priority

- [x] Deterministic priority engine
- [x] Confidence review logic
- [x] Priority tests

## Analysis Pipeline

- [x] Analysis service
- [x] Storage → CV → severity → location → priority orchestration
- [x] Analysis persistence
- [x] API integration
- [x] Orchestration tests

## Duplicate Detection

- [x] Haversine similarity
- [x] Time similarity
- [x] Duplicate assessment service
- [x] MobileNetV3 visual embedding service
- [x] Visual similarity
- [x] Partial embedding validation
- [x] Duplicate test suite

**Current backend test count: 80 passing**

### Duplicate Analysis Integration

Duplicate detection is now integrated into the main evidence-analysis workflow.

The complete flow is:

1. Retrieve and validate the incident and evidence.
2. Run the pothole vision detector.
3. Estimate severity.
4. Resolve geographic context.
5. Calculate incident priority.
6. Persist the evidence analysis.
7. Retrieve plausible duplicate candidates.
8. Download candidate evidence.
9. Generate visual embeddings.
10. Compare location, time, and visual similarity.
11. Select the strongest candidate.
12. Return the evidence analysis and duplicate-analysis result together.

The duplicate workflow remains separated into dedicated services:

- `DuplicateCandidateService` — reduces the database search space using category, time, and geographic filters.
- `VisualEmbeddingService` — converts evidence images into normalized visual embeddings.
- `DuplicateService` — compares two incidents using location, time, and visual similarity.
- `DuplicateAnalysisService` — orchestrates candidate retrieval and comparison.

This separation keeps candidate retrieval, feature extraction, comparison logic, and orchestration independently testable.

The analysis API now exposes both results through:

`POST /incidents/{incident_id}/evidence/{evidence_id}/analysis`

The response contains:

- evidence analysis
- severity and severity score
- priority and priority score
- review requirement
- strongest duplicate candidate, when one exists

The incident category is also persisted when analysis succeeds. This is important because candidate retrieval uses the persisted `POTHOLE` category to identify existing pothole reports.

### Duplicate Analysis Testing

The duplicate-analysis integration is covered by unit and orchestration tests.

The test suite verifies:

- incident/evidence validation
- candidate retrieval integration
- evidence ownership validation
- visual embedding integration
- candidate comparison
- strongest-match selection
- no-candidate behavior
- integration with `AnalysisService`
- API serialization of the complete analysis response

The full backend test suite currently passes:

`80 passed`

### Citizen Report Submission Workflow

`POST /reports` is the v1 citizen-facing multipart endpoint. It accepts only
`description`, `latitude`, `longitude`, and `photo`; classification,
severity, priority, and duplicate information remain server-generated.

The endpoint creates the incident, stores validated JPEG/PNG/WEBP evidence,
runs the existing analysis pipeline, performs duplicate analysis, and returns
the incident, evidence, and completed assessment together. Database writes
are committed once, at the end of a successful workflow. If any later stage
fails after object storage succeeds, the database session is rolled back and
the stored evidence is deleted as compensating cleanup.

For v1, a photo where the detector finds no pothole is rejected with `422`.
It does not leave a partially created report. This is deliberately not a
claim that no pothole exists; it means CivicLens could not confirm one from
the submitted image. Human-review submission for uncertain reports is a
future product decision.

### Citizen Reporting Frontend

The `frontend/` application is a mobile-first React and TypeScript app built
with Vite. UI components remain separate from `src/api/reports.ts`, which is
the only frontend module that calls `POST /reports`. The browser submits the
same multipart contract as the backend: `description`, `latitude`,
`longitude`, and `photo`.

The report form validates JPEG/PNG/WEBP files up to 10 MB for immediate
feedback, previews selected photos, supports mobile camera capture where the
browser provides it, and disables the submit action while a request is in
progress. Browser geolocation can fill an always-visible coordinate/map
preview; citizens can also correct coordinates manually when permission is
unavailable. This avoids making reporting dependent on GPS or a map provider.

After a successful submission, the UI presents the server-returned report ID,
assessment, priority, and human-readable lifecycle status. Backend states are
translated as: submitted = Report received, analyzed = Report reviewed,
assigned = Dispatched to repair crew, in_progress = Repair in progress, and
resolved = Road repaired. The local development FastAPI configuration allows
the Vite development origin through CORS; production origins must be narrowed
as part of deployment hardening.

### Citizen Report Tracking

Citizen tracking now reads persisted backend data rather than reconstructing
reports in the browser. The citizen frontend provides a report list, direct
links from a completed submission, and a report-detail view that shows the
stored report ID, description, coordinates, evidence image, persisted
assessment, and lifecycle state.

The tracking API adds:

- `GET /reports` for the persisted report list, newest first.
- `GET /reports/{report_id}` for one report with its latest evidence, a
  time-limited evidence URL, and its latest persisted analysis.

The lifecycle display is driven only by the incident's persisted status. It
uses the already-enforced sequential incident lifecycle and does not create
new transitions in React. Loading, empty, error, and not-found states are
covered in the frontend; backend API tests cover list, detail, evidence,
analysis, lifecycle serialization, and not-found behavior.

There is no authentication or report ownership in v1. Consequently the public
`GET /reports` list contains all CivicLens reports, not a per-citizen private
history. Identity-bound “My Reports” must wait for the authentication
milestone.


---

# 21. Current Git Checkpoints

Known recent checkpoints:

```text
4eb7c1e feat(duplicate): add visual embedding service
8a5fee1 feat(duplicate): add duplicate assessment service
9d611ae feat(duplicate): add time similarity
fccd4fe feat(duplicate): add harversine distance
d185e41 test(analysis): add orchestration coverage
0ad75ee feat(analysis): integrate end-to-end evidence analysis
0ff48c7 refactor(vision): separate detection from severity
```

The visual similarity checkpoint was subsequently committed and pushed after
the 47/47 test run.

The exact latest hash should be verified with `git log` rather than manually
maintained here.

---

# 22. Operational milestone

The operator and authority-routing layer is now integrated into the modular
monolith. Alembic versions authorities, routing decisions, assignments, notes,
and status history. Citizen report submission persists one conservative
internal routing decision in the same transaction as analysis. Operator/admin
bearer-token authorization protects operational mutations; public citizen
reporting/tracking retains its explicit v1 behavior.

The `#/operator` route provides a filtered queue, routing/manual-review
context, assignment, append-only notes, sequential lifecycle controls, and
status history. Routing is not an official external complaint submission.

Future work is verified jurisdiction data, real identity/ownership, and any
explicit authority integrations—not expansion beyond potholes.

# 23. Historical immediate next objective

Build **database-backed duplicate candidate retrieval**.

The next workflow is:

```text
New Incident
     ↓
Retrieve existing incidents
     ↓
Filter by geographic proximity
     ↓
Filter by temporal proximity
     ↓
Retrieve evidence metadata
     ↓
Pass candidates to DuplicateService
```

Initial candidate window:

```text
Distance: ≤ 100 metres
Time:     ≤ 72 hours
```

The candidate retrieval layer should reuse the existing SQLAlchemy
`SessionLocal` / `get_db()` architecture.

It should not modify the pure `DuplicateService` unless a genuine domain
requirement appears.

---

# 23. Future Roadmap

After the pothole v1 vertical slice is complete:

1. Finish duplicate orchestration
2. Connect incident lifecycle
3. Build operator/admin API
4. Build frontend
5. Add map visualization
6. Add authentication
7. Add background processing
8. Add deployment
9. Add production observability
10. Validate duplicate detection using real independent reports
11. Recalibrate severity/priority using collected evidence
12. Consider vector search if scale actually requires it
13. Consider document RAG
14. Expand to additional civic categories

---

# 24. Definition of Done

A meaningful feature is done when appropriate items are complete:

- [ ] Implementation completed
- [ ] Tests added where appropriate
- [ ] Full relevant test suite passes
- [ ] Errors handled
- [ ] API/schema updated if necessary
- [ ] Architecture decision documented if meaningful
- [ ] PROJECT.md updated
- [ ] Git diff reviewed
- [ ] Meaningful commit created
- [ ] Changes pushed to GitHub
- [ ] Working tree verified clean

---

# 25. Learning Goals

This project is also a structured learning vehicle.

The developer should understand the major concepts being used rather than
blindly assembling libraries.

Topics include:

- Git and GitHub
- HTTP and REST APIs
- FastAPI
- Pydantic
- SQL and PostgreSQL
- SQLAlchemy
- Alembic
- Supabase
- Object storage
- Redis
- Docker
- Environment variables
- AI inference
- Object detection
- Embeddings
- Cosine similarity
- Geospatial calculations
- External APIs
- Background jobs
- System design
- Testing
- Deployment
- CI/CD
- Observability

For every new major technology, document:

```text
What it is
Why CivicLens needs it
Why this implementation was selected
What alternatives were considered
What trade-offs it introduces
```

---

# 26. Non-Negotiable Principles

1. Build incrementally.
2. Do not overengineer early.
3. Complete the pothole vertical slice before expanding categories.
4. Understand every major component we add.
5. Do not copy code blindly.
6. Keep GitHub updated from Day 1.
7. Commit meaningful working changes.
8. Push completed changes regularly.
9. Document meaningful architecture decisions.
10. Measure real metrics instead of inventing impressive numbers.
11. Prefer a working end-to-end product over disconnected AI features.
12. Every technology must have a clear architectural reason.
13. Keep pure domain logic independent of infrastructure where practical.
14. Recalibrate provisional heuristics when real project data becomes
    available.

### Duplicate Candidate Retrieval

CivicLens now separates **candidate retrieval** from **duplicate assessment**.

The `DuplicateCandidateService` is responsible for answering:

> "Which existing incidents are worth comparing against this new incident?"

It does **not** decide whether an incident is actually a duplicate. That decision remains the responsibility of `DuplicateService`.

#### Candidate retrieval rules

For CivicLens v1, the candidate search uses:

- **Category:** pothole incidents only
- **Maximum geographic distance:** 100 metres
- **Maximum time difference:** 72 hours
- **Current incident:** excluded when an existing incident ID is supplied
- **Ordering:** newest candidate incidents are returned first

#### Retrieval strategy

The database currently stores latitude and longitude as ordinary `Float` columns rather than spatial/PostGIS types.

Therefore, candidate retrieval uses a two-stage geographic filter:

1. **Database bounding-box pre-filter**
   - Converts the 100 m search radius into approximate latitude/longitude ranges.
   - Allows the database to discard obviously distant incidents cheaply.

2. **Exact Haversine distance check**
   - Calculates the actual distance between the submitted incident and each database candidate.
   - Removes incidents that passed the rectangular bounding box but are actually more than 100 m away.

This gives us a simple and explainable spatial-search layer without introducing PostGIS prematurely.

PostGIS can be considered later if CivicLens reaches a scale where database-native spatial indexing and queries provide a meaningful performance benefit.

#### Why candidate retrieval is separate

Candidate retrieval and duplicate assessment solve different problems:

```text
New Incident
     |
     v
DuplicateCandidateService
     |
     |-- recent enough?
     |-- geographically close enough?
     |-- pothole?
     |
     v
Plausible Candidates
     |
     v
DuplicateService
     |
     |-- location similarity
     |-- time similarity
     |-- visual similarity
     |
     v
DUPLICATE / RELATED / SEPARATE
