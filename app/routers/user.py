from .. import models, schemas, utils
from fastapi import  FastAPI, Response, status, HTTPException, Depends, APIRouter
from sqlalchemy.orm import Session
from ..database import get_db

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