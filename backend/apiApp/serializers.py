from rest_framework import serializers 
from django.contrib.auth import get_user_model
from django.db import models # Import models for models.Q
from django.db.models import Count # Import Count for aggregation
from .models import Cart, CartItem, CustomerAddress, Order, OrderItem, Product, Category, ProductRating, Review, Wishlist

User = get_user_model()


class ProductListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ["id", "name", "slug", "image", "price"]


# This serializer is used for creating a user, it includes password handling
class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, min_length=8)

    class Meta:
        model = User
        fields = ["id", "email", "username", "password", "first_name", "last_name", "profile_picture_url"]

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User.objects.create_user(**validated_data)
        user.set_password(password) # Django handles password hashing here
        user.save()
        return user
   
# This serializer is used for updating a user, it excludes the password field
class ReviewSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    class Meta:
        model = Review 
        fields = ["id", "user", "rating", "review", "created", "updated"]
        read_only_fields = ["user"] # User will be set from request.user in the view

    def validate_rating(self, value):
        if not (1 <= value <= 5):
            raise serializers.ValidationError("Rating must be between 1 and 5.")
        return value

    def validate(self, data):
        # Ensure a user can only review a product once
        user = self.context['request'].user
        product = self.context['product'] # Product instance passed from view
        if Review.objects.filter(user=user, product=product).exists():
            raise serializers.ValidationError("You have already reviewed this product.")
        return data

# This serializer is used for creating a review, it includes the user and product fields
class ProductRatingSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductRating 
        fields =[ "id", "average_rating", "total_reviews"]

    # Note: average_rating and total_reviews are typically updated via signals or directly in views
    # after a review is created/updated/deleted, not validated here.
    def validate_rating(self, value):
        if not (1 <= value <= 5):
            raise serializers.ValidationError("Rating must be between 1 and 5.")
        return value

# This serializer is used for creating a review, it includes the user and product fields
class ProductDetailSerializer(serializers.ModelSerializer):

    reviews = ReviewSerializer(read_only=True, many=True) # N+1 potential: prefetch_related('reviews') in view
    rating = ProductRatingSerializer(read_only=True) # N+1 potential: select_related('rating') in view
    review_counts = serializers.SerializerMethodField()
    similar_products = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = ["id", "name", "description", "slug", "image", "price", "reviews", "rating", "similar_products", "review_counts"]
      
    # This method retrieves similar products based on the category of the current product
    def get_similar_products(self, product):
        # Optimize by prefetching category if not already done in the view
        # Ensure category is selected/prefetched in the view to avoid N+1 for product.category
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
    products = ProductListSerializer(many=True, read_only=True) # N+1 potential: prefetch_related('products') in view
    class Meta:
        model = Category
        fields = ["id", "name", "image", "products"]

# This serializer is used for creating a review, it includes the user and product fields
class CartItemSerializer(serializers.ModelSerializer):
    product = ProductListSerializer(read_only=True) # N+1 potential: select_related('product') in view
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
    cartitems = CartItemSerializer(read_only=True, many=True) # N+1 potential: prefetch_related('cartitems__product') in view
    cart_total = serializers.SerializerMethodField()
    class Meta:
        model = Cart 
        fields = ["id", "cart_code", "cartitems", "cart_total"]

    def get_cart_total(self, cart):
        # N+1 potential: ensure cartitems are prefetched in the view
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
        # N+1 potential: ensure cartitems are prefetched in the view
        items = cart.cartitems.all()
        total = sum([item.quantity for item in items])
        return total

# This serializer is used for creating a cart, it includes the cart code
class AddToCartSerializer(serializers.Serializer):
    cart_code = serializers.CharField(max_length=11)
    product_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1, required=False, default=1)

    def validate_cart_code(self, value):
        # Note: This performs a database lookup. Consider optimizing in view if performance is critical.
        if not Cart.objects.filter(cart_code=value).exists():
            raise serializers.ValidationError("Invalid cart code.")
        return value

    def validate_product_id(self, value):
        # Note: This performs a database lookup. Consider optimizing in view if performance is critical.
        if not Product.objects.filter(id=value).exists():
            raise serializers.ValidationError("Invalid product ID.")
        return value

# This serializer is used for creating a review, it includes the user and product fields
class UpdateCartItemSerializer(serializers.Serializer):
    item_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=0) # Allow 0 to indicate removal

    def validate_item_id(self, value):
        # Note: This performs a database lookup. Consider optimizing in view if performance is critical.
        if not CartItem.objects.filter(id=value).exists():
            raise serializers.ValidationError("Invalid cart item ID.")
        return value


# This serializer is used for creating a wishlist, it includes the user and product fields
class WishlistSerializer(serializers.ModelSerializer):
    product = ProductListSerializer(read_only=True) # N+1 potential: select_related('product') in view
    class Meta:
        model = Wishlist 
        fields = ["id", "product", "created"]
        read_only_fields = ["user"] # User will be set from request.user in the view

class AddToWishlistSerializer(serializers.Serializer):
    product_id = serializers.IntegerField()

    def validate_product_id(self, value):
        # Note: This performs a database lookup. Consider optimizing in view if performance is critical.
        if not Product.objects.filter(id=value).exists():
            raise serializers.ValidationError("Invalid product ID.")
        return value



# NEW ADDED 

class OrderItemSerializer(serializers.ModelSerializer):
    product = ProductListSerializer(read_only=True) # N+1 potential: select_related('product') in view
    class Meta:
        model = OrderItem
        fields = ["id", "quantity", "product"]


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(read_only=True, many=True) # N+1 potential: prefetch_related('items__product') in view
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
        # Consider using a more robust phone number validation library for production
        if not value.isdigit() or not (10 <= len(value) <= 13):
            raise serializers.ValidationError("Phone number must be 10-13 digits.")
        return value


class CustomerAddressSerializer(serializers.ModelSerializer):
    customer = UserSerializer(read_only=True) # N+1 potential: select_related('customer') in view
    class Meta:
        model = CustomerAddress
        fields = "__all__"


class SimpleCartSerializer(serializers.ModelSerializer):
    num_of_items = serializers.SerializerMethodField()
    class Meta:
        model = Cart 
        fields = ["id", "cart_code", "num_of_items"]

    def get_num_of_items(self, cart):
        # N+1 potential: ensure cartitems are prefetched in the view
        num_of_items = sum([item.quantity for item in cart.cartitems.all()])
        return num_of_items

    def validate_rating(self, value):
        if not (1 <= value <= 5):
            raise serializers.ValidationError("Rating must be between 1 and 5.")
        return value

    def validate(self, data):
        # Ensure a user can only review a product once
        user = self.context['request'].user
        product = self.context['product'] # Product instance passed from view
        if Review.objects.filter(user=user, product=product).exists():
            raise serializers.ValidationError("You have already reviewed this product.")
        return data

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
    cart_code = serializers.CharField(max_length=11)
    product_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1, required=False, default=1)

    def validate_cart_code(self, value):
        if not Cart.objects.filter(cart_code=value).exists():
            raise serializers.ValidationError("Invalid cart code.")
        return value

    def validate_product_id(self, value):
        if not Product.objects.filter(id=value).exists():
            raise serializers.ValidationError("Invalid product ID.")
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
