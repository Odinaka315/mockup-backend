from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import Optional, Literal
from pydantic.types import conint

class ProductCreate(BaseModel):
    title: str
    price: int
    description: str
    category: str
    inventory_quantity: int

class ProductResponse(ProductCreate):
    id: int
    created_at: datetime

    class Config:
        orm_mode = True

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    surname: str
    firstname: str
    middlename: str


class UserOut(BaseModel):
    id: int
    email: EmailStr
    surname: str
    firstname: str
    middlename: str
    created_at: datetime

    class Config:
        from_attributes = True

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    id: Optional[str] = None

class InventoryUpdate(BaseModel):
    product_id: int
    
    inventory_change: int = Field(..., ne=0, description="Use positive numbers to add, negative to subtract.")

    class Config:
        orm_mode = True # If using Pydantic v2 (or orm_mode = True for v1)

class CartItemCreate(BaseModel):
    product_id: int
    quantity: int = Field(..., gt=0, description="Quantity must be greater than 0")

# Nested product data returned inside the cart response
class ProductInCart(BaseModel):
    id: int
    title: str
    price: float
    inventory_quantity: int

    class Config:
        from_attributes = True

# What we send back to the frontend
class CartItemResponse(BaseModel):
    id: int
    product_id: int
    quantity: int
    product: ProductInCart  # Nesting the product details

    class Config:
        from_attributes = True

class CartItemReduce(BaseModel):
    product_id: int
    reduce_by: int = Field(..., gt=0, description="The quantity you want to deduct from the cart")

class OrderResponse(BaseModel):
    id: int
    total_price: int
    status: str
    created_at: datetime

    class Config:
        from_attributes = True