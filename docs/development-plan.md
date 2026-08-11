# LLM Evaluation Lab — V1 Implementation Plan

## Context

Faruk (4th-year Yazılım Geliştirme student, job-hunting, AI/LLM focused) wants a new portfolio project he can genuinely defend in an interview — every past project had its code written by AI in a stack (TypeScript/Next.js) he doesn't actually know, which likely hurt his applications. This project is being built the opposite way: entirely in Python, a stack he's learning for real (Python → SQL → Git → LLM/Ollama → RAG → FastAPI → Docker), with a hard rule he set himself: **no technology gets added until it solves an actual problem the project has at that point** (e.g. FastAPI isn't introduced until there's a real reason to expose an API; LangChain isn't introduced until there's real RAG/orchestration complexity to manage — so it does **not** appear in V1 at all, despite being on his long-term tech list).

The project: an **LLM Evaluation Platform** — runs a test dataset (questions + expected answers) through different LLM/prompt configurations ("experiments"), records responses/latency/token usage, scores them, and lets him compare configurations against each other. This is a strong, differentiated portfolio piece for AI/LLM roles and gives him hands-on practice with every skill on his CV.

Scope of this plan is **V1 only** (no RAG, no LangChain, no LLM-as-judge, no agents/tool-calling — those are V2, planned separately once V1 works end-to-end). Work proceeds in 8 independently-runnable milestones; each one is a discrete session of work, not built in one shot.

## Confirmed decisions

