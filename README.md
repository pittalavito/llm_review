# llm_review
LLM-based multi-agent framework for reviewing scientific articles

## Version

- Current version: `0.1.0`

## Project status (first release)

### Backend
- FastAPI app with health endpoint: `GET /health`
- Available model listing: `GET /models`
- LLM test endpoint: `POST /test-llm`
- Agent test placeholder endpoints:
	- `GET /test-agent`
	- `POST /test-agent`

### UI
- `System Status` section for `/health`
- `Test LLM` section for `/models` + `/test-llm`
- `Test Agent` section for `/test-agent` (GET/POST)

### Tooling
- Run app: `./scripts/run-app.ps1`
- Run tests: `./scripts/run-test.ps1`
- Stop running app instances: `./scripts/stop-app.ps1`
- Clean Python cache artifacts: `./scripts/clean-cache.ps1`

## Next step

Implement a real `Review Agent` and its related tool integration:
- add agent registry in backend container
- define agent input/output schemas
- implement at least one production agent endpoint (replacing current placeholder)
- connect the UI `Test Agent` section to real payloads and results
- add integration tests for agent + tool flow

## Quick start (Windows + uv)

```powershell
python -m pip install uv
./scripts/run-app.ps1
```

## Run tests

```powershell
./scripts/run-test.ps1
```

## Stop app instances

```powershell
./scripts/stop-app.ps1 -Preview
./scripts/stop-app.ps1
```

## Clean Python cache artifacts

```powershell
./scripts/clean-cache.ps1 -Preview
./scripts/clean-cache.ps1
```
