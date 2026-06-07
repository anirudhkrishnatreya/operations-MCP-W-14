import sys, os
from pathlib import Path
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from server.mcp_server import search_documents, read_record, save_report


def test_search_finds_return_policy():
    result = search_documents("return")
    assert "return_policy.txt" in result


def test_search_empty_query():
    result = search_documents("")
    assert "Error" in result


def test_read_existing_record():
    result = read_record(1)
    assert "Headphones X200" in result


def test_read_nonexistent_record():
    result = read_record(9999)
    assert "Error" in result


def test_read_invalid_id():
    result = read_record(-5)
    assert "Error" in result


def test_save_report_creates_file(tmp_path, monkeypatch):
    import server.mcp_server as srv

    monkeypatch.setattr(srv, "OUTPUTS_DIR", tmp_path)
    result = save_report("Test Report", "## Summary\nThis is a test.")
    assert "saved" in result.lower()
    files = list(tmp_path.glob("*.md"))
    assert len(files) == 1
