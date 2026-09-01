from __future__ import annotations

import json
import secrets
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import Any, AsyncIterator

from fastapi import HTTPException
from ozonapi import SellerAPI
from ozonapi.seller.schemas.attributes_and_characteristics.v1__description_category_attribute import (
    DescriptionCategoryAttributeRequest,
)
from ozonapi.seller.schemas.fbs.v3__posting_fbs_get import PostingFBSGetRequest
from ozonapi.seller.schemas.fbs.v4__posting_fbs_list import (
    PostingFBSListFilter,
    PostingFBSListRequest,
)
from ozonapi.seller.schemas.prices_and_stocks.v1__product_import_prices import (
    ProductImportPricesItem,
    ProductImportPricesRequest,
)
from ozonapi.seller.schemas.prices_and_stocks.v2__products_stocks import (
    ProductsStocksItem,
    ProductsStocksRequest,
)
from ozonapi.seller.schemas.products.v1__product_archive import ProductArchiveRequest
from ozonapi.seller.schemas.products.v1__product_import_by_sku import (
    ProductImportBySkuRequest,
    ProductImportBySkuRequestItem,
)
from ozonapi.seller.schemas.products.v1__product_import_info import ProductImportInfoRequest
from ozonapi.seller.schemas.products.v1__product_unarchive import ProductUnarchiveRequest
from ozonapi.seller.schemas.products.v3__product_import import (
    ProductImportItem,
    ProductImportRequest,
)
from ozonapi.seller.schemas.products.v3__product_info_list import ProductInfoListRequest
from ozonapi.seller.schemas.products.v3__product_list import (
    ProductListFilter,
    ProductListRequest,
)
from ozonapi.seller.schemas.products.v4__product_info_attributes import (
    ProductInfoAttributesFilter,
    ProductInfoAttributesRequest,
)
from ozonapi.seller.schemas.returns.v2__returns_rfbs_list import ReturnsRfbsListResponse
from sqlalchemy import delete
from sqlalchemy.orm import Session

from .models import Product, ProductStock, RepublishJob, Warehouse
from .settings_store import get_credentials
from .status import is_removed, product_status


def _dump(model: Any) -> dict[str, Any]:
    if model is None:
        return {}
    if hasattr(model, "model_dump"):
        return model.model_dump(mode="json")
    return dict(model)


def _enum_str(value: Any) -> str:
    if value is None:
        return ""
    return str(getattr(value, "value", value))


def _first_image(value: Any) -> str:
    if isinstance(value, list) and value:
        return str(value[0] or "")
    if isinstance(value, str):
        return value
    return ""


def _index_min_price(data: Any) -> str:
    if not data:
        return ""
    dumped = _dump(data)
    return str(dumped.get("min_price") or dumped.get("min_price_value") or "")


@asynccontextmanager
async def ozon_client(db: Session) -> AsyncIterator[SellerAPI]:
    client_id, api_key = get_credentials(db)
    if not client_id or not api_key:
        raise HTTPException(status_code=400, detail="请先在设置页填写 Client-Id 和 Api-Key")
    async with SellerAPI(client_id=client_id, api_key=api_key) as api:
        yield api


async def test_connection(db: Session) -> dict[str, Any]:
    async with ozon_client(db) as api:
        info = await api.seller_info()
        data = _dump(info)
        company = data.get("company") or {}
        return {
            "company_name": company.get("name") or company.get("company_name") or "",
            "raw": data,
        }


async def sync_warehouses(db: Session) -> int:
    async with ozon_client(db) as api:
        from ozonapi.seller.schemas.warehouses.v2__warehouse_list import WarehouseListRequest

        cursor = None
        count = 0
        while True:
            resp = await api.warehouse_list(WarehouseListRequest(cursor=cursor))
            items = resp.warehouses or []
            for item in items:
                address = ""
                if item.address_info:
                    addr = _dump(item.address_info)
                    address = " ".join(
                        part
                        for part in [
                            addr.get("city"),
                            addr.get("address"),
                            addr.get("name"),
                        ]
                        if part
                    )
                row = db.get(Warehouse, item.warehouse_id)
                payload = dict(
                    warehouse_id=item.warehouse_id or 0,
                    name=item.name or "",
                    status=_enum_str(item.status),
                    warehouse_type=_enum_str(item.warehouse_type),
                    is_rfbs=bool(item.is_rfbs),
                    address=address,
                    raw_json=json.dumps(_dump(item), ensure_ascii=False),
                )
                if row is None:
                    db.add(Warehouse(**payload))
                else:
                    for key, value in payload.items():
                        setattr(row, key, value)
                count += 1
            if not resp.has_next or not resp.cursor or resp.cursor == cursor:
                break
            cursor = resp.cursor
        db.commit()
        return count


