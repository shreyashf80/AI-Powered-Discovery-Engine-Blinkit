from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.shared.db import init_db
from src.api.routes import chat, stats, admin

app = FastAPI(title="Blinkit Discovery Engine API")

# Setup CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    init_db()

app.include_router(chat.router, prefix="/api")
app.include_router(stats.router, prefix="/api")
app.include_router(admin.router, prefix="/api/admin")
