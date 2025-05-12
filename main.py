import uvicorn
from dotenv import load_dotenv
import subprocess
import sys
import os

def start_main_server():
    print("Starting main server...")
    uvicorn.run(
        "server.server:app",
        host="localhost",
        port=int(os.getenv("MAIN_SERVER_PORT")),
        reload=True,
    )

def start_a2a_server():
    print("Starting A2A server...")
    subprocess.Popen([sys.executable, "./a2a_server/main.py"], shell=True)

if __name__ == "__main__":
    load_dotenv()

    # start_a2a_server()
    start_main_server()
