from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from src.shared.db import init_db
from src.api.routes import chat, stats, admin, summary

app = FastAPI(title="Blinkit Discovery Engine API")

# Setup CORS
# Allowing localhost for local development, and assuming Vercel frontend in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "https://ai-powered-discovery-engine-blinkit.vercel.app"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"message": "Internal Server Error", "details": str(exc)},
    )

@app.on_event("startup")
async def startup_event():
    init_db()

app.include_router(chat.router, prefix="/api")
app.include_router(stats.router, prefix="/api")
app.include_router(summary.router, prefix="/api")
app.include_router(admin.router, prefix="/api/admin")
