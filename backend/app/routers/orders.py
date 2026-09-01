from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from .. import ozon
from ..db import get_db
from ..schemas import OrderOut, OrderPageOut
from ..translator import enum_label

router = APIRouter(prefix="/api/orders", tags=["orders"])


@router.get("", response_model=OrderPageOut)
async def list_orders(
    cancelled: bool = Query(False),
    days: int = Query(30, ge=1, le=90),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=5, le=100),
    db: Session = Depends(get_db),
) -> OrderPageOut:
    items = await ozon.list_orders(db, cancelled_only=cancelled, days=days)
    if cancelled:
        items = [
            item
            for item in items
            if str(item.get("status", "")).lower() == "cancelled" or item.get("cancel_reason")
        ]
    page_items, total = ozon.paginate(items, page, page_size)
    return OrderPageOut(
        page=page,
        page_size=page_size,
        total=total,
        items=[_order_out(item) for item in page_items],
    )


@router.get("/{posting_number}", response_model=OrderOut)
async def get_order(posting_number: str, db: Session = Depends(get_db)) -> OrderOut:
    return _order_out(await ozon.get_order(db, posting_number))


def _order_out(item: dict) -> OrderOut:
    data = dict(item)
    data["status"] = enum_label(data.get("status"))
    data["substatus"] = enum_label(data.get("substatus"))
    data["cancellation_initiator"] = enum_label(data.get("cancellation_initiator"))
    data["cancellation_type"] = enum_label(data.get("cancellation_type"))
    return OrderOut(**data)
