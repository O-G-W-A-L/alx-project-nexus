import logging
import stripe 
from django.conf import settings
from django.shortcuts import render
from django.contrib.auth import get_user_model
from django.db.models import Q
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .models import Cart, CartItem, Category, CustomerAddress, Order, OrderItem, Product, Review, Wishlist
from .serializers import CartItemSerializer, CartSerializer, CategoryDetailSerializer, CategoryListSerializer, CustomerAddressSerializer, OrderSerializer, ProductListSerializer, ProductDetailSerializer, ReviewSerializer, SimpleCartSerializer, UserSerializer, WishlistSerializer
from .serializers import AddToCartSerializer  

from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt


from drf_yasg.utils import swagger_auto_schema
from rest_framework import serializers
from drf_yasg import openapi

logger = logging.getLogger(__name__)

# Create your views here.
stripe.api_key = settings.STRIPE_SECRET_KEY
endpoint_secret = settings.WEBHOOK_SECRET

from django.http import JsonResponse

def home(request):
    return JsonResponse({"message": "Welcome to our E-commerce API!"})


User = get_user_model()

@api_view(['GET'])
def product_list(request):
    products = Product.objects.filter(featured=True)
    serializer = ProductListSerializer(products, many=True)
    return Response(serializer.data)


@api_view(["GET"])
def product_detail(request, slug):
    product = Product.objects.get(slug=slug)
    serializer = ProductDetailSerializer(product)
    return Response(serializer.data)


@api_view(["GET"])
def category_list(request):
    categories = Category.objects.all()
    serializer = CategoryListSerializer(categories, many=True)
    return Response(serializer.data)

@api_view(["GET"])
def category_detail(request, slug):
    category = Category.objects.get(slug=slug)
    serializer = CategoryDetailSerializer(category)
    return Response(serializer.data)


@swagger_auto_schema(
    method='post',
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=['cart_code', 'product_id'],
        properties={
            'cart_code': openapi.Schema(type=openapi.TYPE_STRING),
            'product_id': openapi.Schema(type=openapi.TYPE_INTEGER),
        },
    ),
    responses={200: CartSerializer()},
)
@api_view(["POST"])
def add_to_cart(request):
    cart_code = request.data.get("cart_code")
    product_id = request.data.get("product_id")

    # Handle missing parameters
    if not cart_code or not product_id:
        return Response({"detail": "cart_code and product_id are required."}, status=400)

    try:
        cart, created = Cart.objects.get_or_create(cart_code=cart_code)
        product = Product.objects.get(id=product_id)
    except Product.DoesNotExist:
        return Response({"detail": "Product not found."}, status=404)

    # Increment quantity if already exists
    cartitem, created = CartItem.objects.get_or_create(product=product, cart=cart)
    if not created:
        cartitem.quantity += 1
    else:
        cartitem.quantity = 1
    cartitem.save()

    serializer = CartSerializer(cart)
    return Response(serializer.data)


@swagger_auto_schema(
    method='put',
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=['item_id', 'quantity'],
        properties={
            'item_id': openapi.Schema(type=openapi.TYPE_INTEGER),
            'quantity': openapi.Schema(type=openapi.TYPE_INTEGER),
        },
    ),
    responses={200: openapi.Response("Cart item updated", CartItemSerializer())}
)
@api_view(['PUT'])
def update_cartitem_quantity(request):
    cartitem_id = request.data.get("item_id")
    quantity = request.data.get("quantity")

    # Validate input
    if cartitem_id is None or quantity is None:
        return Response({"detail": "item_id and quantity are required."}, status=400)

    try:
        cartitem = CartItem.objects.get(id=cartitem_id)
    except CartItem.DoesNotExist:
        return Response({"detail": "Cart item not found."}, status=404)

    try:
        cartitem.quantity = int(quantity)
        cartitem.save()
    except ValueError:
        return Response({"detail": "Quantity must be an integer."}, status=400)

    serializer = CartItemSerializer(cartitem)
    return Response({"data": serializer.data, "message": "Cart item updated successfully!"})


