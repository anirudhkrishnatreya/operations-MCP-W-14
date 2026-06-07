import os
import csv
import queue
import sys
import threading
import asyncio
import socket
from pathlib import Path
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from dotenv import load_dotenv

# Allow importing utils and crew from project root
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load environment
load_dotenv()

app = FastAPI(
    title="Operations Assistant Dashboard",
    description="Sleek operations assistant dashboard built by Anirudh Sharma",
    version="1.0.0"
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATA_DIR = Path(__file__).parent.parent / "data" / "documents"
CSV_PATH = Path(__file__).parent.parent / "data" / "inventory.csv"
OUTPUTS_DIR = Path(__file__).parent.parent / "outputs"
TRACES_DIR = Path(__file__).parent.parent / "traces"

# Make sure directories exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
TRACES_DIR.mkdir(parents=True, exist_ok=True)

class RunSession:
    def __init__(self, question):
        self.question = question
        self.log_queue = queue.Queue()
        self.stdin_queue = queue.Queue()
        self.status = "running"
        self.result = None
        self.thread = None

active_session = None
session_lock = threading.Lock()

class WebStdinRedirect:
    def __init__(self, session, original_stdin):
        self.session = session
        self.original_stdin = original_stdin

    def readline(self):
        # Notify the UI that we are waiting for input
        self.session.log_queue.put("__WAITING_FOR_INPUT__\n")
        # Block until the user sends input
        user_input = self.session.stdin_queue.get()
        # Log it so the user sees it in the stream
        self.session.log_queue.put(f"[User Response]: {user_input}\n")
        return user_input

    def fileno(self):
        return self.original_stdin.fileno()

class WebStdoutRedirect:
    def __init__(self, session, original_stdout):
        self.session = session
        self.original_stdout = original_stdout

    def write(self, text):
        self.original_stdout.write(text)
        self.session.log_queue.put(text)

    def flush(self):
        self.original_stdout.flush()

    def fileno(self):
        return self.original_stdout.fileno()

class WebStderrRedirect:
    def __init__(self, session, original_stderr):
        self.session = session
        self.original_stderr = original_stderr

    def write(self, text):
        self.original_stderr.write(text)
        self.session.log_queue.put(text)

    def flush(self):
        self.original_stderr.flush()

    def fileno(self):
        return self.original_stderr.fileno()

def run_crew_thread(session):
    original_stdout = sys.stdout
    original_stderr = sys.stderr
    original_stdin = sys.stdin

    sys.stdout = WebStdoutRedirect(session, original_stdout)
    sys.stderr = WebStderrRedirect(session, original_stderr)
    sys.stdin = WebStdinRedirect(session, original_stdin)

    try:
        from crew.crew import run_crew
        session.result = run_crew(session.question)
        session.status = "completed"
    except Exception as e:
        session.log_queue.put(f"\n[Execution Error]: {str(e)}\n")
        session.status = "failed"
    finally:
        sys.stdout = original_stdout
        sys.stderr = original_stderr
        sys.stdin = original_stdin
        # Send sentinel
        session.log_queue.put(None)

class RunRequest(BaseModel):
    question: str

class FeedbackRequest(BaseModel):
    input: str

def check_mcp_status() -> bool:
    """Helper to check if the core MCP server is running on port 8000."""
    try:
        with socket.create_connection(("127.0.0.1", 8000), timeout=0.5):
            return True
    except OSError:
        return False

@app.get("/api/mcp-status")
def get_mcp_status():
    return {"online": check_mcp_status()}

@app.post("/api/run")
def start_run(req: RunRequest):
    global active_session
    # Reload environment variables dynamically to pick up edits on the fly
    load_dotenv(override=True)
    with session_lock:
        if active_session and active_session.status == "running":
            raise HTTPException(status_code=400, detail="An operations research session is already running.")
        
        # Check if the GROQ_API_KEY is configured
        if not os.getenv("GROQ_API_KEY"):
            raise HTTPException(
                status_code=400, 
                detail="GROQ_API_KEY is missing from environment. Please add it to your .env file."
            )
            
        active_session = RunSession(req.question)
        active_session.thread = threading.Thread(target=run_crew_thread, args=(active_session,))
        active_session.thread.daemon = True
        active_session.thread.start()
        
        return {"status": "started", "question": req.question}

@app.post("/api/human-input")
def send_human_input(req: FeedbackRequest):
    global active_session
    if not active_session or active_session.status != "running":
        raise HTTPException(status_code=400, detail="No active running session to send input to.")
    
    # Push input into stdin queue
    text = req.input
    if not text.endswith("\n"):
        text += "\n"
    active_session.stdin_queue.put(text)
    return {"status": "received"}

@app.get("/api/stream")
def get_stream():
    def event_generator():
        global active_session
        if not active_session:
            yield "data: No active session\n\n"
            return

        while True:
            try:
                log_item = active_session.log_queue.get(timeout=30)
                if log_item is None:
                    yield f"data: __FINISHED__:{active_session.status}:{active_session.result or ''}\n\n"
                    break
                for line in log_item.splitlines():
                    yield f"data: {line}\n"
                yield "\n" # end of chunk
            except queue.Empty:
                # keep alive ping
                yield "data: __PING__\n\n"
            except Exception as e:
                yield f"data: Stream error: {str(e)}\n\n"
                break

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@app.get("/api/documents")
def list_documents():
    docs = []
    if DATA_DIR.exists():
        for file in DATA_DIR.glob("*.txt"):
            try:
                content = file.read_text(encoding="utf-8")
                docs.append({
                    "name": file.name,
                    "content": content,
                    "size": file.stat().st_size,
                    "updated_at": datetime.fromtimestamp(file.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                })
            except Exception as e:
                docs.append({"name": file.name, "error": str(e)})
    return docs

@app.get("/api/inventory")
def list_inventory():
    records = []
    if CSV_PATH.exists():
        try:
            with open(CSV_PATH, newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    records.append(row)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error reading inventory CSV: {str(e)}")
    else:
        raise HTTPException(status_code=404, detail="Inventory CSV not found")
    return records

@app.get("/api/reports")
def list_reports():
    reports = []
    if OUTPUTS_DIR.exists():
        for file in OUTPUTS_DIR.glob("*.md"):
            try:
                content = file.read_text(encoding="utf-8")
                reports.append({
                    "name": file.name,
                    "content": content,
                    "created_at": datetime.fromtimestamp(file.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                })
            except Exception as e:
                pass
    # Sort reports by creation time, newest first
    reports.sort(key=lambda x: x["created_at"], reverse=True)
    return reports

@app.get("/api/traces")
def list_traces():
    traces = []
    if TRACES_DIR.exists():
        for file in TRACES_DIR.glob("*.txt"):
            try:
                content = file.read_text(encoding="utf-8")
                traces.append({
                    "name": file.name,
                    "content": content,
                    "created_at": datetime.fromtimestamp(file.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                })
            except Exception as e:
                pass
    for file in TRACES_DIR.glob("*.md"):
        try:
            content = file.read_text(encoding="utf-8")
            traces.append({
                "name": file.name,
                "content": content,
                "created_at": datetime.fromtimestamp(file.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
            })
        except Exception as e:
            pass
    traces.sort(key=lambda x: x["created_at"], reverse=True)
    return traces

# Serve Frontend static files
web_dir = Path(__file__).parent / "web"
web_dir.mkdir(parents=True, exist_ok=True)
app.mount("/", StaticFiles(directory=web_dir, html=True), name="web")

if __name__ == "__main__":
    import uvicorn
    # Start web server on port 8080
    uvicorn.run("web_server:app", host="0.0.0.0", port=8080, reload=False)
