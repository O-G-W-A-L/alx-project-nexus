from rest_framework import serializers 
from django.contrib.auth import get_user_model
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
        user.set_password(password)
        user.save()
        return user
   
# This serializer is used for updating a user, it excludes the password field
class ReviewSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    class Meta:
        model = Review 
        fields = ["id", "user", "rating", "review", "created", "updated"]

# This serializer is used for creating a review, it includes the user and product fields
class ProductRatingSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductRating 
        fields =[ "id", "average_rating", "total_reviews"]

# This serializer is used for creating a review, it includes the user and product fields
class ProductDetailSerializer(serializers.ModelSerializer):

    reviews = ReviewSerializer(read_only=True, many=True)
    rating = ProductRatingSerializer(read_only=True)
    poor_review = serializers.SerializerMethodField()
    fair_review = serializers.SerializerMethodField()
    good_review = serializers.SerializerMethodField()
    very_good_review = serializers.SerializerMethodField()
    excellent_review = serializers.SerializerMethodField()

    similar_products = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = ["id", "name", "description", "slug", "image", "price", "reviews", "rating", "similar_products", "poor_review", "fair_review", "good_review",
                  "very_good_review", "excellent_review"]
      
    # This method retrieves similar products based on the category of the current product
    def get_similar_products(self, product):
        products = Product.objects.filter(category=product.category).exclude(id=product.id)
        serializer = ProductListSerializer(products, many=True)
        return serializer.data
    
    # These methods count the number of reviews for each rating level
    def get_poor_review(self, product):
        poor_review_count = product.reviews.filter(rating=1).count()
        return poor_review_count
    
    # This method counts the number of reviews with a rating of 2
    def get_fair_review(self, product):
        fair_review_count = product.reviews.filter(rating=2).count()
        return fair_review_count
    
     # This method counts the number of reviews with a rating of 3
    def get_good_review(self, product):
        good_review_count = product.reviews.filter(rating=3).count()
        return good_review_count
    
    # This method counts the number of reviews with a rating of 4
    def get_very_good_review(self, product):
        very_good_review_count = product.reviews.filter(rating=4).count()
        return very_good_review_count
    
    # This method counts the number of reviews with a rating of 5
    def get_excellent_review(self, product):
        excellent_review_count = product.reviews.filter(rating=5).count()
        return excellent_review_count

# This serializer is used for creating a review, it includes the user and product fields
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
    cart_code = serializers.CharField()
    product_id = serializers.IntegerField()

# This serializer is used for creating a review, it includes the user and product fields
class UpdateCartItemSerializer(serializers.Serializer):
    item_id = serializers.IntegerField()
    quantity = serializers.IntegerField()


# This serializer is used for creating a wishlist, it includes the user and product fields
class WishlistSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    product = ProductListSerializer(read_only=True)
    class Meta:
        model = Wishlist 
        fields = ["id", "user", "product", "created"]



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
    email = serializers.EmailField()
    street = serializers.CharField()
    city = serializers.CharField()
    state = serializers.CharField()
    phone = serializers.CharField()


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

