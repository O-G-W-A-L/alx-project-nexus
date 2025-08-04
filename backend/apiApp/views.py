import logging
import stripe 
from django.conf import settings
from django.shortcuts import render, get_object_or_404
from django.contrib.auth import get_user_model
from django.db.models import Q, F, Avg
from django.db import transaction
from django.db.models import Q, F, Avg

from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework import viewsets
from rest_framework.permissions import IsAdminUser, AllowAny, IsAuthenticated
from rest_framework import filters
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.exceptions import APIException, ValidationError

from django_ratelimit.decorators import ratelimit

from .models import Cart, CartItem, Category, CustomerAddress, Order, OrderItem, Product, Review, Wishlist, ProductRating
from .serializers import (
    CartItemSerializer, CartSerializer, CategoryDetailSerializer, CategoryListSerializer, 
    CustomerAddressSerializer, OrderSerializer, ProductListSerializer, ProductDetailSerializer, 
    ReviewSerializer, SimpleCartSerializer, UserSerializer, WishlistSerializer,
    AddToCartSerializer, UpdateCartItemSerializer, AddToWishlistSerializer, AddressCreateSerializer
)

from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt


from drf_yasg.utils import swagger_auto_schema
from rest_framework import serializers
from drf_yasg import openapi

from .filters import ProductFilter

logger = logging.getLogger(__name__)

# Create your views here.
stripe.api_key = settings.STRIPE_SECRET_KEY
endpoint_secret = settings.WEBHOOK_SECRET

from django.http import JsonResponse

def home(request):
    return JsonResponse({"message": "Welcome to our E-Commerce API!"})


User = get_user_model()

class ProductViewSet(viewsets.ModelViewSet):
    """
    A ViewSet for viewing and editing product instances.
    Provides CRUD operations for products.
    """
    # Optimize queryset for common access patterns to avoid N+1 queries
    queryset = Product.objects.select_related('category', 'rating').prefetch_related('reviews').all()
    serializer_class = ProductDetailSerializer # Use ProductDetailSerializer for full CRUD
    lookup_field = 'slug' # Use slug for URL lookups
    filter_backends = [filters.OrderingFilter, filters.SearchFilter, DjangoFilterBackend]
    ordering_fields = ['price', 'name', 'created_at'] # Fields available for ordering
    search_fields = ['name', 'description', 'category__name'] # Fields available for search
    filterset_class = ProductFilter # Custom filter class for products

    def get_serializer_class(self):
        """
        Returns the appropriate serializer class based on the action.
        Uses ProductListSerializer for list view and ProductDetailSerializer for detail views.
        """
        if self.action == 'list':
            return ProductListSerializer
        return ProductDetailSerializer

    def get_permissions(self):
        """
        Sets permissions for different actions.
        Only admin users can create, update, or delete products.
        Any user can view products.
        """
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            self.permission_classes = [IsAdminUser]
        else:
            self.permission_classes = [AllowAny]
        return super().get_permissions()

class CategoryViewSet(viewsets.ModelViewSet):
    """
    A ViewSet for viewing and editing category instances.
    Provides CRUD operations for categories.
    """
    # Optimize queryset for common access patterns to avoid N+1 queries
    queryset = Category.objects.prefetch_related('products').all()
    serializer_class = CategoryDetailSerializer
    lookup_field = 'slug' # Use slug for URL lookups
    filter_backends = [filters.OrderingFilter, filters.SearchFilter]
    ordering_fields = ['name'] # Fields available for ordering
    search_fields = ['name'] # Fields available for search

    def get_serializer_class(self):
        """
        Returns the appropriate serializer class based on the action.
        Uses CategoryListSerializer for list view and CategoryDetailSerializer for detail views.
        """
        if self.action == 'list':
            return CategoryListSerializer
        return CategoryDetailSerializer

    def get_permissions(self):
        """
        Sets permissions for different actions.
        Only admin users can create, update, or delete categories.
        Any user can view categories.
        """
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            self.permission_classes = [IsAdminUser]
        else:
            self.permission_classes = [AllowAny]
        return super().get_permissions()


