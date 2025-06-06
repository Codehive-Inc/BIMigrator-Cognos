#!/usr/bin/env python3
"""
Installation script for required packages
"""
import subprocess
import sys
import os

def install_package(package):
    """Install a package using pip"""
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        print(f"✅ Successfully installed {package}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install {package}: {e}")
        return False

def main():
    """Main installation function"""
    packages = [
        "requests>=2.32.3",
        "pydantic>=2.0.0", 
        "jinja2>=3.1.0",
        "python-dotenv>=1.0.0",
        "lxml>=4.9.0",
        "dataclasses-json>=0.5.7",
        "typing-extensions>=4.0.0",
        "click>=8.0.0"
    ]
    
    print("Installing required packages...")
    print(f"Using Python: {sys.executable}")
    
    failed_packages = []
    for package in packages:
        if not install_package(package):
            failed_packages.append(package)
    
    if failed_packages:
        print(f"\n❌ Failed to install: {', '.join(failed_packages)}")
        return 1
    else:
        print("\n✅ All packages installed successfully!")
        return 0

if __name__ == "__main__":
    sys.exit(main())
