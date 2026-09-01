from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import ozon
from ..db import get_db
from ..schemas import SettingsOut, SettingsUpdate
from ..settings_store import get_credentials, mask_key, save_credentials

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("", response_model=SettingsOut)
async def read_settings(db: Session = Depends(get_db)) -> SettingsOut:
    client_id, api_key = get_credentials(db)
    return SettingsOut(
        client_id=client_id,
        api_key_masked=mask_key(api_key),
        configured=bool(client_id and api_key),
    )


@router.put("", response_model=SettingsOut)
async def update_settings(body: SettingsUpdate, db: Session = Depends(get_db)) -> SettingsOut:
    save_credentials(db, body.client_id, body.api_key or None)
    return await read_settings(db)


@router.post("/test", response_model=SettingsOut)
async def test_settings(db: Session = Depends(get_db)) -> SettingsOut:
    client_id, api_key = get_credentials(db)
    if not client_id or not api_key:
        raise HTTPException(status_code=400, detail="请先填写 Client-Id 和 Api-Key")
    try:
        info = await ozon.test_connection(db)
        return SettingsOut(
            client_id=client_id,
            api_key_masked=mask_key(api_key),
            configured=True,
            connected=True,
            company_name=info.get("company_name") or "",
            message="连接成功",
        )
    except HTTPException:
        raise
    except Exception as exc:
        return SettingsOut(
            client_id=client_id,
            api_key_masked=mask_key(api_key),
            configured=True,
            connected=False,
            message=str(exc),
        )
