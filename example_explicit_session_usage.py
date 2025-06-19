#!/usr/bin/env python3
"""
Example usage of explicit session-based migration functions

This demonstrates how to use the new functions that don't depend on .env files
"""

from cognos_migrator.module_migrator import (
    test_cognos_connection,
    migrate_module_with_explicit_session,
    post_process_module_with_explicit_session
)
from cognos_migrator.client import CognosAPIError


def example_usage():
    """Example of how to use the new explicit session functions"""
    
    # These values would typically come from your application
    cognos_url = "http://20.244.32.126:9300/api/v1"
    session_key = "YOUR_VALID_SESSION_KEY_HERE"
    module_id = "i5F34A7A52E2645C0AB03C34BA50941D7"
    output_path = "./output/my_module"
    
    try:
        # Step 1: Test connection first
        print("Testing connection...")
        if not test_cognos_connection(cognos_url, session_key):
            print("❌ Connection failed or session expired")
            return False
        print("✅ Connection successful")
        
        # Step 2: Migrate the module
        print("Starting module migration...")
        success = migrate_module_with_explicit_session(
            module_id=module_id,
            output_path=output_path,
            cognos_url=cognos_url,
            session_key=session_key,
            report_ids=["report1", "report2"],  # Optional
            cpf_file_path=None,  # Optional CPF file path
            auth_key="IBM-BA-Authorization"  # Optional, defaults to this value
        )
        
        if not success:
            print("❌ Module migration failed")
            return False
        print("✅ Module migration completed")
        
        # Step 3: Post-process the module
        print("Post-processing module...")
        post_success = post_process_module_with_explicit_session(
            module_id=module_id,
            output_path=output_path,
            cognos_url=cognos_url,
            session_key=session_key,
            successful_report_ids=["report1", "report2"],  # Optional
            auth_key="IBM-BA-Authorization"  # Optional
        )
        
        if not post_success:
            print("❌ Post-processing failed")
            return False
        print("✅ Post-processing completed")
        
        print(f"\n🎉 Migration completed successfully!")
        print(f"📁 Output saved to: {output_path}")
        return True
        
    except CognosAPIError as e:
        print(f"❌ Cognos API Error: {e}")
        print("💡 The session key may have expired. Please generate a new one.")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False


def integrate_with_web_application():
    """Example of how this could be integrated into a web application"""
    
    # This is how you might use these functions in a Flask/Django/FastAPI app
    def migration_endpoint(request_data):
        """
        Example web endpoint handler
        
        request_data would contain:
        {
            "cognos_url": "http://...",
            "session_key": "CAM ...",
            "module_id": "i5F...",
            "output_path": "/tmp/migration_123",
            "report_ids": ["report1", "report2"]
        }
        """
        
        try:
            # Validate session first
            if not test_cognos_connection(
                request_data["cognos_url"], 
                request_data["session_key"]
            ):
                return {
                    "success": False,
                    "error": "Invalid or expired session key"
                }
            
            # Perform migration
            success = migrate_module_with_explicit_session(
                module_id=request_data["module_id"],
                output_path=request_data["output_path"],
                cognos_url=request_data["cognos_url"],
                session_key=request_data["session_key"],
                report_ids=request_data.get("report_ids", [])
            )
            
            if success:
                # Post-process
                post_process_module_with_explicit_session(
                    module_id=request_data["module_id"],
                    output_path=request_data["output_path"],
                    cognos_url=request_data["cognos_url"],
                    session_key=request_data["session_key"],
                    successful_report_ids=request_data.get("report_ids", [])
                )
            
            return {
                "success": success,
                "output_path": request_data["output_path"] if success else None
            }
            
        except CognosAPIError:
            return {
                "success": False,
                "error": "Session expired during migration"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    # Example usage
    sample_request = {
        "cognos_url": "http://20.244.32.126:9300/api/v1",
        "session_key": "CAM_YOUR_SESSION_KEY_HERE",
        "module_id": "i5F34A7A52E2645C0AB03C34BA50941D7",
        "output_path": "/tmp/migration_123",
        "report_ids": ["report1", "report2"]
    }
    
    result = migration_endpoint(sample_request)
    print(f"Migration result: {result}")


if __name__ == "__main__":
    print("=== Explicit Session Migration Example ===")
    print("\nKey Benefits:")
    print("✅ No .env file dependencies")
    print("✅ Explicit session management")
    print("✅ Clear error handling for expired sessions")
    print("✅ Easy integration into web applications")
    print("✅ Complete control over authentication")
    
    print("\n" + "="*50)
    print("Example usage (update session_key to test):")
    example_usage()
    
    print("\n" + "="*50)
    print("Web application integration example:")
    integrate_with_web_application()