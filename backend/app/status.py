from __future__ import annotations

from enum import Enum

from .models import Product


class ProductStatus(str, Enum):
    IN_SALE = "IN_SALE"
    READY_TO_SELL = "READY_TO_SELL"
    ERROR = "ERROR"
    NEED_UPDATE = "NEED_UPDATE"
    NOT_FOR_SALE = "NOT_FOR_SALE"
    REMOVED_FROM_SALE = "REMOVED_FROM_SALE"
    ARCHIVED = "ARCHIVED"
    EMPTY_STOCK = "EMPTY_STOCK"
    UNKNOWN = "UNKNOWN"


LABELS: dict[ProductStatus, str] = {
    ProductStatus.IN_SALE: "销售中",
    ProductStatus.READY_TO_SELL: "准备销售",
    ProductStatus.ERROR: "错误",
    ProductStatus.NEED_UPDATE: "待修改",
    ProductStatus.NOT_FOR_SALE: "商品已下架",
    ProductStatus.REMOVED_FROM_SALE: "商品已下架",
    ProductStatus.ARCHIVED: "档案",
    ProductStatus.EMPTY_STOCK: "无库存",
    ProductStatus.UNKNOWN: "未知",
}


def classify(
    status: str = "",
    status_name: str = "",
    status_description: str = "",
    is_archived: bool = False,
) -> ProductStatus:
    if is_archived:
        return ProductStatus.ARCHIVED
    text = " ".join([status or "", status_name or "", status_description or ""]).casefold()
    if any(key in text for key in ("state_failed", "failed", "ошибк")):
        return ProductStatus.ERROR
    if any(key in text for key in ("validation_state_fail", "need_update", "доработ", "требует измен")):
        return ProductStatus.NEED_UPDATE
    if any(key in text for key in ("убран из продажи", "removed_from_sale", "removed from sale", "скрыт")):
        return ProductStatus.REMOVED_FROM_SALE
    if any(key in text for key in ("не продается", "not for sale", "invisible", "disabled")):
        return ProductStatus.NOT_FOR_SALE
    if any(key in text for key in ("ready_to_sell", "ready_to_supply", "to_supply", "готов к продаж", "готовится к продаж")):
        return ProductStatus.READY_TO_SELL
    if any(key in text for key in ("продается", "in_sale", "in sale")):
        return ProductStatus.IN_SALE
    if "empty_stock" in text or "нет в наличии" in text:
        return ProductStatus.EMPTY_STOCK
    return ProductStatus.UNKNOWN


def product_status(row: Product) -> ProductStatus:
    return classify(row.status, row.status_name, row.status_description, row.is_archived)


def is_removed(code: ProductStatus) -> bool:
    return code in {ProductStatus.REMOVED_FROM_SALE, ProductStatus.NOT_FOR_SALE}


def label(code: ProductStatus) -> str:
    return LABELS[code]
