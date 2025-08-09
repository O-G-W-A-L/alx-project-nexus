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
    
    # Product Search Endpoint
    path("search/", views.product_search, name="search"),

    # Cart Management Endpoints
    path("cart/add/", views.add_to_cart, name="add_to_cart"),
    path("cart/update_item_quantity/", views.update_cartitem_quantity, name="update_cartitem_quantity"),
    path("cart/delete_item/<int:pk>/", views.delete_cartitem, name="delete_cartitem"),
    path("cart/get/<str:cart_code>/", views.get_cart, name="get_cart"),
    path("cart/stats/", views.get_cart_stat, name="get_cart_stat"),
    path("cart/product_in_cart/", views.product_in_cart, name="product_in_cart"),

    # Review Endpoints
    path("reviews/add/", views.add_review, name="add_review"),
    path("reviews/update/<int:pk>/", views.update_review, name="update_review"),
    path("reviews/delete/<int:pk>/", views.delete_review, name="delete_review"),
    
    # Wishlist Endpoints
    path("wishlist/add/", views.add_to_wishlist, name="add_to_wishlist"),
    path("wishlist/my_lists/", views.my_wishlists, name="my_wishlists"),
    path("wishlist/product_in_wishlist/", views.product_in_wishlist, name="product_in_wishlist"),

    # Payment (Stripe) Endpoints
    path("payment/create_checkout_session/", views.create_checkout_session, name="create_checkout_session"),
    path("payment/webhook/", views.my_webhook_view, name="webhook"), 

    # User and Address Management Endpoints
    path("users/create/", views.create_user, name="create_user"),
    path("users/existing/<str:email>/", views.existing_user, name="existing_user"),
    path("addresses/add/", views.add_address, name="add_address"),
    path("addresses/get/", views.get_address, name="get_address"),
    path("orders/place/", views.place_order, name="place_order"), 
    path("orders/get/", views.get_orders, name="get_orders"), 

    # JWT Authentication Endpoints
    path('auth/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'), 
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]
