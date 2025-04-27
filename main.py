import uvicorn

def main():
    print("Starting FastAPI server...")
    uvicorn.run("server:app", host="localhost", port=8000, reload=True)

if __name__ == "__main__":
    main()
