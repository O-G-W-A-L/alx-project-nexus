from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views  
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

# Create a router and register our viewsets with it.
router = DefaultRouter()
router.register(r'products', views.ProductViewSet, basename='product')
router.register(r'categories', views.CategoryViewSet, basename='category')


# The API URLs are now determined automatically by the router.
urlpatterns = [
    path("", include(router.urls)), # Includes URLs for ProductViewSet and CategoryViewSet
    
    # Cart Management Endpoints
    path("add_to_cart/", views.add_to_cart, name="add_to_cart"),
    path("update_cartitem_quantity/", views.update_cartitem_quantity, name="update_cartitem_quantity"),
    path("delete_cartitem/<int:pk>/", views.delete_cartitem, name="delete_cartitem"),
    path("get_cart/<str:cart_code>/", views.get_cart, name="get_cart"),
    path("get_cart_stat/", views.get_cart_stat, name="get_cart_stat"),
    path("product_in_cart/", views.product_in_cart, name="product_in_cart"),

    # Review Endpoints
    path("add_review/", views.add_review, name="add_review"),
    path("update_review/<int:pk>/", views.update_review, name="update_review"),
    path("delete_review/<int:pk>/", views.delete_review, name="delete_review"),
    
    # Wishlist Endpoints
    path("add_to_wishlist/", views.add_to_wishlist, name="add_to_wishlist"),
    path("my_wishlists/", views.my_wishlists, name="my_wishlists"),
    path("product_in_wishlist/", views.product_in_wishlist, name="product_in_wishlist"),

    # Search Endpoint
    path("search/", views.product_search, name="search"),

    # Payment (Stripe) Endpoints
    path("create_checkout_session/", views.create_checkout_session, name="create_checkout_session"),
    path("webhook/", views.my_webhook_view, name="webhook"), # Stripe webhook for payment fulfillment

    # User and Address Management Endpoints
    path("create_user/", views.create_user, name="create_user"),
    path("existing_user/<str:email>/", views.existing_user, name="existing_user"),
    path("add_address/", views.add_address, name="add_address"),
    path("get_address/", views.get_address, name="get_address"),
    path("get_orders/", views.get_orders, name="get_orders"), # Get orders for authenticated user

    # JWT Authentication Endpoints
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'), # Get JWT access and refresh tokens
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'), # Refresh JWT access token
]