@swagger_auto_schema(
    method='post',
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=['product_id', 'email', 'rating', 'review'],
        properties={
            'product_id': openapi.Schema(type=openapi.TYPE_INTEGER),
            'email': openapi.Schema(type=openapi.TYPE_STRING, format='email'),
            'rating': openapi.Schema(type=openapi.TYPE_INTEGER),
            'review': openapi.Schema(type=openapi.TYPE_STRING),
        },
    ),
    responses={200: ReviewSerializer()}
)
@api_view(["POST"])
def add_review(request):
    product_id = request.data.get("product_id")
    email = request.data.get("email")
    rating = request.data.get("rating")
    review_text = request.data.get("review")

    # Try to get product
    try:
        product = Product.objects.get(id=product_id)
    except Product.DoesNotExist:
        return Response({"error": "Product not found."}, status=status.HTTP_404_NOT_FOUND)

    # Try to get user
    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)

    # Prevent duplicate review
    if Review.objects.filter(product=product, user=user).exists():
        return Response({"error": "You already dropped a review for this product"}, status=status.HTTP_400_BAD_REQUEST)

    # Create review
    review = Review.objects.create(product=product, user=user, rating=rating, review=review_text)
    serializer = ReviewSerializer(review)
    return Response(serializer.data, status=status.HTTP_201_CREATED)


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
def update_review(request, pk):
    try:
        review = Review.objects.get(id=pk)
    except Review.DoesNotExist:
        return Response({"error": "Review not found."}, status=404)

    rating = request.data.get("rating")
    review_text = request.data.get("review")

    if rating is None:
        return Response({"error": "Rating is required."}, status=400)

    review.rating = rating
    if review_text is not None:
        review.review = review_text

    review.save()

    serializer = ReviewSerializer(review)
    return Response(serializer.data)



@api_view(['DELETE'])
def delete_review(request, pk):
    review = Review.objects.get(id=pk) 
    review.delete()

    return Response("Review deleted successfully!", status=204)

@api_view(['DELETE'])
def delete_cartitem(request, pk):
    cartitem = CartItem.objects.get(id=pk) 
    cartitem.delete()

    return Response("Cartitem deleted successfully!", status=204)



@api_view(['POST'])
def add_to_wishlist(request):
    email = request.data.get("email")
    product_id = request.data.get("product_id")

    user = User.objects.get(email=email)
    product = Product.objects.get(id=product_id) 

    wishlist = Wishlist.objects.filter(user=user, product=product)
    if wishlist:
        wishlist.delete()
        return Response("Wishlist deleted successfully!", status=204)

    new_wishlist = Wishlist.objects.create(user=user, product=product)
    serializer = WishlistSerializer(new_wishlist)
    return Response(serializer.data)

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
def product_search(request):
    query = request.query_params.get("query") 
    if not query:
        return Response("No query provided", status=400)
    
    products = Product.objects.filter(
        Q(name__icontains=query) | 
        Q(description__icontains=query) |
        Q(category__name__icontains=query)
    )
    serializer = ProductListSerializer(products, many=True)
    return Response(serializer.data)






@api_view(['POST'])
def create_checkout_session(request):
    cart_code = request.data.get("cart_code")
    email = request.data.get("email")
    cart = Cart.objects.get(cart_code=cart_code)
    try:
        checkout_session = stripe.checkout.Session.create(
            customer_email= email,
            payment_method_types=['card'],


            line_items=[
                {
                    'price_data': {
                        'currency': 'usd',
                        'product_data': {'name': item.product.name},
                        'unit_amount': int(item.product.price * 100),  # Amount in cents
                    },
                    'quantity': item.quantity,
                }
                for item in cart.cartitems.all()
            ] + [
                {
                    'price_data': {
                        'currency': 'usd',
                        'product_data': {'name': 'VAT Fee'},
                        'unit_amount': 500,  # $5 in cents
                    },
                    'quantity': 1,
                }
            ],


           
            mode='payment',
            # success_url="http://localhost:3000/success",
            # cancel_url="http://localhost:3000/cancel",

            success_url="https://next-shop-self.vercel.app/success",
            cancel_url="https://next-shop-self.vercel.app/failed",
            metadata = {"cart_code": cart_code}
        )
        return Response({'data': checkout_session})
    except Exception as e:
        return Response({'error': str(e)}, status=400)




@csrf_exempt
def my_webhook_view(request):
  payload = request.body
  sig_header = request.META['HTTP_STRIPE_SIGNATURE']
  event = None

  try:
    event = stripe.Webhook.construct_event(
      payload, sig_header, endpoint_secret
    )
  except ValueError as e:
    # Invalid payload
    return HttpResponse(status=400)
  except stripe.error.SignatureVerificationError as e:
    # Invalid signature
    return HttpResponse(status=400)

  if (
    event['type'] == 'checkout.session.completed'
    or event['type'] == 'checkout.session.async_payment_succeeded'
  ):
    session = event['data']['object']
    cart_code = session.get("metadata", {}).get("cart_code")

    fulfill_checkout(session, cart_code)


  return HttpResponse(status=200)



