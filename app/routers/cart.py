from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from .. import models, schemas, database, oauth2

router = APIRouter(
    prefix="/api/v1/cart", 
    tags=["Shopping Cart"]
    )

# 1. GET ALL ITEMS IN USER'S CART

@router.get("/", response_model=schemas.CartSummaryResponse)
def get_cart(
    db: Session = Depends(database.get_db), 
    current_user: models.User = Depends(oauth2.get_current_user)
):
    
    cart_items = db.query(models.CartItem).filter(models.CartItem.user_id == current_user.id).all()
    
   
    total_price = 0
    total_quantity = 0
    
   
    for item in cart_items:
        
        total_price += (item.product.price * item.quantity)
        total_quantity += item.quantity
        
    
    return {
        "total_price": total_price,
        "total_quantity": total_quantity,
        "items": cart_items
    }


# 2. ADD ITEM TO CART (OR INCREMENT QUANTITY IF ALREADY EXISTS)
@router.post("/", status_code=status.HTTP_201_CREATED, response_model=schemas.CartItemResponse)
def add_to_cart(
    item: schemas.CartItemCreate, 
    db: Session = Depends(database.get_db), 
    current_user: models.User = Depends(oauth2.get_current_user)
):
    # Check if product exists and has enough stock
    product = db.query(models.Product).filter(models.Product.id == item.product_id).first()
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    if product.inventory_quantity < item.quantity:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Only {product.inventory_quantity} items in stock")

    # Check if this item is already in the user's cart
    existing_item = db.query(models.CartItem).filter(
        models.CartItem.user_id == current_user.id,
        models.CartItem.product_id == item.product_id
    ).first()

    if existing_item:
        # If it exists, update the quantity
        new_quantity = existing_item.quantity + item.quantity
        if product.inventory_quantity < new_quantity:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot add more; exceeds available stock")
        existing_item.quantity = new_quantity
        db.commit()
        db.refresh(existing_item)
        return existing_item
    
    # If it's a new item, create a new record
    new_cart_item = models.CartItem(user_id=current_user.id, **item.model_dump())
    db.add(new_cart_item)
    db.commit()
    db.refresh(new_cart_item)
    return new_cart_item


# 3. DELETE ITEM FROM CART
# Change from @router.delete to @router.patch and remove the id from the URL string
@router.patch("/remove", response_model=schemas.CartItemResponse)
def remove_from_cart(
    payload: schemas.CartItemReduce, 
    db: Session = Depends(database.get_db), 
    current_user: models.User = Depends(oauth2.get_current_user)
):
    # 1. Find if the item actually exists in the user's cart
    cart_item_query = db.query(models.CartItem).filter(
        models.CartItem.user_id == current_user.id, 
        models.CartItem.product_id == payload.product_id
    )
    
    cart_item = cart_item_query.first()
    if not cart_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Item not found in your cart"
        )
        
    # 2. Calculate the new quantity remaining
    new_quantity = cart_item.quantity - payload.reduce_by

    # 3. If the deduction drops the quantity to 0 or below, delete the row entirely
    if new_quantity <= 0:
        cart_item_query.delete(synchronize_session=False)
        db.commit()
        # Return a custom message or construct an empty response structure
        raise HTTPException(
            status_code=status.HTTP_200_OK, 
            detail="Item completely removed from cart because quantity reached 0"
        )
        
    # 4. Otherwise, update the row with the subtracted quantity
    cart_item_query.update({"quantity": new_quantity}, synchronize_session=False)
    db.commit()
    db.refresh(cart_item)
    
    return cart_item