from __future__ import annotations

import hashlib
import json
import re
from typing import Iterable

import httpx
from sqlalchemy.orm import Session

from .config import settings
from .models import TranslationCache

CYRILLIC = re.compile(r"[А-Яа-яЁё]")
CHINESE = re.compile(r"[\u4e00-\u9fff]")

ENUM_ZH: dict[str, str] = {
    "ALL": "全部",
    "VISIBLE": "可见",
    "INVISIBLE": "不可见",
    "IN_SALE": "在售",
    "TO_SUPPLY": "待供货",
    "READY_TO_SUPPLY": "可供货",
    "REMOVED_FROM_SALE": "已下架",
    "ARCHIVED": "已归档",
    "DISABLED": "已停用",
    "EMPTY_STOCK": "无库存",
    "NOT_MODERATED": "未审核",
    "MODERATED": "已审核",
    "STATE_FAILED": "创建失败",
    "VALIDATION_STATE_PENDING": "预审中",
    "VALIDATION_STATE_FAIL": "预审未通过",
    "VALIDATION_STATE_SUCCESS": "预审通过",
    "OVERPRICED": "定价偏高",
    "CRITICALLY_OVERPRICED": "定价严重偏高",
    "OVERPRICED_WITH_STOCK": "偏高但仍在售",
    "QUARANTINE": "价格检疫",
    "EMPTY_BARCODE": "无条码",
    "BARCODE_EXISTS": "有条码",
    "PARTIAL_APPROVED": "部分通过",
    "BAN_REASON_DUPLICATE_DESCRIPTION": "因重复描述被禁",
    "BAN_REASON_MANUAL": "人工封禁",
    "BAN_REASON_LEGAL": "合规封禁",
    "COLOR_INDEX_SUPER": "超值",
    "COLOR_INDEX_GREEN": "绿色（有竞争力）",
    "COLOR_INDEX_YELLOW": "黄色（一般）",
    "COLOR_INDEX_RED": "红色（偏贵）",
    "COLOR_INDEX_WITHOUT_INDEX": "无指数",
    "SUPER": "超值",
    "GREEN": "绿色（有竞争力）",
    "YELLOW": "黄色（一般）",
    "RED": "红色（偏贵）",
    "WITHOUT_INDEX": "无指数",
    "awaiting_registration": "待登记",
    "acceptance_in_progress": "接收中",
    "awaiting_approve": "待确认",
    "awaiting_packaging": "待打包",
    "awaiting_deliver": "待交运",
    "arbitration": "仲裁中",
    "client_arbitration": "买家仲裁",
    "delivering": "配送中",
    "driver_pickup": "司机取件",
    "delivered": "已送达",
    "cancelled": "已取消",
    "not_accepted": "未签收",
    "seller": "卖家",
    "buyer": "买家",
    "customer": "买家",
    "ozon": "Ozon",
    "marketplace": "平台",
    "seller_cancel": "卖家取消",
    "client_cancel": "买家取消",
    "ozon_cancel": "平台取消",
    "created": "已创建",
    "active": "启用",
    "disabled": "停用",
    "blocked": "已停用",
    "new": "新建",
    "fbs": "FBS",
    "rfbs": "rFBS",
    "FBS": "FBS",
    "rFBS": "rFBS",
    "success": "成功",
    "failed": "失败",
    "submitted": "已提交",
    "pending": "处理中",
    "running": "进行中",
    "imported": "已导入",
    "create": "新建",
    "unarchive": "恢复归档",
    "import-by-sku": "按 SKU 复制",
    "import-snapshot": "快照重建",
    "Cancellation": "取消",
    "cancellation": "取消",
    "Return": "退货",
    "return": "退货",
    "OnTheWay": "在途中",
    "OnWayToOzon": "在途中",
    "InTransit": "在途中",
    "delivering": "在途中",
    "Utilizing": "核销中",
    "На утилизации": "核销中",
    "WaitingForSeller": "待卖家处理",
    "ReadyForPickup": "待领取",
    "Utilization": "核销",
    "Utilized": "已核销",
    "ReturnedToSeller": "已退回卖家",
    "В пути": "在途中",
    "В пути к продавцу": "在途中",
    "Отмена": "取消",
    "Возврат": "退货",
    "Утилизация": "销毁",
    "Утилизирован": "已核销",
    "Списание": "核销",
    "Списан": "已核销",
    "Ожидает продавца": "待卖家处理",
    "Готов к выдаче": "待领取",
    "Возвращён продавцу": "已退回卖家",
    "realFBS": "rFBS",
    "RFBS": "rFBS",
    "Продается": "在售",
    "Не продается": "未在售",
    "Убран из продажи": "已下架",
    "price_sent": "已同步价格",
}


def enum_label(text: str | None) -> str:
    raw = _norm(text or "")
    return _enum_zh(raw) if _enum_zh(raw) is not None else raw


def _norm(text: str) -> str:
    return (text or "").strip()


