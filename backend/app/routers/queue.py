from fastapi import APIRouter, HTTPException

from .. import queue
from ..schemas import QueueJobOut

router = APIRouter(prefix="/api/queue", tags=["queue"])


@router.get("/jobs", response_model=list[QueueJobOut])
def list_jobs() -> list[QueueJobOut]:
    import json

    rows = []
    for row in queue.list_jobs():
        try:
            result = json.loads(row.result_json or "{}")
        except json.JSONDecodeError:
            result = {}
        rows.append(
            QueueJobOut(
                id=row.id,
                kind=row.kind,
                status=row.status,
                error=row.error,
                created_at=row.created_at,
                result=result if isinstance(result, dict) else {},
            )
        )
    return rows


@router.get("/jobs/{job_id}", response_model=QueueJobOut)
def get_job(job_id: str) -> QueueJobOut:
    import json

    row = queue.get_job(job_id)
    if row is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    try:
        result = json.loads(row.result_json or "{}")
    except json.JSONDecodeError:
        result = {}
    return QueueJobOut(
        id=row.id,
        kind=row.kind,
        status=row.status,
        error=row.error,
        created_at=row.created_at,
        result=result if isinstance(result, dict) else {},
    )
