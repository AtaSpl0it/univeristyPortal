import uvicorn
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.core.database import Base, engine
from app.api.endpoints import router as api_router

# Initialize database
Base.metadata.create_all(bind=engine)

app = FastAPI(title="SAS University Portal")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount the API routes
app.include_router(api_router, prefix="/api")

# --- PATH RESOLUTION ---
# 1. Get the directory where main.py lives (the 'app' folder)
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

# 2. Go up one level to the root directory
ROOT_DIR = os.path.dirname(CURRENT_DIR)

# 3. Target the frontend directory
FRONTEND_DIR = os.path.join(ROOT_DIR, "frontend")

# Mount the static directories so the HTML files can find their assets
app.mount("/css", StaticFiles(directory=os.path.join(FRONTEND_DIR, "css")), name="css")
app.mount("/js", StaticFiles(directory=os.path.join(FRONTEND_DIR, "js")), name="js")
app.mount("/pages", StaticFiles(directory=os.path.join(FRONTEND_DIR, "pages")), name="pages")

# Serve the root index.html file specifically
@app.get("/")
async def serve_index():
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=3000, reload=True)
