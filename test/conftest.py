import os
import sys
import tempfile
from pathlib import Path

import pytest

# Ensure `src/` is importable when running tests directly with pytest.
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

# Fake provider credentials: tests must run without a .env file or real keys.
# Clients are only constructed, never invoked (MockChatModel handles LLM calls),
# so a placeholder is enough to satisfy the factory checks.
# Set at import time because main.py instantiates Config() when imported.
os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")
os.environ.setdefault("OLLAMA_URL", "http://localhost:11434")

# Isolated per-session SQLite database: tests must never touch resource/db/.
# Assigned (not setdefault) at import time so every Config() — including the
# module-level one in main.py — picks it up.
_TEST_DB_DIR = Path(tempfile.mkdtemp(prefix="llm-review-test-db-"))
os.environ["DATABASE_URL"] = f"sqlite:///{(_TEST_DB_DIR / 'test.sqlite').as_posix()}"
os.environ["REDIS_URL"] = ""  # file-only RAG indices: no Redis in tests


@pytest.fixture(scope="session", autouse=True)
def seed_run_history():
    """Seed the session database with the committed legacy runs so endpoints
    asserting a non-empty run history keep passing."""
    from config import Config, RESULTS_DIR
    from db.engine import create_db_engine, init_db
    from db.import_legacy import import_results_dir

    engine = create_db_engine(Config())
    init_db(engine)
    import_results_dir(engine, RESULTS_DIR)
    engine.dispose()
    yield