@swagger_auto_schema(
    method='post',
    request_body=AddToCartSerializer(),
    responses={
        200: CartSerializer(),
        400: 'Bad Request',
        404: 'Not Found'
    },
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
@ratelimit(key='user', rate='5/s', block=True)
def add_to_cart(request):
    """
    Adds a product to a user's cart or an anonymous cart.
    If the cart code is provided, it attempts to use that cart.
    If the cart is anonymous and the user logs in, the cart is assigned to the user.
    Handles stock validation and atomic updates for cart items.
    """
    serializer = AddToCartSerializer(data=request.data)
    try:
        serializer.is_valid(raise_exception=True)
    except ValidationError as e:
        logger.error(f"Add to cart validation error: {e.detail}")
        return Response({"detail": e.detail}, status=status.HTTP_400_BAD_REQUEST)

    cart_code = serializer.validated_data["cart_code"]
    product_id = serializer.validated_data["product_id"]
    quantity = serializer.validated_data.get("quantity", 1)

    try:
        # Attempt to retrieve the cart and product
        cart = get_object_or_404(Cart, cart_code=cart_code)
        product = get_object_or_404(Product, id=product_id)
    except Exception as e:
        logger.error(f"Error retrieving cart ({cart_code}) or product ({product_id}): {e}")
        return Response({"detail": "Cart or Product not found."}, status=status.HTTP_404_NOT_FOUND)

    # Use a transaction to ensure atomicity for cart operations
    with transaction.atomic():
        # Logic to handle cart ownership and creation
        if cart_code:
            try:
                cart = Cart.objects.get(cart_code=cart_code)
                # If cart exists and is anonymous, assign it to the authenticated user
                if request.user.is_authenticated and cart.user is None:
                    cart.user = request.user
                    cart.save()
                    logger.info(f"Anonymous cart {cart_code} assigned to user {request.user.email}.")
                # If cart exists and belongs to another user, deny access
                elif request.user.is_authenticated and cart.user != request.user:
                    logger.warning(f"User {request.user.email} attempted to access cart {cart_code} belonging to another user.")
                    return Response({"detail": "This cart code belongs to another user."}, status=status.HTTP_403_FORBIDDEN)
            except Cart.DoesNotExist:
                # If cart_code doesn't exist, create a new one for the user (or anonymous)
                cart = Cart.objects.create(user=request.user if request.user.is_authenticated else None, cart_code=cart_code)
                logger.info(f"New cart {cart_code} created for user {request.user.email if request.user.is_authenticated else 'anonymous'}.")
        else:
            # If no cart_code is provided, try to get the user's existing cart or create a new one
            if request.user.is_authenticated:
                cart, created = Cart.objects.get_or_create(user=request.user, defaults={'cart_code': Cart.generate_unique_cart_code()})
                if created:
                    logger.info(f"New cart {cart.cart_code} created for authenticated user {request.user.email}.")
                else:
                    logger.info(f"Existing cart {cart.cart_code} retrieved for authenticated user {request.user.email}.")
            else:
                # For anonymous users, a cart_code must be provided to identify the cart
                logger.warning("Anonymous user attempted to add to cart without providing a cart_code.")
                return Response({"detail": "cart_code is required for anonymous users."}, status=status.HTTP_400_BAD_REQUEST)

        # Check if product exists and has enough stock before adding to cart
        try:
            product = Product.objects.select_for_update().get(id=product_id) # Lock product row for update
        except Product.DoesNotExist:
            logger.error(f"Product with ID {product_id} not found during add to cart operation.")
            return Response({"detail": "Product not found."}, status=status.HTTP_404_NOT_FOUND)

        if product.stock < quantity:
            logger.warning(f"Insufficient stock for product {product.name}. Requested: {quantity}, Available: {product.stock}.")
            return Response({"detail": f"Not enough stock for {product.name}. Available: {product.stock}"}, status=status.HTTP_400_BAD_REQUEST)

        # Get or create cart item and update quantity
        cartitem, created = CartItem.objects.get_or_create(product=product, cart=cart)
        if not created:
            # Atomically update quantity to prevent race conditions
            CartItem.objects.filter(id=cartitem.id).update(quantity=F('quantity') + quantity)
            cartitem.refresh_from_db() # Refresh to get the updated quantity
            logger.info(f"Updated quantity for product {product.name} in cart {cart.cart_code} to {cartitem.quantity}.")
        else:
            cartitem.quantity = quantity
            cartitem.save()
            logger.info(f"Added product {product.name} to cart {cart.cart_code} with quantity {quantity}.")

        # Note: Product stock decrement is handled during checkout for final decrement.
        # A temporary decrement here could be considered for more immediate stock reflection,
        # but the current approach defers final decrement to payment fulfillment.

        response_serializer = CartSerializer(cart) # Serialize the updated cart
        return Response(response_serializer.data, status=status.HTTP_200_OK)


@swagger_auto_schema(
    method='put',
    request_body=UpdateCartItemSerializer(),
    responses={
        200: openapi.Response("Cart item updated", CartItemSerializer()),
        400: 'Bad Request',
        404: 'Not Found'
    }
)
@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_cartitem_quantity(request):
    serializer = UpdateCartItemSerializer(data=request.data)
    try:
        serializer.is_valid(raise_exception=True)
    except ValidationError as e:
        return Response({"detail": e.detail}, status=status.HTTP_400_BAD_REQUEST)

    cartitem_id = serializer.validated_data["item_id"]
    quantity = serializer.validated_data["quantity"]

    try:
        cartitem = get_object_or_404(CartItem, id=cartitem_id)
    except Exception as e:
        logger.error(f"Error retrieving cart item: {e}")
        return Response({"detail": "Cart item not found."}, status=status.HTTP_404_NOT_FOUND)

    # Authorization check:
    # If the cart is associated with a user, ensure the request user is that user.
    # If the cart is anonymous (cart.user is None), allow any user to modify it via cart_code.
    if cartitem.cart.user is not None and cartitem.cart.user != request.user:
        return Response({"detail": "You do not have permission to update this cart item."}, status=status.HTTP_403_FORBIDDEN)

    with transaction.atomic():
        if quantity == 0:
            cartitem.delete()
            return Response({"message": "Cart item removed successfully!"}, status=status.HTTP_204_NO_CONTENT)
        else:
            # Atomically update quantity to prevent race conditions
            CartItem.objects.filter(id=cartitem_id).update(quantity=quantity)
            cartitem.refresh_from_db() # Refresh to get the updated quantity
            response_serializer = CartItemSerializer(cartitem)
            return Response({"data": response_serializer.data, "message": "Cart item updated successfully!"}, status=status.HTTP_200_OK)


@swagger_auto_schema(
    method='post',
    request_body=ReviewSerializer(),
    responses={
        201: ReviewSerializer(),
        400: 'Bad Request',
        404: 'Not Found',
        403: 'Forbidden'
    }
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
@ratelimit(key='user', rate='1/m', block=True) # Limit to 1 review per minute per user
def add_review(request):
    product_id = request.data.get("product_id")
    
    try:
        product = get_object_or_404(Product, id=product_id)
    except Exception as e:
        logger.error(f"Error retrieving product: {e}")
        return Response({"detail": "Product not found."}, status=status.HTTP_404_NOT_FOUND)

    serializer = ReviewSerializer(data=request.data, context={'request': request, 'product': product})
    try:
        serializer.is_valid(raise_exception=True)
    except ValidationError as e:
        return Response({"detail": e.detail}, status=status.HTTP_400_BAD_REQUEST)

    # User is already authenticated via permission_classes
    user = request.user
    
    with transaction.atomic():
        review = Review.objects.create(product=product, user=user, **serializer.validated_data)
        # Update ProductRating after review is added
        product_rating, created = ProductRating.objects.get_or_create(product=product)
        
        # Recalculate average rating and total reviews atomically
        # This is a more robust way to handle updates to avoid race conditions
        total_reviews = Review.objects.filter(product=product).count()
        average_rating = Review.objects.filter(product=product).aggregate(avg_rating=Avg('rating'))['avg_rating'] or 0.0
        
        product_rating.total_reviews = total_reviews
        product_rating.average_rating = average_rating
        product_rating.save()

    response_serializer = ReviewSerializer(review)
    return Response(response_serializer.data, status=status.HTTP_201_CREATED)


update_review_request = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    required=['rating'],
    properties={
        'rating': openapi.Schema(type=openapi.TYPE_INTEGER, description='Rating from 1 to 5'),
        'review': openapi.Schema(type=openapi.TYPE_STRING, description='Review text'),
    },
)

@swagger_auto_schema(method='put', request_body=update_review_request, responses={200: ReviewSerializer()})
@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_review(request, pk):
    try:
        review = get_object_or_404(Review, id=pk)
    except Exception as e:
        logger.error(f"Error retrieving review: {e}")
        return Response({"detail": "Review not found."}, status=status.HTTP_404_NOT_FOUND)

    if review.user != request.user:
        return Response({"detail": "You do not have permission to update this review."}, status=status.HTTP_403_FORBIDDEN)

    serializer = ReviewSerializer(review, data=request.data, partial=True, context={'request': request, 'product': review.product})
    try:
        serializer.is_valid(raise_exception=True)
    except ValidationError as e:
        return Response({"detail": e.detail}, status=status.HTTP_400_BAD_REQUEST)

    with transaction.atomic():
        serializer.save()
        # Update ProductRating after review is updated
        product = review.product
        product_rating, created = ProductRating.objects.get_or_create(product=product)
        
        total_reviews = Review.objects.filter(product=product).count()
        average_rating = Review.objects.filter(product=product).aggregate(avg_rating=Avg('rating'))['avg_rating'] or 0.0
        
        product_rating.total_reviews = total_reviews
        product_rating.average_rating = average_rating
        product_rating.save()

    return Response(serializer.data, status=status.HTTP_200_OK)



@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_review(request, pk):
    try:
        review = get_object_or_404(Review, id=pk) 
    except Exception as e:
        logger.error(f"Error retrieving review: {e}")
        return Response({"detail": "Review not found."}, status=status.HTTP_404_NOT_FOUND)

    if review.user != request.user:
        return Response({"detail": "You do not have permission to delete this review."}, status=status.HTTP_403_FORBIDDEN)

    with transaction.atomic():
        product = review.product # Get product before deleting review
        review.delete()
        # Update ProductRating after review is deleted
        product_rating, created = ProductRating.objects.get_or_create(product=product)
        
        total_reviews = Review.objects.filter(product=product).count()
        average_rating = Review.objects.filter(product=product).aggregate(avg_rating=Avg('rating'))['avg_rating'] or 0.0
        
        product_rating.total_reviews = total_reviews
        product_rating.average_rating = average_rating
        product_rating.save()

    return Response({"message": "Review deleted successfully!"}, status=status.HTTP_204_NO_CONTENT)

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_cartitem(request, pk):
    try:
        cartitem = get_object_or_404(CartItem, id=pk) 
    except Exception as e:
        logger.error(f"Error retrieving cart item: {e}")
        return Response({"detail": "Cart item not found."}, status=status.HTTP_404_NOT_FOUND)

    # Authorization check:
    # If the cart is associated with a user, ensure the request user is that user.
    # If the cart is anonymous (cart.user is None), allow any user to delete it via cart_code.
    if cartitem.cart.user is not None and cartitem.cart.user != request.user:
        return Response({"detail": "You do not have permission to delete this cart item."}, status=status.HTTP_403_FORBIDDEN)

    cartitem.delete()
    return Response({"message": "Cart item deleted successfully!"}, status=status.HTTP_204_NO_CONTENT)





@swagger_auto_schema(
    method='post',
    request_body=AddToWishlistSerializer(),
    responses={
        200: WishlistSerializer(),
        204: 'No Content',
        400: 'Bad Request',
        404: 'Not Found',
        409: 'Conflict' # For duplicate entry
    }
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def add_to_wishlist(request):
    serializer = AddToWishlistSerializer(data=request.data)
    try:
        serializer.is_valid(raise_exception=True)
    except ValidationError as e:
        return Response({"detail": e.detail}, status=status.HTTP_400_BAD_REQUEST)

    product_id = serializer.validated_data["product_id"]
    user = request.user # Use authenticated user

    try:
        product = get_object_or_404(Product, id=product_id)
    except Exception as e:
        logger.error(f"Error retrieving product: {e}")
        return Response({"detail": "Product not found."}, status=status.HTTP_404_NOT_FOUND)

    wishlist_entry = Wishlist.objects.filter(user=user, product=product)
    if wishlist_entry.exists():
        wishlist_entry.delete()
        return Response({"message": "Product removed from wishlist."}, status=status.HTTP_204_NO_CONTENT)
    else:
        try:
            new_wishlist = Wishlist.objects.create(user=user, product=product)
            response_serializer = WishlistSerializer(new_wishlist)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        except Exception as e:
            logger.error(f"Error adding to wishlist: {e}")
            return Response({"detail": "Could not add to wishlist. Possible duplicate entry."}, status=status.HTTP_409_CONFLICT)


# Define the query parameter for Swagger
query_param = openapi.Parameter(
    'query',
    openapi.IN_QUERY,
    description="Search term (product name, description, or category)",
    type=openapi.TYPE_STRING,
    required=True
)

@swagger_auto_schema(
    method='get',
    manual_parameters=[query_param]
)
@api_view(['GET'])
@permission_classes([AllowAny]) # Search can be public
def product_search(request):
    query = request.query_params.get("query") 
    if not query:
        return Response({"detail": "No query provided."}, status=status.HTTP_400_BAD_REQUEST)
    
    products = Product.objects.filter(
        Q(name__icontains=query) | 
        Q(description__icontains=query) |
        Q(category__name__icontains=query)
    )
    serializer = ProductListSerializer(products, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)






@swagger_auto_schema(
    method='post',
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=['cart_code'],
        properties={
            'cart_code': openapi.Schema(type=openapi.TYPE_STRING, description='Unique code of the cart to checkout.'),
        },
    ),
    responses={
        200: openapi.Response("Checkout session URL", openapi.Schema(type=openapi.TYPE_OBJECT, properties={'data': openapi.Schema(type=openapi.TYPE_STRING)})),
        400: 'Bad Request',
        403: 'Forbidden',
        404: 'Not Found',
        500: 'Internal Server Error'
    },
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@ratelimit(key='user', rate='1/m', block=True) # Limit checkout session creation
def create_checkout_session(request):
    """
    Creates a Stripe Checkout Session for the specified cart.
    Requires authentication and the cart_code in the request body.
    Performs stock validation and ensures the user has permission to checkout the cart.
    """
    cart_code = request.data.get("cart_code")
    
    if not cart_code:
        logger.warning("create_checkout_session: cart_code not provided in request.")
        return Response({"detail": "cart_code is required."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        cart = get_object_or_404(Cart, cart_code=cart_code)
    except Exception as e:
        logger.error(f"Error retrieving cart for checkout (cart_code: {cart_code}): {e}")
        return Response({"detail": "Cart not found."}, status=status.HTTP_404_NOT_FOUND)

    # Authorization check:
    # If the cart is associated with a user, ensure the request user is that user.
    # If the cart is anonymous (cart.user is None), allow any user to checkout via cart_code.
    if cart.user is not None and cart.user != request.user:
        return Response({"detail": "You do not have permission to checkout this cart."}, status=status.HTTP_403_FORBIDDEN)

    if not cart.cartitems.exists():
        return Response({"detail": "Cart is empty. Cannot create checkout session."}, status=status.HTTP_400_BAD_REQUEST)

    with transaction.atomic():
        # Lock products for update to prevent race conditions during stock check
        cart_items_with_products = cart.cartitems.select_related('product').select_for_update()

        line_items = []
        for item in cart_items_with_products:
            product = item.product
            if product.stock < item.quantity:
                return Response({"detail": f"Not enough stock for {product.name}. Available: {product.stock}"}, status=status.HTTP_400_BAD_REQUEST)
            
            line_items.append({
                'price_data': {
                    'currency': 'usd',
                    'product_data': {'name': product.name},
                    'unit_amount': int(product.price * 100),  # Amount in cents
                },
                'quantity': item.quantity,
            })
        
        # Add VAT Fee
        line_items.append({
            'price_data': {
                'currency': 'usd',
                'product_data': {'name': 'VAT Fee'},
                'unit_amount': 500,  # $5 in cents
            },
            'quantity': 1,
        })

        try:
            checkout_session = stripe.checkout.Session.create(
                customer_email= request.user.email, # Use authenticated user's email
                payment_method_types=['card'],
                line_items=line_items,
                mode='payment',
                success_url="https://next-shop-self.vercel.app/success",
                cancel_url="https://next-shop-self.vercel.app/failed",
                metadata = {"cart_code": cart_code, "user_id": str(request.user.id)} # Store user_id for fulfillment
            )
            return Response({'data': checkout_session.url}, status=status.HTTP_200_OK) # Return URL for redirection
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error during checkout session creation: {e}")
            return Response({'detail': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            logger.error(f"Unexpected error during checkout session creation: {e}")
            return Response({'detail': 'An unexpected error occurred.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@csrf_exempt
def my_webhook_view(request):
  payload = request.body
  sig_header = request.META.get('HTTP_STRIPE_SIGNATURE') # Use .get for safety
  event = None

  if not sig_header:
      logger.warning("Webhook received without Stripe-Signature header.")
      return HttpResponse(status=400)

  try:
    event = stripe.Webhook.construct_event(
      payload, sig_header, endpoint_secret
    )
  except ValueError as e:
    logger.error(f"Invalid payload for Stripe webhook: {e}")
    return HttpResponse(status=400)
  except stripe.error.SignatureVerificationError as e:
    logger.error(f"Invalid signature for Stripe webhook: {e}")
    return HttpResponse(status=400)
  except Exception as e:
    logger.error(f"Unexpected error during Stripe webhook processing: {e}")
    return HttpResponse(status=500)

  if (
    event['type'] == 'checkout.session.completed'
    or event['type'] == 'checkout.session.async_payment_succeeded'
  ):
    session = event['data']['object']
    cart_code = session.get("metadata", {}).get("cart_code")
    user_id = session.get("metadata", {}).get("user_id")

    if not cart_code or not user_id:
        logger.error(f"Missing metadata in checkout session: cart_code={cart_code}, user_id={user_id}")
        return HttpResponse(status=400)

    # Ensure idempotency: check if order already exists for this stripe_checkout_id
    if Order.objects.filter(stripe_checkout_id=session["id"]).exists():
        logger.info(f"Order for checkout session {session['id']} already exists. Skipping fulfillment.")
        return HttpResponse(status=200) # Return 200 OK for duplicate events

    try:
        fulfill_checkout(session, cart_code, user_id)
    except Exception as e:
        logger.error(f"Error fulfilling checkout for session {session.id}: {e}")
        return HttpResponse(status=500)

  return HttpResponse(status=200)


def fulfill_checkout(session, cart_code, user_id):
    with transaction.atomic():
        try:
            user = get_object_or_404(User, id=user_id)
            order = Order.objects.create(
                stripe_checkout_id=session["id"],
                amount=session["amount_total"] / 100, # Convert cents to dollars
                currency=session["currency"],
                customer_email=session["customer_email"],
                status="Paid"
            )
            logger.info(f"Order {order.id} created for user {user.email} with Stripe ID {session['id']}.")

            cart = get_object_or_404(Cart, cart_code=cart_code)
            cartitems = cart.cartitems.select_related('product').select_for_update() # Lock cart items and products
            logger.info(f"Fulfilling order for cart {cart_code} with {cartitems.count()} items.")

            for item in cartitems:
                # Decrement product stock atomically
                Product.objects.filter(id=item.product.id).update(stock=F('stock') - item.quantity)
                OrderItem.objects.create(order=order, product=item.product, quantity=item.quantity)
                logger.info(f"Decremented stock for product {item.product.name} by {item.quantity}.")
            
            cart.delete()
            logger.info(f"Cart {cart_code} deleted after successful checkout and order fulfillment.")

        except Product.DoesNotExist:
            logger.error(f"Product not found during fulfillment for cart {cart_code}. This should not happen if stock check was done.")
            raise # Re-raise to be caught by webhook view
        except Cart.DoesNotExist:
            logger.error(f"Cart {cart_code} not found during fulfillment. This should not happen.")
            raise
        except Exception as e:
            logger.error(f"Failed to fulfill checkout for cart {cart_code} and user {user_id}: {e}")
            raise # Re-raise to be caught by webhook view






# Serializer for Swagger and validation
class CreateUserSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)

@swagger_auto_schema(method='post', request_body=CreateUserSerializer)
@api_view(['POST'])
@permission_classes([AllowAny]) # User creation is public
def create_user(request):
    serializer = CreateUserSerializer(data=request.data)
    try:
        serializer.is_valid(raise_exception=True)
    except ValidationError as e:
        return Response({"detail": e.detail}, status=status.HTTP_400_BAD_REQUEST)

    data = serializer.validated_data
    try:
        user = User.objects.create_user(
            username=data['username'],
            email=data['email'],
            password=data['password']
        )
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)
    except Exception as e:
        logger.error(f"Error creating user: {e}")
        return Response({"detail": "Could not create user. Email or username might already be taken."}, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET"])
@permission_classes([AllowAny]) # Checking user existence can be public
def existing_user(request, email):
    if not email:
        return Response({"detail": "Email parameter is required."}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        User.objects.get(email=email)
        return Response({"exists": True}, status=status.HTTP_200_OK)
    except User.DoesNotExist:
        return Response({"exists": False}, status=status.HTTP_404_NOT_FOUND) # Return 404 if not found for consistency


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_orders(request):
    # Optimize query to avoid N+1 for order items and their products
    orders = Order.objects.filter(customer_email=request.user.email).prefetch_related('items__product')
    serializer = OrderSerializer(orders, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


address_schema = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    required=['street', 'city', 'state', 'phone'], # Email removed as it's from authenticated user
    properties={
        'street': openapi.Schema(type=openapi.TYPE_STRING),
        'city': openapi.Schema(type=openapi.TYPE_STRING),
        'state': openapi.Schema(type=openapi.TYPE_STRING),
        'phone': openapi.Schema(type=openapi.TYPE_STRING),
    },
)
@swagger_auto_schema(method='post', request_body=AddressCreateSerializer()) # Use serializer for validation
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def add_address(request):
    serializer = AddressCreateSerializer(data=request.data)
    try:
        serializer.is_valid(raise_exception=True)
    except ValidationError as e:
        return Response({"detail": e.detail}, status=status.HTTP_400_BAD_REQUEST)

    customer = request.user # Use authenticated user
    
    try:
        address, created = CustomerAddress.objects.get_or_create(customer=customer)
        for attr, value in serializer.validated_data.items():
            setattr(address, attr, value)
        address.save()
    except Exception as e:
        logger.error(f"Error adding/updating address for user {customer.email}: {e}")
        return Response({"detail": "Could not save address."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    response_serializer = CustomerAddressSerializer(address)
    return Response(response_serializer.data, status=status.HTTP_201_CREATED)



@swagger_auto_schema(
    method='get',
    responses={
        200: CustomerAddressSerializer(),
        404: 'Address not found'
    }
)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_address(request):
    customer = request.user # Use authenticated user
    
    try:
        # Optimize query to avoid N+1 for customer (user)
        address = get_object_or_404(CustomerAddress.objects.select_related('customer'), customer=customer)
        serializer = CustomerAddressSerializer(address)
        return Response(serializer.data, status=status.HTTP_200_OK)
    except Exception as e:
        logger.error(f"Error retrieving address for user {customer.email}: {e}")
        return Response({"detail": "Address not found."}, status=status.HTTP_404_NOT_FOUND)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def my_wishlists(request):
    # Optimize query to avoid N+1 for product
    wishlists = Wishlist.objects.filter(user=request.user).select_related('product')
    serializer = WishlistSerializer(wishlists, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def product_in_wishlist(request):
    product_id = request.query_params.get("product_id")

    if not product_id:
        return Response({"detail": "product_id parameter is required."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        product_id = int(product_id)
    except ValueError:
        return Response({"detail": "product_id must be an integer."}, status=status.HTTP_400_BAD_REQUEST)

    product_exists = Wishlist.objects.filter(product__id=product_id, user=request.user).exists()
    return Response({"product_in_wishlist": product_exists}, status=status.HTTP_200_OK)



@api_view(['GET'])
@permission_classes([AllowAny]) # Cart can be accessed by code without authentication
def get_cart(request, cart_code):
    if not cart_code:
        return Response({"detail": "Cart code is required."}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # Optimize query to avoid N+1 for cart items and their products
        cart = get_object_or_404(Cart.objects.prefetch_related('cartitems__product'), cart_code=cart_code)
        serializer = CartSerializer(cart)
        return Response(serializer.data, status=status.HTTP_200_OK)
    except Exception as e:
        logger.error(f"Error retrieving cart {cart_code}: {e}")
        return Response({"detail": "Cart not found."}, status=status.HTTP_404_NOT_FOUND)




cart_code_param = openapi.Parameter(
    'cart_code', openapi.IN_QUERY, description="Cart code", type=openapi.TYPE_STRING, required=True
)

@swagger_auto_schema(
    method='get',
    manual_parameters=[cart_code_param],
    responses={200: 'OK'}
)
@api_view(['GET'])
@permission_classes([AllowAny]) # Cart stats can be public
def get_cart_stat(request):
    cart_code = request.query_params.get("cart_code")
    if not cart_code:
        return Response({"detail": "cart_code is required."}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # Optimize query to avoid N+1 for cart items
        cart = get_object_or_404(Cart.objects.prefetch_related('cartitems'), cart_code=cart_code)
        serializer = SimpleCartSerializer(cart) # Using SimpleCartSerializer for stats
        return Response(serializer.data, status=status.HTTP_200_OK)
    except Exception as e:
        logger.error(f"Error retrieving cart stats for {cart_code}: {e}")
        return Response({"detail": "Cart not found."}, status=status.HTTP_404_NOT_FOUND)


cart_code_param = openapi.Parameter(
    'cart_code', openapi.IN_QUERY,
    description="Cart code string",
    type=openapi.TYPE_STRING,
    required=True
)

product_id_param = openapi.Parameter(
    'product_id', openapi.IN_QUERY,
    description="Product ID integer",
    type=openapi.TYPE_INTEGER,
    required=True
)

@swagger_auto_schema(manual_parameters=[cart_code_param, product_id_param],method='get')
@api_view(['GET'])
@permission_classes([AllowAny]) # Checking product in cart can be public
def product_in_cart(request):
    cart_code = request.query_params.get("cart_code")
    product_id = request.query_params.get("product_id")

    if not cart_code or not product_id:
        return Response({"detail": "Both cart_code and product_id are required."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        product_id = int(product_id)
    except ValueError:
        return Response({"detail": "product_id must be an integer."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        cart = get_object_or_404(Cart, cart_code=cart_code)
        product = get_object_or_404(Product, id=product_id)
    except Exception as e:
        logger.error(f"Error checking product in cart: {e}")
        logger.error(f"Error checking product in cart: {e}")
        return Response({"detail": "Cart or Product not found."}, status=status.HTTP_404_NOT_FOUND)

    product_exists_in_cart = CartItem.objects.filter(cart=cart, product=product).exists()

    return Response({'product_in_cart': product_exists_in_cart}, status=status.HTTP_200_OK)
