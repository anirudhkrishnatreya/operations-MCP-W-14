import os
import csv
import re
import sys
from pathlib import Path
from datetime import datetime
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field, field_validator

# Allow importing utils from the project root
sys.path.insert(0, str(Path(__file__).parent.parent))
from utils import sanitize as _sanitize_content

DATA_DIR = Path(__file__).parent.parent / "data" / "documents"
CSV_PATH = Path(__file__).parent.parent / "data" / "inventory.csv"
OUTPUTS_DIR = Path(__file__).parent.parent / "outputs"
OUTPUTS_DIR.mkdir(exist_ok=True)

mcp = FastMCP("Operations Assistant")


class SearchInput(BaseModel):
    query: str = Field(
        ..., min_length=1, max_length=500, description="Search term (1–500 characters)"
    )


class RecordInput(BaseModel):
    record_id: int = Field(..., ge=1, le=9999, description="Positive integer record ID")


class ReportInput(BaseModel):
    title: str = Field(..., min_length=1, max_length=100)
    content: str = Field(..., min_length=10, max_length=50000)

    @field_validator("title")
    @classmethod
    def no_path_chars(cls, v):
        if any(c in v for c in r"/\.."):
            raise ValueError("Title must not contain path characters")
        return v


@mcp.tool()
def search_documents(query: str) -> str:
    """
    Search through operations documents for content matching the query.
    Returns matching document names and relevant excerpts.

    Args:
        query: A search term or question to look for in the documents.

    Returns:
        A formatted string listing matching documents and their excerpts.
    """
    # Validation using Pydantic schema model (manual check for string input since fastmcp unpacks arguments)
    try:
        validated = SearchInput(query=query)
        query = validated.query
    except ValueError as e:
        return f"Error: {e}"

    query_lower = query.lower()
    results = []

    for doc_path in DATA_DIR.glob("*.txt"):
        content = doc_path.read_text(encoding="utf-8")
        if query_lower in content.lower():
            # Return first 300 chars of matching content as excerpt
            lines = [l for l in content.splitlines() if query_lower in l.lower()]
            excerpt = lines[0][:300] if lines else content[:300]
            # Layer 1 guardrail: redact injection payloads before returning to LLM
            safe_excerpt = _sanitize_content(excerpt)
            results.append(f"[{doc_path.name}]: {safe_excerpt}")

    if not results:
        return f"No documents found matching '{query}'."

    return "\n\n".join(results)


@mcp.tool()
def read_record(record_id: int) -> str:
    """
    Read a specific inventory or order record by its numeric ID.

    Args:
        record_id: The integer ID of the record to retrieve.

    Returns:
        A formatted string of the record's fields, or an error if not found.
    """
    try:
        validated = RecordInput(record_id=record_id)
        record_id = validated.record_id
    except ValueError as e:
        return f"Error: {e}"

    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if int(row["id"]) == record_id:
                return "\n".join(f"{k}: {v}" for k, v in row.items())

    return f"Error: No record found with id={record_id}."


@mcp.tool()
def save_report(title: str, content: str) -> str:
    """
    Save a markdown report to the outputs folder.

    Args:
        title: The title of the report (used as filename). Alphanumeric and spaces only.
        content: The full markdown content of the report.

    Returns:
        Confirmation message with the saved file path.
    """
    try:
        validated = ReportInput(title=title, content=content)
        title = validated.title
        content = validated.content
    except ValueError as e:
        return f"Error: {e}"

    # Sanitize filename — no path traversal
    safe_title = re.sub(r"[^a-zA-Z0-9 _-]", "", title).strip().replace(" ", "_")
    if not safe_title:
        return "Error: title contains no valid characters."

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{safe_title}_{timestamp}.md"
    output_path = OUTPUTS_DIR / filename

    output_path.write_text(content, encoding="utf-8")
    return f"Report saved to: outputs/{filename}"


if __name__ == "__main__":
    # Run as an SSE server on http://localhost:8000/sse
    # Start with: uv run python server/mcp_server.py
    mcp.run(transport="sse")
