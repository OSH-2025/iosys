from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import OpenAI
import os
from fastapi.responses import FileResponse
from pathlib import Path
from agent.src.app import FileManagerApp
from agent.src.config import AgentConfig

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict to localhost
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MODEL = os.environ.get("LLM_MODEL_NAME")

client = OpenAI(
    base_url=os.environ.get("LLM_BASE_URL"),
    api_key=os.environ.get("LLM_API_KEY"),
)

# Initialize Agent
agent_base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))
os.makedirs(agent_base_dir, exist_ok=True)
agent_config = AgentConfig(base_dir=agent_base_dir)
file_manager = FileManagerApp(agent_config)


@app.post("/status")
async def status_endpoint():
    return {
        "server": "ready",
        "rag": "ready",
        "llm": MODEL,
        "fs": "ready",
        "agent": "ready",
    }


class ChatRequest(BaseModel):
    input: str


@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    try:
        # Use OpenAI SDK to get a response
        completion = client.chat.completions.create(
            extra_body={},
            model=MODEL,
            messages=[
                {
                    "role": "developer",
                    "content": "Talk like a pirate.",
                },
                {
                    "role": "user",
                    "content": request.input,
                },
            ],
        )
        return {"response": completion.choices[0].message.content}
    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class AgentRequest(BaseModel):
    command: str


@app.post("/agent")
async def agent_endpoint(request: AgentRequest):
    """Process natural language file management commands"""
    try:
        result = file_manager.process_command(request.command)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/files")
@app.post("/files")
async def list_files(request: dict = None, path: str = ""):
    """List files and directories in the agent's managed directory"""
    try:
        # Handle both GET and POST requests
        if request and 'path' in request:
            path = request['path'] or ""
        
        target_path = Path(agent_base_dir) / path
        if not target_path.exists() or not str(target_path).startswith(agent_base_dir):
            raise HTTPException(status_code=404, detail="Path not found")

        items = []
        for item in target_path.iterdir():
            relative_path = str(item.relative_to(agent_base_dir))
            items.append(
                {
                    "name": item.name,
                    "path": relative_path,
                    "type": "directory" if item.is_dir() else "file",
                    "size": item.stat().st_size if item.is_file() else None,
                }
            )

        return {"items": sorted(items, key=lambda x: (x["type"] == "file", x["name"]))}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class PreviewRequest(BaseModel):
    id: str


@app.post("/preview")
async def preview_endpoint(request: PreviewRequest):
    # Support both absolute paths and relative paths from agent directory
    if os.path.isabs(request.id):
        filepath = request.id
    else:
        filepath = os.path.join(agent_base_dir, request.id)

    return {
        "url": f"http://localhost:8000/raw?filepath={filepath}",
    }


@app.get("/raw")
async def raw_endpoint(filepath: str):
    # Security check: ensure file is within allowed directories
    abs_filepath = os.path.abspath(filepath)
    if not (
        abs_filepath.startswith(agent_base_dir)
        or abs_filepath.startswith(os.path.abspath("."))
    ):
        raise HTTPException(status_code=403, detail="Access denied")

    if not os.path.exists(abs_filepath):
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(abs_filepath)
