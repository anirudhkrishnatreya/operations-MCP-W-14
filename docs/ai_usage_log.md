# AI Usage Log

During the development and finalization of the Operations Assistant project, an AI coding assistant (Gemini/Antigravity) was used to accelerate development and ensure code quality.

## Areas of AI Assistance:
1. **Architecture & Documentation**:
   - The AI assistant was used to generate a Mermaid architecture diagram mapping out the interactions between the multi-agent CrewAI system, the two MCP servers (Core and Fetch), and the local filesystem.
   - Used to make synthetic data.

2. **Security & Hardening**:
   - Brainstorming and refining the prompt injection defense mechanisms (`utils/injection_guard.py`) utilizing regex patterns to detect and redact malicious LLM payloads.
   - Reviewing Pydantic validation schemas in `mcp_server.py` to ensure robust path-traversal protections on the `save_report` tool.

3. **Code Review & Verification**:
   - Used as a pair-programming partner to methodically cross-check the codebase against the MVP, Core (Hardening), and Stretch goal rubrics.
   - Verified that the human-in-the-loop (HITL) gate was correctly isolating the `save_report` tool via CrewAI task delegation.

4. **Debugging**:
   - Assisted in resolving early type-mismatch issues between FastMCP tools and CrewAI agent tool-calling payloads.

## Impact
Using the AI assistant significantly reduced the time spent writing boilerplate documentation and provided a rigorous external check on the security architecture before finalizing the project.
