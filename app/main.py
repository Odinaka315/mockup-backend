from fastapi import  FastAPI
# from . import models
# from .database import engine
from . routers import product, user, auth, cart, orders, wishlist, reviews, analytics
# from .config import settings
from fastapi.middleware.cors import CORSMiddleware
import cloudinary
from .config import settings
# print(settings.database_password)

# models.Base.metadata.create_all(bind=engine)
app = FastAPI(title="Mockup E-Commerce API")

origins = [
    "http://localhost:5173",
    "http://localhost:3000", # Good to have if you ever run on port 3000
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(product.router)
app.include_router(user.router)
app.include_router(auth.router)
app.include_router(cart.router)
app.include_router(orders.router)
app.include_router(wishlist.router)
app.include_router(reviews.router)
app.include_router(analytics.router)

cloudinary.config( 
  cloud_name = settings.cloudinary_name, 
  api_key = settings.cloudinary_api_key, 
  api_secret = settings.cloudinary_api_secret,
  secure = settings.cloudinary_secure
)

@app.get("/")
async def root():
    return {"message": "Welcome to the E-Commerce API"}