- **Location:** new folder `C:\Users\fbc\Desktop\cv-project\llm-eval-lab`
- **Env/package manager:** `uv`, src-layout package (`src/llm_eval_lab/`)
- **Database:** PostgreSQL via Docker Compose from the start (DB only — containerizing the app itself is deferred to M8), host port **5433** (avoids colliding with any local Postgres)
- **ORM/migrations:** SQLAlchemy 2.0 typed style (`Mapped[...]`) + Alembic — kept over SQLModel because he'll need separate API request/response schemas at M7 anyway, and plain SQLAlchemy is more broadly recognizable on a portfolio
- **LLM backend (V1):** Ollama, local, HTTP via `httpx` against `/api/generate` (no LangChain — single call has no orchestration to manage)
- **Models to pull:** `qwen2.5:7b` (primary) and `llama3.2:3b` (deliberately weaker, for a visually convincing comparison demo in M6). Both run comfortably on his hardware (16GB RAM, 12GB VRAM NVIDIA GPU).
- **Schema:** `experiments` (config: dataset+model_config+prompt) and `experiment_runs` (one execution instance of that config) are **separate tables** — lets him re-run the same config later and compare runs over time, matching what a real eval platform does. `responses.raw_response` (JSONB, Ollama's raw output) is kept as a deliberate, cheap exception to the "don't add until needed" rule — avoids a backfill migration later when debugging.
- **Naming fix:** the LLM-config table is `model_configs` (not `models`) to avoid colliding with the `models/` ORM package name.

## Target layout (built incrementally across milestones, not all at once)

```
C:\Users\fbc\Desktop\cv-project\llm-eval-lab\
  pyproject.toml, uv.lock, .env.example, .gitignore, README.md
  docker-compose.yml          (M1: db only → M8: + app)
  Dockerfile                  (M8)
  alembic.ini
  migrations\versions\
  src\llm_eval_lab\
    config.py  db.py
    models\      (SQLAlchemy ORM: dataset.py, test_case.py, model_config.py, prompt.py,
                   experiment.py, experiment_run.py, response.py, evaluation_result.py)
    datasets\    (repository + JSON file loader)
    llm\         (base.py: LLMClient protocol, ollama_client.py, factory.py registry)
    runner\      (experiment_runner.py)
    evaluation\  (base.py: Evaluator protocol, deterministic.py, runner.py)
    comparison\  (compare.py — pandas groupby aggregation)
    schemas\     (M7: Pydantic DTOs, separate from ORM models)
    api\         (M7: main.py, deps.py, routers\)
    cli\         (argparse entrypoints, one per milestone)
  tests\ (conftest.py — transactional-rollback fixture against the same compose Postgres,
          factories.py — grows every milestone)
  data\sample_datasets\qa_smoke_test.json   (~8-10 Q/A pairs, fixture reused all milestones)
```

## Milestones

### M1 — Skeleton, uv, Postgres via Docker Compose, SQLAlchemy+Alembic wiring
- `uv init --package llm-eval-lab` (src layout). `uv add sqlalchemy "psycopg[binary]" alembic pydantic-settings`; `uv add --dev pytest pytest-cov httpx`.
- `docker-compose.yml`: single `db` service (`postgres:16-alpine`), named volume, healthcheck, port `5433:5432`.
- `.env.example`: `DATABASE_URL=postgresql+psycopg://llm_eval:llm_eval@localhost:5433/llm_eval_lab`, `OLLAMA_HOST=http://localhost:11434`, `OLLAMA_DEFAULT_MODEL=qwen2.5:7b`.
- `config.py` (pydantic-settings `Settings`), `db.py` (`Base(DeclarativeBase)`, `engine`, `SessionLocal`).
- `alembic init migrations` at repo root, wired to `Base.metadata` + `settings.database_url` for autogenerate.
- No tables yet — prove the pipeline with an empty migration.
- **Verify:** `docker compose up -d db` → smoke test does `SELECT 1`. `uv run alembic upgrade head` succeeds. `uv run pytest` runs (connectivity test only).

### M2 — Datasets & test cases
- ORM: `Dataset(id, name, description, created_at)`, `TestCase(id, dataset_id FK, question, expected_answer, reference_source nullable, created_at)`.
- `datasets/repository.py`: create dataset, add test case, `load_dataset_from_file(path)` (flat JSON list, validates required fields).
- `cli/import_dataset.py`, `data/sample_datasets/qa_smoke_test.json` fixture, `tests/factories.py` started.
- **Verify:** `alembic upgrade head` creates tables; CLI import + count check; pytest round-trip + malformed-record rejection test.

### M3 — Model/prompt config + a single working Ollama call
- ORM: `ModelConfig(id, name, provider, model_name, parameters JSONB nullable, created_at)`, `Prompt(id, name, template, created_at)` (immutable by convention — edits = new row).
- `llm/base.py`: `LLMClient` protocol, `LLMResponse(text, latency_ms, prompt_tokens, completion_tokens, raw)`.
- `llm/ollama_client.py`: `httpx` call to `/api/generate` (`stream: false`, generous timeout for cold model load). `prompt_tokens` ← `prompt_eval_count`, `completion_tokens` ← `eval_count`; `latency_ms` measured with `time.perf_counter()` around the call (not Ollama's internal duration fields).
- `llm/factory.py`: provider registry dict (`{"ollama": OllamaClient}`) — the seam for a future second provider.
- `cli/ollama_smoke_test.py`.
- **Verify:** `ollama pull qwen2.5:7b && ollama pull llama3.2:3b`, run smoke test CLI manually. Automated: mocked-`httpx` parsing test (no live Ollama needed for default `pytest`), one `@pytest.mark.integration` test that does hit real Ollama.

### M4 — Experiment runner (experiments, experiment_runs, responses)
- ORM: `Experiment(id, name, description, dataset_id FK, model_config_id FK, prompt_id FK, created_at)`; `ExperimentRun(id, experiment_id FK, status enum[pending,running,completed,failed], started_at, completed_at nullable, created_at)`; `Response(id, experiment_run_id FK, test_case_id FK, response_text, latency_ms, prompt_tokens nullable, completion_tokens nullable, raw_response JSONB nullable, error Text nullable, created_at)`, unique `(experiment_run_id, test_case_id)`.
- `runner/experiment_runner.py`: `run_experiment(session, experiment_id, llm_client=None)` — LLMClient injected (unit-testable without live Ollama), iterates test cases, simple `str.format()` prompt rendering (no template engine needed for one variable), per-item try/except so one failure doesn't abort the run (stored on `Response.error`), updates run status.
- `cli/run_experiment.py`.
- **Verify:** unit test with fake `LLMClient` (N test cases → N responses, simulated failure doesn't abort run). Manual + integration test: real run against Ollama on `qa_smoke_test`.

### M5 — Deterministic evaluation engine (evaluation_results)
- ORM: `EvaluationResult(id, response_id FK, metric_name, score float, details JSONB nullable, created_at)` — **one row per metric per response** (EAV-style), not fixed columns, because 9 metrics are planned long-term (several arriving via LLM-judge in V2) and this avoids a migration per new metric.
- `evaluation/base.py`: `Evaluator` protocol, pure functions (string in, score out, no DB coupling — this is what lets a future `LLMJudgeEvaluator` slot in later without touching the runner).
- `evaluation/deterministic.py`: `ExactMatchEvaluator` (normalize: lowercase/strip/collapse whitespace), `NormalizedSimilarityEvaluator` (stdlib `difflib.SequenceMatcher`, zero new dependency).
- `evaluation/runner.py`: `evaluate_run(session, experiment_run_id, evaluators)`.
- `cli/evaluate_run.py`.
- **Verify:** unit tests on evaluators (known string pairs → expected scores incl. normalization edge cases). Integration-style test on a fake run. Manual: evaluate the real M4 run.

### M6 — Experiment comparison
- No new tables — read-only aggregation.
- `comparison/compare.py`: `compare_experiment_runs(session, run_ids) -> ComparisonReport` (avg latency, avg tokens, per-metric avg score via `pandas` `groupby`, success rate). **This is the deliberate, justified point `pandas` enters the project** — aggregating tabular metrics is exactly its use case; introducing it earlier would have violated the project's own "don't add tech until needed" rule.
- `cli/compare_runs.py`.
- **Verify:** unit test with two seeded runs, known expected averages. Manual: compare the strong (`qwen2.5:7b`) vs weak (`llama3.2:3b`) model runs and confirm the score gap is real and visible.

### M7 — FastAPI layer
- `uv add fastapi "uvicorn[standard]"`.
- `schemas/`: Pydantic DTOs separate from ORM models (`from_attributes=True`).
- `api/deps.py` (`get_db()`), `api/routers/{datasets,experiments,results}.py` — **thin wrappers over the exact functions already built in M2–M6**, zero new business logic (this is only possible because every prior milestone kept logic in plain functions taking a `Session`, with no framework coupling).
- Endpoints: dataset CRUD, experiment create + `POST /experiments/{id}/runs` (synchronous — an explicit, stated V1 limitation, no background jobs added to solve it), results/evaluation/comparison GETs.
- **Verify:** `uv run uvicorn llm_eval_lab.api.main:app --reload`, exercise via `/docs`. `TestClient` router tests overriding `get_db` with the M1 transactional fixture.

### M8 — Dockerize the app itself
- Multi-stage `Dockerfile` (installs `uv`, `uv sync --frozen --no-dev`, copies `src/`, runs uvicorn).
- Extend `docker-compose.yml` with an `app` service, `depends_on: db (healthy)`. Inside the container: `DATABASE_URL` points at service name `db` (not `localhost`); `OLLAMA_HOST=http://host.docker.internal:11434` (Docker Desktop-specific — Ollama itself stays on the host, not containerized). Migrations run via an explicit `docker compose run --rm app alembic upgrade head`, not auto-run on boot.
- `.dockerignore`.
- **Verify:** `docker compose up --build`, `curl http://localhost:8000/docs`, run one full experiment end-to-end via the API from inside the container (confirms host networking to both Postgres and Ollama).

## Explicitly out of scope for this plan (V2, planned separately later)
RAG (chunking, embeddings, pgvector, retriever), LangChain, LLM-as-a-Judge, faithfulness/context-relevance/hallucination-rate metrics, tool-calling & agent evaluation, reranking. These get added exactly when V1 is solid and a real need for each appears — not before.

## Verification (end-to-end, once all 8 milestones are done)
1. `docker compose up -d db`, `ollama serve` running with both models pulled.
2. `uv run alembic upgrade head`.
3. Import `qa_smoke_test.json`, create two `Experiment`s (same dataset/prompt, `qwen2.5:7b` vs `llama3.2:3b`), run both via the API, evaluate both, hit `/compare?run_ids=...` and confirm scores diverge sensibly (stronger model scores higher).
4. `docker compose up --build` (full stack) and repeat step 3 through the containerized API to confirm the Docker path also works.
5. `uv run pytest` green throughout (run after every milestone, not just at the end).

## Progress log

### M1 — done (2026-08-11)
- `uv init --package .` (src layout, Python 3.12, `uv_build` backend).
- Deps added: `sqlalchemy 2.0.51`, `psycopg[binary] 3.3.4`, `alembic 1.19.1`, `pydantic-settings 2.15.0`; dev: `pytest 9.1.1`, `pytest-cov`, `httpx`.
- `docker-compose.yml`: `db` service (`postgres:16-alpine`), named volume `db_data`, healthcheck via `pg_isready`, port `5433:5432`.
- `.env.example` + `.gitignore` (added `.env`, IDE dirs on top of uv's default ignores).
- `src/llm_eval_lab/config.py` (`Settings` via pydantic-settings, reads `.env`) and `db.py` (`Base(DeclarativeBase)`, `engine`, `SessionLocal`).
- Alembic wired: `migrations/env.py` imports `Base.metadata` as `target_metadata` and overrides `sqlalchemy.url` from `settings.database_url` at runtime (the `alembic.ini` placeholder URL is intentionally left as a dummy, annotated as unused).
- Empty migration `e5988e261560_initial_empty_schema` generated (autogenerate confirmed connectivity + correctly produced a no-op upgrade/downgrade against a schema with no models yet) and applied.
- **Verified:** `docker compose up -d db` → healthy; `SELECT 1` passes via a `tests/test_db_connectivity.py` pytest test; `alembic upgrade head` succeeds; `uv run pytest` green (1 passed).
- **Environment note:** Docker Desktop installs to `%LOCALAPPDATA%\Programs\DockerDesktop\resources\bin` (admin-less installer), not `C:\Program Files\Docker`. This is on the persisted **User** PATH, so new terminals pick it up automatically — only shells that were already open before install need `export PATH="/c/Users/$USER/AppData/Local/Programs/DockerDesktop/resources/bin:$PATH"` (bash) to see `docker`/`docker-credential-desktop` for the rest of that session.

### M2 — done (2026-08-11)
- ORM: `models/dataset.py` (`Dataset`: id, name, description nullable, created_at server-default `now()`), `models/test_case.py` (`TestCase`: id, dataset_id FK, question, expected_answer, reference_source nullable, created_at), 1-to-many with `cascade="all, delete-orphan"` from `Dataset.test_cases`. `models/__init__.py` re-exports both — imported by `migrations/env.py` (`import llm_eval_lab.models`) so autogenerate actually sees them on `Base.metadata`.
- `datasets/repository.py`: `create_dataset`, `add_test_case`, `load_dataset_from_file(session, path, dataset_name, dataset_description=None)` — validates every record's required fields (`question`, `expected_answer`) in a first pass *before* writing anything, so a malformed record anywhere in the file leaves zero rows persisted (no separate rollback machinery needed for this guarantee).
- `data/sample_datasets/qa_smoke_test.json`: 10 general-knowledge Q/A pairs (one with `reference_source`), reused as the fixture for all later milestones as planned.
- `cli/import_dataset.py`: `argparse` CLI, run as `uv run python -m llm_eval_lab.cli.import_dataset <path> --name ... [--description ...]`; no `pyproject.toml` script entry added (not needed yet — module invocation is sufficient, consistent with "don't add until needed").
- `tests/conftest.py`: `db_session` fixture using SQLAlchemy's `join_transaction_mode="create_savepoint"` against the real compose Postgres — code under test can call `session.commit()` and the outer connection-level transaction still rolls everything back after each test. `tests/factories.py`: `make_dataset`, `make_test_case` (thin wrappers over the repository functions).
- Migration `241be2b5a975_add_datasets_and_test_cases_tables` (autogenerated, applied) creates both tables with the FK.
- Added `[tool.pytest.ini_options].filterwarnings` in `pyproject.toml` to silence pytest's `PytestCollectionWarning` on the `TestCase` class name (a deliberate domain-model name colliding with pytest's own convention, not a mistake).
- **Verified:** `alembic upgrade head` applied the new migration; `uv run pytest` green (4 passed: connectivity + repository round-trip + malformed-record rejection, which asserts zero rows persisted); manual CLI import of `qa_smoke_test.json` produced a dataset with exactly 10 test cases (confirmed via direct query), then cleaned up (cascade delete verified both tables empty again afterward).
- Next: M3 (model/prompt config + a single working Ollama call).
