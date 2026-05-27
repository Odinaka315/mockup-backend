from .. import models, schemas, oauth2
from fastapi import status, HTTPException, Depends, APIRouter, UploadFile, File
from sqlalchemy.orm import Session
from ..database import get_db
from typing import Optional, List
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

# app/routers/users.py

# ... your other user routes ...

@router.get("/me", response_model=schemas.UserOut)
def get_user_profile(current_user: models.User = Depends(oauth2.get_current_user)):
    """
    Returns the profile data of the currently logged-in user.
    """
    return current_user

@router.put("/me", response_model=schemas.UserOut)
def update_user(
    user_update: schemas.UserUpdate, 
    db: Session = Depends(get_db), 
    current_user: models.User = Depends(oauth2.get_current_user)
):
    # Fetch the specific user from the database
    user_query = db.query(models.User).filter(models.User.id == current_user.id)
    user = user_query.first()

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Create a dictionary of the fields the user actually wants to update (ignoring None values)
    update_data = user_update.model_dump(exclude_unset=True)

    # If they are trying to change their email, make sure it's not already taken
    if "email" in update_data and update_data["email"] != user.email:
        existing_user = db.query(models.User).filter(models.User.email == update_data["email"]).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="Email is already registered by another user"
            )

    # Update the database record
    user_query.update(update_data, synchronize_session=False)
    db.commit()
    db.refresh(user)

    return user

@router.get("/", response_model=List[schemas.UserOut])
def get_all_users(
    db: Session = Depends(get_db),
    current_admin: models.User = Depends(oauth2.get_current_admin_user) # Admin Lock!
):
    users = db.query(models.User).order_by(models.User.created_at.desc()).all()
    return users


@router.put("/{id}/role", response_model=schemas.UserOut)
def toggle_user_role(
    id: int, 
    db: Session = Depends(get_db),
    current_admin: models.User = Depends(oauth2.get_current_admin_user)
):
    # Prevent the admin from demoting themselves and locking themselves out!
    if id == current_admin.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You cannot change your own role.")

    user = db.query(models.User).filter(models.User.id == id).first()
    
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Flip the boolean
    user.is_admin = not user.is_admin
    db.commit()
    db.refresh(user)

    return user


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    id: int, 
    db: Session = Depends(get_db),
    current_admin: models.User = Depends(oauth2.get_current_admin_user)
):
    # Prevent self-deletion
    if id == current_admin.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You cannot delete your own account.")

    user_query = db.query(models.User).filter(models.User.id == id)
    
    if not user_query.first():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    user_query.delete(synchronize_session=False)
    db.commit()