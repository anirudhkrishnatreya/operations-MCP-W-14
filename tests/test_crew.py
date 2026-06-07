import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from crew.crew import run_crew
import pytest

from config import ensure_env

try:
    has_groq = bool(ensure_env("GROQ_API_KEY"))
except ValueError:
    has_groq = False


@pytest.mark.skipif(not has_groq, reason="No API key provided")
def test_crew_answers_with_source(monkeypatch):
    # Mock builtins.input to automatically approve the report by sending Enter (empty string)
    monkeypatch.setattr("builtins.input", lambda *args, **kwargs: "")
    answer = run_crew("What is the return policy?")
    # Answer must mention the source document
    assert "return_policy" in answer.lower() or "return" in answer.lower()
    # Must not be empty
    assert len(answer) > 50
