from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import OpenAI
import os
from fastapi.responses import Response

from jfs import new_fs
from agent.app import FileManagerApp
from agent.config import AgentConfig
from rag import IOSYSRAG

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict to localhost
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MODEL = os.environ["LLM_MODEL_NAME"]
llm = OpenAI(
    base_url=os.environ["LLM_BASE_URL"],
    api_key=os.environ["LLM_API_KEY"],
)

fs = new_fs()
rag = IOSYSRAG(fs=fs)
file_manager = FileManagerApp(AgentConfig(llm=llm, fs=fs, rag=rag))


@app.post("/status")
async def status_endpoint():
    return {
        "server": "ready",
        "rag": "ready",
        "llm": MODEL,
        "fs": "ready" if fs.is_running() else "error",
        "agent": "ready",
        "graph_revision": rag.graph.revision,
    }


class ChatRequest(BaseModel):
    input: str


@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
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


class AgentRequest(BaseModel):
    command: str


@app.post("/agent")
async def agent_endpoint(request: AgentRequest):
    """Process natural language file management commands"""
    return await file_manager.process_command(request.command)


@app.get("/files")
@app.post("/files")
async def list_files(request: dict | None, id: str = ""):
    """List files and directories in the agent's managed directory"""
    # Handle both GET and POST requests
    if request and "id" in request:
        id = request["id"] or ""

    node = fs.get_node(id)
    if not node:
        raise HTTPException(status_code=404, detail="Directory not found")

    items = []
    for item in node.children():
        items.append(item.to_dict())

    return {"items": sorted(items, key=lambda x: (x["type"] == "file", x["name"]))}


@app.get("/graph")
@app.post("/graph")
async def graph_endpoint():
    """Get the current state of the file management graph"""
    return rag.graph.to_dict()


class PreviewRequest(BaseModel):
    id: str


@app.post("/preview")
async def preview_endpoint(request: PreviewRequest):
    return {
        "url": f"http://localhost:8000/raw?fileid={request.id}",
    }


@app.get("/raw")
async def raw_endpoint(fileid: str):
    node = fs.get_node(fileid)
    if not node:
        raise HTTPException(status_code=404, detail="File not found")

    return Response(
        media_type="application/octet-stream",
        content=node.read(),
    )
