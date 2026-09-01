from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import queue
from ..db import get_db
from ..models import Warehouse
from ..schemas import WarehouseOut
from ..translator import enum_label

router = APIRouter(prefix="/api/warehouses", tags=["warehouses"])


@router.get("", response_model=list[WarehouseOut])
def list_warehouses(db: Session = Depends(get_db)) -> list[WarehouseOut]:
    rows = db.query(Warehouse).order_by(Warehouse.name.asc()).all()
    return [
        WarehouseOut(
            warehouse_id=row.warehouse_id,
            name=row.name,
            status=enum_label(row.status),
            warehouse_type=row.warehouse_type,
            is_rfbs=row.is_rfbs,
            address=row.address,
        )
        for row in rows
    ]


@router.post("/sync")
async def sync_warehouses() -> dict:
    return await queue.submit_and_wait("sync_warehouses", {}, timeout=60)
