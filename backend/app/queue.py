from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime
from typing import Any

from fastapi import HTTPException
from redis.asyncio import Redis

from .config import settings
from .db import SessionLocal
from .models import QueueJob

log = logging.getLogger(__name__)
QUEUE_KEY = "ozon-admin:jobs"

_redis: Redis | None = None
_worker_task: asyncio.Task | None = None


def _now() -> datetime:
    return datetime.utcnow()


async def get_redis() -> Redis:
    global _redis
    if _redis is None:
        _redis = Redis.from_url(settings.redis_url, decode_responses=True)
    return _redis


async def ping() -> bool:
    try:
        return bool(await (await get_redis()).ping())
    except Exception:
        return False


async def depth() -> int:
    try:
        return int(await (await get_redis()).llen(QUEUE_KEY))
    except Exception:
        return 0


def _load_job(job_id: str) -> QueueJob | None:
    db = SessionLocal()
    try:
        return db.get(QueueJob, job_id)
    finally:
        db.close()


def _save_job(job_id: str, **fields: Any) -> QueueJob | None:
    db = SessionLocal()
    try:
        row = db.get(QueueJob, job_id)
        if row is None:
            return None
        for key, value in fields.items():
            setattr(row, key, value)
        row.updated_at = _now()
        db.commit()
        db.refresh(row)
        return row
    finally:
        db.close()


async def _handle(kind: str, payload: dict[str, Any]) -> dict[str, Any]:
    from . import ozon
    from .translator import pick, translate_zh_to_ru

    db = SessionLocal()
    try:
        if kind == "translate_listing":
            mapping = await translate_zh_to_ru(
                db,
                [payload.get("name") or "", payload.get("description") or ""],
                "zh-ru-listing",
            )
            return {
                "name_ru": pick(mapping, payload.get("name") or ""),
                "description_ru": pick(mapping, payload.get("description") or ""),
            }
        if kind == "create_product":
            return await ozon.create_product(db, payload)
        if kind == "copy_product":
            return await ozon.copy_product(
                db,
                int(payload["product_id"]),
                payload.get("new_offer_id"),
                payload.get("price"),
            )
        if kind == "republish_product":
            return await ozon.republish_product(
                db,
                int(payload["product_id"]),
                payload.get("new_offer_id"),
                payload.get("name"),
                payload.get("price"),
            )
        if kind == "sync_products":
            return {"synced": await ozon.sync_products(db)}
        if kind == "sync_warehouses":
            return {"synced": await ozon.sync_warehouses(db)}
        raise ValueError(f"未知任务类型：{kind}")
    finally:
        db.close()


async def execute_job(job_id: str) -> None:
    row = _load_job(job_id)
    if row is None or row.status not in {"pending", "running"}:
        return
    _save_job(job_id, status="running")
    try:
        result = await _handle(row.kind, json.loads(row.payload_json or "{}"))
        _save_job(job_id, status="success", result_json=json.dumps(result, ensure_ascii=False), error="")
    except Exception as exc:
        log.exception("队列任务失败 %s", job_id)
        _save_job(job_id, status="failed", error=str(exc)[:2000])


async def submit(kind: str, payload: dict[str, Any]) -> str:
    db = SessionLocal()
    job_id = uuid.uuid4().hex
    try:
        db.add(
            QueueJob(
                id=job_id,
                kind=kind,
                status="pending",
                payload_json=json.dumps(payload, ensure_ascii=False),
            )
        )
        db.commit()
    finally:
        db.close()
    try:
        await (await get_redis()).lpush(QUEUE_KEY, job_id)
    except Exception as exc:
        log.warning("Redis 不可用，改为进程内执行：%s", exc)
        asyncio.create_task(execute_job(job_id))
    return job_id


async def wait_job(job_id: str, timeout: float = 60) -> dict[str, Any]:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        row = _load_job(job_id)
        if row and row.status == "success":
            return json.loads(row.result_json or "{}")
        if row and row.status == "failed":
            raise HTTPException(status_code=502, detail=row.error or "后台任务失败")
        await asyncio.sleep(0.2)
    raise HTTPException(status_code=504, detail="后台任务超时，请稍后在任务列表查看")


async def submit_and_wait(kind: str, payload: dict[str, Any], timeout: float = 60) -> dict[str, Any]:
    job_id = await submit(kind, payload)
    result = await wait_job(job_id, timeout=timeout)
    result["job_id"] = job_id
    return result


def get_job(job_id: str) -> QueueJob | None:
    return _load_job(job_id)


def list_jobs(limit: int = 50) -> list[QueueJob]:
    db = SessionLocal()
    try:
        return db.query(QueueJob).order_by(QueueJob.created_at.desc()).limit(limit).all()
    finally:
        db.close()


async def worker_loop() -> None:
    redis = await get_redis()
    log.info("队列 worker 已连接 %s", settings.redis_url)
    while True:
        try:
            item = await redis.brpop(QUEUE_KEY, timeout=2)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            log.warning("读取 Redis 队列失败：%s", exc)
            await asyncio.sleep(1)
            continue
        if not item:
            continue
        _, job_id = item
        await execute_job(job_id)


async def start() -> None:
    global _worker_task
    if not settings.queue_embedded:
        return
    if _worker_task and not _worker_task.done():
        return
    _worker_task = asyncio.create_task(worker_loop(), name="ozon-queue-worker")


async def stop() -> None:
    global _worker_task, _redis
    if _worker_task:
        _worker_task.cancel()
        try:
            await _worker_task
        except asyncio.CancelledError:
            pass
        _worker_task = None
    if _redis is not None:
        await _redis.aclose()
        _redis = None
