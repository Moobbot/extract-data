from fastapi import FastAPI
from app.api.routes import router
import uvicorn

app = FastAPI(
    title="AI Table Extractor API",
    description="API to extract tables from images using Gemini or OpenAI",
    version="1.0.0",
)

app.include_router(router, prefix="/api/v1")


@app.get("/")
def health_check():
    return {"status": "ok", "message": "Service is running"}


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
