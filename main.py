import uvicorn
from dotenv import load_dotenv
import subprocess
import sys

def main():
    subprocess.Popen([sys.executable, "./a2a_server/main.py"], shell=True)
    print("Starting FastAPI server...")
    uvicorn.run("server:app", host="localhost", port=8000, reload=True)

if __name__ == "__main__":
    load_dotenv()
    main()
