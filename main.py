import uvicorn
from dotenv import load_dotenv
import subprocess
import sys

if __name__ == "__main__":
    load_dotenv()
    subprocess.Popen([sys.executable, "./a2a_server/main.py"], shell=True)
    print("Starting FastAPI server...")
    uvicorn.run(
        "server.server:app",
        ost="localhost",
        port=8000,
        reload=True,
    )
