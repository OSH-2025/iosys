import uvicorn
from dotenv import load_dotenv
from a2a_server import start_a2a

def main():
    print("Starting A2A server...")
    start_a2a(host="localhost", port=8001)
    print("Starting FastAPI server...")
    uvicorn.run("server:app", host="localhost", port=8000, reload=True)

if __name__ == "__main__":
    load_dotenv()
    main()