def fulfill_checkout(session, cart_code):
    
    order = Order.objects.create(stripe_checkout_id=session["id"],
        amount=session["amount_total"],
        currency=session["currency"],
        customer_email=session["customer_email"],
        status="Paid")
    

    print(session)


    cart = Cart.objects.get(cart_code=cart_code)
    cartitems = cart.cartitems.all()

    for item in cartitems:
        orderitem = OrderItem.objects.create(order=order, product=item.product, 
                                             quantity=item.quantity)
    
    cart.delete()




# Newly Added



# Serializer for Swagger and validation
class CreateUserSerializer(serializers.Serializer):
    username = serializers.CharField()
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

@swagger_auto_schema(method='post', request_body=CreateUserSerializer)
@api_view(['POST'])
def create_user(request):
    serializer = CreateUserSerializer(data=request.data)
    if serializer.is_valid():
        data = serializer.validated_data
        user = User.objects.create_user(
            username=data['username'],
            email=data['email'],
            password=data['password']
        )
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



@api_view(["GET"])
def existing_user(request, email):
    try:
        User.objects.get(email=email)
        return Response({"exists": True}, status=status.HTTP_200_OK)
    except User.DoesNotExist:
        return Response({"exists": False}, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
def get_orders(request):
    email = request.query_params.get("email")
    orders = Order.objects.filter(customer_email=email)
    serializer = OrderSerializer(orders, many=True)
    return Response(serializer.data)


@api_view(["POST"])
def add_address(request):
    email = request.data.get("email")
    street = request.data.get("street")
    city = request.data.get("city")
    state = request.data.get("state")
    phone = request.data.get("phone")

    if not email:
        return Response({"error": "Email is required"}, status=400)
    
    customer = User.objects.get(email=email)

    address, created = CustomerAddress.objects.get_or_create(
        customer=customer)
    address.email = email 
    address.street = street 
    address.city = city 
    address.state = state
    address.phone = phone 
    address.save()

    serializer = CustomerAddressSerializer(address)
    return Response(serializer.data)


@api_view(["GET"])
def get_address(request):
    email = request.query_params.get("email") 
    address = CustomerAddress.objects.filter(customer__email=email)
    if address.exists():
        address = address.last()
        serializer = CustomerAddressSerializer(address)
        return Response(serializer.data, status=status.HTTP_200_OK)
    return Response({"error": "Address not found"}, status=200)


@api_view(["GET"])
def my_wishlists(request):
    email = request.query_params.get("email")
    wishlists = Wishlist.objects.filter(user__email=email)
    serializer = WishlistSerializer(wishlists, many=True)
    return Response(serializer.data)


@api_view(["GET"])
def product_in_wishlist(request):
    email = request.query_params.get("email")
    product_id = request.query_params.get("product_id")

    if Wishlist.objects.filter(product__id=product_id, user__email=email).exists():
        return Response({"product_in_wishlist": True})
    return Response({"product_in_wishlist": False})



@api_view(['GET'])
def get_cart(request, cart_code):
    cart = Cart.objects.filter(cart_code=cart_code).first()
    
    if cart:
        serializer = CartSerializer(cart)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    return Response({"error": "Cart not found."}, status=status.HTTP_404_NOT_FOUND)




cart_code_param = openapi.Parameter(
    'cart_code', openapi.IN_QUERY, description="Cart code", type=openapi.TYPE_STRING, required=True
)

@swagger_auto_schema(
    method='get',
    manual_parameters=[cart_code_param],
    responses={200: 'OK'}
)
@api_view(['GET'])
def get_cart_stat(request):
    cart_code = request.query_params.get("cart_code")
    if not cart_code:
        return Response({"error": "cart_code is required"}, status=400)
    # Your logic here
    return Response({"message": f"Cart stats for {cart_code}"})


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
def product_in_cart(request):
    cart_code = request.query_params.get("cart_code")
    product_id = request.query_params.get("product_id")

    if not cart_code or not product_id:
        return Response({"error": "Both cart_code and product_id are required."}, status=400)

    try:
        product_id = int(product_id)
    except ValueError:
        return Response({"error": "product_id must be an integer."}, status=400)

    cart = Cart.objects.filter(cart_code=cart_code).first()
    if not cart:
        return Response({"error": "Cart not found."}, status=404)

    try:
        product = Product.objects.get(id=product_id)
    except Product.DoesNotExist:
        return Response({"error": "Product not found."}, status=404)

    product_exists_in_cart = CartItem.objects.filter(cart=cart, product=product).exists()

    return Response({'product_in_cart': product_exists_in_cart})

