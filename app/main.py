from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import router
import uvicorn
import os
from fastapi.responses import FileResponse
from app.core.config import settings

app = FastAPI(
    title="AI Table Extractor API",
    description="API to extract tables from images using configurable AI agents",
    version="1.0.0",
)

app.include_router(router, prefix="/api/v1")

if settings.CORS_ALLOW_ORIGINS.strip():
    allow_origins = [
        origin.strip()
        for origin in settings.CORS_ALLOW_ORIGINS.split(",")
        if origin.strip()
    ]
    if allow_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=allow_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )


@app.get("/")
def health_check():
    return {"status": "ok", "message": "Service is running"}


@app.get("/ui")
def quick_ui():
    ui_path = os.path.join(os.path.dirname(__file__), "ui", "index.html")
    return FileResponse(ui_path)


@app.get("/ui/settings")
def ui_settings():
    ui_path = os.path.join(os.path.dirname(__file__), "ui", "settings.html")
    return FileResponse(ui_path)


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
