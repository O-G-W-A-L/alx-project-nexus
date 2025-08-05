from rest_framework import serializers 
from django.contrib.auth import get_user_model
from django.db import models # Import models for models.Q
from django.db.models import Count # Import Count for aggregation
from .models import Cart, CartItem, CustomerAddress, Order, OrderItem, Product, Category, ProductRating, Review, Wishlist

User = get_user_model()


class ProductListSerializer(serializers.ModelSerializer):
    """
    Serializer for listing product details, showing only essential fields.
    """
    class Meta:
        model = Product
        fields = ["id", "name", "slug", "image", "price"]


class UserSerializer(serializers.ModelSerializer):
    """
    Serializer for user creation and representation.
    Includes password handling for creation and excludes it for updates.
    """
    password = serializers.CharField(write_only=True, required=True, min_length=8, help_text="Required. User's password (write-only).")

    class Meta:
        model = User
        fields = ["id", "email", "username", "password", "first_name", "last_name", "profile_picture_url"]
        extra_kwargs = {'password': {'write_only': True}} # Ensure password is write-only

    def create(self, validated_data):
        """
        Creates and returns a new `User` instance, given the validated data.
        Handles password hashing using Django's `set_password`.
        """
        password = validated_data.pop('password')
        user = User.objects.create_user(**validated_data)
        user.set_password(password) # Django handles password hashing here
        user.save()
        return user
   
class ReviewSerializer(serializers.ModelSerializer):
    """
    Serializer for product reviews.
    Handles creation and validation of reviews, ensuring a user can only review a product once.
    """
    user = UserSerializer(read_only=True, help_text="The user who submitted the review (read-only).")
    class Meta:
        model = Review 
        fields = ["id", "user", "rating", "review", "created", "updated"]
        read_only_fields = ["user"] # User will be set from request.user in the view

class ProductRatingSerializer(serializers.ModelSerializer):
    """
    Serializer for displaying product rating information (average rating and total reviews).
    """
    class Meta:
        model = ProductRating 
        fields =[ "id", "average_rating", "total_reviews"]

    # Note: average_rating and total_reviews are typically updated via signals or directly in views
    # after a review is created/updated/deleted, not validated here.
    def validate_rating(self, value):
        """
        Validates that the rating is between 1 and 5.
        """
        if not (1 <= value <= 5):
            raise serializers.ValidationError({"detail": "Rating must be between 1 and 5."})
        return value

class ProductDetailSerializer(serializers.ModelSerializer):
    """
    Serializer for displaying detailed product information, including reviews,
    average rating, review counts by rating, and similar products.
    """
    reviews = ReviewSerializer(read_only=True, many=True, help_text="List of reviews for the product.") # N+1 potential: prefetch_related('reviews') in view
    rating = ProductRatingSerializer(read_only=True, help_text="Aggregated rating information for the product.") # N+1 potential: select_related('rating') in view
    review_counts = serializers.SerializerMethodField(help_text="Counts of reviews for each rating level (1-5).")
    similar_products = serializers.SerializerMethodField(help_text="List of similar products based on category.")

    class Meta:
        model = Product
        fields = ["id", "name", "description", "slug", "image", "price", "reviews", "rating", "similar_products", "review_counts"]
      
    def get_similar_products(self, product):
        """
        Retrieves a list of similar products based on the category of the current product.
        Excludes the current product from the list.
        """
        # Optimize by prefetching category if not already done in the view
        # Ensure category is selected/prefetched in the view to avoid N+1 for product.category
        products = Product.objects.filter(category=product.category).exclude(id=product.id).select_related('category')
        serializer = ProductListSerializer(products, many=True)
        return serializer.data
    
    def get_review_counts(self, product):
        """
        Counts the number of reviews for each rating level (1-5) for the product.
        Uses Django ORM annotations for efficient aggregation.
        """
        # Use annotations to get all review counts in a single query
        counts = product.reviews.aggregate(
            poor_review=Count('id', filter=models.Q(rating=1)),
            fair_review=Count('id', filter=models.Q(rating=2)),
            good_review=Count('id', filter=models.Q(rating=3)),
            very_good_review=Count('id', filter=models.Q(rating=4)),
            excellent_review=Count('id', filter=models.Q(rating=5))
        )
        return counts

class CategoryListSerializer(serializers.ModelSerializer):
    """
    Serializer for listing category details, showing only essential fields.
    """
    class Meta:
        model = Category
        fields = ["id", "name", "image", "slug"]

