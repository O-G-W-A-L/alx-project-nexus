from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model
from .models import Category, Product, Cart, CartItem, Review, Wishlist, Order, OrderItem, CustomerAddress
from .serializers import ProductListSerializer, CategoryListSerializer, CartSerializer, ReviewSerializer
import json

User = get_user_model()

class TestSetup(APITestCase):
    """
    Base class for setting up common test data and clients.
    """
    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            username='admin', email='admin@example.com', password='adminpassword'
        )
        self.regular_user = User.objects.create_user(
            username='testuser', email='test@example.com', password='testpassword'
        )
        self.another_user = User.objects.create_user(
            username='anotheruser', email='another@example.com', password='anotherpassword'
        )

        self.category1 = Category.objects.create(name='Electronics', slug='electronics')
        self.category2 = Category.objects.create(name='Books', slug='books')

        self.product1 = Product.objects.create(
            name='Laptop', description='Powerful laptop', price=1200.00,
            category=self.category1, slug='laptop'
        )
        self.product2 = Product.objects.create(
            name='Smartphone', description='Latest smartphone', price=800.00,
            category=self.category1, slug='smartphone'
        )
        self.product3 = Product.objects.create(
            name='Python Book', description='Learn Python', price=50.00,
            category=self.category2, slug='python-book'
        )

        self.cart_code = 'testcart123'
        self.cart = Cart.objects.create(cart_code=self.cart_code)
        self.cart_item = CartItem.objects.create(cart=self.cart, product=self.product1, quantity=2)

        self.review = Review.objects.create(
            product=self.product1, user=self.regular_user, rating=5, review="Great product!"
        )

        self.wishlist = Wishlist.objects.create(user=self.regular_user, product=self.product1)

        # URLs for common endpoints
        self.product_list_url = reverse('product-list')
        self.category_list_url = reverse('category-list')
        self.add_to_cart_url = reverse('add_to_cart')
        self.update_cartitem_quantity_url = reverse('update_cartitem_quantity')
        self.add_review_url = reverse('add_review')
        self.add_to_wishlist_url = reverse('add_to_wishlist')
        self.product_search_url = reverse('search')
        self.create_user_url = reverse('create_user')
        self.get_cart_url = reverse('get_cart', args=[self.cart_code])
        self.delete_cartitem_url = reverse('delete_cartitem', args=[self.cart_item.id])
        self.delete_review_url = reverse('delete_review', args=[self.review.id])
        self.update_review_url = reverse('update_review', args=[self.review.id])
        self.existing_user_url = lambda email: reverse('existing_user', args=[email])
        self.get_address_url = reverse('get_address')
        self.add_address_url = reverse('add_address')
        self.my_wishlists_url = reverse('my_wishlists')
        self.product_in_wishlist_url = reverse('product_in_wishlist')
        self.product_in_cart_url = reverse('product_in_cart')
        self.get_orders_url = reverse('get_orders')
        self.create_checkout_session_url = reverse('create_checkout_session')


        return super().setUp()

    def tearDown(self):
        # Clean up created objects if necessary (though APITestCase handles transactions)
        pass

class UserModelTests(TestSetup):
    """
    Tests for the CustomUser model and related API endpoints.
    """
    def test_create_user_api(self):
        data = {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password': 'newpassword123',
            'first_name': 'New',
            'last_name': 'User'
        }
        response = self.client.post(self.create_user_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(email='newuser@example.com').exists())

    def test_create_user_api_missing_fields(self):
        data = {
            'username': 'incomplete',
            'email': 'incomplete@example.com'
            # Missing password
        }
        response = self.client.post(self.create_user_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password', response.data)

    def test_existing_user_api_exists(self):
        response = self.client.get(self.existing_user_url(self.regular_user.email))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['exists'])

    def test_existing_user_api_not_exists(self):
        response = self.client.get(self.existing_user_url('nonexistent@example.com'))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertFalse(response.data['exists'])

