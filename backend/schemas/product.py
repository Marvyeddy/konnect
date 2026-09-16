from typing import Optional
from pydantic import BaseModel


class ProductCreate(BaseModel):
    name: str
    description: str
    price: float
    discount: int
    in_stock: bool
    images: list[str] = []
    category: str


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    discount: Optional[int] = None
    in_stock: Optional[bool] = None
    category: Optional[str] = None