class CategoryDetailSerializer(serializers.ModelSerializer):
    """
    Serializer for displaying detailed category information, including products within the category.
    """
    products = ProductListSerializer(many=True, read_only=True, help_text="List of products belonging to this category.") # N+1 potential: prefetch_related('products') in view
    class Meta:
        model = Category
        fields = ["id", "name", "image", "products"]

class CartItemSerializer(serializers.ModelSerializer):
    """
    Serializer for cart items, including product details and sub-total calculation.
    """
    product = ProductListSerializer(read_only=True, help_text="The product in the cart item (read-only).") # N+1 potential: select_related('product') in view
    sub_total = serializers.SerializerMethodField(help_text="Calculated sub-total for this cart item (price * quantity).")
    class Meta:
        model = CartItem 
        fields = ["id", "product", "quantity", "sub_total"]
    
    def validate_quantity(self, value):
        """
        Validates that the quantity is at least 1.
        """
        if value < 1:
            raise serializers.ValidationError({"detail": "Quantity must be at least 1."})
        return value
    
    def get_sub_total(self, cartitem):
        """
        Calculates the sub-total for a cart item (product price * quantity).
        """
        total = cartitem.product.price * cartitem.quantity 
        return total

class CartSerializer(serializers.ModelSerializer):
    """
    Serializer for displaying full cart details, including all cart items and the total cart price.
    """
    cartitems = CartItemSerializer(read_only=True, many=True, help_text="List of items in the cart (read-only).") # N+1 potential: prefetch_related('cartitems__product') in view
    cart_total = serializers.SerializerMethodField(help_text="Calculated total price of all items in the cart.")
    class Meta:
        model = Cart 
        fields = ["id", "cart_code", "cartitems", "cart_total"]

    def get_cart_total(self, cart):
        """
        Calculates the total price of all items in the cart.
        """
        # N+1 potential: ensure cartitems are prefetched in the view
        items = cart.cartitems.all()
        total = sum([item.quantity * item.product.price for item in items])
        return total
    
class CartStatSerializer(serializers.ModelSerializer): 
    """
    Serializer for providing a simplified view of cart statistics,
    specifically the total number of items in the cart.
    """
    total_quantity = serializers.SerializerMethodField(help_text="Total number of items (sum of quantities) in the cart.")
    class Meta:
        model = Cart 
        fields = ["id", "cart_code", "total_quantity"]

    def get_total_quantity(self, cart):
        """
        Calculates the total quantity of all items in the cart.
        """
        # N+1 potential: ensure cartitems are prefetched in the view
        items = cart.cartitems.all()
        total = sum([item.quantity for item in items])
        return total

class AddToCartSerializer(serializers.Serializer):
    """
    Serializer for adding a product to a cart.
    Requires product_id, and an optional quantity. cart_code is optional for authenticated users.
    """
    cart_code = serializers.CharField(max_length=11, required=False, allow_blank=True, help_text="Unique code of the cart to add the product to (optional for authenticated users).")
    product_id = serializers.IntegerField(help_text="ID of the product to add to the cart.")
    quantity = serializers.IntegerField(min_value=1, required=False, default=1, help_text="Quantity of the product to add (defaults to 1).")

    def validate_product_id(self, value):
        """
        Validates that the product ID exists.
        """
        # Note: This performs a database lookup. Consider optimizing in view if performance is critical.
        if not Product.objects.filter(id=value).exists():
            raise serializers.ValidationError({"detail": "Invalid product ID."})
        return value

class UpdateCartItemSerializer(serializers.Serializer):
    """
    Serializer for updating the quantity of a specific cart item.
    Allows setting quantity to 0 to indicate removal.
    """
    item_id = serializers.IntegerField(help_text="ID of the cart item to update.")
    quantity = serializers.IntegerField(min_value=0, help_text="New quantity for the cart item (0 to remove).") # Allow 0 to indicate removal

    def validate_item_id(self, value):
        """
        Validates that the cart item ID exists.
        """
        # Note: This performs a database lookup. Consider optimizing in view if performance is critical.
        if not CartItem.objects.filter(id=value).exists():
            raise serializers.ValidationError({"detail": "Invalid cart item ID."})
        return value


class WishlistSerializer(serializers.ModelSerializer):
    """
    Serializer for displaying wishlist entries, including product details.
    """
    product = ProductListSerializer(read_only=True, help_text="The product in the wishlist (read-only).") # N+1 potential: select_related('product') in view
    class Meta:
        model = Wishlist 
        fields = ["id", "product", "created"]
        read_only_fields = ["user"] # User will be set from request.user in the view

