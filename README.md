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

- connect the UI `Test Agent` section to real payloads and results
- add integration tests for agent + tool flow
- create Technical Reviewer (Correctness & Quality)
	- Main responsibility: verify that content is technically and logically correct and internally consistent.
- create Style & Readability Reviewer (Communication)
	- Main responsibility: verify that the text is clear, readable, and communicatively effective.
- define additional reviewer roles and responsibilities as needed.
- ........
