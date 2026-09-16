from typing import Annotated
import uuid
from cloudinary.exceptions import BadRequest, Error
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.concurrency import run_in_threadpool
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.dependencies import get_current_user
from backend.errors import ProductsException
from backend.external.database import get_session
from backend.models.users import Users
from backend.schemas.product import ProductCreate, ProductUpdate
from backend.services.product import ProductService
from backend.core.logging import get_app_logger
from backend.authorization import RoleChecker
import cloudinary.uploader

product_router = APIRouter()
product_service = ProductService()
logger = get_app_logger(__name__)

vendor_role = RoleChecker(["vendor"])


@product_router.get("")
async def get_products(session: Annotated[AsyncSession, Depends(get_session)]):
    logger.info("Attempting to get products")
    products = await product_service.get_all_products(session)

    if not products:
        logger.warning("No products found")
        raise ProductsException

    return products


@product_router.get("/vendor/{vendor_id}")
async def get_vendor_products(
    vendor_id: str, session: Annotated[AsyncSession, Depends(get_session)]
):
    try:
        vendor_uuid = uuid.UUID(vendor_id)
    except ValueError:
        logger.warning(f"Invalid UUID format for vendor_id: {vendor_id}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid vendor ID format. Must be a valid UUID.",
        )

    products = await product_service.get_products_by_vendor_id(vendor_uuid, session)

    if not products:
        logger.warning(f"No products found for vendor: {vendor_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No products found for vendor ID {vendor_id}",
        )

    return products


@product_router.get("/{product_id}")
async def get_product(
    product_id: str, session: Annotated[AsyncSession, Depends(get_session)]
):
    try:
        product_uuid = uuid.UUID(product_id)
    except ValueError:
        logger.warning(f"Invalid UUID format for vendor_id: {product_id}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid product ID format. Must be a valid UUID.",
        )

    product = await product_service.get_product(product_uuid, session)

    if not product:
        logger.warning(f"No products found for product ID: {product_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No products found for product ID {product_id}",
        )

    return product


@product_router.post(
    "", status_code=status.HTTP_201_CREATED, dependencies=[Depends(vendor_role)]
)
async def create_product(
    product_data_str: Annotated[str, Form(alias="product_data")],
    current_user: Annotated[Users, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
    images: Annotated[list[UploadFile] | None, File()] = None,
):
    try:
        product_data = ProductCreate.model_validate_json(product_data_str)
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=e.errors()
        )

    # 1. VALIDATION PHASE: Validate all files upfront before uploading anything
    if images:
        allowed_img_extensions = {"jpg", "jpeg", "png", "gif", "webp"}
        allowed_img_types = {"image/jpeg", "image/png", "image/gif", "image/webp"}

        for image in images:
            img_ext = (
                image.filename.split(".")[-1].lower() if "." in image.filename else ""
            )
            if img_ext not in allowed_img_extensions:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid image file extension for file '{image.filename}'",
                )

            file_bytes = await image.read()
            if len(file_bytes) > 10 * 1024 * 1024:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Image '{image.filename}' size is too large (Max 10MB)",
                )

            if image.content_type not in allowed_img_types:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid image content type for file '{image.filename}'",
                )

            await image.seek(0)

    image_urls: list[str] = []
    if images:
        for image in images:
            file_bytes = await image.read()
            try:
                unique_id = uuid.uuid4().hex[:8]
                base_img_name = (
                    image.filename.rsplit(".", 1)[0]
                    if "." in image.filename
                    else image.filename
                )

                upload_result = await run_in_threadpool(
                    cloudinary.uploader.upload,
                    file_bytes,
                    public_id=f"vendors/products/{base_img_name}_{unique_id}",
                    overwrite=True,
                )
                image_url = upload_result.get("secure_url")
                if image_url:
                    image_urls.append(image_url)
            except (BadRequest, Error) as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Image upload failed for '{image.filename}': {e!s}",
                )

    # Persist data
    created_product = await product_service.create_product(
        vendor_id=current_user.id,
        product_data=product_data,
        images=image_urls,
        session=session,
    )
    return created_product


@product_router.patch("/{product_id}", dependencies=[Depends(vendor_role)])
async def edit_product(
    product_id: str,
    product_data_str: Annotated[str, Form(alias="product_data")],
    current_user: Annotated[Users, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
    images: Annotated[list[UploadFile] | None, File()] = None,
):
    try:
        user_data = ProductUpdate.model_validate_json(product_data_str)
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=e.errors()
        )

    product = await product_service.get_product_by_id_and_vendor(
        product_id=product_id, vendor_id=current_user.id, session=session
    )
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found or not authorized",
        )

    update_data = user_data.model_dump(exclude_unset=True)

    if images:
        allowed_img_types = {"image/png", "image/jpeg", "image/jpg", "image/webp"}
        for image in images:
            file_bytes = await image.read()
            if (
                len(file_bytes) > 10 * 1024 * 1024
                or image.content_type not in allowed_img_types
            ):
                raise HTTPException(
                    status_code=400,
                    detail=f"Validation failed for image '{image.filename}'",
                )
            await image.seek(0)

    image_urls: list[str] = []
    if images:
        for image in images:
            file_bytes = await image.read()
            try:
                unique_id = uuid.uuid4().hex[:8]
                base_img_name = (
                    image.filename.rsplit(".", 1)[0]
                    if "." in image.filename
                    else image.filename
                )
                upload_result = await run_in_threadpool(
                    cloudinary.uploader.upload,
                    file_bytes,
                    public_id=f"vendors/products/{base_img_name}_{unique_id}",
                    overwrite=True,
                )
                if url := upload_result.get("secure_url"):
                    image_urls.append(url)
            except (BadRequest, Error) as e:
                raise HTTPException(
                    status_code=500, detail=f"Image upload failed: {e!s}"
                )

    if not update_data and not image_urls:
        raise HTTPException(status_code=400, detail="No fields provided for updates.")

    updated_product = await product_service.update_product(
        product_id=product_id,
        vendor_id=current_user.id,
        product_data=update_data,
        images=image_urls if image_urls else None,
        session=session,
    )

    if not updated_product:
        raise HTTPException(status_code=400, detail="Failed to update product.")

    return updated_product
