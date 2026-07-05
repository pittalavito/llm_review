import os
import sys
from pathlib import Path

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