async def sync_products(db: Session) -> int:
    async with ozon_client(db) as api:
        product_ids: list[int] = []
        last_id = None
        while True:
            resp = await api.product_list(
                ProductListRequest(
                    last_id=last_id,
                    limit=1000,
                    filter=ProductListFilter(visibility="ALL"),
                )
            )
            items = resp.result.items if resp.result else []
            for item in items:
                product_ids.append(item.product_id)
            last_id = resp.result.last_id if resp.result else None
            if not items or not last_id:
                break

        for offset in range(0, len(product_ids), 100):
            batch = product_ids[offset : offset + 100]
            info = await api.product_info_list(ProductInfoListRequest(product_id=batch))
            for item in info.items:
                sku = None
                for source in item.sources or []:
                    source_sku = getattr(source, "sku", None)
                    if source_sku:
                        sku = int(source_sku)
                        break
                stocks = item.stocks
                present = 0
                reserved = 0
                if stocks and stocks.stocks:
                    for stock in stocks.stocks:
                        present += int(getattr(stock, "present", 0) or 0)
                        reserved += int(getattr(stock, "reserved", 0) or 0)
                indexes = item.price_indexes
                color_index = _enum_str(getattr(indexes, "color_index", None))
                payload = dict(
                    product_id=item.id,
                    offer_id=item.offer_id or "",
                    sku=sku,
                    name=item.name or "",
                    status=item.statuses.status if item.statuses else "",
                    status_name=item.statuses.status_name if item.statuses else "",
                    status_description=item.statuses.status_description if item.statuses else "",
                    is_archived=bool(item.is_archived),
                    price=str(item.price or ""),
                    old_price=str(item.old_price or ""),
                    min_price=str(item.min_price or ""),
                    vat=_enum_str(item.vat),
                    currency_code=item.currency_code or "RUB",
                    color_index=color_index,
                    ozon_min_price=_index_min_price(getattr(indexes, "ozon_index_data", None)),
                    external_min_price=_index_min_price(
                        getattr(indexes, "external_index_data", None)
                    ),
                    has_stock=bool(stocks.has_stock) if stocks else False,
                    stock_present=present,
                    stock_reserved=reserved,
                    primary_image=_first_image(item.primary_image) or _first_image(item.images),
                    description_category_id=item.description_category_id,
                    type_id=item.type_id,
                    synced_at=datetime.utcnow(),
                )
                row = db.get(Product, item.id)
                if row is None:
                    db.add(Product(**payload))
                else:
                    for key, value in payload.items():
                        setattr(row, key, value)

        db.commit()

        for offset in range(0, len(product_ids), 100):
            batch = product_ids[offset : offset + 100]
            try:
                attrs = await api.product_info_attributes(
                    ProductInfoAttributesRequest(
                        limit=1000,
                        filter=ProductInfoAttributesFilter(product_id=batch),
                    )
                )
            except Exception:
                continue
            for item in attrs.result or []:
                row = db.get(Product, item.id)
                snapshot = _dump(item)
                if row is None:
                    db.add(
                        Product(
                            product_id=item.id,
                            offer_id=item.offer_id or "",
                            sku=item.sku,
                            name=item.name or "",
                            snapshot_json=json.dumps(snapshot, ensure_ascii=False),
                            description_category_id=item.description_category_id,
                            type_id=item.type_id,
                            primary_image=_first_image(item.primary_image)
                            or _first_image(item.images),
                        )
                    )
                else:
                    row.snapshot_json = json.dumps(snapshot, ensure_ascii=False)
                    if item.sku:
                        row.sku = item.sku
                    if item.description_category_id:
                        row.description_category_id = item.description_category_id
                    if item.type_id:
                        row.type_id = item.type_id
        db.commit()

        try:
            db.execute(delete(ProductStock))
            from ozonapi.seller.schemas.prices_and_stocks.v4__product_info_stocks import (
                ProductInfoStocksFilter,
                ProductInfoStocksRequest,
            )

            for offset in range(0, len(product_ids), 100):
                batch = product_ids[offset : offset + 100]
                cursor = ""
                while True:
                    stocks_resp = await api.product_info_stocks(
                        ProductInfoStocksRequest(
                            cursor=cursor,
                            limit=1000,
                            filter=ProductInfoStocksFilter(product_id=batch),
                        )
                    )
                    for item in stocks_resp.items or []:
                        for stock in item.stocks or []:
                            warehouse_ids = getattr(stock, "warehouse_ids", None) or [0]
                            for warehouse_id in warehouse_ids:
                                db.add(
                                    ProductStock(
                                        product_id=item.product_id,
                                        warehouse_id=int(warehouse_id or 0),
                                        sku=getattr(stock, "sku", None),
                                        present=int(getattr(stock, "present", 0) or 0),
                                        reserved=int(getattr(stock, "reserved", 0) or 0),
                                        stock_type=_enum_str(getattr(stock, "type", "")),
                                    )
                                )
                    cursor = stocks_resp.cursor or ""
                    if not stocks_resp.items or not cursor:
                        break
            db.commit()
        except Exception:
            db.rollback()

        return len(product_ids)


