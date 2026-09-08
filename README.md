# Peblo TV Mini

I built a full-stack content management and delivery platform. Editors and administrators manage video assets, artwork, and metadata in a React-based CMS powered by a FastAPI/PostgreSQL backend. When a catalogue is published, the system atomically generates a static JSON payload and serves it to a read-only React Viewer application.

## Run locally

To start the full stack, run:

    docker compose up --build -d

The services will be available at:
* CMS: http://localhost:3000
* Viewer: http://localhost:3001
* API: http://localhost:8000
* API Health: http://localhost:8000/health/ready

The PostgreSQL database is automatically migrated and seeded on startup. A local storage directory is mounted to persist uploaded media. No manual environment configuration is required for local development.

### Development credentials

The database seed provisions two default accounts for testing:

* Admin: admin@peblo.tv / admin123
* Editor: editor@peblo.tv / editor123

## Key decisions & trade-offs

### Atomic publishing
The publisher writes the catalogue to a new, versioned file (`catalogues/{run_id}.json`). The live pointer (`catalogues/current.json`) is updated only after the new file is successfully written. This pointer update is atomic, ensuring readers never see a partially-written catalogue. If publishing fails or the process dies mid-write, the previous good catalogue remains live.
Publishing is strictly gated by a validation report; if blocking issues exist (e.g., missing required artwork), the publish is refused, the failure is recorded, and the live catalogue is untouched.

### Storage abstraction
For this take-home, media and catalogues are stored on local disk. However, storage is accessed through an abstraction layer. For production, the local implementation can be swapped for Cloudflare R2 by creating an `R2Storage` class using boto3, injecting it in the backend, and providing bucket credentials. The core business logic remains unchanged.

### Search
In the CMS, search, filtering, and pagination are performed server-side via SQL queries. In the Viewer, search runs against the published catalogue API. Loading a single JSON file into memory is appropriate for the current catalogue size. As the catalogue grows to tens of thousands of shows, this approach would cause unacceptable latency. The next step would be implementing PostgreSQL full-text search on a GIN-indexed `tsvector` column or utilizing a dedicated search service (like Elasticsearch or Typesense) for the Viewer read path.

### Why a pre-published catalogue?
I chose a static catalogue generation model to completely separate the read path from the transactional CMS database. This provides the Viewer with a highly stable, fast read model that can be distributed via a CDN, scaling independently and removing load from the primary database. The trade-off is that the catalogue can become stale until the next successful publish, and generating a single large JSON file eventually becomes unsuitable for massive libraries.

### Validation and data decisions
Validation enforces strict rules: artwork must meet specific dimensions, aspect ratios, and a 200 KB size limit. At the database level, uniqueness is guaranteed for `content_group` + `language` combinations. "Season 0" is explicitly modeled to handle trailers. Rather than silently dropping or repairing imperfect seed data, the loader records anomalies as `ContentIssue` rows, surfacing them to editors to fix manually.

### Roles
I implemented role-based access control enforced at the backend dependency level, not just hidden in the UI. Editors can perform CRUD operations on shows and episodes. Administrators have the same privileges, plus the ability to publish the catalogue and view validation reports. The Viewer endpoints require no authentication.

## What I left out

* Cloud deployment: The system relies on local disk storage instead of a production S3/R2 bucket. No live deployment environment was provisioned.
* Catalogue rollback: There is no UI to revert to a previously published catalogue version, though the files are retained on disk.
* Authentication robustness: The implementation uses a simple JWT stored in localStorage. A production app would require HttpOnly cookies, refresh tokens, and strict session invalidation.
* Duration UI: Missing duration correctly blocks publishing, but there is no field in the CMS to edit it yet.

## Testing

I verified the system using the following checks:
* Backend: Ran the full Pytest suite against a dedicated test database (`pytest tests/ -v`), passing 47/47 tests.
* Builds: Verified that the CMS and Viewer Vite production builds succeed.
* Docker Compose: Tested that the containers build cleanly, the database is healthy, migrations complete, and the API recovers gracefully.
* End-to-End: Manually tested the admin and editor workflows, invalid logins, artwork uploads, validation blockers preventing publish, and Viewer rendering.

## AI usage

I used AI assistance during implementation primarily for planning, debugging, code review, and identifying edge cases. I reviewed and tested the generated suggestions rather than accepting them blindly. For example, AI-assisted review helped identify issues around atomic publishing, role enforcement, artwork validation, Docker configuration, and seed-data handling; I verified the resulting behavior with tests and end-to-end checks.

## Time spent

| Part | Approx. time |
|---|---:|
| Backend/schema/auth/storage | 2.5 hours |
| CRUD + validation + publishing | 2.0 hours |
| CMS | 1.5 hours |
| Viewer | 1.0 hours |
| Docker/CI/integration/debugging | 1.0 hours |
| Testing/polish/README | 1.0 hours |
| **Total** | **9.0 hours** |

*Note: Infrastructure debugging, test isolation fixes, and Docker network issues extended the integration phase slightly.*

## Deployment note

The repository includes GitHub Actions CI to run linting and tests. In a production environment, deployment would target a managed container service with Cloudflare R2 for storage. Production secrets (e.g., `SECRET_KEY`, database credentials) would be injected dynamically via a secure manager rather than committed `.env` files.
