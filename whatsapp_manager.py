#!/usr/bin/env python3
"""
W3BHub WhatsApp Automation System Manager

Single script to manage all operations:
- Test Telegram integration
- Read CSV files from Telegram
- Check channel information
- Simulate CSV uploads
- Import workflows to n8n
- Check system health
"""

import os
import requests
import json
import time
import random
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration from environment variables
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHANNEL_ID = os.environ.get("TELEGRAM_CHANNEL_ID")
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
ADMIN_TELEGRAM_ID = os.environ.get("ADMIN_TELEGRAM_ID")

class WhatsAppManager:
    def __init__(self):
        self.telegram_bot_token = TELEGRAM_BOT_TOKEN
        self.telegram_channel_id = TELEGRAM_CHANNEL_ID
        self.supabase_url = SUPABASE_URL
        self.supabase_key = SUPABASE_KEY
        self.admin_telegram_id = ADMIN_TELEGRAM_ID

    # TELEGRAM INTEGRATION FUNCTIONS
    def test_telegram_bot(self):
        """Test if Telegram bot is properly configured"""
        if not self.telegram_bot_token:
            print("❌ TELEGRAM_BOT_TOKEN not set")
            return False
        
        if not self.telegram_channel_id:
            print("❌ TELEGRAM_CHANNEL_ID not set")
            return False
        
        try:
            # Test bot authentication
            url = f"https://api.telegram.org/bot{self.telegram_bot_token}/getMe"
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
            url = f"https://api.telegram.org/bot{self.telegram_bot_token}/getChat"
            params = {"chat_id": self.telegram_channel_id}
            response = requests.get(url, params=params)
            
            if response.status_code == 200:
                chat_info = response.json()
                if chat_info.get("ok"):
                    print(f"✅ Channel access confirmed: {chat_info['result']['title']}")
                    print(f"✅ Channel type: {chat_info['result']['type']}")
                else:
                    print("❌ Channel access failed")
                    print(f"❌ Error: {chat_info}")
                    return False
            else:
                print(f"❌ Channel access failed with status {response.status_code}")
                print(f"❌ Response: {response.text}")
                return False
            
            print("✅ All Telegram tests passed!")
            return True
            
        except Exception as e:
            print(f"❌ Error testing Telegram integration: {e}")
            return False

    def check_channel_info(self):
        """Get chat/channel information"""
        if not self.telegram_bot_token or not self.telegram_channel_id:
            print("❌ TELEGRAM_BOT_TOKEN or TELEGRAM_CHANNEL_ID not set")
            return None
        
        try:
            # Get chat info
            url = f"https://api.telegram.org/bot{self.telegram_bot_token}/getChat"
            params = {"chat_id": self.telegram_channel_id}
            response = requests.get(url, params=params)
            
            if response.status_code == 200:
                chat_info = response.json()
                if chat_info.get("ok"):
                    print("📱 Chat Information:")
                    print(f"  Title: {chat_info['result'].get('title', 'N/A')}")
                    print(f"  Type: {chat_info['result'].get('type', 'N/A')}")
                    print(f"  ID: {chat_info['result'].get('id', 'N/A')}")
                    if 'username' in chat_info['result']:
                        print(f"  Username: @{chat_info['result']['username']}")
                else:
                    print(f"❌ Chat info failed: {chat_info}")
                    return None
            else:
                print(f"❌ Chat info failed with status {response.status_code}")
                print(f"Response: {response.text}")
                return None
            
            # Get bot's membership info
            me_url = f"https://api.telegram.org/bot{self.telegram_bot_token}/getMe"
            me_response = requests.get(me_url)
            
            if me_response.status_code == 200:
                me_info = me_response.json()
                if me_info.get("ok"):
                    bot_user_id = me_info['result']['id']
                    
                    url = f"https://api.telegram.org/bot{self.telegram_bot_token}/getChatMember"
                    params = {
                        "chat_id": self.telegram_channel_id,
                        "user_id": bot_user_id
                    }
                    response = requests.get(url, params=params)
                    
                    if response.status_code == 200:
                        member_info = response.json()
                        if member_info.get("ok"):
                            print("\n🤖 Bot Membership:")
                            print(f"  Status: {member_info['result'].get('status', 'N/A')}")
                            print(f"  User: {member_info['result'].get('user', {}).get('username', 'N/A')}")
                            print(f"  Can Read Messages: {member_info['result'].get('can_read_messages', 'N/A')}")
                            print(f"  Can Post Messages: {member_info['result'].get('can_post_messages', 'N/A')}")
                        else:
                            print(f"❌ Member info failed: {member_info}")
                    else:
                        print(f"❌ Member info failed with status {response.status_code}")
                        print(f"Response: {response.text}")
                else:
                    print(f"❌ Bot info failed: {me_info}")
            else:
                print(f"❌ Bot info failed with status {me_response.status_code}")
            
            return True
            
        except Exception as e:
            print(f"❌ Error checking channel info: {e}")
            return False

    def read_todays_csv(self):
        """Read today's CSV file from Telegram channel"""
        if not self.telegram_bot_token or not self.telegram_channel_id:
            print("❌ TELEGRAM_BOT_TOKEN or TELEGRAM_CHANNEL_ID not set")
            return False
        
        try:
            # Get bot info
            url = f"https://api.telegram.org/bot{self.telegram_bot_token}/getMe"
            response = requests.get(url)
            
            if response.status_code == 200:
                bot_info = response.json()
                if bot_info.get("ok"):
                    print(f"✅ Bot connected: @{bot_info['result']['username']} ({bot_info['result']['first_name']})")
                else:
                    print("❌ Bot authentication failed")
                    return False
            else:
                print(f"❌ Bot authentication failed with status {response.status_code}")
                return False
            
            # Get recent messages
            print("📥 Getting recent messages from channel...")
            url = f"https://api.telegram.org/bot{self.telegram_bot_token}/getUpdates"
            params = {
                "offset": -1,  # Get latest updates
                "limit": 20,   # Get last 20 messages
                "timeout": 30
            }
            
            response = requests.get(url, params=params)
            
            if response.status_code == 200:
                updates = response.json()
                if updates.get("ok"):
                    messages = updates.get("result", [])
                else:
                    print("❌ Failed to get updates")
                    return False
            else:
                print(f"❌ Failed to get updates with status {response.status_code}")
                return False
            
            if not messages:
                print("⚠️  No messages found in the channel")
                return False
            
            print(f"📬 Found {len(messages)} recent messages")
            
            # Find today's CSV files
            today = datetime.now().strftime("%Y-%m-%d")
            print(f"🔍 Looking for CSV files from today ({today})")
            
            csv_files = []
            
            for update in messages:
                if "message" in update and "document" in update["message"]:
                    message = update["message"]
                    document = message["document"]
                    
                    # Check if it's a CSV file
                    if document.get("file_name", "").endswith(".csv"):
                        # Get message date
                        message_date = datetime.fromtimestamp(message["date"]).strftime("%Y-%m-%d")
                        
                        print(f"📄 Found CSV file: {document['file_name']} (sent on {message_date})")
                        
                        # Check if it's from today
                        if message_date == today:
                            csv_files.append({
                                "file_id": document["file_id"],
                                "file_name": document["file_name"],
                                "file_size": document.get("file_size", 0),
                                "date": message_date,
                                "message_id": message["message_id"]
                            })
                            print(f"✅ Today's CSV file found: {document['file_name']}")
            
            if not csv_files:
                print("⚠️  No CSV files found for today")
                return False
            
            print(f"\n🎉 Found {len(csv_files)} CSV file(s) for today!")
            
            # Download the files
            for csv_file in csv_files:
                print(f"\n⬇️  Downloading: {csv_file['file_name']}")
                try:
                    # Get file path
                    url = f"https://api.telegram.org/bot{self.telegram_bot_token}/getFile"
                    params = {"file_id": csv_file['file_id']}
                    response = requests.get(url, params=params)
                    
                    if response.status_code == 200:
                        file_info = response.json()
                        if file_info.get("ok"):
                            file_path = file_info["result"]["file_path"]
                            
                            # Download the file
                            download_url = f"https://api.telegram.org/file/bot{self.telegram_bot_token}/{file_path}"
                            file_response = requests.get(download_url)
                            
                            if file_response.status_code == 200:
                                # Save file
                                with open(csv_file['file_name'], "wb") as f:
                                    f.write(file_response.content)
                                print(f"✅ File downloaded successfully: {csv_file['file_name']}")
                                
                                # Show first few lines of the file
                                try:
                                    with open(csv_file['file_name'], 'r', encoding='utf-8') as f:
                                        lines = f.readlines()
                                        print(f"📄 First 5 lines of {csv_file['file_name']}:")
                                        for i, line in enumerate(lines[:5]):
                                            print(f"  {i+1}: {line.strip()}")
                                except Exception as e:
                                    print(f"❌ Error reading file: {e}")
                            else:
                                print(f"❌ Failed to download file: {file_response.status_code}")
                        else:
                            print("❌ Failed to get file info")
                    else:
                        print(f"❌ Failed to get file info: {response.status_code}")
                except Exception as e:
                    print(f"❌ Error downloading file: {e}")
            
            return True
            
        except Exception as e:
            print(f"❌ Error reading today's CSV: {e}")
            return False

    # SUPABASE FUNCTIONS
    def check_supabase_connection(self):
        """Check if Supabase table exists and is accessible"""
        if not self.supabase_url or not self.supabase_key:
            print("❌ SUPABASE_URL or SUPABASE_KEY not set")
            return False
        
        try:
            url = f"{self.supabase_url}/rest/v1/sent_numbers?limit=1"
            headers = {
                "apikey": self.supabase_key,
                "Authorization": f"Bearer {self.supabase_key}"
            }
            response = requests.get(url, headers=headers)
            
            if response.status_code == 200:
                print("✅ Supabase table is accessible")
                data = response.json()
                print(f"   Found {len(data)} existing records")
                return True
            else:
                print(f"❌ Supabase table access failed with status {response.status_code}")
                print(f"Response: {response.text}")
                return False
        except Exception as e:
            print(f"❌ Error accessing Supabase: {e}")
            return False

    def create_sample_csv(self):
        """Create a sample CSV file for testing"""
        csv_content = """phone,business_name,email
919876543210,ABC Shop,contact@abcshop.com
919876543211,XYZ Store,info@xyzstore.com
919876543212,123 Services,services@123.com
919876543213,Tech Solutions,tech@solutions.com
919876543214,Fashion Hub,fashion@hub.com"""
        
        with open("sample_leads.csv", "w", newline="", encoding="utf-8") as f:
            f.write(csv_content)
        
        print("✅ Sample CSV file created: sample_leads.csv")
        return "sample_leads.csv"

    def insert_test_data(self):
        """Insert test data into Supabase"""
        if not self.supabase_url or not self.supabase_key:
            print("❌ Supabase credentials not configured")
            return False
        
        test_numbers = [
            {
                "phone": "919876543210",
                "business_name": "ABC Shop",
                "email": "contact@abcshop.com",
                "initial_sent_batch": "test_batch_" + datetime.now().strftime("%Y%m%d_%H%M%S")
            },
            {
                "phone": "919876543211",
                "business_name": "XYZ Store",
                "email": "info@xyzstore.com",
                "initial_sent_batch": "test_batch_" + datetime.now().strftime("%Y%m%d_%H%M%S")
            },
            {
                "phone": "919876543212",
                "business_name": "123 Services",
                "email": "services@123.com",
                "initial_sent_batch": "test_batch_" + datetime.now().strftime("%Y%m%d_%H%M%S")
            }
        ]
        
        success_count = 0
        for number_data in test_numbers:
            try:
                url = f"{self.supabase_url}/rest/v1/sent_numbers"
                headers = {
                    "apikey": self.supabase_key,
                    "Authorization": f"Bearer {self.supabase_key}",
                    "Content-Type": "application/json",
                    "Prefer": "resolution=merge-duplicates"
                }
                
                response = requests.post(url, headers=headers, json=number_data)
                if response.status_code in [200, 201]:
                    print(f"✅ Inserted test data for {number_data['business_name']}")
                    success_count += 1
                else:
                    print(f"❌ Failed to insert test data for {number_data['business_name']}: {response.status_code}")
                    print(f"Response: {response.text}")
            except Exception as e:
                print(f"❌ Error inserting test data for {number_data['business_name']}: {e}")
        
        return success_count == len(test_numbers)

    # N8N FUNCTIONS
    def wait_for_n8n(self):
        """Wait for n8n to be ready"""
        max_attempts = 30
        for attempt in range(max_attempts):
            try:
                response = requests.get('http://localhost:5678/healthz')
                if response.status_code == 200:
                    print("✅ n8n is ready!")
                    return True
            except requests.exceptions.RequestException:
                pass
            
            print(f"⏳ Waiting for n8n to start... (attempt {attempt + 1}/{max_attempts})")
            time.sleep(2)
        
        print("❌ n8n did not start in time")
        return False

    def import_workflow(self):
        """Import the WhatsApp campaign workflow"""
        workflow_path = Path("whatsapp_campaign.json")
        
        if not workflow_path.exists():
            print(f"❌ Workflow file not found: {workflow_path}")
            return False
        
        # Wait for n8n to be ready
        if not self.wait_for_n8n():
            return False
        
        # Read the workflow file
        with open(workflow_path, 'r') as f:
            workflow_data = json.load(f)
        
        # Import the workflow
        url = 'http://localhost:5678/workflows'
        headers = {
            'accept': 'application/json',
            'Content-Type': 'application/json'
        }
        
        try:
            response = requests.post(url, headers=headers, json=workflow_data)
            if response.status_code == 200:
                print("✅ Workflow imported successfully!")
                return True
            else:
                print(f"❌ Failed to import workflow: {response.status_code} - {response.text}")
                return False
        except requests.exceptions.RequestException as e:
            print(f"❌ Error importing workflow: {e}")
            return False

    # SYSTEM HEALTH FUNCTIONS
    def check_system_health(self):
        """Check health of all system components"""
        print("🏥 Checking system health...")
        
        # Check WhatsApp worker
        try:
            response = requests.get('http://localhost:8000/health')
            if response.status_code == 200:
                print("✅ WhatsApp Worker: Healthy")
            else:
                print("❌ WhatsApp Worker: Unhealthy")
        except Exception as e:
            print(f"❌ WhatsApp Worker: Cannot connect - {e}")
        
        # Check n8n
        try:
            response = requests.get('http://localhost:5678/healthz')
            if response.status_code == 200:
                print("✅ n8n: Healthy")
            else:
                print("❌ n8n: Unhealthy")
        except Exception as e:
            print(f"❌ n8n: Cannot connect - {e}")

    # MAIN OPERATIONS
    def test_full_integration(self):
        """Test the complete integration"""
        print("🧪 Testing full system integration...")
        
        # Test Telegram
        print("\n1. Testing Telegram integration:")
        self.test_telegram_bot()
        
        # Check channel
        print("\n2. Checking channel information:")
        self.check_channel_info()
        
        # Check Supabase
        print("\n3. Checking Supabase connection:")
        self.check_supabase_connection()
        
        # Check system health
        print("\n4. Checking system health:")
        self.check_system_health()
        
        print("\n🎉 Integration test completed!")

    def simulate_daily_workflow(self):
        """Simulate the daily workflow"""
        print("🔄 Simulating daily workflow...")
        
        # Check system health
        self.check_system_health()
        
        # Create sample CSV
        print("\n📄 Creating sample CSV file:")
        self.create_sample_csv()
        
        # Show instructions
        print("\n📝 To complete the simulation:")
        print("1. Upload sample_leads.csv to your Telegram channel")
        print("2. Wait up to 10 minutes for n8n to process it")
        print("3. Check Supabase for new records")

    def send_test_message(self, phone, business_name):
        """Send a test message to a phone number"""
        try:
            # Prepare message
            message = random.choice([
                f"Hi {business_name}, this is W3BHub — we build clean, fast websites and WhatsApp automations for local businesses. If you want, we can make a free sample homepage for your business. View → https://w3bhub.co.in",
                f"Hello {business_name}, W3BHub here — want a quick free sample of a website for your shop? We create websites that bring more customers. See our work: https://w3bhub.co.in"
            ])
            
            # Send message via WhatsApp worker API
            url = "http://localhost:8000/send"
            payload = {
                "phone": phone,
                "message": message,
                "business_name": business_name
            }
            
            response = requests.post(url, json=payload, timeout=60)
            if response.status_code == 200:
                print(f"✅ Message sent successfully to {business_name} ({phone})")
                return True
            else:
                print(f"❌ Failed to send message: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Error sending test message: {e}")
            return False

    def start_messaging_test(self):
        """Start messaging test for 1 hour"""
        print("🚀 Starting 1-hour messaging test...")
        
        # First insert test data into Supabase
        print("📥 Inserting test data into Supabase...")
        if not self.insert_test_data():
            print("❌ Failed to insert test data")
            return
        
        # Send test messages to sample numbers
        test_numbers = [
            ("919876543210", "ABC Shop"),
            ("919876543211", "XYZ Store"),
            ("919876543212", "123 Services")
        ]
        
        for phone, name in test_numbers:
            print(f"\n📱 Sending test message to {name} ({phone})...")
            success = self.send_test_message(phone, name)
            if success:
                print(f"✅ Test message sent to {name}")
            else:
                print(f"❌ Failed to send test message to {name}")
            
            # Wait a bit between messages
            time.sleep(5)

    def get_whatsapp_qr(self):
        """Get WhatsApp QR code for authentication"""
        print("📱 Getting WhatsApp QR code for authentication...")
        print("\n📝 Instructions:")
        print("1. Run this command in a separate terminal:")
        print("   docker exec -it whatsapp-worker python -c \"from worker import init_webdriver; driver = init_webdriver(); driver.get('https://web.whatsapp.com'); input('Press Enter after scanning QR code...'); driver.quit()\"")
        print("\n2. This will open WhatsApp Web in the container")
        print("3. Scan the QR code that appears with your phone")
        print("4. Press Enter after scanning to continue")
        print("\n⚠️  Note: You may need to run this command multiple times if the first attempt fails")

    def verify_whatsapp_session(self):
        """Verify WhatsApp session is active"""
        try:
            # This would normally check if WhatsApp Web is authenticated
            # For now, we'll just check if the worker is responsive
            response = requests.get("http://localhost:8000/health", timeout=10)
            if response.status_code == 200:
                print("✅ WhatsApp worker is responsive")
                return True
            else:
                print("❌ WhatsApp worker is not responsive")
                return False
        except Exception as e:
            print(f"❌ Error checking WhatsApp worker: {e}")
            return False