async def archive_products(db: Session, product_ids: list[int], archive: bool) -> Any:
    async with ozon_client(db) as api:
        if archive:
            resp = await api.product_archive(ProductArchiveRequest(product_id=product_ids))
        else:
            resp = await api.product_unarchive(ProductUnarchiveRequest(product_id=product_ids))
        for product_id in product_ids:
            row = db.get(Product, product_id)
            if row:
                row.is_archived = archive
        db.commit()
        return _dump(resp)


async def update_prices(db: Session, items: list[dict[str, Any]]) -> Any:
    async with ozon_client(db) as api:
        payload = [
            ProductImportPricesItem(
                product_id=item["product_id"],
                price=str(item["price"]),
                old_price=str(item["old_price"]) if item.get("old_price") else None,
                min_price=str(item["min_price"]) if item.get("min_price") else None,
            )
            for item in items
        ]
        resp = await api.product_import_prices(ProductImportPricesRequest(prices=payload))
        for item in items:
            row = db.get(Product, item["product_id"])
            if row:
                row.price = str(item["price"])
                if item.get("old_price") is not None:
                    row.old_price = str(item["old_price"])
        db.commit()
        return _dump(resp)


async def update_stocks(db: Session, items: list[dict[str, Any]]) -> Any:
    async with ozon_client(db) as api:
        payload = [
            ProductsStocksItem(
                product_id=item["product_id"],
                offer_id=item.get("offer_id") or None,
                stock=int(item["stock"]),
                warehouse_id=int(item["warehouse_id"]),
            )
            for item in items
        ]
        resp = await api.products_stocks(ProductsStocksRequest(stocks=payload))
        return _dump(resp)


def _new_offer_id(offer_id: str, suffix: str) -> str:
    base = (offer_id or "sku")[:40]
    candidate = f"{base}-{suffix}"
    return candidate[:50]


_DESC_ATTR_IDS = {4191, 11254}
_TEXT_DESC_ATTR_ID = 4191


def _decoy_tag() -> str:
    return f"лот {secrets.token_hex(3)}"


def _append_decoy(raw: str, tag: str) -> str:
    text = raw or ""
    if tag in text:
        return text
    stripped = text.strip()
    if stripped.startswith("{"):
        try:
            data = json.loads(stripped)
            for widget in data.get("content") or []:
                items = (widget.get("title") or {}).get("items") or []
                if items and items[0].get("content"):
                    items[0]["content"] = f"{str(items[0]['content']).rstrip()} {tag}"
                    return json.dumps(data, ensure_ascii=False)
            data.setdefault("content", []).append(
                {
                    "widgetName": "raTextBlock",
                    "title": {"items": [{"type": "text", "content": tag}]},
                }
            )
            return json.dumps(data, ensure_ascii=False)
        except json.JSONDecodeError:
            pass
    sep = "<br/>" if "<br" in text.lower() else " "
    return f"{text.rstrip()}{sep}{tag}" if text.strip() else tag


