from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Product, Warehouse
from ..schemas import DashboardOut
from ..status import ProductStatus, is_removed, product_status

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("", response_model=DashboardOut)
def dashboard(db: Session = Depends(get_db)) -> DashboardOut:
    rows = db.query(Product).all()
    total = len(rows)
    archived = sum(1 for row in rows if row.is_archived)
    in_sale = sum(1 for row in rows if product_status(row) == ProductStatus.IN_SALE)
    removed = sum(1 for row in rows if is_removed(product_status(row)))
    red_price = sum(1 for row in rows if "RED" in (row.color_index or "").upper())
    yellow_price = sum(1 for row in rows if "YELLOW" in (row.color_index or "").upper())
    empty_stock = sum(1 for row in rows if not row.is_archived and row.stock_present == 0)
    last_sync = db.query(func.max(Product.synced_at)).scalar()
    warehouse_count = db.query(func.count(Warehouse.warehouse_id)).scalar() or 0
    return DashboardOut(
        product_total=total,
        in_sale=in_sale,
        archived=archived,
        removed=removed,
        red_price=red_price,
        yellow_price=yellow_price,
        empty_stock=empty_stock,
        warehouse_count=warehouse_count,
        last_sync=last_sync,
    )