class CategoryAPITests(TestSetup):
    """
    Tests for Category model and API endpoints.
    """
    def test_category_slug_generation(self):
        new_category = Category.objects.create(name='Test Category')
        self.assertEqual(new_category.slug, 'test-category')
        # Test uniqueness
        another_category = Category.objects.create(name='Test Category')
        self.assertNotEqual(another_category.slug, 'test-category')
        self.assertTrue(another_category.slug.startswith('test-category-'))

    def test_get_category_list(self):
        response = self.client.get(self.category_list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Handle both direct list and paginated response formats
        if isinstance(response.data, dict) and 'results' in response.data:
            actual_data = response.data['results']
        else:
            actual_data = response.data

        # The CategoryViewSet now uses pagination, so response.data will be a dictionary
        # with a 'results' key.
        self.assertIn('results', response.data)
        actual_data = response.data['results']
        
        self.assertEqual(len(actual_data), 2) # category1, category2
        # Check for specific names as order might vary slightly without explicit test ordering
        expected_category_names = {self.category1.name, self.category2.name}
        actual_category_names = {item['name'] for item in actual_data}
        self.assertEqual(actual_category_names, expected_category_names)

    def test_get_category_detail(self):
        response = self.client.get(reverse('category-detail', args=[self.category1.slug]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], self.category1.name)
        self.assertIn('products', response.data) # Check if products are nested

    def test_create_category_as_admin(self):
        self.client.force_authenticate(user=self.admin_user)
        data = {'name': 'New Category'}
        response = self.client.post(self.category_list_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Category.objects.filter(name='New Category').exists())

    def test_create_category_as_regular_user_forbidden(self):
        self.client.force_authenticate(user=self.regular_user)
        data = {'name': 'Forbidden Category'}
        response = self.client.post(self.category_list_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_category_as_admin(self):
        self.client.force_authenticate(user=self.admin_user)
        data = {'name': 'Updated Category Name'}
        response = self.client.patch(reverse('category-detail', args=[self.category1.slug]), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.category1.refresh_from_db()
        self.assertEqual(self.category1.name, 'Updated Category Name')

    def test_delete_category_as_admin(self):
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.delete(reverse('category-detail', args=[self.category1.slug]))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Category.objects.filter(slug=self.category1.slug).exists())

class ProductAPITests(TestSetup):
    """
    Tests for Product model and API endpoints, including filtering, sorting, and search.
    """
    def test_product_slug_generation(self):
        new_product = Product.objects.create(name='New Product', description='Desc', price=10.00)
        self.assertEqual(new_product.slug, 'new-product')
        # Test uniqueness
        another_product = Product.objects.create(name='New Product', description='Desc', price=20.00)
        self.assertNotEqual(another_product.slug, 'new-product')
        self.assertTrue(another_product.slug.startswith('new-product-'))

    def test_get_product_list(self):
        response = self.client.get(self.product_list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 3) # product1, product2, product3
        self.assertEqual(response.data['results'][0]['name'], self.product1.name)

    def test_get_product_detail(self):
        response = self.client.get(reverse('product-detail', args=[self.product1.slug]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], self.product1.name)
        self.assertIn('reviews', response.data) # Check if reviews are nested
        self.assertIn('rating', response.data) # Check if rating is nested

    def test_create_product_as_admin(self):
        self.client.force_authenticate(user=self.admin_user)
        data = {
            'name': 'New Gadget',
            'description': 'A cool new gadget',
            'price': 250.00,
            'category': self.category1.id # Use category ID
        }
        response = self.client.post(self.product_list_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Product.objects.filter(name='New Gadget').exists())

    def test_create_product_as_regular_user_forbidden(self):
        self.client.force_authenticate(user=self.regular_user)
        data = {
            'name': 'Forbidden Gadget',
            'description': 'A forbidden gadget',
            'price': 100.00,
            'category': self.category1.id
        }
        response = self.client.post(self.product_list_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_filter_products_by_category(self):
        response = self.client.get(self.product_list_url + f'?category={self.category1.slug}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)
        self.assertEqual(response.data['results'][0]['name'], self.product1.name)
        self.assertEqual(response.data['results'][1]['name'], self.product2.name)

    def test_filter_products_by_price_range(self):
        response = self.client.get(self.product_list_url + '?min_price=100&max_price=1000')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1) # Smartphone
        self.assertEqual(response.data['results'][0]['name'], self.product2.name)

    def test_sort_products_by_price_descending(self):
        response = self.client.get(self.product_list_url + '?ordering=-price')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['results'][0]['name'], self.product1.name) # Laptop (1200)
        self.assertEqual(response.data['results'][1]['name'], self.product2.name) # Smartphone (800)
        self.assertEqual(response.data['results'][2]['name'], self.product3.name) # Python Book (50)

    def test_search_products_by_name(self):
        response = self.client.get(self.product_list_url + '?search=Laptop')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['name'], self.product1.name)

    def test_search_products_by_description(self):
        response = self.client.get(self.product_list_url + '?search=smartphone')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['name'], self.product2.name)

    def test_search_products_by_category_name(self):
        response = self.client.get(self.product_list_url + '?search=Books')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['name'], self.product3.name)

    def test_product_list_pagination(self):
        # Assuming default page_size is 10, create more products to test pagination
        for i in range(15):
            Product.objects.create(
                name=f'Product {i}', description='Test', price=10.00, category=self.category1
            )
        response = self.client.get(self.product_list_url + '?page=1&page_size=5')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 5)
        self.assertIn('next', response.data)
        self.assertIn('count', response.data)
        self.assertEqual(response.data['count'], 18) # 3 initial + 15 new

