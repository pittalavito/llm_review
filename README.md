# llm_review

Multi-agent system for automated scientific paper review. It simulates an ML/NLP conference committee: three independent reviewers evaluate the paper in parallel, a meta-reviewer synthesizes the judgments, an area chair makes the accept/revise decision, and an author agent produces revision notes. The loop repeats until acceptance or the maximum number of rounds is reached.

Each agent in the graph is individually configurable with its own LLM model and temperature. The graph itself can be recompiled at runtime with a different agent configuration without restarting the server.

Reviewers also expose persona axes that shape their behavior: **focus** (soundness, empirical, novelty), **commitment** (responsible/irresponsible), **intention** (benign/malicious), and **knowledgeability** (knowledgeable/unknowledgeable). The area chair has a configurable decision style (authoritarian, conformist, inclusive). These parameters allow fine-grained control over review dynamics and simulation of diverse committee compositions.

## Stack

| Layer | Technologies |
|---|---|
| Agent orchestration | LangGraph, LangChain |
| Supported LLMs | Ollama (local), OpenAI, Anthropic |
| Backend | FastAPI, Uvicorn, Pydantic |
| Persistence | SQLite via SQLModel (runs), Redis cache (RAG indices), Docker Compose |
| Retrieval | Custom BM25, PyPDF for text extraction |
| Tooling | uv, pytest, pytest-cov |

## Demo static page with real reviews

https://pittalavito.github.io/llm_review/

## Review Graph

6 nodes, 3 reviewers running **in parallel**:

The loop feeds back to the fan-out node, re-launching reviewers in parallel with the author's rebuttal injected into each prompt.

![Review Pipeline](docs/pipeline.svg)

## API

All endpoints under `/llm-review`.

### Graph & Run

| Method | Endpoint | Description |
|---|---|---|
| POST | `/graph/compile` | Compile the graph (optional: per-agent model/temperature config) |
| GET | `/graph/config` | Current graph configuration |
| POST | `/graph/run` | Run the full pipeline on a paper |

### Results

| Method | Endpoint | Description |
|---|---|---|
| GET | `/runs` | List all saved runs |
| GET | `/runs/{run_id}` | Single run detail |
| GET | `/runs/{run_id}/agent-runs` | Agent traces (filter by name/round) |

### Prompt versions

| Method | Endpoint | Description |
|---|---|---|
| GET | `/prompts` | List registered prompt versions (metadata) |
| GET | `/prompts/{id}` | Version detail including template text |
| POST | `/prompts` | Register a new immutable version (409 on duplicate role/label) |
| PATCH | `/prompts/{id}` | Update description / is_active only |

### Comparison

| Method | Endpoint | Description |
|---|---|---|
| GET | `/compare/papers` | List papers available for comparison |
| GET | `/compare` | Compare pipeline results against reference reviews for a paper |

### Other (dev/test)

| Method | Endpoint | Description |
|---|---|---|
| GET | `/health` | Health check |
| GET | `/models` | List available LLM models |
| POST | `/test-llm` | Direct LLM test |
| GET | `/agents` | List agent names |
| POST | `/agents` | Test a single agent |
| POST | `/agents/prompt-preview` | Preview the built prompt for an agent |
| POST | `/agents/retrieval` | Test agent with RAG |
| GET | `/papers` | List available papers |
| POST | `/papers/index` | Index a paper |
| GET | `/papers/indexed` | List indexed papers |
| GET | `/papers/indexed/detail` | Index detail for a single paper |

## Database

Run history is persisted in **SQLite** (`resource/db/llm-review.sqlite`, created automatically at startup) through **SQLModel**. Design principle: analytical facts live in typed, CHECK-constrained, indexed columns; full payloads are preserved verbatim in JSON columns for audit and API fidelity.

```
RUN 1 ──< AGENT_RUN            (one row per agent invocation, ordered by id)
RUN 1 ──< RUN_AGENT_CONFIG     (per-agent model/temperature/persona, from graph_config)
PROMPT_VERSION 1 ──< RUN_AGENT_CONFIG   (which base prompt each agent used)
```

| Table | Typed columns (extract) | JSON columns |
|---|---|---|
| `run` | run_id PK, timestamp, paper_path, decision, total_rounds, max_rounds, meta_overall_score | reviews, meta_review, area_chair_response, author_response, retrieval_metadata, graph_config |
| `agent_run` | run_id FK, agent, round, rating, confidence, overall_score, decision, latency_ms, input/output/total_tokens | response_payload, prompt_trace, runtime_trace |
| `run_agent_config` | run_id FK, agent_name, model, temperature, prompt_version (+FK), persona axes, area_chair_style | — |
| `prompt_version` | agent_role, version_label (UNIQUE pair), template, template_hash, description, is_active | — |

