from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from .. import models, schemas, database, oauth2

router = APIRouter(
    prefix="/api/v1/wishlist", 
    tags=["Wishlist"]
)

# 1. GET: Fetch all items in the user's wishlist
@router.get("/", response_model=List[schemas.WishlistItemResponse])
def get_wishlist(
    db: Session = Depends(database.get_db), 
    current_user: models.User = Depends(oauth2.get_current_user)
):
    wishlist = db.query(models.WishlistItem).filter(models.WishlistItem.user_id == current_user.id).all()
    return wishlist


# 2. POST: Add an item to the wishlist
@router.post("/{product_id}", status_code=status.HTTP_201_CREATED)
def add_to_wishlist(
    product_id: int, 
    db: Session = Depends(database.get_db), 
    current_user: models.User = Depends(oauth2.get_current_user)
):
    # Check if product actually exists
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    # Check if already in wishlist
    existing_item = db.query(models.WishlistItem).filter(
        models.WishlistItem.user_id == current_user.id,
        models.WishlistItem.product_id == product_id
    ).first()
    
    if existing_item:
        return {"message": "Product is already in your wishlist"}

    # Add to wishlist
    new_item = models.WishlistItem(user_id=current_user.id, product_id=product_id)
    db.add(new_item)
    db.commit()
    
    return {"message": "Added to wishlist"}


# 3. DELETE: Remove an item from the wishlist
@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_from_wishlist(
    product_id: int, 
    db: Session = Depends(database.get_db), 
    current_user: models.User = Depends(oauth2.get_current_user)
):
    item_query = db.query(models.WishlistItem).filter(
        models.WishlistItem.user_id == current_user.id,
        models.WishlistItem.product_id == product_id
    )
    
    if not item_query.first():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found in wishlist")
        
    item_query.delete(synchronize_session=False)
    db.commit()