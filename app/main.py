from fastapi import  FastAPI
# from . import models
# from .database import engine
from . routers import product, user, auth, cart, orders
# from .config import settings
from fastapi.middleware.cors import CORSMiddleware

# print(settings.database_password)

# models.Base.metadata.create_all(bind=engine)
app = FastAPI(title="Mockup E-Commerce API")

origins = ["*"]
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



@app.get("/")
async def root():
    return {"message": "World"}



