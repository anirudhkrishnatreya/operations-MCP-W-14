# Reflection

## Why these tools and agent roles?
I decided to split the work between a Researcher, a Writer, and a Fact Checker. The Researcher does the messy, iterative work of digging through text files and filtering CSV records. The Writer takes over to focus purely on formatting and presenting that knowledge clearly. Finally, the Fact Checker compares the draft directly against the Researcher's retrieved evidence to catch hallucinations and correct unsupported statements.

The tools themselves (`search_documents`, `read_record`, `save_report`) were built to give each agent strict, bounded capabilities. For example, the `save_report` tool was shifted from the Writer to the Fact Checker to ensure only verified reports are saved. I also made sure to pull all the agent instructions, backstories, and task descriptions out into YAML files under `config/`. This keeps the actual Python code a lot cleaner and separates the "prompt engineering" from the hard logic.

## What broke first when you connected the crew to the server?
The very first thing that tripped me up was getting the Pydantic schemas to play nicely with the MCP tools. FastMCP tries to automatically infer inputs, and it took some tweaking to get the types to align perfectly. I also ran into an issue where the crew agent would occasionally hallucinate arguments—like passing an empty query or a completely invalid ID. I had to tighten up the prompt instructions and set strict `max_iter` limits to stop the agents from getting stuck in endless retry loops when they got confused.

## Show one wrong or ungrounded answer. Did your guardrail catch it?
During a live run, the Researcher agent hallucinated two random record IDs to query, calling `read_record(record_id=12345)` and `read_record(record_id=67890)`.

Our guardrails caught this at two levels:
1. **Pydantic Validation:** The MCP tool's `RecordInput` schema has a strict rule (`le=9999`), so the tool immediately rejected the request with a clear `validation error for RecordInput`.
2. **System Prompt Guardrail:** Because the prompt explicitly instructed the agent to "state explicitly" if nothing useful is found and "do NOT guess," the agent correctly digested the validation error. In its final output, instead of making up a fake record, it accurately reported: *"No records found matching record IDs 12345 and 67890."*

## Where is the biggest security risk in your server?
Without a doubt, it's the `save_report` tool. Since it actively writes files to the disk, a hallucinating (or malicious) model could easily attempt a path traversal attack—something like passing `title="../../../etc/passwd"`. To lock this down, I added a strict regular expression to sanitize the filename and hardcoded the logic so it can *only* write files into the `./outputs/` directory.

## What would you change before touching real company data?
If I were deploying this to a real production environment, I'd definitely add a few safeguards:
1. **Authentication:** I'd lock down the MCP server so only permitted, authenticated clients could even connect to it.
2. **Read-Only Policies:** I'd enforce strict read-only database permissions for the data-fetching tools.
3. **Human-in-the-loop (HITL) (Implemented):** We integrated an interactive human approval gate into the Verification task, prompting the user in the terminal to review and approve the final verified report draft before it gets written to disk.
4. **Rate Limiting:** I'd add rate limits to make sure a runaway agent loop couldn't accidentally DDOS external APIs or thrash the local file system.

## Why switch from Stdio to SSE for the primary MCP server?
Switching to SSE (Server-Sent Events) transport decouples the MCP server lifecycle from the crew's Python process. With Stdio, the server lived entirely inside the crew's subprocess; killing the crew killed the server. With SSE, the Operations Server runs as an independent HTTP service that multiple clients could potentially connect to simultaneously. This is a much more realistic production deployment model — you'd run the MCP server as a persistent microservice (e.g. in Docker or on a VM) and have the crew connect over the network. The trade-off is that you must now start the server before running the crew, which is documented clearly in the README.
