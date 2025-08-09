# Use a lightweight Python image as the base
FROM python:3.12-slim-bullseye

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV DJANGO_SETTINGS_MODULE=ecommerce.settings

# Set the working directory in the container
WORKDIR /app/backend

# Install system dependencies required for psycopg2-binary and other packages
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        gcc \
        libpq-dev \
        postgresql-client \
        build-essential \
        python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file and install Python dependencies
COPY requirements.txt /app/backend/
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . /app/backend/

# Expose the port Gunicorn will run on
EXPOSE 8000

# Run migrations, collect static files, then start Gunicorn
CMD /bin/sh -c "python manage.py migrate --no-input && python manage.py collectstatic --no-input --clear && gunicorn ecommerce.wsgi:application --bind 0.0.0.0:8000"
