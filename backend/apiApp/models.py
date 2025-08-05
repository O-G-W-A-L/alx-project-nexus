from django.conf import settings
from django.db import models, transaction, IntegrityError
from django.utils.text import slugify
from django.contrib.auth.models import AbstractUser
from django.db.models import F

class CustomUser(AbstractUser):
    """
    Custom User model for the e-commerce application.
    Extends Django's AbstractUser to allow for email-based authentication
    and an optional profile picture URL.
    """
    email = models.EmailField(unique=True, help_text="Required. User's email address, must be unique.")
    profile_picture_url = models.URLField(blank=True, null=True, help_text="Optional URL for the user's profile picture.")

    def __str__(self):
        """Returns the email as the string representation of the user."""
        return self.email
    
class Category(models.Model):
    """
    Represents a product category in the e-commerce store.
    Categories are ordered by name by default.
    """
    name = models.CharField(max_length=100, help_text="Name of the product category.")
    slug = models.SlugField(unique=True, blank=True, db_index=True, help_text="URL-friendly unique identifier for the category.")
    image = models.FileField(upload_to="category_img", blank=True, null=True, help_text="Optional image for the category.")

    class Meta:
        ordering = ['name'] # Default ordering for categories
        verbose_name_plural = "Categories" # Correct plural name for admin interface

    def __str__(self):
        """Returns the category name as its string representation."""
        return self.name

    def save(self, *args, **kwargs):
        """
        Overrides the save method to automatically generate a unique slug
        from the category name if one is not provided.
        Ensures slug uniqueness by appending a counter if necessary.
        """
        if not self.slug:
            base_slug = slugify(self.name)
            self.slug = base_slug
            counter = 1
            # Ensure slug uniqueness by appending a counter
            while Category.objects.filter(slug=self.slug).exists():
                self.slug = f"{base_slug}-{counter}"
                counter += 1
        super().save(*args, **kwargs) # Call super().save() after a unique slug is found or if slug exists

class Product(models.Model):
    """
    Represents a product available in the e-commerce store.
    Includes details like name, description, price, stock, and category.
    """
    name = models.CharField(max_length=100, help_text="Name of the product.")
    description = models.TextField(help_text="Detailed description of the product.")
    price = models.DecimalField(max_digits=10, decimal_places=2, help_text="Price of the product.")
    stock = models.PositiveIntegerField(default=0, help_text="Current stock quantity of the product.")
    slug = models.SlugField(unique=True, blank=True, db_index=True, help_text="URL-friendly unique identifier for the product.")
    image = models.ImageField(upload_to="product_img", blank=True, null=True, help_text="Optional image for the product.")
    featured = models.BooleanField(default=False, help_text="Indicates if the product is featured.")
    category = models.ForeignKey(
        Category, 
        on_delete=models.SET_NULL, 
        related_name="products",  
        blank=True, 
        null=True, 
        db_index=True,
        help_text="The category to which the product belongs."
    )

    class Meta:
        ordering = ['name'] # Default ordering for products

    def __str__(self):
        """Returns the product name as its string representation."""
        return self.name
    
    def save(self, *args, **kwargs):
        """
        Overrides the save method to automatically generate a unique slug
        from the product name if one is not provided.
        Ensures slug uniqueness by appending a counter if necessary.
        """
        if not self.slug:
            base_slug = slugify(self.name)
            self.slug = base_slug
            counter = 1
            # Ensure slug uniqueness by appending a counter
            while Product.objects.filter(slug=self.slug).exists():
                self.slug = f"{base_slug}-{counter}"
                counter += 1
        super().save(*args, **kwargs) # Call super().save() after a unique slug is found or if slug exists

