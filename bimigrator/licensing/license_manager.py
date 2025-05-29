"""License manager for the BIMigrator application."""

import logging
import os
from datetime import datetime
from typing import Dict, Any, Optional, Tuple

from bimigrator.licensing.db_connection import execute_query
from bimigrator.licensing.exceptions import (
    LicenseError, 
    LicenseExpiredError, 
    LicenseLimitError, 
    LicenseConnectionError,
    LicenseNotFoundError
)

# Configure logging
logger = logging.getLogger(__name__)


class LicenseManager:
    """Manager for license validation and tracking."""
    
    def __init__(self, license_id: Optional[int] = None):
        """Initialize the license manager.
        
        Args:
            license_id: ID of the license to use. If None, will use the ID from environment variable
                        BIMIGRATOR_LICENSE_ID or default to 1.
        """
        self.license_id = license_id or int(os.environ.get('BIMIGRATOR_LICENSE_ID', '1'))
        logger.debug(f"License manager initialized with license ID: {self.license_id}")
    
    def check_license(self) -> Dict[str, Any]:
        """Check the current license status without incrementing the migration count.
        
        Returns:
            Dictionary with license status information
            
        Raises:
            LicenseConnectionError: If connection to the database fails
            LicenseNotFoundError: If no license is found with the specified ID
        """
        try:
            # Call the get_license_status function in the database
            query = "SELECT * FROM get_license_status(%s);"
            result = execute_query(query, (self.license_id,), fetch_one=True)
            
            if not result:
                raise LicenseNotFoundError(f"No license found with ID: {self.license_id}")
            
            # Parse the result into a dictionary
            status = {
                'is_active': result[0],
                'expires_at': result[1],
                'max_migrations': result[2],
                'migrations_used': result[3],
                'migrations_remaining': result[4],
                'status_message': result[5]
            }
            
            logger.info(f"License status: {status['status_message']} "
                       f"(Remaining: {status['migrations_remaining']}, "
                       f"Expires: {status['expires_at']})")
            
            return status
        except Exception as e:
            if isinstance(e, LicenseError):
                raise
            logger.error(f"Failed to check license: {str(e)}")
            raise LicenseConnectionError(f"Failed to check license: {str(e)}")
    
    def validate_license(self) -> bool:
        """Validate the license and increment the migration count if valid.
        
        This method calls the increment_migration_count stored function in the database,
        which will check if the license is valid (not expired and within migration limits)
        and increment the migration count if it is.
        
        Returns:
            True if license is valid and migration count was incremented
            
        Raises:
            LicenseExpiredError: If the license has expired
            LicenseLimitError: If the migration limit has been reached
            LicenseConnectionError: If connection to the database fails
            LicenseNotFoundError: If no license is found with the specified ID
        """
        try:
            # First check the license status to get detailed information
            status = self.check_license()
            
            # If license is not active, raise appropriate exception
            if not status['is_active']:
                raise LicenseExpiredError(
                    "License has expired", 
                    expires_at=status['expires_at']
                )
            
            # If migration limit reached, raise exception
            if status['migrations_remaining'] <= 0:
                raise LicenseLimitError(
                    "Migration limit reached", 
                    used=status['migrations_used'], 
                    limit=status['max_migrations']
                )
            
            # Call the increment_migration_count function in the database
            query = "SELECT increment_migration_count(%s);"
            result = execute_query(query, (self.license_id,), fetch_one=True)
            
            if not result or not result[0]:
                # Get updated status to determine the reason for failure
                updated_status = self.check_license()
                
                if not updated_status['is_active']:
                    raise LicenseExpiredError(
                        "License has expired", 
                        expires_at=updated_status['expires_at']
                    )
                
                if updated_status['migrations_remaining'] <= 0:
                    raise LicenseLimitError(
                        "Migration limit reached", 
                        used=updated_status['migrations_used'], 
                        limit=updated_status['max_migrations']
                    )
                
                # If we get here, something else went wrong
                raise LicenseError("License validation failed for unknown reason")
            
            logger.info(f"License validated successfully. Migration count incremented.")
            return True
        except Exception as e:
            if isinstance(e, LicenseError):
                logger.warning(f"License validation failed: {str(e)}")
                raise
            logger.error(f"Failed to validate license: {str(e)}")
            raise LicenseConnectionError(f"Failed to validate license: {str(e)}")
    
    def get_license_info(self) -> Dict[str, Any]:
        """Get detailed license information.
        
        This is a convenience method that returns the same information as check_license()
        but with additional formatted fields for display purposes.
        
        Returns:
            Dictionary with license information
            
        Raises:
            LicenseConnectionError: If connection to the database fails
            LicenseNotFoundError: If no license is found with the specified ID
        """
        status = self.check_license()
        
        # Add formatted fields for display
        if status['expires_at']:
            days_remaining = (status['expires_at'].date() - datetime.now().date()).days
            status['days_remaining'] = max(0, days_remaining)
            status['expires_at_formatted'] = status['expires_at'].strftime('%Y-%m-%d')
        else:
            status['days_remaining'] = 0
            status['expires_at_formatted'] = 'N/A'
        
        return status
