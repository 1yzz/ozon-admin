from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from .. import ozon, queue
from ..db import get_db
from ..models import Product, ProductStock, RepublishJob
from ..schemas import (
    CategoryAttributeOut,
    CopyProductIn,
    CreateProductIn,
    PriceUpdateIn,
    ProductOut,
    RepublishIn,
    RepublishJobOut,
    StockUpdateIn,
    TranslateCopyIn,
)
from ..status import ProductStatus, is_removed, label, product_status
from ..translator import enum_label

router = APIRouter(prefix="/api/products", tags=["products"])


def _to_out(row: Product) -> ProductOut:
    code = product_status(row)
    return ProductOut(
        product_id=row.product_id,
        offer_id=row.offer_id,
        sku=row.sku,
        name=row.name,
        status=row.status,
        status_name=row.status_name,
        status_description=row.status_description,
        is_archived=row.is_archived,
        price=row.price,
        old_price=row.old_price,
        min_price=row.min_price,
        vat=row.vat,
        currency_code=row.currency_code,
        color_index=row.color_index,
        ozon_min_price=row.ozon_min_price,
        external_min_price=row.external_min_price,
        has_stock=row.has_stock,
        stock_present=row.stock_present,
        stock_reserved=row.stock_reserved,
        primary_image=row.primary_image,
        description_category_id=row.description_category_id,
        type_id=row.type_id,
        synced_at=row.synced_at,
        has_snapshot=bool(row.snapshot_json),
        status_code=code.value,
        status_label=label(code),
        is_removed=is_removed(code),
        color_index_label=enum_label(row.color_index),
    )


@router.get("", response_model=list[ProductOut])
def list_products(
    q: str = "",
    visibility: str = "ALL",
    color_index: str = "",
    db: Session = Depends(get_db),
) -> list[ProductOut]:
    query = db.query(Product)
    if q:
        like = f"%{q}%"
        query = query.filter(
            or_(
                Product.name.like(like),
                Product.offer_id.like(like),
                Product.status_name.like(like),
            )
        )
    if visibility == "ARCHIVED":
        query = query.filter(Product.is_archived.is_(True))
    elif visibility == "REMOVED":
        query = query.filter(
            Product.is_archived.is_(False),
            or_(
                Product.status_name.contains("Не продается"),
                Product.status_description.contains("Убран"),
                Product.status.ilike("%removed%"),
                Product.status.ilike("%ban%"),
            ),
        )
    elif visibility == "IN_SALE":
        query = query.filter(Product.is_archived.is_(False), Product.status_name == "Продается")
    if color_index:
        query = query.filter(Product.color_index.ilike(f"%{color_index}%"))
    rows = query.order_by(Product.synced_at.desc()).limit(2000).all()
    if visibility == "IN_SALE":
        rows = [row for row in rows if product_status(row) == ProductStatus.IN_SALE]
    elif visibility == "REMOVED":
        rows = [row for row in rows if is_removed(product_status(row))]
    return [_to_out(row) for row in rows]


@router.post("/sync")
async def sync_products() -> dict:
    return await queue.submit_and_wait("sync_products", {}, timeout=180)


@router.post("/create")
async def create_product_early(body: CreateProductIn) -> dict:
    return await queue.submit_and_wait("create_product", body.model_dump(), timeout=120)


@router.post("/translate")
async def translate_listing_early(body: TranslateCopyIn) -> dict:
    return await queue.submit_and_wait("translate_listing", body.model_dump(), timeout=60)


@router.get("/meta/categories")
async def categories(db: Session = Depends(get_db)) -> list[dict]:
    return await ozon.category_tree(db)


@router.get("/meta/attributes", response_model=list[CategoryAttributeOut])
async def attributes(
    description_category_id: int = Query(...),
    type_id: int = Query(...),
    db: Session = Depends(get_db),
) -> list[CategoryAttributeOut]:
    items = await ozon.category_attributes(db, description_category_id, type_id)
    return [
        CategoryAttributeOut(
            id=item.get("id"),
            name=item.get("name") or "",
            description=item.get("description") or "",
            is_required=bool(item.get("is_required")),
            type=str(item.get("type") or ""),
            dictionary_id=int(item.get("dictionary_id") or 0),
            group_name=item.get("group_name") or "",
            is_aspect=bool(item.get("is_aspect")),
        )
        for item in items
        if item.get("id") is not None
    ]


@router.get("/jobs/republish", response_model=list[RepublishJobOut])
def list_jobs(db: Session = Depends(get_db)) -> list[RepublishJob]:
    return db.query(RepublishJob).order_by(RepublishJob.id.desc()).limit(100).all()


@router.post("/jobs/{job_id}/refresh")
async def refresh_job(job_id: int, db: Session = Depends(get_db)) -> dict:
    return await ozon.refresh_import_job(db, job_id)


@router.get("/{product_id}", response_model=ProductOut)
def get_product(product_id: int, db: Session = Depends(get_db)) -> ProductOut:
    row = db.get(Product, product_id)
    if row is None:
        raise HTTPException(status_code=404, detail="商品不存在")
    return _to_out(row)


@router.get("/{product_id}/stocks")
def product_stocks(product_id: int, db: Session = Depends(get_db)) -> list[dict]:
    rows = db.query(ProductStock).filter(ProductStock.product_id == product_id).all()
    return [
        {
            "warehouse_id": row.warehouse_id,
            "sku": row.sku,
            "present": row.present,
            "reserved": row.reserved,
            "stock_type": row.stock_type,
        }
        for row in rows
    ]


@router.post("/archive")
async def archive_products(product_ids: list[int], db: Session = Depends(get_db)) -> dict:
    return await ozon.archive_products(db, product_ids, True)


@router.post("/unarchive")
async def unarchive_products(product_ids: list[int], db: Session = Depends(get_db)) -> dict:
    return await ozon.archive_products(db, product_ids, False)


@router.post("/price")
async def update_price(body: PriceUpdateIn, db: Session = Depends(get_db)) -> dict:
    return await ozon.update_prices(db, [body.model_dump()])


@router.post("/stock")
async def update_stock(body: StockUpdateIn, db: Session = Depends(get_db)) -> dict:
    return await ozon.update_stocks(db, [body.model_dump()])


@router.post("/{product_id}/copy")
async def copy_product(product_id: int, body: CopyProductIn) -> dict:
    return await queue.submit_and_wait(
        "copy_product",
        {"product_id": product_id, "new_offer_id": body.new_offer_id, "price": body.price},
        timeout=90,
    )


@router.post("/{product_id}/republish")
async def republish_product(product_id: int, body: RepublishIn) -> dict:
    return await queue.submit_and_wait(
        "republish_product",
        {
            "product_id": product_id,
            "new_offer_id": body.new_offer_id,
            "name": body.name,
            "price": body.price,
        },
        timeout=90,
    )

