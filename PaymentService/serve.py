import uvicorn

if __name__ == "__main__":
    # Run the FastAPI app with reload for local development
    uvicorn.run("main:app", host="0.0.0.0", port=8104, reload=True)