def main():
    """Main function"""
    manager = WhatsAppManager()
    
    # If no arguments provided, show help
    import sys
    if len(sys.argv) < 2:
        print("W3BHub WhatsApp Automation System Manager")
        print("Usage: python whatsapp_manager.py [command]")
        print("\nAvailable commands:")
        print("  test-telegram     - Test Telegram integration")
        print("  check-channel     - Check Telegram channel information")
        print("  read-csv          - Read today's CSV files from Telegram")
        print("  test-supabase     - Test Supabase connection")
        print("  create-sample     - Create sample CSV file")
        print("  import-workflow   - Import n8n workflow")
        print("  check-health      - Check system health")
        print("  test-integration  - Test full system integration")
        print("  simulate-daily    - Simulate daily workflow")
        print("  send-test         - Send test messages (1-hour test)")
        print("  get-qr           - Get WhatsApp QR code for authentication")
        print("  verify-session   - Verify WhatsApp session is active")
        return
    
    command = sys.argv[1]
    
    if command == "test-telegram":
        manager.test_telegram_bot()
    elif command == "check-channel":
        manager.check_channel_info()
    elif command == "read-csv":
        manager.read_todays_csv()
    elif command == "test-supabase":
        manager.check_supabase_connection()
    elif command == "create-sample":
        manager.create_sample_csv()
    elif command == "import-workflow":
        manager.import_workflow()
    elif command == "check-health":
        manager.check_system_health()
    elif command == "test-integration":
        manager.test_full_integration()
    elif command == "simulate-daily":
        manager.simulate_daily_workflow()
    elif command == "send-test":
        manager.start_messaging_test()
    elif command == "get-qr":
        manager.get_whatsapp_qr()
    elif command == "verify-session":
        manager.verify_whatsapp_session()
    else:
        print(f"Unknown command: {command}")
        print("Use without arguments to see available commands")

if __name__ == "__main__":
    main()