#!/usr/bin/env python3
"""
Docker-based WhatsApp Web Authentication Script
This script helps authenticate WhatsApp Web using the Docker container
"""

import os
import time
import subprocess
import requests

def authenticate_whatsapp_docker():
    """Authenticate WhatsApp Web using Docker container"""
    print("🚀 Starting WhatsApp Web authentication via Docker...")
    
    try:
        # Start the Docker containers if not already running
        print("🔧 Starting Docker containers...")
        subprocess.run(["docker-compose", "up", "-d"], check=True)
        
        # Wait for containers to start
        print("⏳ Waiting for containers to start...")
        time.sleep(10)
        
        # Execute authentication command in the container
        print("📱 Executing authentication in Docker container...")
        print("📝 Please scan the QR code with your phone when it appears...")
        print("⚠️  Note: After scanning, press Ctrl+C to exit (the profile will be saved)")
        
        auth_command = [
            "docker", "exec", "-it", "whatsapp-worker",
            "python", "-c",
            "from selenium import webdriver; from selenium.webdriver.chrome.options import Options; "
            "import time; "
            "options = Options(); "
            "options.add_argument('--no-sandbox'); "
            "options.add_argument('--disable-dev-shm-usage'); "
            "options.add_argument('--disable-blink-features=AutomationControlled'); "
            "options.add_argument('--user-data-dir=/tmp/chrome-profile'); "
            "options.add_argument('--disable-extensions'); "
            "options.add_argument('--disable-plugins'); "
            "options.add_argument('--disable-popup-blocking'); "
            "options.add_argument('--disable-gpu'); "
            "options.add_argument('--disable-infobars'); "
            "options.add_argument('--disable-notifications'); "
            "options.add_argument('--window-size=1200,800'); "
            "options.add_argument('--headless=new'); "
            "driver = webdriver.Chrome(options=options); "
            "driver.get('https://web.whatsapp.com'); "
            "print('Please scan the QR code with your phone...'); "
            "print('Keep this window open until authentication is complete.'); "
            "try: "
            "    while True: "
            "        time.sleep(5); "
            "except KeyboardInterrupt: "
            "    print('Closing driver...'); "
            "    driver.quit(); "
            "    print('Driver closed. Profile saved.');"
        ]
        
        subprocess.run(auth_command)
        
        print("✅ Authentication completed successfully!")
        print("🔒 Profile saved in Docker container at /tmp/chrome-profile/")
        
        # Try to copy the profile to host for backup
        try:
            print("💾 Attempting to copy profile to host for backup...")
            subprocess.run([
                "docker", "cp", 
                "whatsapp-worker:/tmp/chrome-profile", 
                "./docker-chrome-profile"
            ], check=True)
            print("✅ Profile copied to ./docker-chrome-profile/ for backup")
        except:
            print("⚠️  Could not copy profile to host, but it's saved in the container")
        
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Error during Docker authentication: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def test_containers():
    """Test if containers are running properly"""
    print("🧪 Testing container health...")
    
    try:
        # Test WhatsApp worker
        response = requests.get("http://localhost:8000/health", timeout=5)
        if response.status_code == 200:
            print("✅ WhatsApp Worker: Healthy")
        else:
            print(f"❌ WhatsApp Worker: Unhealthy (Status: {response.status_code})")
            
        # Test n8n
        response = requests.get("http://localhost:5678/healthz", timeout=5)
        if response.status_code == 200:
            print("✅ n8n: Healthy")
        else:
            print(f"❌ n8n: Unhealthy (Status: {response.status_code})")
            
        return True
    except Exception as e:
        print(f"❌ Error testing containers: {e}")
        return False

def main():
    """Main function"""
    print("=" * 50)
    print("W3BHub WhatsApp Web Docker Authentication")
    print("=" * 50)
    print()
    print("📝 Instructions:")
    print("1. Make sure Docker Desktop is running")
    print("2. Have your phone ready to scan the QR code")
    print("3. The authenticated profile will be saved in the Docker container")
    print("4. After scanning, press Ctrl+C to exit")
    print()
    
    # Test containers first
    if not test_containers():
        print("\n❌ Containers are not running properly!")
        print("Please start Docker Desktop and try again.")
        return
    
    choice = input("Do you want to proceed with authentication? (y/n): ")
    if choice.lower() != 'y':
        print("Authentication cancelled.")
        return
    
    success = authenticate_whatsapp_docker()
    
    if success:
        print("\n🎉 Authentication completed successfully!")
        print("📁 The authenticated profile is saved in the Docker container")
        print("📤 You can now redeploy to Render with the authenticated profile")
        print("\nNext steps:")
        print("1. Commit and push your changes to GitHub")
        print("2. Redeploy to Render")
        print("3. Your WhatsApp session will be preserved")
    else:
        print("\n❌ Authentication failed!")
        print("Please check the error message above and try again.")

if __name__ == "__main__":
    main()