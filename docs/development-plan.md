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

### M3 — done (2026-08-11)
- ORM: `models/model_config.py` (`ModelConfig`: id, name, provider, model_name, `parameters` as Postgres `JSONB` nullable, created_at), `models/prompt.py` (`Prompt`: id, name, template, created_at — docstring states the immutable-by-convention rule). Both re-exported from `models/__init__.py`.
- `llm/base.py`: `LLMResponse` frozen dataclass (`text, latency_ms, prompt_tokens, completion_tokens, raw`) and an `LLMClient` `Protocol` with one method, `generate(model, prompt, parameters=None) -> LLMResponse`.
- `llm/ollama_client.py`: `OllamaClient` posts to `/api/generate` with `stream: false`; `latency_ms` measured with `time.perf_counter()` wrapping the call (not Ollama's internal duration fields, per plan); `prompt_tokens`/`completion_tokens` read from `prompt_eval_count`/`eval_count`. Takes an optional injected `http_client: httpx.Client`, defaulting to a real one with a 120s timeout (generous for cold model loads) — the injection seam is what makes the mocked unit tests possible without monkeypatching a module-level function.
- `llm/factory.py`: `get_llm_client(provider, **kwargs)` over a `{"ollama": OllamaClient}` registry dict — the seam for a future second provider.
- `cli/ollama_smoke_test.py`: sends one prompt (arg or default), prints model/latency/token counts/response text.
- Tests (`tests/test_ollama_client.py`): three unit tests against `httpx.MockTransport` (response parsing, `parameters` → request `options`, HTTP error → `httpx.HTTPStatusError`), plus one `@pytest.mark.integration` test that calls the real local Ollama. Registered the `integration` marker in `pyproject.toml` with `addopts = "-m 'not integration'"` so default `uv run pytest` skips it and only `-m integration` runs it.
- Migration `cc7148b9205a_add_model_configs_and_prompts_tables` (autogenerated, applied) creates both tables.
- **Environment note:** Ollama Desktop was installed but its background server wasn't running; `ollama list` (or any CLI call) auto-starts it. Confirmed models already pulled locally: `qwen2.5:7b` (the plan's primary model) and `nomic-embed-text` — `llama3.2:3b` (the plan's deliberately-weaker M6 comparison model) is **not** pulled yet; `llama3.1:8b` is present instead but is not a substitute for the M6 demo. Pulling `llama3.2:3b` is deferred to whenever M6 starts, not needed for M3.
- **Verified:** `uv run alembic upgrade head` applied cleanly. `uv run pytest` green (7 passed, 1 deselected — the integration test). `uv run pytest -m integration` passed (1 passed) against the real local Ollama server. Manual CLI run: `uv run python -m llm_eval_lab.cli.ollama_smoke_test "What is the capital of France? One word answer."` → `qwen2.5:7b`, ~2.2s latency, 40 prompt/2 completion tokens, response `"Paris"`.
- Next: M4 (experiment runner — experiments, experiment_runs, responses).

### M4 — done (2026-08-11)
- ORM: `models/experiment.py` (`Experiment`: id, name, description nullable, `dataset_id`/`model_config_id`/`prompt_id` FKs, created_at); `models/experiment_run.py` (`ExperimentRun`: id, experiment_id FK, `status` — a real Postgres enum `run_status` backed by a `RunStatus(str, enum.Enum)` with members `PENDING/RUNNING/COMPLETED/FAILED`, started_at/completed_at nullable, created_at; `runs` relationship back-populated from `Experiment` with `cascade="all, delete-orphan"`); `models/response.py` (`Response`: id, experiment_run_id/test_case_id FKs, `response_text`/`latency_ms` nullable — needed nullable in practice, not just the explicitly-nullable columns from the plan text, since a failed call has neither — plus prompt_tokens/completion_tokens/raw_response(JSONB)/error all nullable, unique `(experiment_run_id, test_case_id)` via `UniqueConstraint`). All re-exported from `models/__init__.py`.
- `runner/experiment_runner.py`: `run_experiment(session, experiment_id, llm_client=None)` — looks up the `Experiment` (raises `ValueError` if missing), defaults `llm_client` to `get_llm_client(experiment.model_config.provider, host=settings.ollama_host)` when not injected (the injection seam from M3's factory is what makes this unit-testable without live Ollama), creates an `ExperimentRun` row (`RUNNING`, `started_at=now`), iterates `experiment.dataset.test_cases`, renders each prompt via `experiment.prompt.template.format(question=test_case.question)` (single-variable `str.format()`, no template engine per plan), calls the client per test case inside its own try/except — a raised exception is caught and stored as `Response.error` (text/latency/tokens left `None`) and the loop continues; a successful call stores `response_text`/`latency_ms`/`prompt_tokens`/`completion_tokens`/`raw_response`. Per-item failures do **not** fail the run — `run.status` is set to `COMPLETED` regardless, since "one failure doesn't abort the run" per the plan. A second, outer try/except around the whole loop catches *unexpected* (non-LLM-call) errors — e.g. a DB error — sets `run.status = FAILED`, stamps `completed_at`, and re-raises, so a truly broken run is still recorded rather than left dangling as `RUNNING`.
- `cli/run_experiment.py`: `uv run python -m llm_eval_lab.cli.run_experiment <experiment_id>`, prints run id/status/succeeded/failed counts.
- `tests/factories.py` extended with `make_model_config`, `make_prompt`, `make_experiment`.
- Migration `6327e736fc4a_add_experiments_experiment_runs_and_` (autogenerated, applied) creates all three tables plus the `run_status` Postgres enum type and the responses unique constraint.
- Tests (`tests/test_experiment_runner.py`): a `FakeLLMClient` (records calls, raises `RuntimeError` for prompts in a configurable `fail_on` set) drives three unit tests — N test cases → N responses; one simulated per-item failure produces `error` set + `response_text=None` on exactly one `Response` while the other two succeed and the run still completes; unknown `experiment_id` raises `ValueError`. Plus one `@pytest.mark.integration` test hitting real Ollama end-to-end (mirrors the M3 pattern, excluded from default `pytest` runs).
- **Verified:** `alembic upgrade head` applied the new migration. `uv run pytest` green (10 passed, 2 deselected). `uv run pytest -m integration` green (2 passed) including the new runner integration test. Manual end-to-end: imported `qa_smoke_test.json` (10 rows), seeded one `ModelConfig` (`qwen2.5:7b`) + one `Prompt` + one `Experiment` via a scratch script (no CLI for creating these yet — out of scope for M4, which only ships `run_experiment.py`), ran `uv run python -m llm_eval_lab.cli.run_experiment <id>` → `status=completed, 10 succeeded, 0 failed`; spot-checked `Response` rows directly (correct `response_text`/`latency_ms`/token counts, e.g. `"Paris"` for the France question). Manual seed data deleted afterward (cascade-verified) to leave the DB clean.
- Next: M5 (deterministic evaluation engine — evaluation_results).

### M5 — done (2026-08-11)
- ORM: `models/evaluation_result.py` (`EvaluationResult`: id, `response_id` FK, `metric_name`, `score` float, `details` JSONB nullable, created_at) — EAV-style one row per (response, metric), per plan. `Response` gained `evaluation_results` relationship (`cascade="all, delete-orphan"`), re-exported from `models/__init__.py`.
- `evaluation/base.py`: `EvaluationScore` frozen dataclass (`value`, `details=None`) and an `Evaluator` `Protocol` (`metric_name: str`, `evaluate(response_text, expected_answer) -> EvaluationScore`) — pure, no DB coupling, mirroring the `LLMClient` protocol seam from M3 so a future `LLMJudgeEvaluator` slots in without touching the runner.
- `evaluation/deterministic.py`: shared `_normalize()` (lowercase/strip/collapse whitespace) used by both; `ExactMatchEvaluator` (1.0/0.0 on normalized equality), `NormalizedSimilarityEvaluator` (stdlib `difflib.SequenceMatcher.ratio()` on normalized strings, zero new dependency, per plan).
- `evaluation/runner.py`: `evaluate_run(session, experiment_run_id, evaluators)` — looks up the `ExperimentRun` (raises `ValueError` if missing), iterates `run.responses`, skips any with `response_text is None` (failed LLM calls — nothing to score), scores each remaining response against `response.test_case.expected_answer` with every evaluator, writes one `EvaluationResult` per (response, evaluator). `evaluators` is a required plain list (no default baked into the runner) — the CLI decides which evaluators to run, keeping the runner itself evaluator-agnostic.
- `cli/evaluate_run.py`: `uv run python -m llm_eval_lab.cli.evaluate_run <experiment_run_id>`, uses both deterministic evaluators, prints per-metric averages.
- Migration `aa88b5d8b46c_add_evaluation_results_table` (autogenerated — confirmed it detected *only* the new table, no unrelated diffs — applied) creates `evaluation_results` with the FK to `responses`.
- Tests: `tests/test_deterministic_evaluators.py` — parametrized `ExactMatchEvaluator` cases (identical/case-insensitive/whitespace/collapsed-whitespace all → 1.0; different strings and non-exact-substring → 0.0) plus `NormalizedSimilarityEvaluator` cases (identical → 1.0, case/whitespace-only differences → 1.0, completely different → 0.0, partial overlap → strictly between 0 and 1). `tests/test_evaluation_runner.py` — a `ScriptedLLMClient` (per-prompt canned answers, optional `fail_on`) drives `run_experiment` to build a real run, then `evaluate_run` against it: asserts 2 responses × 2 evaluators = 4 `EvaluationResult` rows with the expected scores, asserts a failed response is skipped (no `EvaluationResult` for it), asserts unknown `experiment_run_id` raises `ValueError`.
- **Verified:** `uv run alembic upgrade head` applied cleanly (autogenerate diff showed only the new table). `uv run pytest` green (23 passed, 2 deselected). Manual end-to-end against the real M4 pipeline: imported `qa_smoke_test.json` fresh, seeded `ModelConfig`/`Prompt`/`Experiment` via scratch script (same pattern as M4), ran `run_experiment` against real Ollama (`qwen2.5:7b`, 10/10 succeeded), then `uv run python -m llm_eval_lab.cli.evaluate_run <run_id>` → 20 evaluation results, `exact_match: avg=0.400 (n=10)`, `normalized_similarity: avg=0.666 (n=10)`; spot-checked individual rows — exact numeric/short answers (`"56"`, `"Au"`, `"8"`, `"Portuguese"`) scored 1.0/1.0 on both metrics, while correct-but-prose answers (e.g. `"The capital of France is Paris."` vs expected `"Paris"`) correctly scored `exact_match=0.0` with a partial `normalized_similarity`, confirming both evaluators behave sensibly on real model output. Manual seed data deleted afterward; confirmed all 7 tables (including `evaluation_results`) empty again (cascade delete verified through `experiment → experiment_runs → responses → evaluation_results`).
- Next: M6 (experiment comparison) — not started, out of scope for this session.

### M6 — done (2026-08-11)
- `comparison/compare.py`: `RunComparison` (per-run stats: `run_id`, `experiment_name`, `model_name`, `total_responses`, `succeeded`, `success_rate`, `avg_latency_ms`, `avg_prompt_tokens`, `avg_completion_tokens`, `avg_scores` dict keyed by metric name) and `ComparisonReport` (`runs: list[RunComparison]`), both frozen dataclasses. `compare_experiment_runs(session, run_ids)` looks up each `ExperimentRun` (raises `ValueError` listing the missing id if any run_id doesn't exist), walks `run.responses`/`response.evaluation_results` into two `pandas` DataFrames (responses: run_id/succeeded/latency_ms/prompt_tokens/completion_tokens; scores: run_id/metric_name/score — explicit `columns=` passed so an all-failed or metric-less run still yields a DataFrame with the right shape instead of a `KeyError`), then aggregates per run: `succeeded`/`total` for success_rate, `groupby("metric_name")["score"].mean()` for `avg_scores`, and `.mean()` (pandas skips `NaN`, so failed responses' `None` latency/tokens don't pollute the average) for the numeric columns — **this is the deliberate, justified point `pandas` enters the project**, per plan, since aggregating tabular metrics is exactly its use case.
- `cli/compare_runs.py`: `uv run python -m llm_eval_lab.cli.compare_runs <run_id> [run_id ...]`, prints success rate, avg latency/tokens, and avg score per metric for each run.
- `uv add pandas` (pulled in `numpy` as a transitive dependency).
- Tests (`tests/test_compare.py`): a local `ScriptedLLMClient` (mirrors M5's, plus a configurable `latency_ms` so averages are predictable) drives `run_experiment` + `evaluate_run` to build two real evaluated runs (a "strong" model scoring 1.0 exact-match on both test cases vs a "weak" one scoring 0.5), then asserts `compare_experiment_runs` reports the exact known averages for both, in the order the run_ids were passed; a second test seeds one failing response and asserts it's excluded from `success_rate` (0.5), `avg_latency_ms` (only the succeeded response counts), and `avg_scores` (already excluded upstream by `evaluate_run`, which skips responses with no `response_text`); a third asserts `ValueError` on an unknown run_id.
- **Environment note:** `llama3.2:3b` (the plan's M6 comparison model, not yet pulled as of M3) was pulled this session (`ollama pull llama3.2:3b`, ~2.0GB) — now alongside `qwen2.5:7b`, `llama3.1:8b`, `nomic-embed-text` locally.
- **Verified:** `uv run pytest` green (26 passed, 2 deselected — up from 23). Manual end-to-end per plan: seeded (via scratch script, same pattern as M4/M5) one dataset (`qa_smoke_test.json`, 10 rows), two `ModelConfig`s (`qwen2.5:7b` "strong", `llama3.2:3b` "weak"), one shared `Prompt`, and two `Experiment`s; ran and evaluated both against real Ollama; `compare_runs` output confirmed the score gap is real and visible as the plan requires: `qwen2.5:7b` → `exact_match=0.400, normalized_similarity=0.666, avg_latency_ms=861.7`; `llama3.2:3b` → `exact_match=0.000, normalized_similarity=0.427, avg_latency_ms=2487.5` (stronger model scores higher and answers faster, as expected). Fixed an em-dash in the CLI's print output (mojibake'd in the terminal) to a plain hyphen, matching the rest of the codebase's ASCII-only CLI output. Manual seed data deleted afterward via a second scratch script using `session.delete()` (not bulk `delete()`, which would bypass the ORM-level cascades) on the two `Experiment`s and the `Dataset`, plus explicit deletes of the two `ModelConfig`s and the `Prompt`; confirmed all 8 tables empty again via a direct `psql` count query.
- Next: M7 (FastAPI layer) — not started, out of scope for this session.

### M7 — done (2026-08-11)
- `uv add fastapi "uvicorn[standard]"`.
- Repository layer gained the reads/writes M2-M6 never needed standalone: `datasets/repository.py` gained `get_dataset`, `list_datasets`, `update_dataset`, `delete_dataset` (all plain functions taking a `Session`, matching the existing `create_dataset`/`add_test_case` pattern). New `experiments/repository.py` (mirroring `datasets/repository.py`) holds `create_model_config`/`list_model_configs`, `create_prompt`/`list_prompts`, `create_experiment`/`get_experiment`/`list_experiments` — these didn't exist before M7 because M4-M6 always seeded that data through ad-hoc scratch scripts for manual verification; exposing them over HTTP required promoting that logic into real functions. `tests/factories.py`'s `make_model_config`/`make_prompt`/`make_experiment` were refactored to delegate to these new repository functions instead of constructing ORM objects directly, removing the duplication.
- `schemas/`: one module per resource (mirroring `models/`), Pydantic DTOs with `from_attributes=True` on all `*Read` models, `protected_namespaces=()` set wherever a field starts with `model_` (`model_config_id`, `model_name`) to silence pydantic's namespace-collision warning against its own `model_config` class var. `ResponseRead` deliberately omits `raw_response` (Ollama's raw JSONB, a debugging-only field per the plan's decisions) — the first concrete case of a DTO actually diverging from its ORM model. `ExperimentRunDetail`/`ResponseWithEvaluations` nest responses and their evaluation results under a run for the `results` GETs.
- `api/deps.py`: `get_db()` yields a `SessionLocal()`, commits on success, rolls back and re-raises on exception, always closes.
- `api/routers/datasets.py`: full dataset CRUD (`POST/GET/PATCH/DELETE /datasets`, `GET /datasets/{id}` returns `test_cases` nested) — thin wrappers over the new repository functions. `DELETE` catches `IntegrityError` (a dataset still referenced by an `Experiment`, or by `Response` through its test cases) and returns `409` instead of leaking a raw `500`/SQL traceback — the one bit of new error-translation logic in the router layer, since HTTP status mapping is an API-layer concern the plain repository functions correctly stay agnostic of.
- `api/routers/experiments.py`: `POST/GET /model-configs`, `POST/GET /prompts` (both needed to create an `Experiment` via the API at all, not called out as separate router files in the plan's layout but grouped into this file since they're only ever consumed alongside experiment creation), `POST/GET /experiments`, `GET /experiments/{id}`, `POST /experiments/{id}/runs` — the last one calls M4's `run_experiment` unmodified and runs **synchronously**, per the plan's explicit V1 limitation (no background jobs).
- `api/routers/results.py`: `GET /runs/{id}` (run + nested responses + nested evaluation results), `POST /runs/{id}/evaluate` (runs M5's `evaluate_run` with both deterministic evaluators, mirroring the `evaluate_run` CLI), `GET /compare?run_ids=...` (thin wrapper over M6's `compare_experiment_runs`, repeatable query param).
- `api/main.py`: `FastAPI(title="LLM Evaluation Lab")`, includes all three routers, no prefixes (routers declare full paths themselves).
- `tests/conftest.py` gained a `client` fixture: overrides `get_db` to yield the existing `db_session` directly (no commit/close inside the override — `db_session`'s own teardown still owns rollback), so `TestClient` requests and test assertions share one transactional session per the plan's stated approach.
- New test files: `test_api_datasets.py`, `test_api_experiments.py` (includes one `@pytest.mark.integration` test hitting real Ollama through the run-trigger endpoint, mirroring the M3-M6 pattern), `test_api_results.py` (seeds real evaluated runs via `run_experiment`+`evaluate_run` with a local `ScriptedLLMClient`, no live Ollama needed for evaluate/compare since neither calls the LLM).
- Fixed the `pyproject.toml` pytest `filterwarnings` entry for the `TestCase`-name collision warning: it was an exact-match regex that didn't cover the new `TestCaseRead` DTO; changed to a prefix match covering both.
- **Verified:** `uv run pytest` green (45 passed, 3 deselected). `uv run pytest -m integration` green (3 passed) including the new live-Ollama run-trigger test. Docker Desktop and the Ollama background server both needed a manual start this session (neither was running). `uv run uvicorn llm_eval_lab.api.main:app` boots; `/docs` and `/openapi.json` both serve correctly, confirmed all 10 expected paths registered. Full manual walkthrough via raw `curl` against the live server (not just `/docs`): created a dataset and exercised update/list/delete (including a real `409` on deleting a dataset still referenced by an experiment); imported `qa_smoke_test.json` via the existing M2 CLI (API has no bulk test-case-import endpoint, by design — that stays a CLI/file-loading concern); created `ModelConfig`+`Prompt`+`Experiment` via the API for both `qwen2.5:7b` and `llama3.2:3b`; ran both experiments via `POST /experiments/{id}/runs` against real Ollama; evaluated both via `POST /runs/{id}/evaluate`; confirmed `GET /runs/{id}` nests responses with their evaluation scores correctly; confirmed `GET /compare` reproduces the same real score gap as M6's manual run (`qwen2.5:7b` exact_match=0.5 vs `llama3.2:3b` exact_match=0.0 on this run, along with the expected latency gap). All manually-created data deleted afterward via a scratch script; confirmed all 8 tables empty again via `psql`.
- Next: M8 (Dockerize the app itself) — not started, out of scope for this session.
