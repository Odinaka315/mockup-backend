from .. import models, schemas, oauth2
from fastapi import status, HTTPException, Depends, APIRouter, UploadFile, File
from sqlalchemy.orm import Session
from ..database import get_db
from typing import Optional
import cloudinary.uploader

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
def create_product(product: schemas.ProductCreate, db: Session = Depends(get_db), current_user: models.User = Depends(oauth2.get_current_admin_user)):
   
  
    new_product = models.Product(**product.model_dump())
    db.add(new_product)
    db.commit()
    db.refresh(new_product)
    return new_product

@router.post("/{id}/image", response_model=schemas.ProductResponse)
def upload_product_image(
    id: int, 
    file: UploadFile = File(...), 
    db: Session = Depends(get_db),
    current_admin: models.User = Depends(oauth2.get_current_admin_user) # Locked to admins!
):
    # 1. Verify the product exists
    product_query = db.query(models.Product).filter(models.Product.id == id)
    product = product_query.first()
    
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # 2. Upload the file stream directly to Cloudinary
    try:
        # We pass the raw file stream directly to Cloudinary
        # We also tell it to organize these images into a specific folder in your dashboard
        result = cloudinary.uploader.upload(
            file.file, 
            folder="ecommerce_mockup/products" 
        )
        
        # Cloudinary returns a large dictionary. We just want the secure https URL:
        image_url = result.get("secure_url")
        
    except Exception as e:
        # If the upload fails (e.g., bad internet, wrong API keys), catch it safely
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"There was an error uploading the file to Cloudinary: {str(e)}"
        )

    # 3. Save that new Cloudinary URL string to the PostgreSQL database
    product_query.update({"image_url": image_url}, synchronize_session=False)
    db.commit()
    db.refresh(product)

    return product




@router.patch("/{id}/inventory", response_model=schemas.ProductResponse)
def update_product_inventory(
    id: int, 
    payload: schemas.InventoryUpdate, 
    db: Session = Depends(get_db),
    current_admin: models.User = Depends(oauth2.get_current_admin_user)
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