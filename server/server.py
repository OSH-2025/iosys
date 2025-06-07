from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import OpenAI
import os
from fastapi.responses import Response

from ..jfs import IOSYSFileSystem
from ..agent.app import FileManagerApp
from ..agent.config import AgentConfig
from ..rag import IOSYSRAG

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
llm = OpenAI(
    base_url=os.environ.get("LLM_BASE_URL"),
    api_key=os.environ.get("LLM_API_KEY"),
)

fs = IOSYSFileSystem()

rag = IOSYSRAG(fs=fs)

agent_config = AgentConfig(fs=fs)
file_manager = FileManagerApp(agent_config)


@app.post("/status")
async def status_endpoint():
    return {
        "server": "ready",
        "rag": "ready",
        "llm": MODEL,
        "fs": "ready" if fs.service.is_running() else "error",
        "agent": "ready",
    }


class ChatRequest(BaseModel):
    input: str


@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    try:
        # Use OpenAI SDK to get a response
        completion = llm.chat.completions.create(
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
async def list_files(request: dict = None, id: str = ""):
    """List files and directories in the agent's managed directory"""
    try:
        # Handle both GET and POST requests
        if request and "id" in request:
            id = request["id"] or ""

        items = []
        for item in fs.get_dir_node(id).children():
            items.append(item.to_dict())

        return {"items": sorted(items, key=lambda x: (x["type"] == "file", x["name"]))}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/graph")
@app.post("/graph")
async def graph_endpoint():
    """Get the current state of the file management graph"""
    return rag.graph.dump()


class PreviewRequest(BaseModel):
    id: str


@app.post("/preview")
async def preview_endpoint(request: PreviewRequest):
    return {
        "url": f"http://localhost:8000/raw?fileid={request.id}",
    }


@app.get("/raw")
async def raw_endpoint(fileid: str):
    node = fs.get_file_node(fileid)
    if not node:
        raise HTTPException(status_code=404, detail="File not found")

    return Response(
        media_type="application/octet-stream",
        content=node.read(),
    )
