from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import Optional, Literal, List
from pydantic.types import conint

class ProductCreate(BaseModel):
    title: str
    price: int
    description: str
    category: str
    inventory_quantity: int
    image_url: Optional[str] = None # Added here

class ProductResponse(ProductCreate):
    id: int
    title: str
    price: float
    image_url: str | None = None

    class Config:
        from_attributes = True

class ProductUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = Field(None, gt=0)
    inventory_quantity: Optional[int] = Field(None, ge=0)
    category: Optional[str] = None
    image_url: Optional[str] = None

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    surname: str
    firstname: str
    middlename: str
    is_admin: bool = False


class UserOut(BaseModel):
    id: int
    email: EmailStr
    surname: str
    firstname: str
    middlename: str
    created_at: datetime
    profile_image_url: Optional[str] = None
    is_admin: bool = False


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
        from_attributes = True 

class CartItemCreate(BaseModel):
    product_id: int
    quantity: int = Field(..., gt=0, description="Quantity must be greater than 0")

# Nested product data returned inside the cart response
class ProductInCart(BaseModel):
    id: int
    title: str
    price: float
    inventory_quantity: int
    image_url: str | None = None

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


# ... your existing CartItemResponse ...

class CartSummaryResponse(BaseModel):
    total_price: int
    total_quantity: int
    items: List[CartItemResponse]

    class Config:
        from_attributes = True

class CartItemReduce(BaseModel):
    product_id: int
    reduce_by: int = Field(..., gt=0, description="The quantity you want to deduct from the cart")

class OrderResponse(BaseModel):
    id: int
    user_id: int
    total_price: float
    status: str
    created_at: datetime
    items: List[OrderItemResponse] = []
    street: str
    city: str
    lga: str
    state: str
    country: str
    class Config:
        from_attributes = True

class OrderItemResponse(BaseModel):
    id: int
    product_id: int
    inventory_quantity: int
    price_at_purchase: float
    product: ProductResponse
    class Config:
        from_attributes = True

# What the full order looks like, inheriting your original OrderResponse
class OrderHistoryResponse(OrderResponse):
    user: UserOut
    items: List[OrderItemResponse] = []

class OrderStatusUpdate(BaseModel):
    # Literal enforces strict string matching
    status: Literal["Pending", "Processing", "Shipped", "Delivered", "Cancelled"] = Field(
        ..., description="The new status of the order"
    )

class UserUpdate(BaseModel):
    firstname: Optional[str] = None
    lastname: Optional[str] = None
    middlename: Optional[str] = None
    email: Optional[EmailStr] = None
    profile_image_url: Optional[str] = None

class WishlistItemResponse(BaseModel):
    id: int
    user_id: int
    product_id: int
    created_at: datetime
    
    # Include the nested product so React can show the image/title/price!
    product: ProductResponse 

    class Config:
        from_attributes = True

class ReviewCreate(BaseModel):
    rating: int = Field(ge=1, le=5, description="Rating must be between 1 and 5")
    comment: Optional[str] = None

class ReviewResponse(BaseModel):
    id: int
    product_id: int
    rating: int
    comment: Optional[str]
    created_at: datetime
    
    # Include the user so React can show who left the review
    user: UserOut 

    class Config:
        from_attributes = True

class CheckoutRequest(BaseModel):
    street: str
    city: str
    lga: str
    state: str
    country: str