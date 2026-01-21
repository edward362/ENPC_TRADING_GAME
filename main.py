# app/main.py (or main.py at the project root)
# This file creates the FastAPI application, loads routes, serves the UI,
# and registers the WebSocket endpoint for the trading game.

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

# REST routes for your normal HTTP API
from api.routes import router as api_router

# WebSocket endpoint (the async function websockets/endpoints.py)
from websockets.endpoints import ws_endpoint

# Create the main FastAPI application
app = FastAPI(title="Multiplayer Trading Game", version="2.0")

# Base directories
BASE_DIR = Path(__file__).parent
UI_DIR = BASE_DIR / "ui"

# ---------------------------------------------------------
# CORS SETTINGS
# ---------------------------------------------------------
# CORS allows browsers from any domain to access this backend.
# This is required so the frontend (index.html) can talk to the server.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],     # Allow requests from ANY website
    allow_methods=["*"],     # Allow GET/POST/PUT/DELETE/etc.
    allow_headers=["*"],     # Allow all custom headers
)

# ---------------------------------------------------------
# SERVE THE FRONTEND UI (index.html)
# ---------------------------------------------------------
@app.get("/")
async def serve_ui():
    # Locate index.html inside the "ui" folder (next to this file)
    file_path = UI_DIR / "index.html"

    # Return the file with "no cache" headers so  browser always reloads it fresh
    return FileResponse(
        file_path,
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )

# ---------------------------------------------------------
# STATIC FILES: CSS & JS
# ---------------------------------------------------------
css_dir = UI_DIR / "css"
js_dir = UI_DIR / "js"

if css_dir.exists():
    app.mount("/css", StaticFiles(directory=css_dir), name="css")

if js_dir.exists():
    app.mount("/js", StaticFiles(directory=js_dir), name="js")

# ---------------------------------------------------------
# STATIC FILES (optional images)
# ---------------------------------------------------------
images_dir = BASE_DIR / "images"
if images_dir.exists():
    app.mount("/images", StaticFiles(directory=images_dir), name="images")

# ---------------------------------------------------------
# REST API ROUTES
# ---------------------------------------------------------
# This loads normal HTTP endpoints under the prefix /api
app.include_router(api_router)

# ---------------------------------------------------------
# WEBSOCKET ENDPOINT
# ---------------------------------------------------------
# Attach the WebSocket handler at URL: /ws
# This is where players connect for real-time gameplay
app.websocket("/ws")(ws_endpoint)

# ---------------------------------------------------------
# HEALTHCHECK
# ---------------------------------------------------------
# Simple endpoint to verify the server is running
@app.get("/health")
async def health():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=5001, reload=True, ws="wsproto")
