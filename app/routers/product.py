from .. import models, schemas, utils, oauth2
from fastapi import  FastAPI, Response, status, HTTPException, Depends, APIRouter
from sqlalchemy.orm import Session
from ..database import get_db
from typing import Optional
from sqlalchemy import func

router = APIRouter(
    prefix="/api/v1/products",
    tags=["Products"]
)

@router.get("/", response_model=list[schemas.ProductResponse])
def get_products(db: Session = Depends(get_db), current_user: int = Depends(oauth2.get_current_user), limit: int = 10, skip: int = 0, search: Optional[str] = ""):

    products = db.query(models.Product).filter(
    models.Product.title.contains(search)).limit(limit).offset(skip).all()
    
    return products

@router.post("/", status_code=status.HTTP_201_CREATED, response_model=schemas.ProductResponse)
def create_product(product: schemas.ProductCreate, db: Session = Depends(get_db)):
   
  
    new_product = models.Product(**product.model_dump())
    db.add(new_product)
    db.commit()
    db.refresh(new_product)
    return new_product




@router.patch("/{id}/inventory", response_model=schemas.ProductResponse)
def update_product_inventory(
    id: int, 
    payload: schemas.InventoryUpdate, 
    db: Session = Depends(get_db)
     # Keeping authentication
):
    # 1. Query the database for the specific product
    product_query = db.query(models.Product).filter(models.Product.id == id)
    product = product_query.first()

    # 2. If product doesn't exist, raise a 404 error
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with id {id} was not found"
        )
        
    # Optional Security Check: Ensure the current user owns this product
    # if product.owner_id != current_user.id:
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN,
    #         detail="Not authorized to perform requested action"
    #     )

    # 3. Calculate the new inventory amount
    # Assuming your model's field is named 'inventory' or 'quantity'
    new_inventory = product.inventory_quantity + payload.inventory_change

    # 4. Prevent inventory from dropping below zero
    if new_inventory < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Operation failed. Stock cannot drop below 0. Current stock: {product.inventory_quantity}"
        )

    # 5. Update the database using SQLAlchemy's update method
    product_query.update({"inventory_quantity": new_inventory}, synchronize_session=False)
    db.commit()
    db.refresh(product)

    return product