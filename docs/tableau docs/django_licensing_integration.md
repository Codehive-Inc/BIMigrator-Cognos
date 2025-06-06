# BIMigrator Licensing System - Django Backend Integration Guide

This document provides detailed instructions for integrating the BIMigrator licensing system with a Django backend application. The licensing system uses PostgreSQL to store and enforce license constraints (migration count and expiry date).

## Overview

The licensing system consists of:
1. PostgreSQL database schema and stored procedures
2. Python SDK integration for license validation
3. Django API endpoints for license status and management

This guide focuses on steps 1 and 3, as the SDK integration has already been implemented.

## 1. Database Setup

### 1.1 Prerequisites

- PostgreSQL 12+ installed and running
- Database superuser access for initial setup

### 1.2 Run SQL Scripts

Execute the SQL scripts in the following order to set up the licensing database:

```bash
# Create the database (if it doesn't exist)
psql -U postgres -c "CREATE DATABASE bimigrator_db;"

# Run each script in order
psql -U postgres -d bimigrator_db -f /path/to/BIMigrator/sql/licensing/01_create_tables.sql
psql -U postgres -d bimigrator_db -f /path/to/BIMigrator/sql/licensing/02_create_functions.sql
psql -U postgres -d bimigrator_db -f /path/to/BIMigrator/sql/licensing/03_create_users.sql
psql -U postgres -d bimigrator_db -f /path/to/BIMigrator/sql/licensing/04_initial_license.sql
```

Alternatively, you can run the master script:

```bash
psql -U postgres -d bimigrator_db -f /path/to/BIMigrator/sql/licensing/00_setup_all.sql
```

### 1.3 Verify Database Setup

Verify that the database setup was successful:

```bash
# Connect to the database
psql -U postgres -d bimigrator_db

# Check if the licenses table exists
\dt licenses

# Check if the stored functions exist
\df increment_migration_count
\df get_license_status

# Check if the app_user exists
\du app_user

# Check if the initial license record was created
SELECT * FROM licenses;
```

## 2. Django Integration

### 2.1 Add Required Dependencies

Add the following to your Django project's `requirements.txt`:

```
psycopg2-binary>=2.9.5
python-dotenv>=0.21.0
```

### 2.2 Configure Environment Variables

Create or update your Django project's `.env` file with the following variables:

```
# Database Connection Settings
BIMIGRATOR_DB_HOST=localhost
BIMIGRATOR_DB_PORT=5432
BIMIGRATOR_DB_NAME=bimigrator_db
BIMIGRATOR_DB_USER=app_user
BIMIGRATOR_DB_PASSWORD=change_me_in_production

# Connection Pool Settings
BIMIGRATOR_DB_POOL_MIN=1
BIMIGRATOR_DB_POOL_MAX=5

# License Settings
BIMIGRATOR_LICENSE_ID=1
```

### 2.3 Create License Models

Create a Django app for licensing if it doesn't exist:

```bash
python manage.py startapp licensing
```

Add the following model to `licensing/models.py`:

```python
from django.db import models

class License(models.Model):
    """
    Mirror of the licenses table in the PostgreSQL database.
    This is a read-only model used for displaying license information.
    """
    license_key = models.CharField(max_length=255, unique=True)
    activated_at = models.DateTimeField()
    expires_at = models.DateTimeField()
    max_migrations = models.IntegerField()
    migrations_used = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    client_name = models.CharField(max_length=255, null=True, blank=True)
    license_type = models.CharField(max_length=50, null=True, blank=True)

    class Meta:
        managed = False  # This model is read-only
        db_table = 'licenses'
        
    @property
    def migrations_remaining(self):
        return max(0, self.max_migrations - self.migrations_used)
    
    @property
    def is_active(self):
        from django.utils import timezone
        return timezone.now() <= self.expires_at
    
    @property
    def status_message(self):
        if not self.is_active:
            return "License expired"
        elif self.migrations_remaining <= 0:
            return "Migration limit reached"
        else:
            return "License is active"
```

