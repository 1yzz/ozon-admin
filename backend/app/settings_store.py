from sqlalchemy.orm import Session

from .config import settings
from .models import AppSetting


CLIENT_ID_KEY = "ozon_client_id"
API_KEY_KEY = "ozon_api_key"


def _get(db: Session, key: str) -> str | None:
    row = db.get(AppSetting, key)
    return row.value if row else None


def _set(db: Session, key: str, value: str) -> None:
    row = db.get(AppSetting, key)
    if row is None:
        db.add(AppSetting(key=key, value=value))
    else:
        row.value = value


def get_credentials(db: Session) -> tuple[str, str]:
    client_id = (_get(db, CLIENT_ID_KEY) or settings.ozon_client_id or "").strip()
    api_key = (_get(db, API_KEY_KEY) or settings.ozon_api_key or "").strip()
    return client_id, api_key


def save_credentials(db: Session, client_id: str, api_key: str | None) -> None:
    _set(db, CLIENT_ID_KEY, client_id.strip())
    if api_key:
        _set(db, API_KEY_KEY, api_key.strip())
    db.commit()


def mask_key(api_key: str) -> str:
    if not api_key:
        return ""
    if len(api_key) <= 8:
        return "****"
    return f"{api_key[:4]}…{api_key[-4:]}"
