from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import openai

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost"],  # Restrict to localhost
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Define the request body model
class ChatRequest(BaseModel):
    text: str

# Set up OpenAI API key
openai.api_key = "your-openai-api-key"

@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    try:
        # Use OpenAI SDK to get a response
        response = openai.Completion.create(
            engine="text-davinci-003",
            prompt=request.text,
            max_tokens=150
        )
        return {"response": response.choices[0].text.strip()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