def _is_http_url(value: str) -> bool:
    return value.startswith("http://") or value.startswith("https://")


def _inject_description_decoy(snapshot: dict[str, Any], tag: str) -> None:
    attrs = list(snapshot.get("attributes") or [])
    cleaned: list[dict[str, Any]] = []
    touched = False
    for attr in attrs:
        attr_id = int(attr.get("id") or 0)
        values = attr.get("values") or []
        raw = ""
        if values and isinstance(values[0], dict):
            raw = str(values[0].get("value") or "")
        if attr_id == 4194 and raw and not _is_http_url(raw):
            continue
        if attr_id in _DESC_ATTR_IDS and values and isinstance(values[0], dict):
            values[0]["value"] = _append_decoy(raw, tag)
            touched = True
        cleaned.append(attr)
    if not touched:
        cleaned.append(
            {
                "id": _TEXT_DESC_ATTR_ID,
                "complex_id": 0,
                "values": [{"dictionary_value_id": 0, "value": tag}],
            }
        )
    snapshot["attributes"] = cleaned


async def _archive_source_if_removed(api: SellerAPI, db: Session, row: Product) -> bool:
    if row.is_archived or not is_removed(product_status(row)):
        return False
    await api.product_archive(ProductArchiveRequest(product_id=[row.product_id]))
    row.is_archived = True
    return True


async def copy_product(db: Session, product_id: int, new_offer_id: str | None, price: str | None) -> dict[str, Any]:
    row = db.get(Product, product_id)
    if row is None:
        raise HTTPException(status_code=404, detail="本地没有该商品，请先同步")
    if not row.snapshot_json and not row.sku:
        raise HTTPException(status_code=400, detail="该商品没有 SKU，也没有本地快照，请先同步")
    offer_id = new_offer_id or _new_offer_id(row.offer_id, datetime.now().strftime("%Y%m%d%H%M%S"))
    decoy = _decoy_tag()
    async with ozon_client(db) as api:
        if row.snapshot_json:
            snapshot = json.loads(row.snapshot_json)
            snapshot["price"] = price or row.price or snapshot.get("price")
            snapshot["vat"] = _vat_value(row.vat or snapshot.get("vat"))
            snapshot["currency_code"] = row.currency_code or snapshot.get("currency_code")
            _inject_description_decoy(snapshot, decoy)
            task_id = await _import_from_snapshot(api, snapshot, offer_id, row.name, price)
            strategy = "import-snapshot"
            message = "已用快照复制并写入混淆描述"
        else:
            resp = await api.product_import_by_sku(
                ProductImportBySkuRequest(
                    items=[
                        ProductImportBySkuRequestItem(
                            sku=row.sku,
                            name=row.name or None,
                            offer_id=offer_id,
                            price=price or row.price or None,
                            old_price=row.old_price or None,
                            vat=_vat_value(row.vat),
                            currency_code=row.currency_code or None,
                        )
                    ]
                )
            )
            data = _dump(resp)
            task_id = (
                data.get("task_id")
                or ((data.get("result") or {}).get("task_id") if isinstance(data.get("result"), dict) else None)
            )
            strategy = "import-by-sku"
            message = "已按 SKU 复制（无快照，未能改描述）"

        archived = False
        try:
            archived = await _archive_source_if_removed(api, db, row)
        except Exception as exc:
            db.add(
                RepublishJob(
                    source_product_id=product_id,
                    source_offer_id=row.offer_id,
                    new_offer_id=offer_id,
                    strategy=strategy,
                    task_id=task_id,
                    status="submitted",
                    message=f"{message}；归档原卡失败：{exc}",
                )
            )
            db.commit()
            raise HTTPException(
                status_code=502,
                detail=f"复制已提交 task_id={task_id}，但归档原下架商品失败：{exc}。请先归档原卡再重试，避免重复复制。",
            ) from exc

        if archived:
            message = f"{message}，原下架商品已归档"
        job = RepublishJob(
            source_product_id=product_id,
            source_offer_id=row.offer_id,
            new_offer_id=offer_id,
            strategy=strategy,
            task_id=task_id,
            status="submitted",
            message=message,
        )
        db.add(job)
        db.commit()
        return {
            "task_id": task_id,
            "offer_id": offer_id,
            "strategy": strategy,
            "archived": archived,
            "decoy": decoy if strategy == "import-snapshot" else "",
            "message": message,
        }


