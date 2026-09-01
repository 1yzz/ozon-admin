from datetime import datetime

from pydantic import BaseModel, Field


class SettingsOut(BaseModel):
    client_id: str
    api_key_masked: str
    configured: bool
    connected: bool | None = None
    company_name: str = ""
    message: str = ""


class SettingsUpdate(BaseModel):
    client_id: str
    api_key: str = ""


class ProductOut(BaseModel):
    product_id: int
    offer_id: str
    sku: int | None
    name: str
    status: str
    status_name: str
    status_description: str
    is_archived: bool
    price: str
    old_price: str
    min_price: str
    vat: str
    currency_code: str
    color_index: str
    ozon_min_price: str
    external_min_price: str
    has_stock: bool
    stock_present: int
    stock_reserved: int
    primary_image: str
    description_category_id: int | None
    type_id: int | None
    synced_at: datetime | None
    has_snapshot: bool = False
    status_code: str = "UNKNOWN"
    status_label: str = "未知"
    is_removed: bool = False
    color_index_label: str = ""


class PriceUpdateIn(BaseModel):
    product_id: int
    price: str
    old_price: str | None = None
    min_price: str | None = None


class StockUpdateIn(BaseModel):
    product_id: int
    warehouse_id: int
    stock: int = Field(ge=0)
    offer_id: str | None = None


class CopyProductIn(BaseModel):
    new_offer_id: str | None = None
    price: str | None = None


class RepublishIn(BaseModel):
    new_offer_id: str | None = None
    name: str | None = None
    price: str | None = None


class CreateProductIn(BaseModel):
    name: str
    description: str = ""
    offer_id: str
    price: str
    vat: str = "0.20"
    description_category_id: int
    type_id: int
    depth: int
    width: int
    height: int
    weight: int
    dimension_unit: str = "mm"
    weight_unit: str = "g"
    images: list[str] = []
    attributes: list[dict] = []
    currency_code: str = "RUB"
    old_price: str | None = None


class TranslateCopyIn(BaseModel):
    name: str = ""
    description: str = ""


class CategoryNode(BaseModel):
    description_category_id: int | None
    category_name: str | None
    type_id: int | None
    type_name: str | None
    disabled: bool
    children: list["CategoryNode"] = []


class CategoryAttributeOut(BaseModel):
    id: int
    name: str
    description: str
    is_required: bool
    type: str
    dictionary_id: int
    group_name: str


class WarehouseOut(BaseModel):
    warehouse_id: int
    name: str
    status: str
    warehouse_type: str
    is_rfbs: bool
    address: str


class OrderProductOut(BaseModel):
    name: str
    offer_id: str
    sku: int | None
    quantity: int
    price: str


class PageMeta(BaseModel):
    page: int
    page_size: int
    total: int


class OrderOut(BaseModel):
    posting_number: str
    order_number: str
    order_id: int | None
    status: str
    substatus: str
    in_process_at: str
    shipment_date: str
    delivering_date: str
    warehouse_name: str
    products: list[OrderProductOut]
    cancel_reason: str = ""
    cancel_reason_id: int | None = None
    cancellation_initiator: str = ""
    cancellation_type: str = ""
    cancelled_after_ship: bool = False


class OrderPageOut(PageMeta):
    items: list[OrderOut]


class ReturnOut(BaseModel):
    id: int
    type: str
    type_label: str
    mode: str
    status: str
    status_sys: str
    status_at: str
    posting_number: str
    order_number: str
    order_id: int | None
    reason: str
    product_name: str
    offer_id: str
    sku: int | None
    quantity: int
    price: str
    currency_code: str
    place_name: str
    target_place: str
    return_date: str


class ReturnPageOut(PageMeta):
    items: list[ReturnOut]


class RepublishJobOut(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    source_product_id: int
    source_offer_id: str
    new_offer_id: str
    strategy: str
    task_id: int | None
    status: str
    message: str
    created_at: datetime


class QueueJobOut(BaseModel):
    id: str
    kind: str
    status: str
    error: str
    created_at: datetime
    result: dict = {}


class DashboardOut(BaseModel):
    product_total: int
    in_sale: int
    archived: int
    removed: int
    red_price: int
    yellow_price: int
    empty_stock: int
    warehouse_count: int
    last_sync: datetime | None
