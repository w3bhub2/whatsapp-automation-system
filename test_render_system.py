#!/usr/bin/env python3
"""
Simple test script for Render-deployed WhatsApp Automation System
"""

import os
import requests
import json
import time
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration from environment variables
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHANNEL_ID = os.environ.get("TELEGRAM_CHANNEL_ID")
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
ADMIN_TELEGRAM_ID = os.environ.get("ADMIN_TELEGRAM_ID")
WHATSAPP_WORKER_ENDPOINT = "https://whatsapp-worker-w53e.onrender.com"  # Your actual Render URL

def test_whatsapp_worker():
    """Test if WhatsApp worker is responding"""
    print("Testing WhatsApp Worker...")
    try:
        response = requests.get(f"{WHATSAPP_WORKER_ENDPOINT}/health", timeout=10)
        if response.status_code == 200:
            print("✅ WhatsApp Worker: Healthy")
            return True
        else:
            print(f"❌ WhatsApp Worker: Unhealthy (Status: {response.status_code})")
            return False
    except Exception as e:
        print(f"❌ WhatsApp Worker: Cannot connect - {e}")
        return False

def test_telegram_bot():
    """Test if Telegram bot is properly configured"""
    print("\nTesting Telegram Bot...")
    if not TELEGRAM_BOT_TOKEN:
        print("❌ TELEGRAM_BOT_TOKEN not set")
        return False
    
    if not TELEGRAM_CHANNEL_ID:
        print("❌ TELEGRAM_CHANNEL_ID not set")
        return False
    
    try:
        # Test bot authentication
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getMe"
        response = requests.get(url)
        
        if response.status_code == 200:
            bot_info = response.json()
            if bot_info.get("ok"):
                print(f"✅ Bot authenticated: {bot_info['result']['username']}")
            else:
                print("❌ Bot authentication failed")
                return False
        else:
            print(f"❌ Bot authentication failed with status {response.status_code}")
            return False
        
        # Test channel access
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getChat"
        params = {"chat_id": TELEGRAM_CHANNEL_ID}
        response = requests.get(url, params=params)
        
        if response.status_code == 200:
            chat_info = response.json()
            if chat_info.get("ok"):
                print(f"✅ Channel access confirmed: {chat_info['result']['title']}")
            else:
                print("❌ Channel access failed")
                return False
        else:
            print(f"❌ Channel access failed with status {response.status_code}")
            return False
        
        print("✅ All Telegram tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Error testing Telegram integration: {e}")
        return False

def check_supabase_connection():
    """Check if Supabase table exists and is accessible"""
    print("\nTesting Supabase Connection...")
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("❌ SUPABASE_URL or SUPABASE_KEY not set")
        return False
    
    try:
        url = f"{SUPABASE_URL}/rest/v1/sent_numbers?limit=1"
        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}"
        }
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            print("✅ Supabase table is accessible")
            data = response.json()
            print(f"   Found {len(data)} existing records")
            return True
        else:
            print(f"❌ Supabase table access failed with status {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error accessing Supabase: {e}")
        return False

def send_test_message():
    """Send a test message via WhatsApp worker"""
    print("\nSending Test Message...")
    try:
        # Prepare message
        message = "Hi ABC Shop, this is W3BHub — we build clean, fast websites and WhatsApp automations for local businesses. If you want, we can make a free sample homepage for your business. View → https://w3bhub.co.in"
        
        # Send message via WhatsApp worker API
        url = f"{WHATSAPP_WORKER_ENDPOINT}/send"
        payload = {
            "phone": "918123894565",  # Your WhatsApp marketing number
            "message": message,
            "business_name": "ABC Shop",
            "batch_id": "test_batch_" + datetime.now().strftime("%Y%m%d_%H%M%S")
        }
        
        response = requests.post(url, json=payload, timeout=60)
        if response.status_code == 200:
            print("✅ Test message sent successfully!")
            return True
        else:
            print(f"❌ Failed to send test message: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error sending test message: {e}")
        return False

def create_sample_csv():
    """Create a sample CSV file for testing"""
    print("\nCreating Sample CSV File...")
    csv_content = """phone,business_name,email
918123894565,W3BHub Test,w3bhub@example.com
919876543210,ABC Shop,contact@abcshop.com
919876543211,XYZ Store,info@xyzstore.com"""
    
    with open("sample_leads.csv", "w", newline="", encoding="utf-8") as f:
        f.write(csv_content)
    
    print("✅ Sample CSV file created: sample_leads.csv")
    return "sample_leads.csv"

def main():
    """Main function"""
    print("🚀 Testing Render-Deployed WhatsApp Automation System")
    print("=" * 50)
    
    # Test all components
    worker_ok = test_whatsapp_worker()
    telegram_ok = test_telegram_bot()
    supabase_ok = check_supabase_connection()
    
    if worker_ok and telegram_ok and supabase_ok:
        print("\n🎉 All system components are working!")
        
        # Create sample CSV
        create_sample_csv()
        
        print("\n📋 Next steps:")
        print("1. Upload sample_leads.csv to your Telegram channel")
        print("2. Wait 10-15 minutes for the system to process it")
        print("3. Check your Supabase dashboard for new records")
        print("4. Messages will be sent between 9 AM - 6 PM IST")
        
        # Ask if user wants to send a test message now
        choice = input("\nWould you like to send a test message now? (y/n): ")
        if choice.lower() == 'y':
            send_test_message()
    else:
        print("\n❌ Some system components are not working properly.")
        print("Please check the errors above and fix the configuration.")

if __name__ == "__main__":
    main()