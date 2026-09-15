from typing import Annotated
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.errors import ProductsException
from backend.external.database import get_session
from backend.services.product import ProductService
from backend.core.logging import get_app_logger

product_router = APIRouter()
product_service = ProductService()
logger = get_app_logger(__name__)


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
