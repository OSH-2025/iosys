import uvicorn
from dotenv import load_dotenv
import os


def start_server():
    print("Starting server...")
    uvicorn.run(
        "server.server:app",
        host="localhost",
        port=int(os.environ["MAIN_SERVER_PORT"]),
        reload=True,
    )


if __name__ == "__main__":
    load_dotenv()
    start_server()
