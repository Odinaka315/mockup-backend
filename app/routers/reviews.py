from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from .. import models, schemas, database, oauth2

# We map this to the products prefix to keep URLs RESTful
router = APIRouter(
    prefix="/api/v1/products",
    tags=["Reviews"]
)

@router.get("/{product_id}/reviews", response_model=List[schemas.ReviewResponse])
def get_reviews(product_id: int, db: Session = Depends(database.get_db)):
    reviews = db.query(models.Review).filter(models.Review.product_id == product_id).order_by(models.Review.created_at.desc()).all()
    return reviews


@router.post("/{product_id}/reviews", response_model=schemas.ReviewResponse, status_code=status.HTTP_201_CREATED)
def create_review(
    product_id: int, 
    review: schemas.ReviewCreate, 
    db: Session = Depends(database.get_db), 
    current_user: models.User = Depends(oauth2.get_current_user)
):
    # 1. Verify the product exists
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    # 2. Check if the user already reviewed this product
    existing_review = db.query(models.Review).filter(
        models.Review.product_id == product_id,
        models.Review.user_id == current_user.id
    ).first()

    if existing_review:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You have already reviewed this product")

    # 3. Create and save the review
    new_review = models.Review(
        product_id=product_id,
        user_id=current_user.id,
        rating=review.rating,
        comment=review.comment
    )
    
    db.add(new_review)
    db.commit()
    db.refresh(new_review)

    return new_review