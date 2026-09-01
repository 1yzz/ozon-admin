from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


class AppSetting(Base):
    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str] = mapped_column(Text, default="")


class Product(Base):
    __tablename__ = "products"

    product_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    offer_id: Mapped[str] = mapped_column(String(64), index=True, default="")
    sku: Mapped[int | None] = mapped_column(Integer, nullable=True)
    name: Mapped[str] = mapped_column(String(500), default="")
    status: Mapped[str] = mapped_column(String(64), default="")
    status_name: Mapped[str] = mapped_column(String(128), default="")
    status_description: Mapped[str] = mapped_column(Text, default="")
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False)
    price: Mapped[str] = mapped_column(String(32), default="")
    old_price: Mapped[str] = mapped_column(String(32), default="")
    min_price: Mapped[str] = mapped_column(String(32), default="")
    vat: Mapped[str] = mapped_column(String(16), default="")
    currency_code: Mapped[str] = mapped_column(String(8), default="RUB")
    color_index: Mapped[str] = mapped_column(String(64), default="")
    ozon_min_price: Mapped[str] = mapped_column(String(32), default="")
    external_min_price: Mapped[str] = mapped_column(String(32), default="")
    has_stock: Mapped[bool] = mapped_column(Boolean, default=False)
    stock_present: Mapped[int] = mapped_column(Integer, default=0)
    stock_reserved: Mapped[int] = mapped_column(Integer, default=0)
    primary_image: Mapped[str] = mapped_column(Text, default="")
    description_category_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    type_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    snapshot_json: Mapped[str] = mapped_column(Text, default="")
    synced_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Warehouse(Base):
    __tablename__ = "warehouses"

    warehouse_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), default="")
    status: Mapped[str] = mapped_column(String(64), default="")
    warehouse_type: Mapped[str] = mapped_column(String(64), default="")
    is_rfbs: Mapped[bool] = mapped_column(Boolean, default=False)
    address: Mapped[str] = mapped_column(Text, default="")
    raw_json: Mapped[str] = mapped_column(Text, default="")


class RepublishJob(Base):
    __tablename__ = "republish_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_product_id: Mapped[int] = mapped_column(Integer, index=True)
    source_offer_id: Mapped[str] = mapped_column(String(64), default="")
    new_offer_id: Mapped[str] = mapped_column(String(64), default="")
    strategy: Mapped[str] = mapped_column(String(32), default="")
    task_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="pending")
    message: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class TranslationCache(Base):
    __tablename__ = "translation_cache"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    source_text: Mapped[str] = mapped_column(Text, default="")
    context: Mapped[str] = mapped_column(String(64), default="generic", index=True)
    translated_text: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class QueueJob(Base):
    __tablename__ = "queue_jobs"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    kind: Mapped[str] = mapped_column(String(64), index=True, default="")
    status: Mapped[str] = mapped_column(String(32), default="pending", index=True)
    payload_json: Mapped[str] = mapped_column(Text, default="")
    result_json: Mapped[str] = mapped_column(Text, default="")
    error: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class ProductStock(Base):
    __tablename__ = "product_stocks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(Integer, index=True)
    warehouse_id: Mapped[int] = mapped_column(Integer, default=0)
    sku: Mapped[int | None] = mapped_column(Integer, nullable=True)
    present: Mapped[int] = mapped_column(Integer, default=0)
    reserved: Mapped[int] = mapped_column(Integer, default=0)
    stock_type: Mapped[str] = mapped_column(String(32), default="")
