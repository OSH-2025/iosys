from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import OpenAI
import os

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict to localhost
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Define the request body model
class ChatRequest(BaseModel):
    text: str


client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ.get("OPEN_ROUTER_API_KEY"),
)


@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    try:
        # Use OpenAI SDK to get a response
        completion = client.chat.completions.create(
            extra_headers={
                "HTTP-Referer": "<YOUR_SITE_URL>",  # Optional. Site URL for rankings on openrouter.ai.
                "X-Title": "<YOUR_SITE_NAME>",  # Optional. Site title for rankings on openrouter.ai.
            },
            extra_body={},
            model="google/gemini-2.0-flash-001",
            messages=[
                {
                    "role": "developer",
                    "content": "Talk like a pirate.",
                },
                {
                    "role": "user",
                    "content": request.text,
                },
            ],
        )
        return {"response": completion.choices[0].message.content}
    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
