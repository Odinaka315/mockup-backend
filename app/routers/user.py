from .. import models, schemas, oauth2
from fastapi import status, HTTPException, Depends, APIRouter, UploadFile, File
from sqlalchemy.orm import Session
from ..database import get_db
from typing import Optional
import cloudinary.uploader
from .. import utils

router = APIRouter(
    prefix="/api/v1/users",
    tags=["Users"]
)


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=schemas.UserOut)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
   
    
    hashed_password = utils.hash(user.password)
    
    user_data = user.model_dump()
    user_data["password"] = hashed_password
    

    new_user = models.User(**user_data)  # ✅ use user_data, not user.model_dump()
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

# Make sure to import this at the top of users.py!


@router.post("/me/image", response_model=schemas.UserOut)
def upload_profile_image(
    file: UploadFile = File(...), 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user)
):
    # 1. Validate that the file is actually an image
    if not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="The provided file is not an image."
        )

    # 2. Stream the file directly to Cloudinary
    try:
        # Notice we changed the folder name so avatars stay separate from products!
        result = cloudinary.uploader.upload(
            file.file, 
            folder="ecommerce_mockup/avatars" 
        )
        
        # Extract the secure HTTPS URL
        image_url = result.get("secure_url")
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Failed to upload image to Cloudinary: {str(e)}"
        )

    # 3. Save the new Cloudinary URL to the User's database row
    user_query = db.query(models.User).filter(models.User.id == current_user.id)
    user_query.update({"profile_image_url": image_url}, synchronize_session=False)
    
    db.commit()
    db.refresh(current_user)

    return current_user