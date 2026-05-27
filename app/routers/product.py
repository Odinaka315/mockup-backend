from .. import models, schemas, oauth2
from fastapi import status, HTTPException, Depends, APIRouter, UploadFile, File
from sqlalchemy.orm import Session
from ..database import get_db
from typing import Optional
import cloudinary.uploader
from sqlalchemy import or_, func
from typing import List

router = APIRouter(
    prefix="/api/v1/products",
    tags=["Products"]
)


@router.get("/categories", response_model=List[str])
def get_categories(db: Session = Depends(get_db)):
    # Query distinct categories and filter out any None/Null values
    categories = db.query(models.Product.category).distinct().all()
    return [cat[0] for cat in categories if cat[0]]

# 2. UPDATED ENDPOINT: Handle category and sorting filters
@router.get("/", response_model=List[schemas.ProductResponse])
def get_products(
    db: Session = Depends(get_db),
    search: Optional[str] = "",
    category: Optional[str] = "", # NEW
    sort_by: Optional[str] = "",  # NEW
    limit: int = 100,
    randomize: bool = False
):
    # Base query with the search filter
    query = db.query(models.Product).filter(
        or_(
            models.Product.title.ilike(f"%{search}%"),
            models.Product.category.ilike(f"%{search}%")
        )
    )

    # Apply exactly matched category filter if requested
    if category:
        query = query.filter(models.Product.category.ilike(category))

    # Apply sorting logic
    if sort_by == "price_asc":
        query = query.order_by(models.Product.price.asc())
    elif sort_by == "price_desc":
        query = query.order_by(models.Product.price.desc())
    elif sort_by == "newest":
        query = query.order_by(models.Product.id.desc()) # ID acts as a proxy for newest
    elif randomize:
        # Only randomize if they aren't trying to sort by something specific
        query = query.order_by(func.random())

    products = query.limit(limit).all()
    return products

@router.post("/", status_code=status.HTTP_201_CREATED, response_model=schemas.ProductResponse)
def create_product(product: schemas.ProductCreate, db: Session = Depends(get_db), current_user: models.User = Depends(oauth2.get_current_admin_user)):
   
  
    new_product = models.Product(**product.model_dump())
    db.add(new_product)
    db.commit()
    db.refresh(new_product)
    return new_product

@router.put("/{id}", response_model=schemas.ProductResponse)
def update_product(
    id: int, 
    updated_product: schemas.ProductUpdate, 
    db: Session = Depends(get_db),
    current_admin: models.User = Depends(oauth2.get_current_admin_user)
):
    product_query = db.query(models.Product).filter(models.Product.id == id)
    product = product_query.first()

    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Product with id {id} not found")

    # Only update the fields that were actually provided (ignore None)
    update_data = updated_product.model_dump(exclude_unset=True)
    product_query.update(update_data, synchronize_session=False)
    db.commit()
    db.refresh(product)
    
    return product

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(
    id: int, 
    db: Session = Depends(get_db),
    current_admin: models.User = Depends(oauth2.get_current_admin_user)
):
    product_query = db.query(models.Product).filter(models.Product.id == id)
    
    if not product_query.first():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Product with id {id} not found")

    product_query.delete(synchronize_session=False)
    db.commit()
    return None

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

@router.get("/{id}", response_model=schemas.ProductResponse) # Make sure the response_model is added if you are strictly using schemas!
def get_product(id: int, db: Session = Depends(get_db)):
    # Query the database for the specific product ID
    product = db.query(models.Product).filter(models.Product.id == id).first()
    
    # If the product doesn't exist (e.g., someone typed a random ID in the URL)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=f"Product with ID {id} was not found"
        )
        
    return product