class AddToWishlistSerializer(serializers.Serializer):
    """
    Serializer for adding a product to a user's wishlist.
    """
    product_id = serializers.IntegerField(help_text="ID of the product to add to the wishlist.")

    def validate_product_id(self, value):
        """
        Validates that the product ID exists.
        """
        # Note: This performs a database lookup. Consider optimizing in view if performance is critical.
        if not Product.objects.filter(id=value).exists():
            raise serializers.ValidationError({"detail": "Invalid product ID."})
        return value


class OrderItemSerializer(serializers.ModelSerializer):
    """
    Serializer for individual items within an order.
    """
    product = ProductListSerializer(read_only=True, help_text="The product included in the order item (read-only).") # N+1 potential: select_related('product') in view
    class Meta:
        model = OrderItem
        fields = ["id", "quantity", "product"]


class OrderSerializer(serializers.ModelSerializer):
    """
    Serializer for displaying order details, including all order items.
    """
    items = OrderItemSerializer(read_only=True, many=True, help_text="List of items in the order (read-only).") # N+1 potential: prefetch_related('items__product') in view
    class Meta:
        model = Order 
        fields = ["id", "stripe_checkout_id", "amount", "items", "status", "created_at"]


class AddressCreateSerializer(serializers.Serializer):
    """
    Serializer for creating or updating a customer's address.
    Includes validation for phone number format.
    """
    street = serializers.CharField(max_length=50, help_text="Street address.")
    city = serializers.CharField(max_length=50, help_text="City.")
    state = serializers.CharField(max_length=50, help_text="State or province.")
    phone = serializers.CharField(max_length=13, help_text="Phone number (e.g., +1234567890).") # Basic phone number validation

    def validate_phone(self, value):
        """
        Validates the phone number format using a regular expression.
        Allows 9-15 digits and an optional leading '+'.
        """
        import re
        phone_regex = re.compile(r'^\+?1?\d{9,15}$') # E.g., +1234567890, 1234567890
        if not phone_regex.match(value):
            raise serializers.ValidationError({"detail": "Phone number must be 9-15 digits and can optionally start with '+'."})
        return value


class CustomerAddressSerializer(serializers.ModelSerializer):
    """
    Serializer for displaying customer address details, including associated customer information.
    """
    customer = UserSerializer(read_only=True, help_text="The customer associated with this address (read-only).") # N+1 potential: select_related('customer') in view
    class Meta:
        model = CustomerAddress
        fields = "__all__"


class SimpleCartSerializer(serializers.ModelSerializer):
    """
    Simplified serializer for cart information, primarily used for displaying
    the total number of items in a cart without full item details.
    """
    num_of_items = serializers.SerializerMethodField(help_text="Total number of distinct items in the cart.")
    class Meta:
        model = Cart 
        fields = ["id", "cart_code", "num_of_items"]

    def get_num_of_items(self, cart):
        """
        Calculates the total number of items (sum of quantities) in the cart.
        """
        # N+1 potential: ensure cartitems are prefetched in the view
        num_of_items = sum([item.quantity for item in cart.cartitems.all()])
        return num_of_items


# This serializer is used for creating a review, it includes the user and product fields
class ProductRatingSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductRating 
        fields =[ "id", "average_rating", "total_reviews"]

    def validate_rating(self, value):
        if not (1 <= value <= 5):
            raise serializers.ValidationError("Rating must be between 1 and 5.")
        return value

# This serializer is used for creating a review, it includes the user and product fields
class ProductDetailSerializer(serializers.ModelSerializer):

    reviews = ReviewSerializer(read_only=True, many=True)
    rating = ProductRatingSerializer(read_only=True)
    review_counts = serializers.SerializerMethodField()
    similar_products = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = ["id", "name", "description", "slug", "image", "price", "reviews", "rating", "similar_products", "review_counts"]
      
    # This method retrieves similar products based on the category of the current product
    def get_similar_products(self, product):
        # Optimize by prefetching category if not already done in the view
        products = Product.objects.filter(category=product.category).exclude(id=product.id).select_related('category')
        serializer = ProductListSerializer(products, many=True)
        return serializer.data
    
    # This method counts the number of reviews for each rating level using annotations
    def get_review_counts(self, product):
        # Use annotations to get all review counts in a single query
        counts = product.reviews.aggregate(
            poor_review=Count('id', filter=models.Q(rating=1)),
            fair_review=Count('id', filter=models.Q(rating=2)),
            good_review=Count('id', filter=models.Q(rating=3)),
            very_good_review=Count('id', filter=models.Q(rating=4)),
            excellent_review=Count('id', filter=models.Q(rating=5))
        )
        return counts

class CategoryListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "image", "slug"]

# This serializer is used for displaying category details, including products in the category
class CategoryDetailSerializer(serializers.ModelSerializer):
    products = ProductListSerializer(many=True, read_only=True)
    class Meta:
        model = Category
        fields = ["id", "name", "image", "products"]

# This serializer is used for creating a review, it includes the user and product fields
class CartItemSerializer(serializers.ModelSerializer):
    product = ProductListSerializer(read_only=True)
    sub_total = serializers.SerializerMethodField()
    class Meta:
        model = CartItem 
        fields = ["id", "product", "quantity", "sub_total"]
    
    def validate_quantity(self, value):
        if value < 1:
            raise serializers.ValidationError("Quantity must be at least 1.")
        return value
    
    def get_sub_total(self, cartitem):
        total = cartitem.product.price * cartitem.quantity 
        return total
# This serializer is used for displaying cart details, including items in the cart and total price
class CartSerializer(serializers.ModelSerializer):
    cartitems = CartItemSerializer(read_only=True, many=True)
    cart_total = serializers.SerializerMethodField()
    class Meta:
        model = Cart 
        fields = ["id", "cart_code", "cartitems", "cart_total"]

    def get_cart_total(self, cart):
        items = cart.cartitems.all()
        total = sum([item.quantity * item.product.price for item in items])
        return total
    
# This serializer is used for creating a cart, it includes the cart code
class CartStatSerializer(serializers.ModelSerializer): 
    total_quantity = serializers.SerializerMethodField()
    class Meta:
        model = Cart 
        fields = ["id", "cart_code", "total_quantity"]

    def get_total_quantity(self, cart):
        items = cart.cartitems.all()
        total = sum([item.quantity for item in items])
        return total

# This serializer is used for creating a cart, it includes the cart code
class AddToCartSerializer(serializers.Serializer):
    cart_code = serializers.CharField(max_length=11, required=False, allow_blank=True)
    product_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1, required=False, default=1)

    def validate_product_id(self, value):
        if not Product.objects.filter(id=value).exists():
            raise serializers.ValidationError({"detail": "Invalid product ID."})
        return value

# This serializer is used for creating a review, it includes the user and product fields
class UpdateCartItemSerializer(serializers.Serializer):
    item_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=0) # Allow 0 to indicate removal

    def validate_item_id(self, value):
        if not CartItem.objects.filter(id=value).exists():
            raise serializers.ValidationError("Invalid cart item ID.")
        return value


# This serializer is used for creating a wishlist, it includes the user and product fields
class WishlistSerializer(serializers.ModelSerializer):
    product = ProductListSerializer(read_only=True)
    class Meta:
        model = Wishlist 
        fields = ["id", "product", "created"]
        read_only_fields = ["user"] # User will be set from request.user

class AddToWishlistSerializer(serializers.Serializer):
    product_id = serializers.IntegerField()

    def validate_product_id(self, value):
        if not Product.objects.filter(id=value).exists():
            raise serializers.ValidationError("Invalid product ID.")
        return value



# NEW ADDED 

class OrderItemSerializer(serializers.ModelSerializer):
    product = ProductListSerializer(read_only=True)
    class Meta:
        model = OrderItem
        fields = ["id", "quantity", "product"]


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(read_only=True, many=True)
    class Meta:
        model = Order 
        fields = ["id", "stripe_checkout_id", "amount", "items", "status", "created_at"]


class AddressCreateSerializer(serializers.Serializer):
    street = serializers.CharField(max_length=50)
    city = serializers.CharField(max_length=50)
    state = serializers.CharField(max_length=50)
    phone = serializers.CharField(max_length=13) # Basic phone number validation

    def validate_phone(self, value):
        # Example: Basic validation for digits and length
        if not value.isdigit() or not (10 <= len(value) <= 13):
            raise serializers.ValidationError("Phone number must be 10-13 digits.")
        return value


class CustomerAddressSerializer(serializers.ModelSerializer):
    customer = UserSerializer(read_only=True)
    class Meta:
        model = CustomerAddress
        fields = "__all__"


class SimpleCartSerializer(serializers.ModelSerializer):
    num_of_items = serializers.SerializerMethodField()
    class Meta:
        model = Cart 
        fields = ["id", "cart_code", "num_of_items"]

    def get_num_of_items(self, cart):
        num_of_items = sum([item.quantity for item in cart.cartitems.all()])
        return num_of_items