class Cart(models.Model):
    """
    Represents a shopping cart, which can be associated with a user or be anonymous.
    Each cart has a unique code for identification.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name="carts", 
        null=True, 
        blank=True,
        help_text="The user to whom this cart belongs (can be null for anonymous carts)."
    )
    cart_code = models.CharField(max_length=11, unique=True, db_index=True, help_text="Unique 11-character alphanumeric code for the cart.")
    created_at = models.DateTimeField(auto_now_add=True, help_text="Timestamp when the cart was created.")
    updated_at = models.DateTimeField(auto_now=True, help_text="Timestamp when the cart was last updated.")

    def __str__(self):
        """Returns the cart code as its string representation."""
        return self.cart_code

    @staticmethod
    def generate_unique_cart_code():
        """
        Generates a unique 11-character alphanumeric cart code using UUID.
        Ensures the generated code does not already exist in the database.
        """
        import uuid # Import uuid here to avoid circular dependency if Cart is imported early
        while True:
            code = str(uuid.uuid4().hex)[:11].upper()
            if not Cart.objects.filter(cart_code=code).exists():
                return code



class CartItem(models.Model):
    """
    Represents an item within a shopping cart, linking a product to a cart
    with a specified quantity.
    """
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="cartitems", help_text="The cart to which this item belongs.")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="item", help_text="The product added to the cart.")
    quantity = models.IntegerField(default=1, help_text="The quantity of the product in the cart.")

    def __str__(self):
        """Returns a string representation of the cart item."""
        return f"{self.quantity} x {self.product.name} in cart {self.cart.cart_code}"
    
class Review(models.Model):
    """
    Represents a user's review for a specific product, including a rating.
    A user can only submit one review per product.
    """
    RATING_CHOICES = [
        (1, '1 - Poor'),
        (2, '2 - Fair'),
        (3, '3 - Good'),
        (4, '4 - Very Good'),
        (5, '5 - Excellent'),
    ]

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="reviews", help_text="The product being reviewed.")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reviews", help_text="The user who submitted the review.")
    rating = models.PositiveIntegerField(choices=RATING_CHOICES, help_text="The rating given to the product (1-5).")
    review = models.TextField(help_text="The text content of the review.")
    created = models.DateTimeField(auto_now_add=True, help_text="Timestamp when the review was created.")
    updated = models.DateTimeField(auto_now=True, help_text="Timestamp when the review was last updated.")

    def __str__(self):
        """Returns a string representation of the review."""
        return f"{self.user.username}'s review on {self.product.name}"
    
    class Meta:
        unique_together = ["user", "product"] # Ensures a user can only review a product once
        ordering = ["-created"] # Order reviews by creation date, newest first

class ProductRating(models.Model):
    """
    Stores aggregated rating information for a product, including
    its average rating and total number of reviews.
    This is a OneToOne field to avoid recalculating on every product view.
    """
    product = models.OneToOneField(Product, on_delete=models.CASCADE, related_name='rating', help_text="The product for which this rating applies.")
    average_rating = models.FloatField(default=0.0, help_text="The calculated average rating for the product.")
    total_reviews = models.PositiveIntegerField(default=0, help_text="The total number of reviews for the product.")

    def __str__(self):
        """Returns a string representation of the product's rating."""
        return f"{self.product.name} - {self.average_rating} ({self.total_reviews} reviews)"

class Wishlist(models.Model):
    """
    Represents a user's wishlist, allowing them to save products for later.
    A user can only add a specific product to their wishlist once.
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="wishlists", help_text="The user who owns this wishlist entry.")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="wishlist", help_text="The product added to the wishlist.")
    created = models.DateTimeField(auto_now_add=True, help_text="Timestamp when the product was added to the wishlist.") 

    class Meta:
        unique_together = ["user", "product"] # Ensures a product can only be in a user's wishlist once

    def __str__(self):
        """Returns a string representation of the wishlist entry."""
        return f"{self.user.username} - {self.product.name}"
    
class Order(models.Model):
    """
    Represents a customer's order, typically created after a successful payment.
    Stores payment details, amount, currency, customer email, and status.
    """
    PAYMENT_CHOICES = [
        ("COD", "Cash on Delivery"),
        ("ONLINE", "Online Payment"),
    ]

    ORDER_STATUS_CHOICES = [
        ("Pending Delivery", "Pending Delivery"),
        ("Processing", "Processing"),
        ("Paid", "Paid"),
        ("Cancelled", "Cancelled"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="orders",
        null=True, # Make user nullable for existing orders
        blank=True,
        help_text="The user who placed this order."
    )
    stripe_checkout_id = models.CharField(max_length=255, unique=True, db_index=True, null=True, blank=True, help_text="Unique ID from Stripe Checkout Session (optional, for online payments).")
    amount = models.DecimalField(max_digits=10, decimal_places=2, help_text="Total amount of the order.")
    currency = models.CharField(max_length=10, help_text="Currency of the order (e.g., 'usd').")
    customer_email = models.EmailField(db_index=True, help_text="Email of the customer who placed the order.")
    payment_method = models.CharField(
        max_length=10,
        choices=PAYMENT_CHOICES,
        default="COD", # Provide a default for existing rows
        help_text="Method of payment for the order."
    )
    status = models.CharField(
        max_length=20,
        choices=ORDER_STATUS_CHOICES,
        default="Pending Delivery", # Default status for new orders
        help_text="Current status of the order (e.g., 'Pending Delivery', 'Paid')."
    )
    created_at = models.DateTimeField(auto_now_add=True, help_text="Timestamp when the order was created.")

    def __str__(self):
        """Returns a string representation of the order."""
        return f"Order {self.stripe_checkout_id} - {self.status}"
    
class OrderItem(models.Model):
    """
    Represents a single item within an order, linking a product to an order
    with a specified quantity.
    """
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE, help_text="The order to which this item belongs.")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, help_text="The product included in the order.")
    quantity = models.IntegerField(default=1, help_text="The quantity of the product in the order.")

    def __str__(self):
        """Returns a string representation of the order item."""
        return f"Order {self.product.name} - {self.order.stripe_checkout_id}"

class CustomerAddress(models.Model):
    """
    Stores a customer's shipping or billing address.
    Each customer can have one primary address.
    """
    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, help_text="The customer to whom this address belongs.")
    street = models.CharField(max_length=50, blank=True, null=True, help_text="Street address.")
    state = models.CharField(max_length=50, blank=True, null=True, help_text="State or province.")
    city = models.CharField(max_length=50, blank=True, null=True, help_text="City.")
    phone = models.CharField(max_length=13, blank=True, null=True, help_text="Phone number associated with the address.")

    def __str__(self):
        """Returns a string representation of the customer address."""
        return f"{self.customer.email} - {self.street} - {self.city}"
