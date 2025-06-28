import uvicorn
import multiprocessing
from dotenv import load_dotenv
import os


def start_main_server():
    print("Starting main server...")
    uvicorn.run(
        "server.server:app",
        host="localhost",
        port=int(os.environ["MAIN_SERVER_PORT"]),
        reload=True,
    )


def start_a2a_server():
    print("Starting A2A server...")
    uvicorn.run(
        "a2a_server.server:app",
        host="localhost",
        port=int(os.environ["A2A_SERVER_PORT"]),
        reload=True,
    )


if __name__ == "__main__":
    load_dotenv()

    processes = [
        multiprocessing.Process(target=start_main_server),
        # multiprocessing.Process(target=start_a2a_server),
    ]
    for process in processes:
        process.start()
    for process in processes:
        process.join()
