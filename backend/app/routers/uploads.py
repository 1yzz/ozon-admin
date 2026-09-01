import uuid
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile

from ..config import settings

router = APIRouter(prefix="/api/uploads", tags=["uploads"])

ALLOWED = {
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}
MAX_BYTES = 12 * 1024 * 1024


@router.post("/images")
async def upload_images(files: list[UploadFile] = File(...)) -> dict:
    if not files:
        raise HTTPException(status_code=400, detail="请选择要上传的图片")
    saved: list[dict] = []
    folder = settings.upload_path
    for upload in files:
        suffix = ALLOWED.get((upload.content_type or "").lower())
        if not suffix:
            name = Path(upload.filename or "").suffix.lower()
            suffix = {".jpg": ".jpg", ".jpeg": ".jpg", ".png": ".png", ".webp": ".webp"}.get(name)
        if not suffix:
            raise HTTPException(status_code=400, detail=f"不支持的图片格式：{upload.filename}")
        data = await upload.read()
        if not data:
            raise HTTPException(status_code=400, detail=f"空文件：{upload.filename}")
        if len(data) > MAX_BYTES:
            raise HTTPException(status_code=400, detail=f"图片超过 12MB：{upload.filename}")
        filename = f"{uuid.uuid4().hex}{suffix}"
        path = folder / filename
        path.write_bytes(data)
        saved.append(
            {
                "filename": filename,
                "original_name": upload.filename or filename,
                "url": f"{settings.public_base_url.rstrip('/')}/uploads/products/{filename}",
                "path": str(path),
            }
        )
    return {"items": saved}