def _vat_value(raw: str | None) -> str:
    allowed = ("0", "0.05", "0.07", "0.10", "0.20", "0.22")
    if not raw:
        return "0.20"
    text = str(getattr(raw, "value", raw)).strip()
    mapping = {
        "PERCENT_0": "0",
        "PERCENT_5": "0.05",
        "PERCENT_7": "0.07",
        "PERCENT_10": "0.10",
        "PERCENT_20": "0.20",
        "PERCENT_22": "0.22",
        "0.00": "0",
        "0.0": "0",
        "0.1": "0.10",
        "0.2": "0.20",
    }
    if text in allowed:
        return text
    if text in mapping:
        return mapping[text]
    try:
        number = float(text)
    except ValueError:
        return "0.20"
    for item in allowed:
        if abs(float(item) - number) < 1e-9:
            return item
    return "0.20"


async def _import_from_snapshot(
    api: SellerAPI,
    snapshot: dict[str, Any],
    offer_id: str,
    name: str | None,
    price: str | None,
) -> int:
    color_image = snapshot.get("color_image")
    if isinstance(color_image, list):
        color_image = color_image[0] if color_image else None
    if isinstance(color_image, str) and color_image and not _is_http_url(color_image):
        color_image = None
    images = [url for url in (snapshot.get("images") or []) if isinstance(url, str) and _is_http_url(url)]
    primary = snapshot.get("primary_image")
    if not isinstance(primary, str) or not _is_http_url(primary):
        primary = images[0] if images else None
    item = ProductImportItem(
        name=name or snapshot.get("name") or offer_id,
        offer_id=offer_id,
        description_category_id=int(snapshot["description_category_id"]),
        new_description_category_id=None,
        type_id=snapshot.get("type_id"),
        price=str(price or snapshot.get("price") or "0"),
        old_price=str(snapshot.get("old_price") or "") or None,
        vat=_vat_value(snapshot.get("vat")),
        currency_code=snapshot.get("currency_code") or "RUB",
        depth=int(snapshot.get("depth") or 10),
        width=int(snapshot.get("width") or 10),
        height=int(snapshot.get("height") or 10),
        weight=int(snapshot.get("weight") or 10),
        dimension_unit=snapshot.get("dimension_unit") or "mm",
        weight_unit=snapshot.get("weight_unit") or "g",
        images=images,
        primary_image=primary,
        attributes=snapshot.get("attributes") or [],
        barcode=snapshot.get("barcode"),
        color_image=color_image,
        complex_attributes=snapshot.get("complex_attributes"),
        images360=snapshot.get("images360"),
    )
    resp = await api.product_import(ProductImportRequest(items=[item]))
    return int(resp.result.task_id)


