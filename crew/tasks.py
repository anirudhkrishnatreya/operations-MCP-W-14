from crewai import Task
import yaml
from pathlib import Path


def get_tasks_config():
    config_path = Path(__file__).parent.parent / "config" / "tasks.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def build_tasks(
    researcher, writer, fact_checker, question: str, save_tool: list
) -> list[Task]:
    config = get_tasks_config()

    # We need to format the question into the description
    # Since config is loaded as dict, we can interpolate it manually
    research_config = config["research_task"]
    research_config["description"] = research_config["description"].format(
        question=question
    )

    research_task = Task(
        config=research_config,
        agent=researcher,
    )

    write_task = Task(
        config=config["write_task"],
        agent=writer,
        context=[research_task],  # writer receives researcher's output
    )

    verification_task = Task(
        config=config["verification_task"],
        agent=fact_checker,
        context=[research_task, write_task],
        human_input=True,
    )

    save_task = Task(
        config=config["save_task"],
        agent=fact_checker,
        tools=save_tool,
        context=[verification_task],
    )

    return [research_task, write_task, verification_task, save_task]