### 2.4 Create License Service

Create a service to interact with the licensing database in `licensing/services.py`:

```python
import os
import logging
from datetime import datetime
from django.utils import timezone
from django.db import connection

logger = logging.getLogger(__name__)

class LicenseService:
    """Service for license validation and status checking."""
    
    @staticmethod
    def get_license_id():
        """Get the license ID from environment variables or use default."""
        license_id = os.environ.get('BIMIGRATOR_LICENSE_ID')
        return int(license_id) if license_id else 1
    
    @classmethod
    def check_license_status(cls, license_id=None):
        """Check the current license status without incrementing the migration count."""
        if license_id is None:
            license_id = cls.get_license_id()
            
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM get_license_status(%s);", [license_id])
            result = cursor.fetchone()
            
            if not result:
                return {
                    'is_active': False,
                    'expires_at': None,
                    'max_migrations': 0,
                    'migrations_used': 0,
                    'migrations_remaining': 0,
                    'status_message': 'License not found'
                }
            
            # Parse the result into a dictionary
            status = {
                'is_active': result[0],
                'expires_at': result[1],
                'max_migrations': result[2],
                'migrations_used': result[3],
                'migrations_remaining': result[4],
                'status_message': result[5]
            }
            
            # Add formatted fields for display
            if status['expires_at']:
                days_remaining = (status['expires_at'].date() - timezone.now().date()).days
                status['days_remaining'] = max(0, days_remaining)
                status['expires_at_formatted'] = status['expires_at'].strftime('%Y-%m-%d')
            else:
                status['days_remaining'] = 0
                status['expires_at_formatted'] = 'N/A'
                
            return status
    
    @classmethod
    def validate_license(cls, license_id=None):
        """Validate the license and increment the migration count if valid."""
        if license_id is None:
            license_id = cls.get_license_id()
            
        # First check the license status
        status = cls.check_license_status(license_id)
        
        # If license is not active or limit reached, return status without incrementing
        if not status['is_active'] or status['migrations_remaining'] <= 0:
            return status
            
        # Call the increment_migration_count function
        with connection.cursor() as cursor:
            cursor.execute("SELECT increment_migration_count(%s);", [license_id])
            result = cursor.fetchone()
            
            if not result or not result[0]:
                # Get updated status to determine the reason for failure
                return cls.check_license_status(license_id)
                
            # License validated successfully, get updated status
            return cls.check_license_status(license_id)
```

### 2.5 Create License API Endpoints

Create API endpoints in `licensing/views.py`:

```python
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
import json
import logging

from .services import LicenseService
from .models import License

logger = logging.getLogger(__name__)

@require_http_methods(["GET"])
def license_status(request):
    """API endpoint to get the current license status."""
    try:
        status = LicenseService.check_license_status()
        return JsonResponse(status)
    except Exception as e:
        logger.error(f"Error checking license status: {str(e)}")
        return JsonResponse({
            'error': f"Failed to check license status: {str(e)}"
        }, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def validate_license(request):
    """API endpoint to validate the license before a migration."""
    try:
        status = LicenseService.validate_license()
        
        if not status['is_active']:
            return JsonResponse({
                'error': "License has expired",
                'status': status
            }, status=403)
            
        if status['migrations_remaining'] <= 0:
            return JsonResponse({
                'error': "Migration limit reached",
                'status': status
            }, status=403)
            
        return JsonResponse({
            'success': True,
            'message': "License validated successfully",
            'status': status
        })
    except Exception as e:
        logger.error(f"Error validating license: {str(e)}")
        return JsonResponse({
            'error': f"Failed to validate license: {str(e)}"
        }, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def create_license(request):
    """API endpoint to create a new license (admin only)."""
    # This should be protected by authentication and authorization
    try:
        data = json.loads(request.body)
        
        # Create a new license record in the database
        # This would typically be done through direct SQL since we're using a separate database
        # with restricted access
        
        return JsonResponse({
            'success': True,
            'message': "License created successfully"
        })
    except Exception as e:
        logger.error(f"Error creating license: {str(e)}")
        return JsonResponse({
            'error': f"Failed to create license: {str(e)}"
        }, status=500)
```

