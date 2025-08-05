from celery import shared_task
import time # For simulating delay
from django.core.mail import send_mail
from django.conf import settings
from apiApp.models import Order, Product # Assuming these models exist

@shared_task
def send_order_confirmation_email(order_id):
    """
    Task to send an order confirmation email.
    """
    try:
        order = Order.objects.get(id=order_id)
        subject = f'Order Confirmation - Order #{order.id}'
        message = f'Dear {order.customer_name},\n\nYour order #{order.id} has been confirmed. Total: ${order.total_price}\n\nThank you for your purchase!'
        from_email = settings.EMAIL_HOST_USER # You'll need to configure email settings in settings.py
        recipient_list = [order.customer_email]

        # Simulate email sending delay
        time.sleep(5)
        send_mail(subject, message, from_email, recipient_list, fail_silently=False)
        print(f"Order confirmation email sent for Order #{order_id}")
    except Order.DoesNotExist:
        print(f"Order with ID {order_id} not found for email confirmation.")
    except Exception as e:
        print(f"Error sending email for Order #{order_id}: {e}")

@shared_task
def process_pay_on_delivery_order(order_id):
    """
    Task to process "Pay on Delivery" order creation.
    This might involve updating order status, logging, etc.
    """
    try:
        order = Order.objects.get(id=order_id)
        # Simulate processing logic
        time.sleep(3)
        order.status = 'Processing' # Example status update
        order.save()
        print(f"Processed 'Pay on Delivery' for Order #{order_id}")
    except Order.DoesNotExist:
        print(f"Order with ID {order_id} not found for 'Pay on Delivery' processing.")
    except Exception as e:
        print(f"Error processing 'Pay on Delivery' for Order #{order_id}: {e}")

@shared_task
def update_stock_after_order(product_id, quantity_ordered):
    """
    Task to asynchronously update product stock after an order is placed.
    """
    try:
        product = Product.objects.get(id=product_id)
        # Ensure stock doesn't go below zero
        if product.stock >= quantity_ordered:
            product.stock -= quantity_ordered
            product.save()
            print(f"Updated stock for Product ID {product_id}: new stock = {product.stock}")
        else:
            print(f"Insufficient stock for Product ID {product_id}. Current stock: {product.stock}, Ordered: {quantity_ordered}")
    except Product.DoesNotExist:
        print(f"Product with ID {product_id} not found for stock update.")
    except Exception as e:
        print(f"Error updating stock for Product ID {product_id}: {e}")
