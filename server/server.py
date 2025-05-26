from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import OpenAI
import os
from fastapi.responses import FileResponse

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

@app.post("/status")
async def status_endpoint():
    return {
        "server": "ready",
        "rag": "ready",
        "llm": MODEL,
        "fs": "ready",
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


class PreviewRequest(BaseModel):
    id: str

@app.post("/preview")
async def preview_endpoint(request: PreviewRequest):
    return {
        "url": f"http://localhost:8000/raw?filepath={request.id}",
    }

# GET /raw?filepath={filepath}
@app.get("/raw")
async def raw_endpoint(filepath: str):
    return FileResponse(filepath, media_type='image/png')
