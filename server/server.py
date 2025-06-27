from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import OpenAI, AsyncOpenAI
import os
from fastapi.responses import Response

from fs import new_fs
from agent import IOSYSAgent
from agent.config import AgentConfig
from parser import IOSYSParser
from rag import IOSYSRAG
from rag.knowledge_graph import IOSYSKnowledgeGraph
from utils.logger import all_logs

from .preview import render_preview_html


load_dotenv()

MODEL = os.environ["LLM_MODEL_NAME"]
llm = OpenAI(
    base_url=os.environ["LLM_BASE_URL"],
    api_key=os.environ["LLM_API_KEY"],
)

fs = new_fs()
parser = IOSYSParser(llm=llm)
rag = IOSYSRAG(fs=fs, parser=parser)
agent = IOSYSAgent(AgentConfig(llm=llm, fs=fs, rag=rag))

async_llm = AsyncOpenAI(
    base_url=os.environ["LLM_BASE_URL"],
    api_key=os.environ["LLM_API_KEY"],
)
knowledge_graph = IOSYSKnowledgeGraph(llm=async_llm, chunk_size=400)

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict to localhost
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/status")
async def status_endpoint():
    return {
        "server": "ready",
        "rag": "ready",
        "llm": MODEL,
        "fs": "ready" if fs.is_running() else "error",
        "agent": "ready",
        "graph_revision": rag.graph.revision,
        "mcp_servers": agent.mcp.get_status(),
        "knowledge_graph": knowledge_graph.status_dict(),
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
    return await agent.process_command(request.command)


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
    path: str


@app.post("/preview")
async def preview_endpoint(request: PreviewRequest):
    return render_preview_html(fs, request.path)


@app.get("/raw")
async def raw_endpoint(path: str):
    node = fs.get_node(path)
    if not node:
        raise HTTPException(status_code=404, detail="File not found")

    return Response(
        headers={
            "Content-Disposition": f'attachment; filename="{node.name}"',
        },
        media_type="application/octet-stream",
        content=node.read(),
    )


class MCPServerRequest(BaseModel):
    config: dict


@app.post("/mcp")
async def sync_mcp_server(request: MCPServerRequest):
    await agent.mcp.sync_config(request.config)


@app.post("/logs")
async def logs_endpoint():
    return [log.to_dict() for log in all_logs]


class KgSpawnRequest(BaseModel):
    path: str


@app.post("/kg/spawn")
async def kg_endpoint(request: KgSpawnRequest):
    node = fs.get_node(request.path)
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    knowledge_graph.spawn_task(node)


class KgGetContentRequest(BaseModel):
    path: str


@app.post("/kg/content")
async def update_kg_endpoint(request: KgGetContentRequest):
    node = fs.get_node(request.path)
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    return knowledge_graph.get_result(node)