def _cache_key(text: str, context: str) -> str:
    return hashlib.sha256(f"{context}\n{text}".encode("utf-8")).hexdigest()


def _enum_zh(text: str) -> str | None:
    raw = _norm(text)
    if not raw:
        return ""
    if raw in ENUM_ZH:
        return ENUM_ZH[raw]
    upper = raw.upper()
    if upper in ENUM_ZH:
        return ENUM_ZH[upper]
    if raw.startswith("COLOR_INDEX_"):
        tail = raw.removeprefix("COLOR_INDEX_")
        if tail in ENUM_ZH:
            return ENUM_ZH[tail]
    return None


def needs_model_translation(text: str) -> bool:
    raw = _norm(text)
    if not raw:
        return False
    if _enum_zh(raw) is not None:
        return False
    if CHINESE.search(raw) and not CYRILLIC.search(raw):
        return False
    if CYRILLIC.search(raw):
        return True
    if re.fullmatch(r"[A-Za-z][A-Za-z0-9_ \-/]{1,40}", raw):
        return True
    return False


def _lookup_cache(db: Session, text: str, context: str) -> str | None:
    row = db.get(TranslationCache, _cache_key(text, context))
    return row.translated_text if row else None


def _save_cache(db: Session, text: str, context: str, translated: str) -> None:
    key = _cache_key(text, context)
    row = db.get(TranslationCache, key)
    if row is None:
        db.add(
            TranslationCache(
                id=key,
                source_text=text,
                context=context,
                translated_text=translated,
            )
        )
    else:
        row.translated_text = translated


async def _deepseek_batch(texts: list[str], system: str) -> list[str]:
    if not settings.deepseek_api_key:
        return texts
    payload = {
        "model": "deepseek-chat",
        "temperature": 0.1,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": json.dumps(texts, ensure_ascii=False)},
        ],
    }
    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(
            "https://api.deepseek.com/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.deepseek_api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"].strip()
        if content.startswith("```"):
            content = re.sub(r"^```(?:json)?\s*|\s*```$", "", content)
        translated = json.loads(content)
        if not isinstance(translated, list) or len(translated) != len(texts):
            raise ValueError("DeepSeek 返回条数不匹配")
        return [str(item) for item in translated]


async def translate_many(db: Session, texts: Iterable[str], context: str = "generic") -> dict[str, str]:
    unique: list[str] = []
    seen: set[str] = set()
    mapping: dict[str, str] = {"": ""}
    for raw in texts:
        text = _norm(str(raw or ""))
        if text in seen:
            continue
        seen.add(text)
        enum_hit = _enum_zh(text)
        if enum_hit is not None:
            mapping[text] = enum_hit
            continue
        cached = _lookup_cache(db, text, context)
        if cached is not None:
            mapping[text] = cached
            continue
        if not needs_model_translation(text):
            mapping[text] = text
            continue
        unique.append(text)

    for offset in range(0, len(unique), 20):
        batch = unique[offset : offset + 20]
        try:
            translated = await _deepseek_batch(
                batch,
                "你是跨境电商翻译。把俄语或英语文本译成简体中文。"
                "保留品牌、型号、数字和货号。不要解释。"
                "只返回 JSON 字符串数组，与输入顺序一一对应。",
            )
        except Exception:
            for text in batch:
                mapping[text] = text
            continue
        for source, target in zip(batch, translated, strict=True):
            target = _norm(target) or source
            mapping[source] = target
            _save_cache(db, source, context, target)
    if unique:
        db.commit()
    return mapping


def pick(mapping: dict[str, str], text: str | None) -> str:
    raw = _norm(text or "")
    return mapping.get(raw, raw)


async def translate_zh_to_ru(db: Session, texts: Iterable[str], context: str = "zh-ru") -> dict[str, str]:
    unique: list[str] = []
    seen: set[str] = set()
    mapping: dict[str, str] = {"": ""}
    for raw in texts:
        text = _norm(str(raw or ""))
        if text in seen:
            continue
        seen.add(text)
        if not text:
            continue
        if CYRILLIC.search(text) and not CHINESE.search(text):
            mapping[text] = text
            continue
        cached = _lookup_cache(db, text, context)
        if cached is not None:
            mapping[text] = cached
            continue
        unique.append(text)

    for offset in range(0, len(unique), 10):
        batch = unique[offset : offset + 10]
        try:
            translated = await _deepseek_batch(
                batch,
                "你是跨境电商文案译员。把简体中文商品标题或描述译成地道俄语。"
                "保留品牌、型号、数字和货号，不要添加营销套话，不要解释。"
                "只返回 JSON 字符串数组，与输入顺序一一对应。",
            )
        except Exception as exc:
            raise RuntimeError(f"中译俄失败：{exc}") from exc
        for source, target in zip(batch, translated, strict=True):
            target = _norm(target) or source
            mapping[source] = target
            _save_cache(db, source, context, target)
    if unique:
        db.commit()
    return mapping