### 2.6 Add URL Routes

Add the following to `licensing/urls.py`:

```python
from django.urls import path
from . import views

urlpatterns = [
    path('status/', views.license_status, name='license_status'),
    path('validate/', views.validate_license, name='validate_license'),
    path('create/', views.create_license, name='create_license'),
]
```

Include these URLs in your project's main `urls.py`:

```python
from django.urls import path, include

urlpatterns = [
    # ... other URL patterns ...
    path('api/license/', include('licensing.urls')),
]
```

### 2.7 Create Migration API Middleware

Create a middleware to validate the license before processing migration requests:

```python
# licensing/middleware.py
import json
from django.http import JsonResponse
from .services import LicenseService

class LicenseValidationMiddleware:
    """Middleware to validate license before processing migration requests."""
    
    def __init__(self, get_response):
        self.get_response = get_response
        
    def __call__(self, request):
        # Only check license for migration API endpoints
        if request.path.startswith('/api/migrate/'):
            try:
                status = LicenseService.check_license_status()
                
                if not status['is_active']:
                    return JsonResponse({
                        'error': "License has expired",
                        'status': status
                    }, status=403)
                    
                if status['migrations_remaining'] <= 0:
                    return JsonResponse({
                        'error': "Migration limit reached",
                        'status': status
                    }, status=403)
            except Exception as e:
                return JsonResponse({
                    'error': f"License validation failed: {str(e)}"
                }, status=500)
        
        return self.get_response(request)
```

Add the middleware to your Django settings:

```python
MIDDLEWARE = [
    # ... other middleware ...
    'licensing.middleware.LicenseValidationMiddleware',
]
```

### 2.8 Create Migration API View

Create an API endpoint for initiating migrations:

```python
# In your migration app's views.py
import os
import tempfile
import logging
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from bimigrator.main import migrate_to_tmdl
from licensing.services import LicenseService

logger = logging.getLogger(__name__)

@csrf_exempt
@require_http_methods(["POST"])
def migrate_tableau_workbook(request):
    """API endpoint to migrate a Tableau workbook to Power BI TMDL format."""
    try:
        # Validate license and increment migration count
        license_status = LicenseService.validate_license()
        
        if not license_status['is_active']:
            return JsonResponse({
                'error': "License has expired",
                'status': license_status
            }, status=403)
            
        if license_status['migrations_remaining'] <= 0:
            return JsonResponse({
                'error': "Migration limit reached",
                'status': license_status
            }, status=403)
        
        # Process the uploaded file
        if 'file' not in request.FILES:
            return JsonResponse({'error': 'No file uploaded'}, status=400)
            
        uploaded_file = request.FILES['file']
        
        # Create a temporary file
        with tempfile.NamedTemporaryFile(suffix='.twb', delete=False) as temp_file:
            for chunk in uploaded_file.chunks():
                temp_file.write(chunk)
            temp_file_path = temp_file.name
        
        try:
            # Get output directory from request or use default
            output_dir = request.POST.get('output_dir', 'output')
            
            # Perform the migration
            migrate_to_tmdl(
                temp_file_path,
                output_dir=output_dir,
                skip_license_check=True  # Skip SDK-level check since we've already validated
            )
            
            # Return success response
            return JsonResponse({
                'success': True,
                'message': 'Migration completed successfully',
                'output_dir': output_dir,
                'license_status': license_status
            })
        finally:
            # Clean up the temporary file
            os.unlink(temp_file_path)
            
    except Exception as e:
        logger.error(f"Error during migration: {str(e)}")
        return JsonResponse({
            'error': f"Migration failed: {str(e)}"
        }, status=500)
```

