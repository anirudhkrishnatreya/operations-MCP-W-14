# Decision Log

## 1. Why FastMCP over raw MCP SDK?
FastMCP offers a significantly more concise API, allowing tools to be written as standard Python functions with Pydantic typing handling the schema generation automatically. It removes boilerplate routing and serialization logic needed by the raw SDK.

## 2. Why Llama 3.1 8B for Researcher, Llama 3.3 70B for Writer (via Groq)?
Llama 3.1 8B on Groq is highly optimized for ultra-low latency inference and tool calling, making it ideal for the iterative loop the Researcher agent goes through. Llama 3.3 70B is more capable at complex reasoning and high-quality prose generation, which perfectly fits the Writer agent's role of synthesizing the gathered data into a clean report. The Groq API provides a fast, free-tier alternative that avoids OAuth/Vertex key restriction errors.

## 3. Why switch from Stdio to SSE for the primary MCP server? (Stretch Goal #6)
SSE transport separates the MCP server's lifecycle from the crew's Python process, making it a standalone HTTP service. This reflects a production-realistic architecture where MCP servers run as persistent microservices that multiple clients can connect to, rather than being tied to a single parent process. The Fetch Server remains on Stdio because it is lightweight, fire-and-forget, and benefits from being automatically managed by `MCPServerAdapter` without needing a separate terminal.

## 4. What did you try first that didn't work?
Initial testing with the raw strings in `search_documents` and `save_report` didn't have robust validation. Pydantic models were added to enforce min/max length and path traversal sanitization, preventing potential runtime issues and ensuring secure file writing.

## 5. What did you reject?
I rejected building custom Python scripts for reading the files in favor of using CrewAI. CrewAI provides out of the box MCP integration via `MCPServerAdapter` which handles standardizing tool execution and agent behavior much more natively than a bespoke pipeline.

## 6. Why externalize agent and task configurations to YAML?
Moving the prompt instructions, roles, backstories, and task descriptions out of the Python execution scripts (`crew/agents.py` and `crew/tasks.py`) into separate configuration files (`config/agents.yaml` and `config/tasks.yaml`) ensures a clean separation of concerns. This allows developers or prompt engineers to edit agent personas and task descriptions declaratively without touching executable Python code, making the system modular and scaling friendly.

## 7. Why separate the Operations Server from the Fetch Server (Multiple MCP Servers)?
- **Security**: Isolates local file/db access from internet-facing tools to enforce least-privilege permissions.
- **Dependency Isolation**: Prevents bloating the core server with web-scraping packages and HTTP clients.
- **Agent Focus**: Allocates only necessary tools to specific agents, reducing LLM tool confusion.

## 8. Why was LiteLLM required?
- **Framework Standard**: CrewAI uses LiteLLM internally as its default translation layer for handling model APIs, allowing us to configure Groq (`groq/...`) seamlessly without custom API clients.
- **Observability Hooks**: LiteLLM exposes a structured callback system (`litellm.success_callback`), enabling us to easily register custom OpenTelemetry tracing hooks to monitor and export LLM latency, token counts, and input/output payloads to the Aspire Dashboard.

## 9. Why add a Fact Checker agent and a Verification task?
- **Anti-Hallucination Guardrail**: Even with descriptive prompts, LLMs can introduce subtle factual errors or omit citations. The Fact Checker acts as a dedicated editor that compares the generated output directly with the retrieved evidence context, correcting discrepancies.
- **Enforcing Least-Privilege Tools**: By transferring the `save_report` tool from the Writer to the Fact Checker, we ensure that a raw draft can never be saved directly without undergoing fact-checking and validation first.

## 10. Why move the Human-in-the-Loop (HITL) approval to the Verification task?
- **Ensuring High Quality Input for Human Review**: It is more efficient for the human auditor to review a fact-checked, validated report rather than a raw draft. Placing the gate at the Verification task ensures that the human only sees the final verified report before it is saved.
- **Task-Level Tool Isolation**: To physically prevent the Fact Checker agent from saving the file before human approval is granted, we stripped the `save_report` tool from the agent-level configuration and assigned it strictly to a subsequent `save_task`. Because `save_task` runs after `verification_task` completes, the file can only be saved once the human approves the verification output.