async def republish_product(
    db: Session,
    product_id: int,
    new_offer_id: str | None,
    name: str | None,
    price: str | None,
) -> dict[str, Any]:
    row = db.get(Product, product_id)
    if row is None:
        raise HTTPException(status_code=404, detail="本地没有该商品，请先同步")

    offer_id = new_offer_id or _new_offer_id(row.offer_id, datetime.now().strftime("%m%d%H%M"))
    job = RepublishJob(
        source_product_id=product_id,
        source_offer_id=row.offer_id,
        new_offer_id=offer_id,
        strategy="",
        status="running",
        message="",
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    async with ozon_client(db) as api:
        if row.is_archived:
            try:
                await api.product_unarchive(ProductUnarchiveRequest(product_id=[product_id]))
                row.is_archived = False
                job.strategy = "unarchive"
                job.status = "success"
                job.message = "商品仅归档，已恢复上架"
                db.commit()
                return {"strategy": job.strategy, "status": job.status, "offer_id": row.offer_id}
            except Exception as exc:
                job.message = f"恢复归档失败，继续尝试重建：{exc}"

        if row.sku:
            try:
                resp = await api.product_import_by_sku(
                    ProductImportBySkuRequest(
                        items=[
                            ProductImportBySkuRequestItem(
                                sku=row.sku,
                                name=name or row.name or None,
                                offer_id=offer_id,
                                price=price or row.price or None,
                                old_price=row.old_price or None,
                                vat=_vat_value(row.vat),
                                currency_code=row.currency_code or None,
                            )
                        ]
                    )
                )
                task_id = resp.result.task_id if resp.result else None
                job.strategy = "import-by-sku"
                job.task_id = task_id
                job.status = "submitted"
                job.message = "已按 SKU 复制提交，等待审核"
                db.commit()
                return {
                    "strategy": job.strategy,
                    "status": job.status,
                    "task_id": task_id,
                    "offer_id": offer_id,
                }
            except Exception as exc:
                job.message = f"按 SKU 复制失败，改用快照重建：{exc}"

        if not row.snapshot_json:
            job.strategy = "failed"
            job.status = "failed"
            job.message = (job.message + "；本地没有商品快照，无法重建卡片。请先同步。").strip("；")
            db.commit()
            raise HTTPException(status_code=400, detail=job.message)

        snapshot = json.loads(row.snapshot_json)
        snapshot["price"] = price or row.price or snapshot.get("price")
        snapshot["vat"] = row.vat or snapshot.get("vat")
        snapshot["currency_code"] = row.currency_code or snapshot.get("currency_code")
        task_id = await _import_from_snapshot(api, snapshot, offer_id, name, price)
        job.strategy = "import-snapshot"
        job.task_id = task_id
        job.status = "submitted"
        job.message = "已用本地快照重新创建商品，等待审核"
        db.commit()
        return {
            "strategy": job.strategy,
            "status": job.status,
            "task_id": task_id,
            "offer_id": offer_id,
        }


async def refresh_import_job(db: Session, job_id: int) -> dict[str, Any]:
    job = db.get(RepublishJob, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    if not job.task_id:
        return _dump_job(job)
    async with ozon_client(db) as api:
        resp = await api.product_import_info(ProductImportInfoRequest(task_id=job.task_id))
        items = [_dump(item) for item in resp.result.items]
        if items:
            statuses = {item.get("status") for item in items}
            errors = [item.get("errors") for item in items if item.get("errors")]
            if any(str(s).lower() in {"imported", "success", "imported_successfully"} for s in statuses):
                job.status = "success"
            elif errors:
                job.status = "failed"
            job.message = json.dumps(items, ensure_ascii=False)[:2000]
        db.commit()
        return {"job": _dump_job(job), "items": items}


def _dump_job(job: RepublishJob) -> dict[str, Any]:
    return {
        "id": job.id,
        "source_product_id": job.source_product_id,
        "source_offer_id": job.source_offer_id,
        "new_offer_id": job.new_offer_id,
        "strategy": job.strategy,
        "task_id": job.task_id,
        "status": job.status,
        "message": job.message,
        "created_at": job.created_at,
    }


def _description_attribute_id(attrs: list[dict[str, Any]]) -> int | None:
    for item in attrs:
        name = str(item.get("name") or "").lower()
        if any(key in name for key in ("описан", "аннотац", "annotation", "description")):
            return int(item["id"])
    return 4191


async def create_product(db: Session, payload: dict[str, Any]) -> dict[str, Any]:
    from .translator import pick, translate_zh_to_ru

    name_zh = str(payload.get("name") or "").strip()
    description_zh = str(payload.get("description") or "").strip()
    mapping = await translate_zh_to_ru(db, [name_zh, description_zh], "zh-ru-listing")
    name_ru = pick(mapping, name_zh) or name_zh
    description_ru = pick(mapping, description_zh)

    attributes = list(payload.get("attributes") or [])
    if description_ru:
        try:
            cat_attrs = await category_attributes(
                db,
                int(payload["description_category_id"]),
                int(payload.get("type_id") or 0),
            )
            desc_id = _description_attribute_id(cat_attrs)
        except Exception:
            desc_id = 4191
        if desc_id:
            attributes = [item for item in attributes if item.get("id") != desc_id]
            attributes.append(
                {"id": desc_id, "complex_id": 0, "values": [{"value": description_ru}]}
            )

    images = payload.get("images") or []
    async with ozon_client(db) as api:
        item = ProductImportItem(
            name=name_ru,
            offer_id=payload["offer_id"],
            description_category_id=payload["description_category_id"],
            new_description_category_id=None,
            type_id=payload.get("type_id"),
            price=str(payload["price"]),
            old_price=payload.get("old_price"),
            vat=_vat_value(payload.get("vat")),
            currency_code=payload.get("currency_code") or "RUB",
            depth=payload["depth"],
            width=payload["width"],
            height=payload["height"],
            weight=payload["weight"],
            dimension_unit=payload.get("dimension_unit") or "mm",
            weight_unit=payload.get("weight_unit") or "g",
            images=images,
            primary_image=images[0] if images else None,
            attributes=attributes,
        )
        resp = await api.product_import(ProductImportRequest(items=[item]))
        task_id = resp.result.task_id
        job = RepublishJob(
            source_product_id=0,
            source_offer_id="",
            new_offer_id=payload["offer_id"],
            strategy="create",
            task_id=task_id,
            status="submitted",
            message="已提交新商品创建任务",
        )
        db.add(job)
        db.commit()
        return {
            "task_id": task_id,
            "name_ru": name_ru,
            "description_ru": description_ru,
        }


async def category_tree(db: Session) -> list[dict[str, Any]]:
    async with ozon_client(db) as api:
        resp = await api.description_category_tree()
        return [_dump(item) for item in resp.result]


async def category_attributes(db: Session, description_category_id: int, type_id: int) -> list[dict[str, Any]]:
    async with ozon_client(db) as api:
        resp = await api.description_category_attribute(
            DescriptionCategoryAttributeRequest(
                description_category_id=description_category_id,
                type_id=type_id,
            )
        )
        return [_dump(item) for item in resp.result]


def _order_window(days: int = 30) -> tuple[str, str]:
    now = datetime.now(timezone.utc)
    since = (now - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")
    until = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    return since, until


def _map_order(item: Any) -> dict[str, Any]:
    data = _dump(item)
    cancellation = data.get("cancellation") or {}
    products = []
    for product in data.get("products") or []:
        price = product.get("price") or {}
        if isinstance(price, dict):
            price_text = str(price.get("price") or price.get("amount") or "")
        else:
            price_text = str(price or "")
        products.append(
            {
                "name": product.get("name") or "",
                "offer_id": product.get("offer_id") or "",
                "sku": product.get("sku"),
                "quantity": int(product.get("quantity") or 0),
                "price": price_text,
            }
        )
    delivery = data.get("delivery_method") or {}
    return {
        "posting_number": data.get("posting_number") or "",
        "order_number": data.get("order_number") or "",
        "order_id": data.get("order_id"),
        "status": _enum_str(data.get("status")),
        "substatus": _enum_str(data.get("substatus")),
        "in_process_at": str(data.get("in_process_at") or ""),
        "shipment_date": str(data.get("shipment_date") or ""),
        "delivering_date": str(data.get("delivering_date") or ""),
        "warehouse_name": delivery.get("warehouse") or delivery.get("name") or "",
        "products": products,
        "cancel_reason": cancellation.get("cancel_reason") or "",
        "cancel_reason_id": cancellation.get("cancel_reason_id"),
        "cancellation_initiator": cancellation.get("cancellation_initiator") or "",
        "cancellation_type": _enum_str(cancellation.get("cancellation_type")),
        "cancelled_after_ship": bool(cancellation.get("cancelled_after_ship")),
    }


async def list_orders(db: Session, cancelled_only: bool = False, days: int = 30) -> list[dict[str, Any]]:
    since, until = _order_window(days)
    async with ozon_client(db) as api:
        orders: list[dict[str, Any]] = []
        cursor = None
        while True:
            request = PostingFBSListRequest(
                cursor=cursor,
                limit=100,
                filter=PostingFBSListFilter(
                    since=since,
                    to=until,
                    statuses=["cancelled"] if cancelled_only else None,
                ),
            )
            resp = await api.posting_fbs_list(request)
            for item in resp.postings or []:
                orders.append(_map_order(item))
            if not resp.has_next or not resp.cursor or resp.cursor == cursor:
                break
            cursor = resp.cursor
            if len(orders) >= 500:
                break
        return orders


async def get_order(db: Session, posting_number: str) -> dict[str, Any]:
    async with ozon_client(db) as api:
        resp = await api.posting_fbs_get(PostingFBSGetRequest(posting_number=posting_number))
        return _map_order(resp.result)


def paginate(items: list[Any], page: int, page_size: int) -> tuple[list[Any], int]:
    total = len(items)
    start = max(page - 1, 0) * page_size
    return items[start : start + page_size], total


def _money(value: Any) -> tuple[str, str]:
    data = _dump(value) if value else {}
    return str(data.get("price") or ""), str(data.get("currency_code") or "")


def _map_return(item: Any) -> dict[str, Any]:
    data = _dump(item)
    product = data.get("product") or {}
    visual = data.get("visual") or {}
    status = visual.get("status") or {}
    if not isinstance(status, dict):
        status = {}
    logistic = data.get("logistic") or {}
    place = data.get("place") or {}
    target = data.get("target_place") or {}
    price, currency = _money(product.get("price"))
    raw_type = str(data.get("type") or "")
    return {
        "id": int(data.get("id") or 0),
        "type": raw_type,
        "type_label": raw_type,
        "mode": data.get("schema_") or data.get("schema") or "",
        "status": status.get("display_name") or status.get("sys_name") or "",
        "status_sys": status.get("sys_name") or "",
        "group_state": "",
        "status_at": str(visual.get("change_moment") or ""),
        "posting_number": data.get("posting_number") or "",
        "order_number": data.get("order_number") or "",
        "order_id": data.get("order_id"),
        "reason": data.get("return_reason_name") or "",
        "product_name": product.get("name") or "",
        "offer_id": product.get("offer_id") or "",
        "sku": product.get("sku"),
        "quantity": int(product.get("quantity") or 0),
        "price": price,
        "currency_code": currency,
        "place_name": place.get("name") or "",
        "target_place": target.get("name") or target.get("address") or "",
        "return_date": str(logistic.get("return_date") or logistic.get("technical_return_moment") or ""),
    }


def _map_rfbs_return(item: Any) -> dict[str, Any]:
    data = item if isinstance(item, dict) else _dump(item)
    product = data.get("product") or {}
    state = data.get("state") or {}
    if not isinstance(state, dict):
        state = {}
    price = product.get("price")
    return {
        "id": int(data.get("return_id") or 0),
        "type": "return",
        "type_label": "退货",
        "mode": "realFBS",
        "status": state.get("state_name") or state.get("state") or "",
        "status_sys": state.get("state") or "",
        "group_state": state.get("group_state") or "",
        "status_at": str(data.get("created_at") or ""),
        "posting_number": data.get("posting_number") or "",
        "order_number": data.get("order_number") or "",
        "order_id": None,
        "reason": "",
        "product_name": product.get("name") or "",
        "offer_id": product.get("offer_id") or "",
        "sku": product.get("sku"),
        "quantity": 1,
        "price": "" if price is None else str(price),
        "currency_code": product.get("currency_code") or "",
        "place_name": "",
        "target_place": "",
        "return_date": str(data.get("created_at") or ""),
    }


async def list_returns(db: Session, days: int = 30, schema: str = "FBS") -> list[dict[str, Any]]:
    since, until = _order_window(days)
    async with ozon_client(db) as api:
        items: list[dict[str, Any]] = []
        last_id = None
        while True:
            payload: dict[str, Any] = {
                "limit": 100,
                "filter": {"created_at": {"from": since, "to": until}},
            }
            if last_id:
                payload["last_id"] = last_id
            raw = await api._request(
                method="post",
                api_version="v2",
                endpoint="returns/rfbs/list",
                payload=payload,
            )
            resp = ReturnsRfbsListResponse(**raw)
            batch = [_map_rfbs_return(row) for row in (resp.returns or [])]
            items.extend(batch)
            if len(batch) < 100:
                break
            next_id = batch[-1]["id"] or last_id
            if not next_id or next_id == last_id:
                break
            last_id = next_id
            if len(items) >= 500:
                break
        if schema and schema.upper() not in {"ALL", "RFBS", "REALFBS"}:
            items = [item for item in items if (item.get("mode") or "").upper() in {"", "FBS", "RFBS", "REALFBS"}]
        return items
