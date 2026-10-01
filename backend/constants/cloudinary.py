import uuid
import cloudinary.uploader
from starlette.concurrency import run_in_threadpool


async def upload_to_cloudinary(
    file_bytes: bytes, folder: str, filename: str, resource_type: str = "image"
) -> str:
    unique_id = uuid.uuid4().hex[:8]
    base = filename.rsplit(".", 1)[0] if "." in filename else filename
    result = await run_in_threadpool(
        cloudinary.uploader.upload,
        file_bytes,
        public_id=f"{folder}/{base}_{unique_id}",
        overwrite=True,
        resource_type=resource_type,
    )
    return result["secure_url"]
