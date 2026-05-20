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