"""
Centralized storage for all system prompts, instruction templates, and prompt strings.
"""

# ==========================================
# Injection Guard Prompts & Triggers
# ==========================================
INJECTION_TRIGGER = "SYSTEM COMPROMISED"
REDACTION_PLACEHOLDER = "[REDACTED: potential injection payload]"


# ==========================================
# Reporting Prompts & Templates
# ==========================================
def get_run_report_template(
    timestamp: str,
    question: str,
    total_tokens: str,
    prompt_tokens: str,
    completion_tokens: str,
    successful_requests: str,
    task_summaries: list[str],
    result_preview: str,
) -> str:
    """Returns the formatted markdown template for the run report."""
    lines = [
        "# Run Report",
        "",
        f"**Timestamp:** {timestamp}",
        f"**Question:** {question}",
        "",
        "## Token Usage",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| Total Tokens | {total_tokens} |",
        f"| Prompt Tokens | {prompt_tokens} |",
        f"| Completion Tokens | {completion_tokens} |",
        f"| Successful LLM Requests | {successful_requests} |",
        "",
        "## Task Summary",
        "",
    ]
    lines.extend(task_summaries)
    lines.extend(
        [
            "## Result Preview",
            "",
            f"> {result_preview}...",
            "",
        ]
    )
    return "\n".join(lines)
