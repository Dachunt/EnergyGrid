from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import metrics, districts
from app.websocket_manager import router as ws_router
from app.db import init_db, close_db

app = FastAPI(title="EnergyGrid Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(metrics.router)
app.include_router(districts.router)
app.include_router(ws_router)

@app.on_event("startup")
async def startup():
    await init_db(app)

@app.on_event("shutdown")
async def shutdown():
    await close_db(app)

@app.get("/health")
async def health():
    return {"status": "ok"}
