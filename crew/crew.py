import sys
from datetime import datetime

from dotenv import load_dotenv
from langfuse.decorators import langfuse_context, observe
from opentelemetry import context as otel_context
from opentelemetry import trace

from crewai import Crew, Process
from crewai_tools import MCPServerAdapter

from patches import apply_patches
from telemetry import setup_telemetry, shutdown_telemetry
from utils import Tee, assert_clean, write_run_report, write_trace

from .agents import FETCH_SERVER_PARAMS, SERVER_PARAMS, build_agents
from .tasks import build_tasks

load_dotenv()
apply_patches()


@observe(name="crew.run")
def run_crew(question: str) -> str:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    tracer = trace.get_tracer("operations-assistant")

    # Set Langfuse explicit trace properties
    langfuse_context.update_current_trace(
        session_id="operations_assistant",
        tags=["crew", "operations"],
        input={"question": question},
    )

    # Start span BEFORE redirecting stdout so span.end() / gRPC export
    # happens outside the Tee capture region (in the finally block below).
    span = tracer.start_span("crew.run")
    span.set_attribute("crew.question", question)
    token = otel_context.attach(trace.set_span_in_context(span))

    original_stdout = sys.stdout
    tee = Tee(original_stdout)
    sys.stdout = tee

    result = None
    crew = None
    tasks = []

    try:
        with MCPServerAdapter(SERVER_PARAMS) as mcp_tools:
            with MCPServerAdapter(FETCH_SERVER_PARAMS) as fetch_tools:
                researcher, writer, fact_checker = build_agents(mcp_tools, fetch_tools)
                save_tool = [t for t in mcp_tools if t.name == "save_report"]
                tasks = build_tasks(
                    researcher, writer, fact_checker, question, save_tool
                )

                crew = Crew(
                    agents=[researcher, writer, fact_checker],
                    tasks=tasks,
                    process=Process.sequential,
                    verbose=True,
                )

                result = crew.kickoff()
                assert_clean(str(result), label="crew final output")
                langfuse_context.update_current_trace(output={"result": str(result)})
    finally:
        # Restore stdout FIRST, then end span — gRPC export runs with real stdout
        sys.stdout = original_stdout
        otel_context.detach(token)

        if result is not None:
            span.set_attribute("crew.result_preview", str(result)[:200])
        span.end()  # export happens here, after stdout is restored

        write_trace(timestamp, question, tee.getvalue(), result)
        if result is not None and crew is not None:
            write_run_report(timestamp, question, result, crew, tasks)

    return str(result)


if __name__ == "__main__":
    setup_telemetry()

    question = sys.argv[1] if len(sys.argv) > 1 else "What is the return policy?"
    try:
        answer = run_crew(question)
        print("\n FINAL ANSWER :")
        print(answer)
    finally:
        shutdown_telemetry()
