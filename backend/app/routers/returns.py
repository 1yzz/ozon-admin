from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from .. import ozon
from ..db import get_db
from ..schemas import ReturnOut, ReturnPageOut
from ..translator import enum_label

router = APIRouter(prefix="/api/returns", tags=["returns"])


def _in_group(item: dict, group: str) -> bool:
    if group == "all":
        return True
    group_state = str(item.get("group_state") or "").casefold()
    blob = f"{group_state} {item.get('status') or ''} {item.get('status_sys') or ''} {item.get('type') or ''}".casefold()
    if group == "in_transit":
        if group_state in {"delivering", "moving", "on_the_way", "ontheway"}:
            return True
        return any(
            key in blob
            for key in (
                "途",
                "transit",
                "ontheway",
                "on_the_way",
                "onwaytoozon",
                "going",
                "moving",
                "delivering",
                "в пути",
                "в_пути",
            )
        )
    if group == "utilization":
        if group_state in {"utilization", "utilizing", "utilized"}:
            return True
        return any(
            key in blob
            for key in (
                "销毁",
                "核销",
                "utiliz",
                "writeoff",
                "write_off",
                "destroy",
                "disposal",
                "утилиз",
                "списан",
            )
        )
    return True


@router.get("", response_model=ReturnPageOut)
async def list_returns(
    days: int = Query(30, ge=1, le=90),
    schema: str = Query("FBS"),
    group: str = Query("all"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=5, le=100),
    db: Session = Depends(get_db),
) -> ReturnPageOut:
    items = await ozon.list_returns(db, days=days, schema=schema)
    items = [item for item in items if _in_group(item, group)]
    items.sort(key=lambda item: item.get("status_at") or item.get("return_date") or "", reverse=True)
    page_items, total = ozon.paginate(items, page, page_size)
    return ReturnPageOut(
        page=page,
        page_size=page_size,
        total=total,
        items=[_return_out(item) for item in page_items],
    )


def _return_out(item: dict) -> ReturnOut:
    data = dict(item)
    data["type_label"] = enum_label(data.get("type")) or data.get("type") or ""
    data["status"] = enum_label(data.get("status")) or data.get("status") or ""
    data["mode"] = data.get("mode") or data.get("schema") or "realFBS"
    return ReturnOut(**data)
