#!/usr/bin/env python3
"""
WhatsApp Authentication Helper for W3BHub WhatsApp Automation System

This script helps with WhatsApp authentication by providing clear instructions
and checking the authentication status.
"""

import requests
import json
import base64
import os

def check_auth_status():
    """Check WhatsApp Web authentication status"""
    print("🔍 Checking WhatsApp authentication status...")
    
    try:
        response = requests.get("http://localhost:8000/check-auth", timeout=10)
        if response.status_code == 200:
            auth_data = response.json()
            is_authenticated = auth_data.get("authenticated", False)
            message = auth_data.get("message", "No message")
            
            print(f"   Authenticated: {'✅ Yes' if is_authenticated else '❌ No'}")
            print(f"   Status: {message}")
            
            return is_authenticated, message
        else:
            print(f"❌ Failed to check auth status: {response.status_code}")
            print(f"   Response: {response.text}")
            return False, "Failed to check auth status"
    except Exception as e:
        print(f"❌ Error checking auth status: {e}")
        return False, str(e)

def start_driver():
    """Start the Chrome driver for WhatsApp Web"""
    print("🚀 Starting Chrome driver...")
    
    try:
        response = requests.post("http://localhost:8000/start", timeout=30)
        if response.status_code == 200:
            start_data = response.json()
            status = start_data.get("status", "unknown")
            message = start_data.get("message", "No message")
            
            print(f"   Status: {status}")
            print(f"   Message: {message}")
            
            if "qr_code_file" in start_data:
                qr_file = start_data["qr_code_file"]
                print(f"   QR Code File: {qr_file}")
                print("   💡 Copy this file from the container to scan with your phone")
                print("   💡 Command: docker cp whatsapp-worker:/app/whatsapp_qr_code.png .")
            
            return True, start_data
        else:
            print(f"❌ Failed to start driver: {response.status_code}")
            print(f"   Response: {response.text}")
            return False, "Failed to start driver"
    except Exception as e:
        print(f"❌ Error starting driver: {e}")
        return False, str(e)

def get_qr_code():
    """Get the QR code for WhatsApp Web authentication"""
    print("📱 Getting QR code for authentication...")
    
    try:
        response = requests.get("http://localhost:8000/get-qr", timeout=30)
        if response.status_code == 200:
            qr_data = response.json()
            status = qr_data.get("status", "unknown")
            message = qr_data.get("message", "No message")
            
            print(f"   Status: {status}")
            print(f"   Message: {message}")
            
            if "qr_code" in qr_data:
                # Save QR code to file
                qr_base64 = qr_data["qr_code"]
                qr_binary = base64.b64decode(qr_base64)
                
                with open("whatsapp_qr_code_latest.png", "wb") as f:
                    f.write(qr_binary)
                
                print("   ✅ QR code saved as 'whatsapp_qr_code_latest.png'")
                print("   💡 Scan this QR code with your WhatsApp mobile app to authenticate")
                
                return True, "QR code saved"
            else:
                return False, "No QR code in response"
        else:
            print(f"❌ Failed to get QR code: {response.status_code}")
            print(f"   Response: {response.text}")
            return False, "Failed to get QR code"
    except Exception as e:
        print(f"❌ Error getting QR code: {e}")
        return False, str(e)

def main():
    """Main function"""
    print("🔐 WhatsApp Authentication Helper for W3BHub")
    print("=" * 50)
    
    # Check current authentication status
    is_authenticated, status_message = check_auth_status()
    
    if is_authenticated:
        print("\n🎉 WhatsApp is already authenticated!")
        print("   You can now send messages through the system.")
        return 0
    
    print("\n🔄 WhatsApp is not authenticated. Let's fix that!")
    
    # Try to get a fresh QR code
    print("\n1. Getting fresh QR code...")
    success, message = get_qr_code()
    
    if not success:
        print("\n2. Trying to start driver and get QR code...")
        success, start_data = start_driver()
        
        if success and "qr_code_file" in start_data:
            # Try to copy the QR code file
            try:
                os.system("docker cp whatsapp-worker:/app/whatsapp_qr_code.png whatsapp_qr_code_docker.png")
                print("   ✅ QR code copied from container as 'whatsapp_qr_code_docker.png'")
            except Exception as e:
                print(f"   ❌ Failed to copy QR code from container: {e}")
    
    print("\n📋 Next steps:")
    print("   1. Scan the QR code with your WhatsApp mobile app")
    print("   2. Wait for authentication to complete (30-60 seconds)")
    print("   3. Run this script again to verify authentication")
    
    print("\n💡 Tips:")
    print("   - Make sure your phone has internet connection")
    print("   - Make sure WhatsApp is installed and logged in on your phone")
    print("   - The QR code expires after a few minutes - run this script again if needed")
    
    return 0

if __name__ == "__main__":
    main()