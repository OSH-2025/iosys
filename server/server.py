from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, File, UploadFile, Form
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
knowledge_graph = IOSYSKnowledgeGraph(llm=llm, fs=fs, chunk_size=400)

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict to localhost
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/status")
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


class AgentRequest(BaseModel):
    command: str
    session_id: str


@app.post("/agent/run")
async def agent_run_endpoint(request: AgentRequest):
    """Process natural language file management commands"""
    return await agent.process_command(request.command, request.session_id)


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


@app.post("/mcp/sync")
async def sync_mcp_server(request: MCPServerRequest):
    await agent.mcp.sync_config(request.config)


@app.get("/mcp/config")
@app.post("/mcp/config")
async def get_mcp_config():
    """Get current MCP configuration"""
    return agent.mcp.get_config()


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


class KgContentRequest(BaseModel):
    path: str


@app.post("/kg/content")
async def kg_content_endpoint(request: KgContentRequest):
    node = fs.get_node(request.path)
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    return knowledge_graph.get_result(node)


class FsDeleteRequest(BaseModel):
    path: str


@app.post("/fs/delete")
async def fs_delete_endpoint(request: FsDeleteRequest):
    node = fs.get_node(request.path)
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    node.remove()


@app.post("/fs/upload")
async def fs_upload_endpoint(
    files: list[UploadFile] = File(...), path: str = Form(...)
):
    try:
        uploaded_files = []

        for file in files:
            # Read file content
            content = await file.read()

            # Construct the full file path by combining directory path with filename
            file_path = f"{path.rstrip('/')}/{file.filename}"

            if fs.get_node(file_path) is not None:
                raise HTTPException(
                    status_code=400,
                    detail=f"File {file.filename} already exists at {file_path}",
                )

            # Create the file node at the specified path
            fs.write_file(file_path, content)

            uploaded_files.append(
                {"filename": file.filename, "path": file_path, "size": len(content)}
            )

        return {
            "success": True,
            "uploaded_files": uploaded_files,
            "total_files": len(uploaded_files),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")
