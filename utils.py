import io
import re
import logging
from pathlib import Path
from prompts import INJECTION_TRIGGER, REDACTION_PLACEHOLDER, get_run_report_template

logger = logging.getLogger(__name__)


# ==========================================
# Logging Utilities
# ==========================================
class Tee(io.StringIO):
    """
    A custom file-like object that writes to both the original standard output
    and a string buffer in memory. This allows capturing traces while still
    letting the user interact with the terminal (e.g. for human input prompts).
    """

    def __init__(self, original_stdout):
        super().__init__()
        self.original_stdout = original_stdout

    def write(self, string):
        self.original_stdout.write(string)
        return super().write(string)

    def flush(self):
        self.original_stdout.flush()
        super().flush()


# ==========================================
# File Writers
# ==========================================
def get_traces_dir() -> Path:
    traces_dir = Path(__file__).parent / "traces"
    traces_dir.mkdir(exist_ok=True)
    return traces_dir


def write_trace(timestamp: str, question: str, trace_content: str, result) -> None:
    trace_path = get_traces_dir() / f"trace_{timestamp}.txt"
    trace_path.write_text(
        f"Question: {question}\n\nTrace:\n{trace_content}\n\nResult:\n{result}",
        encoding="utf-8",
    )
    print(f"\n Trace saved to: {trace_path}")


def write_run_report(timestamp: str, question: str, result, crew, tasks) -> None:
    report_path = get_traces_dir() / f"run_report_{timestamp}.md"

    metrics = getattr(crew, "usage_metrics", None)
    total_tokens = getattr(metrics, "total_tokens", "N/A")
    prompt_tokens = getattr(metrics, "prompt_tokens", "N/A")
    completion_tokens = getattr(metrics, "completion_tokens", "N/A")
    successful_requests = getattr(metrics, "successful_requests", "N/A")

    task_summaries = []
    for i, task in enumerate(tasks, 1):
        agent_name = getattr(task.agent, "role", "Unknown") if task.agent else "Unknown"
        desc_preview = (task.description or "")[:120].replace("\n", " ")
        task_summaries += [
            f"### Task {i}: {agent_name}",
            f"- **Description:** {desc_preview}...",
            "",
        ]

    result_preview = str(result)[:500].replace("\n", " ")

    report_content = get_run_report_template(
        timestamp,
        question,
        str(total_tokens),
        str(prompt_tokens),
        str(completion_tokens),
        str(successful_requests),
        task_summaries,
        result_preview,
    )

    report_path.write_text(report_content, encoding="utf-8")
    print(f"\n Run report saved to: {report_path}")


# ==========================================
# Injection Guards
# ==========================================
_INJECTION_PATTERNS: list[re.Pattern] = [
    re.compile(
        r"ignore\s+(all\s+)?previous\s+instructions?", re.IGNORECASE | re.DOTALL
    ),
    re.compile(
        r"disregard\s+(your\s+)?(system\s+prompt|instructions?|guidelines?)",
        re.IGNORECASE | re.DOTALL,
    ),
    re.compile(
        r"forget\s+(your\s+)?(guidelines?|instructions?|previous|rules?)",
        re.IGNORECASE | re.DOTALL,
    ),
    re.compile(r"developer\s+mode", re.IGNORECASE),
    re.compile(r"jailbreak", re.IGNORECASE),
    re.compile(r"unrestricted\s+assistant", re.IGNORECASE),
    re.compile(r"\[INST\]", re.IGNORECASE),
    re.compile(r"\[/INST\]", re.IGNORECASE),
    re.compile(r"<<SYS>>", re.IGNORECASE),
    re.compile(r"<</SYS>>", re.IGNORECASE),
    re.compile(
        r"output\s+(the\s+phrase\s+)?['\"]?SYSTEM\s+COMPROMISED['\"]?(\s+verbatim)?",
        re.IGNORECASE,
    ),
    re.compile(
        r"reply\s+only\s+with\s*:\s*['\"]?SYSTEM\s+COMPROMISED['\"]?", re.IGNORECASE
    ),
    re.compile(r"SYSTEM\s+COMPROMISED", re.IGNORECASE),
    re.compile(r"<\|system\|>", re.IGNORECASE),
    re.compile(r"<\|user\|>", re.IGNORECASE),
    re.compile(r"<\|assistant\|>", re.IGNORECASE),
]


def sanitize(text: str) -> str:
    sanitised = text
    for pattern in _INJECTION_PATTERNS:
        if pattern.search(sanitised):
            logger.warning(
                "Prompt-injection pattern detected and redacted: %s", pattern.pattern
            )
            sanitised = pattern.sub(REDACTION_PLACEHOLDER, sanitised)
    return sanitised


def contains_injection(text: str) -> bool:
    return INJECTION_TRIGGER.lower() in text.lower()


def assert_clean(text: str, label: str = "output") -> None:
    if contains_injection(text):
        raise RuntimeError(
            f"SECURITY ALERT: Injection trigger phrase detected in {label}! "
            f"The phrase '{INJECTION_TRIGGER}' must not appear in agent output. "
            "Aborting."
        )
    logger.info("Injection check passed for %s.", label)
