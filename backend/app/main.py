from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from sqlalchemy import text

from . import models, queue
from .config import settings
from .db import Base, engine
from .routers import dashboard, orders, products, queue as queue_router, returns
from .routers import settings as settings_router
from .routers import uploads, warehouses

_ = models
Base.metadata.create_all(bind=engine)
with engine.begin() as conn:
    conn.execute(text("DROP TABLE IF EXISTS competitor_leads"))
settings.upload_path


@asynccontextmanager
async def lifespan(_app: FastAPI):
    await queue.start()
    try:
        yield
    finally:
        await queue.stop()


app = FastAPI(title="Ozon Admin", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(settings_router.router)
app.include_router(dashboard.router)
app.include_router(products.router)
app.include_router(orders.router)
app.include_router(returns.router)
app.include_router(warehouses.router)
app.include_router(uploads.router)
app.include_router(queue_router.router)
app.mount("/uploads/products", StaticFiles(directory=settings.upload_path), name="uploads")


@app.get("/api/health")
async def health() -> dict:
    redis_ok = await queue.ping()
    return {"ok": True, "redis": redis_ok, "queue_depth": await queue.depth() if redis_ok else None}
