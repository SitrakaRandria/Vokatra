import cloudinary
import cloudinary.uploader
from typing import Optional, List
import logging
from app.config import settings

logger = logging.getLogger(__name__)

cloudinary.config(
    cloud_name=settings.CLOUDINARY_CLOUD_NAME,
    api_key=settings.CLOUDINARY_API_KEY,
    api_secret=settings.CLOUDINARY_API_SECRET
)

async def upload_image(file_bytes: bytes, folder: str = "listings") -> Optional[str]:
    try:
        result = cloudinary.uploader.upload(file_bytes, folder=folder)
        return result.get("secure_url")
    except Exception as e:
        logger.error(f"Erreur upload Cloudinary: {e}")
        return None

async def upload_multiple_images(files: List[bytes], folder: str = "listings") -> List[str]:
    urls = []
    for file in files:
        url = await upload_image(file, folder)
        if url:
            urls.append(url)
    return urls
