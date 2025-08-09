# E-commerce Backend API

[![Python Version](https://img.shields.io/badge/Python-3.9%2B-blue.svg)](https://www.python.org/)
[![Django Version](https://img.shields.io/badge/Django-5.1.6-green.svg)](https://docs.djangoproject.com/en/5.1/)
[![DRF Version](https://img.shields.io/badge/Django%20REST%20Framework-3.15.1-brightgreen.svg)](https://www.django-rest-framework.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## Overview

This repository hosts a robust backend system designed to support a modern e-commerce product catalog. It emphasizes scalability, security, and performance, simulating a real-world development environment for backend engineers. The system handles comprehensive product data management, secure user authentication, and provides efficient APIs for filtering, sorting, and pagination of product listings.

## Project Goals

*   **CRUD APIs:** Implement full Create, Read, Update, and Delete (CRUD) operations for products, categories, and user authentication.
*   **Filtering, Sorting, Pagination:** Develop robust logic for efficient product discovery, allowing users to filter by category, sort by price, and navigate large datasets through pagination.
*   **Database Optimization:** Design a high-performance relational database schema to support seamless and efficient queries.
*   **API Documentation:** Provide comprehensive and user-friendly API documentation using Swagger/OpenAPI for easy frontend integration.
*   **Secure Authentication:** Implement secure user authentication using JSON Web Tokens (JWT).
*   **Payment Integration:** Integrate a payment gateway (Stripe) for handling checkout processes.

## Key Features

1.  **Product & Category Management:**
    *   Full CRUD operations for products and categories.
    *   Products include details like name, description, price, image, and category.
    *   Categories include name and image.
2.  **User Authentication & Management:**
    *   Secure user registration and login using JWT.
    *   Custom user model (`CustomUser`) extending Django's `AbstractUser`.
    *   User profile management (e.g., `profile_picture_url`).
3.  **Advanced Product Discovery:**
    *   **Filtering:** Filter products by name, category, and price range (min/max).
    *   **Sorting:** Sort products by price and name.
    *   **Searching:** Search products by name, description, and category name.
    *   **Pagination:** Efficiently retrieve large product datasets with paginated responses.
4.  **Shopping Cart Functionality:**
    *   Add/update/delete items in a shopping cart.
    *   Associate cart items with products and quantities.
    *   Calculate cart totals and sub-totals.
5.  **Reviews & Ratings:**
    *   Users can add reviews and ratings for products.
    *   Product ratings are aggregated to show average ratings and review counts.
6.  **Wishlist Management:**
    *   Users can add/remove products to/from their personal wishlists.
7.  **Order Processing:**
    *   Integration with Stripe for secure checkout sessions.
    *   Webhook handling for processing successful payments and creating orders.
    *   Order and Order Item tracking.
8.  **Customer Address Management:**
    *   Store and retrieve customer shipping addresses.
9.  **Comprehensive API Documentation:**
    *   Interactive API documentation generated using `drf_yasg` (Swagger/OpenAPI).
    *   Provides clear endpoints, request/response schemas, and authentication details.

## Technologies Used

*   **Backend Framework:** [Django 5.1.6](https://docs.djangoproject.com/en/5.1/)
*   **RESTful API:** [Django REST Framework 3.15.1](https://www.django-rest-framework.org/)
*   **Database:** [PostgreSQL](https://www.postgresql.org/) (configurable, defaults to SQLite for local development)
*   **Authentication:** [Django REST Framework Simple JWT](https://django-rest-framework-simplejwt.readthedocs.io/en/latest/)
*   **API Documentation:** [DRF-YASG (Swagger/OpenAPI)](https://drf-yasg.readthedocs.io/en/stable/)
*   **Filtering:** [Django-Filter](https://django-filter.readthedocs.io/en/stable/)
*   **Environment Variables:** [Python-Decouple](https://pypi.org/project/python-decouple/)
*   **CORS Handling:** [Django-CORS-Headers](https://pypi.org/project/django-cors-headers/)
*   **Static Files Serving:** [Whitenoise](http://whitenoise.evans.io/en/stable/)
*   **Payment Gateway:** [Stripe](https://stripe.com/)

## Project Structure

```
.
├── backend/
│   ├── .env.example          # Example environment variables
│   ├── .gitignore            # Git ignore file
│   ├── manage.py             # Django management script
│   ├── README.md             # Project README
│   ├── requirements.txt      # Python dependencies
│   ├── apiApp/               # Main API application
│   │   ├── migrations/       # Database migrations
│   │   ├── __init__.py
│   │   ├── admin.py          # Django admin configurations
│   │   ├── apps.py           # App configuration
│   │   ├── filters.py        # Custom Django-Filter classes
│   │   ├── models.py         # Database models (Product, Category, User, Cart, Order, etc.)
│   │   ├── pagination.py     # Custom pagination classes
│   │   ├── serializers.py    # Data serialization/deserialization
│   │   ├── signals.py        # Django signals (e.g., for review/rating updates)
│   │   ├── tests.py          # Unit and integration tests
│   │   ├── urls.py           # API endpoint definitions for apiApp
│   │   └── views.py          # API view logic
│   ├── ecommerce/            # Django project core
│   │   ├── __init__.py
│   │   ├── asgi.py           # ASGI config for async servers
│   │   ├── settings.py       # Project settings (database, installed apps, DRF config)
│   │   ├── urls.py           # Main project URL routing (includes apiApp, admin, swagger)
│   │   └── wsgi.py           # WSGI config for web servers
│   └── media/                # Directory for uploaded media files (product images, category images)
└── .marscode                 # IDE/tool specific file (ignored by Git)
```

## Getting Started

Follow these steps to set up and run the project locally.

### Prerequisites

*   Python 3.9+
*   pip (Python package installer)
*   (Optional) PostgreSQL installed and running if you wish to use it instead of SQLite.

### 1. Clone the Repository

```bash
git clone https://github.com/O-G-W-A-L/alx-project-nexus.git
cd alx-project-nexus/backend
```

### 2. Create and Activate a Virtual Environment

It's highly recommended to use a virtual environment to manage project dependencies.

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: `venv\Scripts\activate`
```

### 3. Install Dependencies

Install all required Python packages using pip:

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Create a `.env` file in the `backend/` directory by copying the `.env.example` file:

```bash
cp .env.example .env
```

Open the newly created `.env` file and update the variables.
**Example `.env` content:**

```
SECRET_KEY=your_django_secret_key_here
DEBUG=True
DB=False # Set to True for PostgreSQL, False for SQLite
# If DB=True, uncomment and configure PostgreSQL details:
# DB_NAME=your_db_name
# DB_USER=your_db_user
# DB_PASSWORD=your_db_password
# DB_HOST=localhost
# DB_PORT=5432

STRIPE_SECRET_KEY=sk_test_your_stripe_secret_key
WEBHOOK_SECRET=whsec_your_stripe_webhook_secret
```
*   Replace `your_django_secret_key_here` with a strong, randomly generated key.
*   Configure `DB` to `True` and provide PostgreSQL credentials if you intend to use PostgreSQL. Otherwise, keep `DB=False` for SQLite.
*   Obtain `STRIPE_SECRET_KEY` and `WEBHOOK_SECRET` from your Stripe Dashboard.

### 5. Run Database Migrations

Apply the database migrations to create the necessary tables:

```bash
python manage.py migrate
```

### 6. Create a Superuser (Optional)

To access the Django Admin panel, create a superuser:

```bash
python manage.py createsuperuser
```

Follow the prompts to set up your superuser credentials.

### 7. Start the Development Server

```bash
python manage.py runserver
```

The API will be accessible at `http://127.0.0.1:8000/`.

## Docker Setup

This project is fully containerized using Docker and Docker Compose.

### Prerequisites

*   [Docker](https://docs.docker.com/get-docker/)
*   [Docker Compose](https://docs.docker.com/compose/install/)

### 1. Configure Environment Variables

Create a `.env` file in the `backend/` directory:

```bash
cp backend/.env.example backend/.env
```

Update the `backend/.env` file with your configuration. For Docker, ensure `DB_HOST` is set to `db`.

### 2. Build and Run the Containers

```bash
docker-compose up --build
```

This command will build the Docker images and start the services.

### 3. Accessing the Services

*   **API:** `http://localhost:8000`
*   **Swagger UI:** `http://localhost:8000/swagger/`
*   **ReDoc:** `http://localhost:8000/redoc/`
*   **RabbitMQ Management:** `http://localhost:15673`

## API Endpoints & Documentation

The API documentation is automatically generated using Swagger UI and ReDoc.

*   **Swagger UI:** `http://127.0.0.1:8000/swagger/`
*   **ReDoc:** `http://127.0.0.1:8000/redoc/`

**Key API Endpoint Categories:**

*   `/api/products/`: CRUD for products, with filtering, sorting, and search.
*   `/api/categories/`: CRUD for categories, with sorting and search.
*   `/api/token/`: Obtain JWT access and refresh tokens.
*   `/api/token/refresh/`: Refresh JWT access token.
*   `/api/create_user/`: Register a new user.
*   `/api/add_to_cart/`: Add product to cart.
*   `/api/get_cart/<cart_code>/`: Retrieve cart details.
*   `/api/add_review/`: Add a review for a product.
*   `/api/add_to_wishlist/`: Add/remove product from wishlist.
*   `/api/create_checkout_session/`: Initiate Stripe checkout.
*   `/api/webhook/`: Stripe webhook endpoint for payment fulfillment.
*   `/api/get_orders/`: Retrieve user orders.
*   `/api/add_address/`: Add/update customer address.

## Database Schema Overview

The core database models include:

*   **`CustomUser`**: Extends Django's `AbstractUser` for authentication, with `email` as a unique identifier.
*   **`Category`**: Defines product categories with `name` and `slug`.
*   **`Product`**: Represents individual products with `name`, `description`, `price`, `image`, `slug`, and a foreign key to `Category`.
*   **`Cart`**: Manages shopping carts with a unique `cart_code`.
*   **`CartItem`**: Links `Cart` to `Product` with `quantity`.
*   **`Review`**: Stores user reviews and ratings for products.
*   **`ProductRating`**: Aggregates average rating and total reviews for each product.
*   **`Wishlist`**: Allows users to save products to a wishlist.
*   **`Order`**: Records completed orders, linked to Stripe checkout.
*   **`OrderItem`**: Details products included in an `Order`.
*   **`CustomerAddress`**: Stores customer shipping information.

## Code Quality & Best Practices

This project adheres to high standards of code quality and best practices:

*   **Modular Design:** Clear separation of concerns into Django apps and distinct files (`models.py`, `views.py`, `serializers.py`, etc.) for enhanced maintainability and scalability.
*   **RESTful Principles:** APIs are designed following RESTful conventions, utilizing Django REST Framework's powerful features.
*   **Secure Authentication:** Implementation of JWT for secure, stateless authentication.
*   **Database Optimization:** Strategic use of database indexing and unique constraints for efficient query performance.
*   **Comprehensive API Documentation:** Automated Swagger/OpenAPI documentation ensures clarity and ease of integration for frontend developers.
*   **Readability:** Consistent naming conventions, logical code organization, and adherence to Django/DRF patterns make the codebase highly readable and easy to onboard new engineers.
*   **Environment Configuration:** Use of `python-decouple` for managing sensitive information and environment-specific settings.

## Deployment

*(This section is a placeholder. Details on deployment to a cloud provider like Heroku, AWS, or Render would go here, including any specific configurations for production environments, Gunicorn/Nginx setup, etc.)*

## Contributing

Contributions are welcome! Please follow these steps:

1.  Fork the repository.
2.  Create a new branch for your feature or bug fix: `git checkout -b feature/your-feature-name` or `git checkout -b bugfix/issue-description`.
3.  Make your changes and ensure they adhere to the project's coding standards.
4.  Write appropriate tests for your changes.
5.  Ensure all existing tests pass.
6.  Commit your changes with a descriptive commit message (e.g., `feat: implement user registration`).
7.  Push your branch to your forked repository.
8.  Create a Pull Request to the `main` branch of this repository, describing your changes in detail.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
