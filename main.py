import sys
from dotenv import load_dotenv
from telemetry import setup_telemetry, shutdown_telemetry
from crew.crew import run_crew

load_dotenv()
setup_telemetry()


def main():
    question = sys.argv[1] if len(sys.argv) > 1 else "What is the return policy?"
    try:
        answer = run_crew(question)
        print("\n FINAL ANSWER :")
        print(answer)
    finally:
        shutdown_telemetry()


if __name__ == "__main__":
    main()
