#!/usr/bin/env python3
"""
Local WhatsApp Web Authentication Script
This script helps authenticate WhatsApp Web locally for use with Render deployment
"""

import os
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service

def authenticate_whatsapp():
    """Authenticate WhatsApp Web locally"""
    print("🚀 Starting WhatsApp Web authentication...")
    
    # Create Chrome options for local authentication
    chrome_options = Options()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--user-data-dir=./local-chrome-profile")  # Local profile
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-plugins")
    chrome_options.add_argument("--disable-popup-blocking")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-infobars")
    chrome_options.add_argument("--disable-notifications")
    chrome_options.add_argument("--window-size=1200,800")
    
    try:
        # Initialize Chrome driver with webdriver-manager
        print("🔧 Initializing Chrome driver with webdriver-manager...")
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        # Navigate to WhatsApp Web
        print("🌐 Opening WhatsApp Web...")
        driver.get("https://web.whatsapp.com")
        
        # Wait for QR code to appear
        print("📱 Please scan the QR code with your phone...")
        print("⏳ Waiting for authentication (scan QR code on your phone)...")
        
        # Wait for authentication (this will hang until you scan the QR code)
        start_time = time.time()
        while time.time() - start_time < 300:  # Wait up to 5 minutes
            try:
                # Check if we're logged in by looking for the chat list
                driver.find_element("xpath", "//div[@role='row']")
                print("✅ Authentication successful!")
                print("🔒 Profile saved to ./local-chrome-profile/")
                break
            except:
                # Not logged in yet, continue waiting
                time.sleep(2)
                print(".", end="", flush=True)
        
        # Keep the session alive for a bit
        print("\n💤 Keeping session alive for 10 seconds...")
        time.sleep(10)
        
        # Quit the driver
        driver.quit()
        print("👋 Chrome driver closed.")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during authentication: {e}")
        return False

def main():
    """Main function"""
    print("=" * 50)
    print("W3BHub WhatsApp Web Local Authentication")
    print("=" * 50)
    print()
    print("📝 Instructions:")
    print("1. Make sure Chrome is installed")
    print("2. Ensure no other Chrome instances are running")
    print("3. Have your phone ready to scan the QR code")
    print()
    
    input("Press Enter to start authentication...")
    
    success = authenticate_whatsapp()
    
    if success:
        print("\n🎉 Authentication completed successfully!")
        print("📁 The authenticated profile is saved in ./local-chrome-profile/")
        print("📤 You can now copy this profile to your Render deployment")
        print("\nNext steps:")
        print("1. Commit and push your changes to GitHub")
        print("2. Redeploy to Render")
        print("3. Your WhatsApp session will be preserved")
    else:
        print("\n❌ Authentication failed!")
        print("Please check the error message above and try again.")

if __name__ == "__main__":
    main()