Add the URL route in your migration app's `urls.py`:

```python
from django.urls import path
from . import views

urlpatterns = [
    path('', views.migrate_tableau_workbook, name='migrate_tableau_workbook'),
]
```

Include these URLs in your project's main `urls.py`:

```python
from django.urls import path, include

urlpatterns = [
    # ... other URL patterns ...
    path('api/migrate/', include('your_migration_app.urls')),
]
```

## 3. Testing the Integration

### 3.1 Test License Status API

```bash
curl http://localhost:8000/api/license/status/
```

Expected response:
```json
{
    "is_active": true,
    "expires_at": "2026-05-28T20:42:05.123456+00:00",
    "max_migrations": 100,
    "migrations_used": 0,
    "migrations_remaining": 100,
    "status_message": "License is active",
    "days_remaining": 365,
    "expires_at_formatted": "2026-05-28"
}
```

### 3.2 Test License Validation API

```bash
curl -X POST http://localhost:8000/api/license/validate/
```

Expected response:
```json
{
    "success": true,
    "message": "License validated successfully",
    "status": {
        "is_active": true,
        "expires_at": "2026-05-28T20:42:05.123456+00:00",
        "max_migrations": 100,
        "migrations_used": 1,
        "migrations_remaining": 99,
        "status_message": "License is active",
        "days_remaining": 365,
        "expires_at_formatted": "2026-05-28"
    }
}
```

### 3.3 Test Migration API

```bash
curl -X POST -F "file=@/path/to/workbook.twb" http://localhost:8000/api/migrate/
```

Expected response:
```json
{
    "success": true,
    "message": "Migration completed successfully",
    "output_dir": "output",
    "license_status": {
        "is_active": true,
        "expires_at": "2026-05-28T20:42:05.123456+00:00",
        "max_migrations": 100,
        "migrations_used": 2,
        "migrations_remaining": 98,
        "status_message": "License is active",
        "days_remaining": 365,
        "expires_at_formatted": "2026-05-28"
    }
}
```

## 4. Admin Interface (Optional)

You can create a Django admin interface for managing licenses:

```python
# licensing/admin.py
from django.contrib import admin
from .models import License

@admin.register(License)
class LicenseAdmin(admin.ModelAdmin):
    list_display = ('license_key', 'client_name', 'license_type', 'migrations_used', 
                   'max_migrations', 'migrations_remaining', 'expires_at', 'is_active')
    search_fields = ('license_key', 'client_name')
    list_filter = ('license_type', 'is_active')
    readonly_fields = ('migrations_remaining', 'is_active', 'status_message')
```

## 5. Troubleshooting

### 5.1 Database Connection Issues

If you encounter database connection issues:

1. Verify that PostgreSQL is running
2. Check that the connection parameters in `.env` are correct
3. Ensure the `app_user` exists and has the necessary permissions
4. Check PostgreSQL logs for connection errors

### 5.2 License Validation Issues

If license validation fails:

1. Check if the license record exists in the database
2. Verify that the license has not expired
3. Check if the migration limit has been reached
4. Ensure the stored functions are working correctly

## 6. Security Considerations

1. **API Security**: Protect the license management endpoints with authentication and authorization
2. **Database Security**: Store database credentials securely and use environment variables
3. **Error Handling**: Avoid exposing sensitive information in error messages
4. **Input Validation**: Validate all input parameters to prevent SQL injection

## 7. Deployment Considerations

1. **Environment Variables**: Use environment variables for all configuration in production
2. **Database Backups**: Regularly backup the license database
3. **Monitoring**: Set up monitoring for license usage and expiration
4. **Logging**: Configure appropriate logging for license validation and errors

## 8. Conclusion

This integration guide provides a comprehensive approach to integrating the BIMigrator licensing system with a Django backend. By following these instructions, you can implement secure license validation and tracking for the BIMigrator application.
