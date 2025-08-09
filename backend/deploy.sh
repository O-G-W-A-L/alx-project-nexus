#!/usr/bin/env bash
# deploy.sh - Complete Django + Supabase deployment script for Render
# Place this file in your project root (same directory as manage.py)

set -o errexit  # Exit on any error
set -o nounset  # Exit on undefined variables
set -o pipefail # Exit on pipe failures

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

error() {
    echo -e "${RED}[ERROR] $1${NC}"
    exit 1
}

success() {
    echo -e "${GREEN}[SUCCESS] $1${NC}"
}

warning() {
    echo -e "${YELLOW}[WARNING] $1${NC}"
}

# Main deployment function
main() {
    log "🚀 Starting Django deployment to Render with Supabase..."
    
    # Step 1: Environment validation
    validate_environment
    
    # Step 2: Install dependencies
    install_dependencies
    
    # Step 3: Database operations
    setup_database
    
    # Step 4: Static files
    collect_static_files
    
    # Step 5: Health checks
    run_health_checks
    
    # Step 6: Optional superuser creation
    create_superuser_if_needed
    
    # Note: Celery workers and Celery Beat are expected to be run as separate services
    # and are not managed by this deployment script.
    
    # Step 7: Send notification
    send_notification
    
    success "🎉 Deployment completed successfully!"
}

# Validate required environment variables
validate_environment() {
    log "🔍 Validating environment variables..."
    
    required_vars=("DATABASE_URL" "SECRET_KEY" "ALLOWED_HOSTS")
    
    for var in "${required_vars[@]}"; do
        if [[ -z "${!var:-}" ]]; then
            error "Required environment variable $var is not set"
        fi
    done
    
    # Check if DATABASE_URL contains Supabase pooler
    if [[ ! "$DATABASE_URL" == *"supabase.com"* ]]; then
        warning "DATABASE_URL doesn't appear to be a Supabase URL"
    fi
    
    # Validate environment setting
    if [[ "${ENV:-}" != "production" ]]; then
        warning "ENV should be set to 'production' for deployment"
    fi
    
    success "Environment validation passed"
}

# Install Python dependencies
install_dependencies() {
    log "📦 Installing Python dependencies..."
    
    if [[ -f "requirements.txt" ]]; then
        pip install --no-cache-dir -r requirements.txt
        success "Dependencies installed"
    else
        error "requirements.txt not found"
    fi
}

# Database setup and migrations
setup_database() {
    log "🗄️  Setting up database and running migrations..."
    
    # Test database connection
    log "Testing database connection and Django ORM..."
    python manage.py shell -c "
from django.db import connection
from django.apps import apps
try:
    # Attempt to get a model and count objects to ensure ORM is working
    # Using User model as a common, always-present model
    from django.contrib.auth import get_user_model
    User = get_user_model()
    user_count = User.objects.count()
    print(f'✅ Database connection and Django ORM successful. Found {user_count} users.')
except Exception as e:
    print(f'❌ Database connection or Django ORM failed: {e}')
    exit(1)
" || error "Database connection or Django ORM test failed"
    
    # Check for pending migrations
    log "Checking for pending migrations..."
    if python manage.py showmigrations --plan | grep -q '\[ \]'; then
        log "Found pending migrations, applying..."
        python manage.py migrate --no-input --verbosity=2
        success "Migrations applied successfully"
    else
        log "No pending migrations found"
    fi
    
    # Verify tables exist
    log "Verifying database tables..."
    python manage.py shell -c "
from django.db import connection
with connection.cursor() as cursor:
    cursor.execute(\"SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public'\")
    table_count = cursor.fetchone()[0]
    print(f'✅ Found {table_count} tables in database')
    if table_count == 0:
        print('⚠️  Warning: No tables found in database')
"
}

# Collect static files
collect_static_files() {
    log "📁 Collecting static files..."
    
    python manage.py collectstatic --no-input --clear
    success "Static files collected"
}

# Run health checks
run_health_checks() {
    log "🏥 Running health checks..."
    
    # Django system check
    log "Running Django system checks..."
    python manage.py check --deploy || warning "Some deployment checks failed (non-critical)"
    
    # Database check
    log "Checking database tables..."
    python manage.py shell -c "
from django.core.management import execute_from_command_line
from django.db import connection
from django.apps import apps

try:
    # Check if we can query a basic model
    from django.contrib.auth.models import User
    user_count = User.objects.count()
    print(f'✅ Database working - {user_count} users found')
except Exception as e:
    print(f'⚠️  Database check warning: {e}')
"
    
    success "Health checks completed"
}

# Create superuser if environment variables are set
create_superuser_if_needed() {
    if [[ -n "${DJANGO_SUPERUSER_USERNAME:-}" && -n "${DJANGO_SUPERUSER_EMAIL:-}" && -n "${DJANGO_SUPERUSER_PASSWORD:-}" ]]; then
        log "👤 Creating superuser..."
        
        python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
username = '$DJANGO_SUPERUSER_USERNAME'
email = '$DJANGO_SUPERUSER_EMAIL'
password = '$DJANGO_SUPERUSER_PASSWORD'

if not User.objects.filter(username=username).exists():
    User.objects.create_superuser(username, email, password)
    print(f'✅ Superuser {username} created')
else:
    print(f'ℹ️  Superuser {username} already exists')
"
        success "Superuser setup completed"
    else
        log "ℹ️  Skipping superuser creation - set DJANGO_SUPERUSER_* variables if needed"
    fi
}

# Send deployment notification if webhook configured
send_notification() {
    if [[ -n "${DEPLOYMENT_WEBHOOK_URL:-}" ]]; then
        log "📢 Sending deployment notification..."
        
        curl -X POST -H 'Content-type: application/json' \
             --data "{\"text\":\"FlipCraft deployment successful - $(date)\",\"url\":\"$ALLOWED_HOSTS\"}" \
             "$DEPLOYMENT_WEBHOOK_URL" || warning "Failed to send notification"
    fi
}

# Cleanup function
cleanup() {
    log "🧹 Cleaning up temporary files..."
    # Add any cleanup tasks here
}

# Error handling
handle_error() {
    error "Deployment failed at step: $1"
    cleanup
    exit 1
}

# Set trap for error handling
trap 'handle_error $LINENO' ERR

# Run main function
main "$@"