class CartAPITests(TestSetup):
    """
    Tests for Cart and CartItem API endpoints.
    """
    def test_add_to_cart_new_cart(self):
        data = {
            'cart_code': 'newcart123',
            'product_id': self.product2.id
        }
        response = self.client.post(self.add_to_cart_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(Cart.objects.filter(cart_code='newcart123').exists())
        new_cart = Cart.objects.get(cart_code='newcart123')
        self.assertEqual(new_cart.cartitems.count(), 1)
        self.assertEqual(new_cart.cartitems.first().product, self.product2)
        self.assertEqual(new_cart.cartitems.first().quantity, 1)

    def test_add_to_cart_existing_cart_new_item(self):
        data = {
            'cart_code': self.cart_code,
            'product_id': self.product2.id
        }
        response = self.client.post(self.add_to_cart_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.cart.cartitems.count(), 2) # product1 (2) + product2 (1)
        self.assertEqual(self.cart.cartitems.get(product=self.product2).quantity, 1)

    def test_add_to_cart_existing_item_increment_quantity(self):
        data = {
            'cart_code': self.cart_code,
            'product_id': self.product1.id
        }
        response = self.client.post(self.add_to_cart_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.cart_item.refresh_from_db()
        self.assertEqual(self.cart_item.quantity, 3) # Was 2, now 3

    def test_add_to_cart_missing_data(self):
        data = {'cart_code': 'missing'} # Missing product_id
        response = self.client.post(self.add_to_cart_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('detail', response.data)

    def test_add_to_cart_product_not_found(self):
        data = {
            'cart_code': self.cart_code,
            'product_id': 9999 # Non-existent product
        }
        response = self.client.post(self.add_to_cart_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn('detail', response.data)

    def test_update_cartitem_quantity(self):
        data = {
            'item_id': self.cart_item.id,
            'quantity': 5
        }
        response = self.client.put(self.update_cartitem_quantity_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.cart_item.refresh_from_db()
        self.assertEqual(self.cart_item.quantity, 5)
        self.assertIn('message', response.data)

    def test_update_cartitem_quantity_invalid_item_id(self):
        data = {
            'item_id': 9999,
            'quantity': 5
        }
        response = self.client.put(self.update_cartitem_quantity_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn('detail', response.data)

    def test_update_cartitem_quantity_invalid_quantity(self):
        data = {
            'item_id': self.cart_item.id,
            'quantity': 'abc'
        }
        response = self.client.put(self.update_cartitem_quantity_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('detail', response.data)

    def test_delete_cartitem(self):
        response = self.client.delete(self.delete_cartitem_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(CartItem.objects.filter(id=self.cart_item.id).exists())

    def test_delete_cartitem_not_found(self):
        response = self.client.delete(reverse('delete_cartitem', args=[9999]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_cart(self):
        response = self.client.get(self.get_cart_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['cart_code'], self.cart_code)
        self.assertEqual(len(response.data['cartitems']), 1)
        self.assertEqual(response.data['cartitems'][0]['product']['name'], self.product1.name)
        self.assertEqual(response.data['cartitems'][0]['quantity'], 2)

    def test_get_cart_not_found(self):
        response = self.client.get(reverse('get_cart', args=['nonexistentcart']))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn('detail', response.data)

    def test_product_in_cart_true(self):
        response = self.client.get(self.product_in_cart_url, {'cart_code': self.cart_code, 'product_id': self.product1.id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['product_in_cart'])

    def test_product_in_cart_false(self):
        response = self.client.get(self.product_in_cart_url, {'cart_code': self.cart_code, 'product_id': self.product3.id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['product_in_cart'])

    def test_product_in_cart_missing_params(self):
        response = self.client.get(self.product_in_cart_url, {'cart_code': self.cart_code}) # Missing product_id
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)

class ReviewAPITests(TestSetup):
    """
    Tests for Review API endpoints.
    """
    def test_add_review(self):
        data = {
            'product_id': self.product2.id,
            'email': self.another_user.email,
            'rating': 4,
            'review': 'Very good product, highly recommend!'
        }
        response = self.client.post(self.add_review_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Review.objects.filter(product=self.product2, user=self.another_user).exists())
        self.assertEqual(Review.objects.get(product=self.product2, user=self.another_user).rating, 4)

    def test_add_review_duplicate(self):
        data = {
            'product_id': self.product1.id,
            'email': self.regular_user.email,
            'rating': 3,
            'review': 'Updated review'
        }
        response = self.client.post(self.add_review_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('detail', response.data)
        self.assertEqual(response.data['detail'], 'You have already reviewed this product.')

    def test_add_review_product_not_found(self):
        data = {
            'product_id': 9999,
            'email': self.regular_user.email,
            'rating': 5,
            'review': 'Non-existent product review'
        }
        response = self.client.post(self.add_review_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn('detail', response.data)

    def test_update_review(self):
        data = {
            'rating': 4,
            'review': 'Updated review text.'
        }
        response = self.client.put(self.update_review_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.review.refresh_from_db()
        self.assertEqual(self.review.rating, 4)
        self.assertEqual(self.review.review, 'Updated review text.')

    def test_update_review_missing_rating(self):
        data = {
            'review': 'Only updating text.'
        }
        response = self.client.put(self.update_review_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('detail', response.data)
        self.assertEqual(response.data['detail'], 'Rating is required.')

    def test_delete_review(self):
        response = self.client.delete(self.delete_review_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Review.objects.filter(id=self.review.id).exists())

    def test_delete_review_not_found(self):
        response = self.client.delete(reverse('delete_review', args=[9999]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

class WishlistAPITests(TestSetup):
    """
    Tests for Wishlist API endpoints.
    """
    def test_add_to_wishlist_new_item(self):
        data = {
            'email': self.another_user.email,
            'product_id': self.product2.id
        }
        response = self.client.post(self.add_to_wishlist_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(Wishlist.objects.filter(user=self.another_user, product=self.product2).exists())

    def test_add_to_wishlist_remove_existing_item(self):
        # Add product1 to regular_user's wishlist (already done in setup)
        # Now try to add it again, which should remove it
        data = {
            'email': self.regular_user.email,
            'product_id': self.product1.id
        }
        response = self.client.post(self.add_to_wishlist_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT) # 204 for successful deletion
        self.assertFalse(Wishlist.objects.filter(user=self.regular_user, product=self.product1).exists())

    def test_my_wishlists(self):
        response = self.client.get(self.my_wishlists_url, {'email': self.regular_user.email})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['product']['name'], self.product1.name)

    def test_product_in_wishlist_true(self):
        response = self.client.get(self.product_in_wishlist_url, {'email': self.regular_user.email, 'product_id': self.product1.id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['product_in_wishlist'])

    def test_product_in_wishlist_false(self):
        response = self.client.get(self.product_in_wishlist_url, {'email': self.regular_user.email, 'product_id': self.product3.id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['product_in_wishlist'])

class CustomerAddressAPITests(TestSetup):
    """
    Tests for CustomerAddress API endpoints.
    """
    def test_add_address_new(self):
        data = {
            'email': self.another_user.email,
            'street': '123 New St',
            'city': 'New City',
            'state': 'NS',
            'phone': '1112223333'
        }
        response = self.client.post(self.add_address_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(CustomerAddress.objects.filter(customer=self.another_user).exists())
        address = CustomerAddress.objects.get(customer=self.another_user)
        self.assertEqual(address.street, '123 New St')

    def test_add_address_update_existing(self):
        CustomerAddress.objects.create(
            customer=self.regular_user,
            street='Old Street', city='Old City', state='OS', phone='0000000000'
        )
        data = {
            'email': self.regular_user.email,
            'street': 'Updated Street',
            'city': 'Updated City',
            'state': 'US',
            'phone': '9998887777'
        }
        response = self.client.post(self.add_address_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        address = CustomerAddress.objects.get(customer=self.regular_user)
        self.assertEqual(address.street, 'Updated Street')
        self.assertEqual(address.city, 'Updated City')

    def test_get_address_exists(self):
        CustomerAddress.objects.create(
            customer=self.regular_user,
            street='Main St', city='Capital', state='CA', phone='1234567890'
        )
        response = self.client.get(self.get_address_url, {'email': self.regular_user.email})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['street'], 'Main St')

    def test_get_address_not_found(self):
        response = self.client.get(self.get_address_url, {'email': 'nonexistent@example.com'})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn('detail', response.data)

    def test_get_address_missing_email(self):
        response = self.client.get(self.get_address_url) # Missing email param
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('detail', response.data)

class SearchAPITests(TestSetup):
    """
    Tests for the product search API endpoint.
    """
    def test_product_search_by_name(self):
        response = self.client.get(self.product_search_url, {'query': 'Laptop'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['name'], self.product1.name)

    def test_product_search_by_description(self):
        response = self.client.get(self.product_search_url, {'query': 'Learn Python'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['name'], self.product3.name)

    def test_product_search_by_category_name(self):
        response = self.client.get(self.product_search_url, {'query': 'Electronics'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        self.assertIn(self.product1.name, [p['name'] for p in response.data])
        self.assertIn(self.product2.name, [p['name'] for p in response.data])

    def test_product_search_no_results(self):
        response = self.client.get(self.product_search_url, {'query': 'NonExistentItem'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)

    def test_product_search_no_query(self):
        response = self.client.get(self.product_search_url) # No query param
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('detail', response.data)
