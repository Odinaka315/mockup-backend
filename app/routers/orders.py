from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from .. import models, schemas, database, oauth2

router = APIRouter(
    prefix="/api/v1/orders",
    tags=["Orders & Checkout"]
)

@router.post("/checkout", status_code=status.HTTP_201_CREATED, response_model=schemas.OrderResponse)
def checkout(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(oauth2.get_current_user)
):
    # 1. Fetch the user's cart
    cart_items = db.query(models.CartItem).filter(models.CartItem.user_id == current_user.id).all()
    
    if not cart_items:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Your cart is empty")

    total_price = 0
    order_items_to_create = []

    # 2. Loop through cart to validate inventory and calculate totals dynamically
    for item in cart_items:
        product = db.query(models.Product).filter(models.Product.id == item.product_id).first()
        
        # Safety check: Does product still exist?
        if not product:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail=f"Product ID {item.product_id} no longer exists."
            )
        
        # Safety check: Is there enough stock right now?
        if product.inventory_quantity < item.quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail=f"Not enough stock for '{product.title}'. Only {product.inventory_quantity} left."
            )
        
        # Calculate subtotal (Frontend cannot be trusted with prices)
        total_price += (product.price * item.quantity)

        # Prep the OrderItem (Notice we use your model's field name 'inventory_quantity' for amount bought)
        new_order_item = models.OrderItem(
            product_id=product.id,
            inventory_quantity=item.quantity, 
            price=product.price,
            price_at_purchase=product.price
        )
        order_items_to_create.append((new_order_item, product, item.quantity))

    # 3. Create the Main Order Record
    new_order = models.Order(
        user_id=current_user.id,
        total_price=total_price,
        status="Pending"
    )
    db.add(new_order)
    db.flush() # Flushes to DB to generate the new_order.id without committing

    # 4. Save OrderItems & Deduct Stock
    for order_item, product, purchased_qty in order_items_to_create:
        # Link the generated order ID to each item
        order_item.order_id = new_order.id 
        db.add(order_item)
        
        # Deduct the stock from the actual product table
        product.inventory_quantity -= purchased_qty

    # 5. Clear the User's Cart
    db.query(models.CartItem).filter(models.CartItem.user_id == current_user.id).delete(synchronize_session=False)

    # 6. Commit the entire transaction!
    db.commit()
    db.refresh(new_order)

    return new_order

from typing import List

@router.get("/me", response_model=List[schemas.OrderHistoryResponse])
def get_my_orders(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(oauth2.get_current_user)
):
    # Fetch all orders belonging to the logged-in user
    orders = db.query(models.Order).filter(models.Order.user_id == current_user.id).all()
    
    if not orders:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="You have no previous orders."
        )
        
    return orders

# 2. ADMIN ONLY: GET ALL PLATFORM ORDERS
# Notice the dependency is now `get_current_admin_user`!
@router.get("/", response_model=List[schemas.OrderHistoryResponse])
def get_all_orders(
    db: Session = Depends(database.get_db),
    current_admin: models.User = Depends(oauth2.get_current_admin_user) 
):
    orders = db.query(models.Order).all()
    return orders


# 3. GET SPECIFIC ORDER BY ID (Smart permissions)
@router.get("/{id}", response_model=schemas.OrderHistoryResponse)
def get_order_by_id(
    id: int, 
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(oauth2.get_current_user)
):
    order = db.query(models.Order).filter(models.Order.id == id).first()
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    # SECURITY LOGIC: 
    # If the user is NOT an admin AND they don't own this order, block them.
    if not current_user.is_admin and order.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Not authorized to view this order"
        )
        
    return order

@router.patch("/{id}/status", response_model=schemas.OrderResponse)
def update_order_status(
    id: int,
    payload: schemas.OrderStatusUpdate,
    db: Session = Depends(database.get_db),
    # 1. Lock this down to admins only
    current_admin: models.User = Depends(oauth2.get_current_admin_user)
):
    # 2. Fetch the order
    order_query = db.query(models.Order).filter(models.Order.id == id)
    order = order_query.first()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Order not found"
        )

    # 3. Prevent "Un-cancelling"
    # If it was cancelled, the stock was returned. Changing it back to pending 
    # could sell stock that no longer exists. Force them to make a new order.
    if order.status == "Cancelled" and payload.status != "Cancelled":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot change the status of a cancelled order. Please create a new order."
        )

    # 4. Inventory Restoration Logic
    # Only restore stock if the order wasn't already cancelled
    if payload.status == "Cancelled" and order.status != "Cancelled":
        
        # Loop through the items inside this specific order
        for order_item in order.items:
            # Find the original product
            product = db.query(models.Product).filter(models.Product.id == order_item.product_id).first()
            
            # If the product hasn't been deleted from the database entirely, restore the stock
            if product:
                product.inventory_quantity += order_item.inventory_quantity

    # 5. Finally, update the status and commit
    order_query.update({"status": payload.status}, synchronize_session=False)
    db.commit()
    db.refresh(order)

    return order