from fastapi import FastAPI
from app.api.routes import router
import uvicorn
import os
from fastapi.responses import FileResponse

app = FastAPI(
    title="AI Table Extractor API",
    description="API to extract tables from images using configurable AI agents",
    version="1.0.0",
)

app.include_router(router, prefix="/api/v1")


@app.get("/")
def health_check():
    return {"status": "ok", "message": "Service is running"}


@app.get("/ui")
def quick_ui():
    ui_path = os.path.join(os.path.dirname(__file__), "ui", "index.html")
    return FileResponse(ui_path)


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
