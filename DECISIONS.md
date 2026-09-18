# CivicLens Architecture Decisions

## Decision: Redis fixed-window limits for public reports and operator API

### Context
Submitting a citizen report can invoke storage, CV, geocoding, routing,
duplicate analysis, and database work. The public endpoint needs inexpensive,
shared abuse protection before that work begins.

### Decision
Use the existing synchronous Redis client for a fixed-window counter. Citizen
submissions use a normalized socket-peer IP key; the existing operator router
uses the validated principal name. A Lua `INCR`/`EXPIRE` script atomically sets
the counter and TTL. Initial configuration is 20 reports/IP/60 seconds and 60
operator requests/principal/60 seconds. Redis outage is logged safely and
fails open in v1 to preserve reporting and operational availability.

### Alternatives and why
An in-memory dictionary would split quotas across workers and disappear on
restart. PostgreSQL would add durable write load to the report path for
temporary counters. A third-party rate-limit service is unjustified while the
project already operates Redis.

### Trade-offs and consequences
Fixed windows permit boundary bursts and IPs are not identity; trusted proxy
configuration is required before forwarded addresses may be used. Redis key
cardinality is bounded by TTL, and keys contain neither bearer tokens nor raw
authorization headers. Revisit for a trusted proxy, citizen accounts, measured
abuse, or a need for smoother token-bucket limits.

### Interview questions
**How does CivicLens prevent report spam?** Redis limits each IP before CV and
other expensive processing.

**Why Redis rather than in-memory or PostgreSQL?** It is shared across API
instances, expires counters naturally, and avoids durable database writes.

**What is HTTP 429?** It tells a client it has made too many requests; CivicLens
also returns Redis's remaining window in `Retry-After`.

## Decision: auditable lifecycle and conservative internal routing

### Context
Operators need explainable actions and routing without treating reverse
geocoding as proof of legal road ownership.

### Problem
Status-only updates lose accountability, and hard-coded road rules would create
misleading operational claims.

### Decision
Enforce lifecycle transitions in the service layer and add an
`IncidentStatusHistory` row for each successful change. Store authorities as
configuration data and persist one current routing decision per incident.
Campus/configured-road evidence may route internally; insufficient evidence
goes to `UNKNOWN` with low confidence and manual review.

### Alternatives considered
Status-only updates, controller `if` statements, external complaint filing,
and always selecting a public authority.

### Why this decision was selected
It keeps uncertainty visible and makes operations inspectable.

### Trade-offs and consequences
Some reports require manual review. The API derives audit authors from a
validated principal rather than allowing request-body impersonation.

### When to revisit
When CivicLens has verified ownership data, named identities, or actual
authority integrations.

### Interview questions
**Why does UNKNOWN exist?** Reverse geocoding describes location, not legal
ownership; guessing would make the queue less trustworthy.

**Is a route a filed complaint?** No: it is a work-queue recommendation until
an explicit authority integration exists.

## Decision: deterministic reasoning around computer vision

### Context
YOLO supplies visual evidence but has imperfect recall and cannot determine
physical danger or administrative ownership.

### Problem
An LLM, vector DB, or microservice architecture adds complexity without the
data to validate it.

### Decision
Keep CV separate from deterministic severity, priority, duplicate, and routing
services. Redis caches OSM/Nominatim and candidate retrieval narrows visual
duplicate comparison by time and location.

### Alternatives considered
LLM detection, vector search, PostGIS now, and event-driven microservices.

### Why this decision was selected
The v1 path is transparent, independently testable, and appropriate for the
current data volume.

### Trade-offs and consequences
Thresholds remain provisional and require recalibration from independent real
reports. Add a vector DB only if measured scale makes candidate retrieval
insufficient.

### When to revisit
At measured scale, with validated labels, or when deployment/team boundaries
require independent services.

### Interview questions
**Why no vector DB?** Nearby/recent candidate retrieval keeps v1 comparison
sets small, so the added infrastructure is not justified.

## Decision: environment-configured bearer tokens for v1 operations

### Context
The repository has no user or Supabase Auth architecture, but lifecycle and
operator actions require a backend-enforced security boundary.

### Decision
Use distinct environment-configured bearer tokens for `operator` and `admin`.
The backend compares tokens server-side and returns a typed internal principal.

### Alternatives Considered
Supabase Auth, a database-backed user system, and frontend route protection.

### Why This Decision
It is the smallest real boundary compatible with the existing FastAPI app and
does not expose privileged credentials in the public Vite bundle.

### Trade-offs
It has no individual user identity or token rotation workflow; actions are
attributed to the configured role rather than a named person.

### Consequences
All operational mutations must require the server dependency. Citizen APIs
remain unauthenticated and cannot claim private ownership.

### Revisit When
Replace it with an identity provider when CivicLens needs individual accounts,
revocation, or private citizen report histories.

## Decision: operator evidence uses authenticated, short-lived storage URLs

### Context
Operator review requires the original pothole image, while Supabase evidence
objects must remain private and storage credentials must never reach Vite.

### Decision
The operator API authorizes the existing operator/admin bearer dependency
before returning a time-limited URL for the latest incident evidence. The URL
is generated through the existing storage service; neither the bucket nor
Supabase service credentials are exposed to the frontend.

### Trade-offs
The browser must request a new URL when selecting an incident, and a displayed
URL eventually expires. This is preferable to making evidence publicly
readable.