### Prompt versioning

Base system prompts live in the `prompt_version` table (seeded at startup from the code templates) and are **selectable per agent at compile time** via `prompt_version` in the graph config (default `"v1"`; the three reviewers share the `reviewer` role). Versions are **immutable**: a new text means a new version; only `description` and `is_active` can change. Every run records label + FK of the version each agent used, so results are always attributable to an exact prompt text. Persona/style modifiers remain code-side composition on top of the base template.

Example analytical query (average reviewer rating by model and persona focus):

```sql
SELECT c.model, c.persona_focus, AVG(a.rating)
FROM agent_run a
JOIN run_agent_config c ON a.run_id = c.run_id AND a.agent = c.agent_name
WHERE a.rating IS NOT NULL
GROUP BY c.model, c.persona_focus;
```

Legacy JSON runs under `resource/results/` can be imported (idempotent) with:

```
uv run python scripts/import-runs.py
```

There are deliberately no schema migrations (no Alembic): after a schema change, delete `resource/db/llm-review.sqlite*` and re-run the import — the JSON archive remains the recovery source.

### Redis cache for RAG indices

BM25 indices (JSON files keyed by SHA-256 under `resource/rag-index/`) are served through a **cache-aside** Redis layer: files remain the source of truth, Redis is a pure read accelerator. If `REDIS_URL` is unset or Redis is unreachable, the app transparently falls back to file-only access (single warning, no crash).

```
docker compose -f resource/docker/docker-compose.redis.yml up -d
# starts redis:7.4-alpine on localhost:6380
# .env: REDIS_URL=redis://localhost:6380/0
```

## Frontend

Two UIs coexist during the React migration:

| UI | Stack | Where | Status |
|---|---|---|---|
| Classic | Vanilla JS (ES Modules) in `ui/` | `http://localhost:8081/` | Stable, untouched |
| New | React 18 + TypeScript + Vite in `ui-react/` | `http://localhost:8081/v2/` (built) or `http://localhost:5173/v2/` (dev) | Full feature parity, under validation |

The React app talks to the same API (`/llm-review`), typed against the Pydantic models. JSX escaping closes the stored-XSS surface the vanilla `storico` section had with LLM-generated text.

```
cd ui-react
npm install       # once
npm run dev       # dev server with proxy to the backend on 8081
npm run build     # production bundle in ui-react/dist, served by FastAPI at /v2
```

The switch of `/` to the React UI (and the retirement of the vanilla one) will happen after validation.

## Scripts

All cross-platform Python. Run with `uv run python scripts/<name>.py`.

| Script | Command | Description |
|---|---|---|
| start-venv | `uv run python scripts/start-venv.py` | Create `.venv` and install dependencies |
| run-app | `uv run python scripts/run-app.py` | Start uvicorn on port 8081 |
| run-test | `uv run python scripts/run-test.py` | Run pytest with coverage |
| stop-app | `uv run python scripts/stop-app.py` | Kill the uvicorn process |
| clean-cache | `uv run python scripts/clean-cache.py` | Remove Python cache artifacts |
| import-runs | `uv run python scripts/import-runs.py` | Import legacy JSON runs into SQLite (idempotent) |

## Todo / Future work

1. ~~**No DB/FTP integration**~~ — **done**: runs live in SQLite (SQLModel), RAG indices are cached in Redis with file fallback. Papers are still plain files under `resource/papers/`.
2. **No file upload from the UI** — a paper must be manually placed in `resource/papers/` and then indexed by hand.
3. **Naive RAG** — the retrieval is basic and could be improved.
4. ~~**UI improvements**~~ — **decided**: the vanilla JS UI is the final one (Streamlit idea dropped — plain web programming fits the thesis better). Prompt-version management UI added.
5. ~~**Prompt versioning**~~ — **done**: base prompts live in the `prompt_version` table, are editable via the `/prompts` API, selectable per agent at compile time, and recorded per run.
6. **Containerization** — Redis already runs via `resource/docker/docker-compose.redis.yml`; the app itself could be containerized too.
7. **Custom mock runs** — allow building custom runs reusing real past responses as mocks, reading them from the DB/Redis.
8. **Compare export** — add a UI function to export the comparison as CSV (can now be a SQL query → CSV endpoint) for use in the thesis.
9. **Dynamic review scope** — let agents set the review scope dynamically (e.g. ICLR, LMN, Other).
