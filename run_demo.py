#!/usr/bin/env python3
"""
Quick Demo Runner - Production Ready
Runs the comprehensive Cognos to Power BI migration demonstration
"""

import sys
import os
import subprocess
import logging

def main():
    """Run the comprehensive demo"""
    print("🚀 COGNOS TO POWER BI MIGRATION - QUICK DEMO")
    print("=" * 60)
    print("This will demonstrate the full-fledged migration capabilities:")
    print("✅ Complete Power BI project generation")
    print("✅ Multi-page reports with visual containers")
    print("✅ Advanced analytics and time intelligence")
    print("✅ Professional themes and resources")
    print()
    
    try:
        # Run the comprehensive demo
        result = subprocess.run([
            sys.executable, 
            "demo_complete_migration.py"
        ], check=True)
        
        print()
        print("🎉 Demo completed successfully!")
        print("📁 Check the 'output/comprehensive_sales_analytics' folder")
        print("   to see the generated Power BI project files.")
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Demo failed with error code: {e.returncode}")
        print("💡 Make sure you have:")
        print("   1. Installed requirements: pip install -r requirements.txt")
        print("   2. Configured .env file with your Cognos credentials")
        print("   3. Network access to your Cognos server")
        sys.exit(1)
    except FileNotFoundError:
        print("❌ Could not find demo_complete_migration.py")
        print("💡 Make sure you're running this from the project root directory")
        sys.exit(1)

if __name__ == "__main__":
    main()