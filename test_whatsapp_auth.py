#!/usr/bin/env python3
"""
Simple WhatsApp Authentication Test Script
"""

import requests
import time

def test_whatsapp_auth():
    """Test if WhatsApp is authenticated"""
    print("🔍 Testing WhatsApp authentication...")
    
    try:
        # Check health first
        print("   Checking worker health...")
        health_response = requests.get("http://localhost:8000/health", timeout=10)
        if health_response.status_code == 200:
            print("   ✅ Worker is healthy")
        else:
            print(f"   ❌ Worker health check failed: {health_response.status_code}")
            return False
        
        # Check authentication status
        print("   Checking authentication status...")
        auth_response = requests.get("http://localhost:8000/check-auth", timeout=10)
        if auth_response.status_code == 200:
            auth_data = auth_response.json()
            is_authenticated = auth_data.get("authenticated", False)
            message = auth_data.get("message", "No message")
            
            print(f"   Authenticated: {'✅ Yes' if is_authenticated else '❌ No'}")
            print(f"   Status: {message}")
            
            return is_authenticated
        else:
            print(f"   ❌ Auth check failed: {auth_response.status_code}")
            print(f"   Response: {auth_response.text}")
            return False
            
    except Exception as e:
        print(f"   ❌ Error testing authentication: {e}")
        return False

def main():
    """Main function"""
    print("🔐 WhatsApp Authentication Test")
    print("=" * 30)
    
    is_authenticated = test_whatsapp_auth()
    
    if is_authenticated:
        print("\n🎉 WhatsApp is authenticated and ready to send messages!")
    else:
        print("\n❌ WhatsApp is not authenticated.")
        print("   Please scan the QR code and try again.")

if __name__ == "__main__":
    main()