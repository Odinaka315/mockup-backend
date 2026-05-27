from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from .. import models, database, oauth2

router = APIRouter(prefix="/api/v1/analytics", tags=["Analytics"])

@router.get("/summary")
def get_analytics_summary(
    db: Session = Depends(database.get_db),
    current_admin: models.User = Depends(oauth2.get_current_admin_user)
):
    # 1. Total Products
    total_products = db.query(models.Product).count()

    # 2. Total Users (Customers)
    total_users = db.query(models.User).filter(models.User.is_admin == False).count()

    # 3. Total Orders
    total_orders = db.query(models.Order).count()

    # 4. Total Revenue (Only count orders that aren't cancelled)
    revenue_query = db.query(func.sum(models.Order.total_price)).filter(
        models.Order.status != "Cancelled"
    ).scalar()
    
    # If there are no orders yet, revenue_query will be None. Default to 0.0
    total_revenue = revenue_query if revenue_query else 0.0

    return {
        "total_revenue": total_revenue,
        "total_orders": total_orders,
        "total_users": total_users,
        "total_products": total_products
    }