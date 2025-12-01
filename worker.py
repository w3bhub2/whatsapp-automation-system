import os
import time
import json
import random
import logging
from datetime import datetime, timedelta
import re
from flask import Flask, request, jsonify
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import undetected_chromedriver as uc
import requests
from threading import Thread, Lock
import urllib.parse

app = Flask(__name__)

# Configuration
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
ADMIN_TELEGRAM_ID = os.getenv('ADMIN_TELEGRAM_ID')
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

# Global state
STOP_SENDING = False
DAILY_SENT_COUNT = 0
START_DATE = datetime.now().date()
SEND_LOCK = Lock()
FAILURE_COUNT = 0
BLOCK_COUNT = 0

# Message templates
INITIAL_TEMPLATES = [
    "Hi {name}, this is W3BHub — we build clean, fast websites and WhatsApp automations for local businesses. If you want, we can make a free sample homepage for your business. View → https://w3bhub.co.in",
    "Hello {name}, W3BHub here — want a quick free sample of a website for your shop? We create websites that bring more customers. See our work: https://w3bhub.co.in",
    "Hey {name}, we help small businesses go online fast with simple websites + automation. Can I send a free sample homepage for your business? https://w3bhub.co.in",
    "Hi {name}, W3BHub — we build affordable websites & WhatsApp automations that get results. If you'd like, we can create a free sample homepage for your business. https://w3bhub.co.in",
    "🙂 Hi {name}, quick note from W3BHub — we design fast websites and setup automation to get customers. Want a free sample homepage? https://w3bhub.co.in"
]

FOLLOWUP_TEMPLATE = "Hi {name}, quick follow-up from W3BHub — we can build a free sample website for your business. If interested, reply and I'll send the sample. https://w3bhub.co.in"

OPTOUT_REPLY = "You will be removed from our outreach list. Sorry for the disturbance. — W3BHub"

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_daily_limit():
    """Calculate daily limit based on warm-up schedule"""
    days_since_start = (datetime.now().date() - START_DATE).days
    
    if days_since_start <= 3:
        return 40
    elif days_since_start <= 7:
        return 100
    elif days_since_start <= 10:
        return 200
    elif days_since_start <= 13:
        return 350
    else:
        return 600

def is_within_send_window():
    """Check if current time is within send window (TEMPORARILY DISABLED FOR TESTING)"""
    # For testing purposes, always return True
    # In production, uncomment the lines below:
    # Convert current UTC time to IST (UTC+5:30)
    # ist_time = datetime.utcnow() + timedelta(hours=5, minutes=30)
    # hour = ist_time.hour
    # return 9 <= hour < 18
    return True

def reset_daily_count_if_needed():
    """Reset daily count if it's a new day"""
    global DAILY_SENT_COUNT, FAILURE_COUNT, BLOCK_COUNT
    today = datetime.now().date()
    if today != START_DATE or datetime.now().hour == 0:
        DAILY_SENT_COUNT = 0
        FAILURE_COUNT = 0
        BLOCK_COUNT = 0

def send_telegram_message(chat_id, text):
    """Send message to Telegram chat"""
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        data = {
            "chat_id": chat_id,
            "text": text
        }
        response = requests.post(url, data=data)
        logger.info(f"Telegram message sent. Response: {response.status_code}")
    except Exception as e:
        logger.error(f"Failed to send Telegram message: {e}")

def update_supabase_record(phone, updates):
    """Update record in Supabase"""
    try:
        url = f"{SUPABASE_URL}/rest/v1/sent_numbers?phone=eq.{phone}"
        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json",
            "Prefer": "return=representation"
        }
        response = requests.patch(url, headers=headers, data=json.dumps(updates))
        logger.info(f"Supabase record updated for {phone}. Status: {response.status_code}")
        return response.status_code == 200
    except Exception as e:
        logger.error(f"Failed to update Supabase record for {phone}: {e}")
        return False

def get_supabase_record(phone):
    """Get record from Supabase"""
    try:
        url = f"{SUPABASE_URL}/rest/v1/sent_numbers?phone=eq.{phone}"
        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}"
        }
        response = requests.get(url, headers=headers)
        if response.status_code == 200 and response.json():
            return response.json()[0]
        return None
    except Exception as e:
        logger.error(f"Failed to get Supabase record for {phone}: {e}")
        return None

def init_webdriver():
    """Initialize Chrome WebDriver with persistent profile"""
    chrome_options = uc.ChromeOptions()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--user-data-dir=/chrome-profile")  # Persistent profile
    # Remove all experimental options that might cause issues
    # chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    # chrome_options.add_experimental_option('useAutomationExtension', False)
    
    try:
        driver = uc.Chrome(options=chrome_options)
        # Remove the javascript execution that might cause issues
        # driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        return driver
    except Exception as e:
        logger.error(f"Failed to initialize Chrome driver: {e}")
        return None

def send_whatsapp_message(driver, phone, message):
    """Send WhatsApp message using Selenium"""
    global DAILY_SENT_COUNT, FAILURE_COUNT, BLOCK_COUNT
    
    # Check safety triggers
    if BLOCK_COUNT >= 10:
        logger.warning("Block count exceeded, stopping for the day")
        send_telegram_message(ADMIN_TELEGRAM_ID, "🚨 Block count exceeded (10), stopping for the day")
        global STOP_SENDING
        STOP_SENDING = True
        return "blocked"
    
    if FAILURE_COUNT >= get_daily_limit() * 0.3:  # 30% failure rate
        logger.warning("Failure rate exceeded 30%, stopping for the day")
        send_telegram_message(ADMIN_TELEGRAM_ID, f"🚨 Failure rate exceeded 30% ({FAILURE_COUNT}/{get_daily_limit()}), stopping for the day")
        STOP_SENDING = True
        return "high_failure_rate"
    
    try:
        # Open WhatsApp Web with the phone number
        encoded_message = urllib.parse.quote(message)
        url = f"https://web.whatsapp.com/send?phone={phone}&text={encoded_message}"
        driver.get(url)
        
        # Wait for the message input field to be ready
        wait = WebDriverWait(driver, 30)
        message_box = wait.until(EC.presence_of_element_located((By.XPATH, '//div[@contenteditable="true"][@data-tab="10"]')))
        
        # Check for limit/suspicious activity alerts
        try:
            alert = driver.find_element(By.XPATH, '//div[contains(text(), "too many requests") or contains(text(), "suspicious") or contains(text(), "blocked")]')
            if alert:
                logger.warning("WhatsApp limit/suspicious activity detected")
                send_telegram_message(ADMIN_TELEGRAM_ID, f"🚨 WhatsApp limit/suspicious activity detected for {phone}")
                BLOCK_COUNT += 1
                return "limit_detected"
        except NoSuchElementException:
            pass
        
        # Send the message by pressing Enter
        message_box.send_keys("\n")
        
        # Wait for confirmation that message was sent
        wait.until(EC.presence_of_element_located((By.XPATH, '//span[@data-icon="msg-time" or @data-icon="check"]')))
        
        # Update daily count
        with SEND_LOCK:
            DAILY_SENT_COUNT += 1
            
        logger.info(f"Message sent successfully to {phone}")
        return "success"
        
    except TimeoutException:
        logger.error(f"Timeout while sending message to {phone}")
        FAILURE_COUNT += 1
        return "timeout"
    except Exception as e:
        logger.error(f"Error sending message to {phone}: {e}")
        FAILURE_COUNT += 1
        return "error"

def detect_replies(driver):
    """Detect replies in WhatsApp Web"""
    try:
        # Look for unread messages
        unread_chats = driver.find_elements(By.XPATH, '//div[@role="row"]//span[@aria-label="Unread message"]')
        
        for chat in unread_chats:
            # Click on the chat to open it
            chat.click()
            time.sleep(2)
            
            # Get the phone number from the chat header
            try:
                header = driver.find_element(By.XPATH, '//header//span[@dir="auto"]')
                contact_name = header.text
                
                # Extract phone number from the URL or page
                current_url = driver.current_url
                phone_match = re.search(r'/send\?phone=(\d+)', current_url)
                if phone_match:
                    phone = phone_match.group(1)
                    
                    # Check messages for opt-out keywords
                    messages = driver.find_elements(By.XPATH, '//div[@data-id]//span[@dir="ltr"]')
                    opt_out_detected = False
                    latest_message = ""
                    
                    for msg in messages:
                        text = msg.text.lower()
                        latest_message = text
                        if any(keyword in text for keyword in ['stop', 'unsubscribe', 'no', 'do not contact']):
                            opt_out_detected = True
                            break
                    
                    if opt_out_detected:
                        # Update as opted out
                        update_supabase_record(phone, {
                            "replied": True,
                            "last_replied_at": datetime.utcnow().isoformat(),
                            "send_error": "optout"
                        })
                        
                        # Send opt-out confirmation
                        send_whatsapp_message(driver, phone, OPTOUT_REPLY)
                        send_telegram_message(ADMIN_TELEGRAM_ID, f"✅ User {phone} ({contact_name}) opted out")
                    else:
                        # Update as replied
                        update_supabase_record(phone, {
                            "replied": True,
                            "last_replied_at": datetime.utcnow().isoformat()
                        })
                        send_telegram_message(ADMIN_TELEGRAM_ID, f"📩 New reply from {phone} ({contact_name}): {latest_message}")
                        
            except Exception as e:
                logger.error(f"Error processing chat: {e}")
                
    except Exception as e:
        logger.error(f"Error detecting replies: {e}")

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "healthy"}), 200

@app.route('/send', methods=['POST'])
def send_message():
    """Send WhatsApp message endpoint"""
    global DAILY_SENT_COUNT, FAILURE_COUNT, BLOCK_COUNT
    
    # Check if sending is stopped
    if STOP_SENDING:
        return jsonify({"status": "sending_stopped"}), 200
    
    # Check daily limit
    if DAILY_SENT_COUNT >= get_daily_limit():
        return jsonify({"status": "daily_limit_reached"}), 200
    
    # Check time window
    if not is_within_send_window():
        return jsonify({"status": "outside_send_window"}), 200
    
    # Parse request data
    data = request.get_json()
    phone = data.get('phone')
    name = data.get('name', '')
    batch_id = data.get('batch_id')
    job_type = data.get('job_type')  # 'initial' or 'followup'
    
    if not phone or not job_type:
        return jsonify({"error": "Missing required fields"}), 400
    
    # Fallback for name if empty
    if not name or name.strip() == '':
        name = 'there'  # Default fallback
    
    # Check Supabase record
    record = get_supabase_record(phone)
    if not record:
        return jsonify({"error": "Record not found"}), 404
    
    # Skip if already replied
    if record.get('replied'):
        return jsonify({"status": "already_replied"}), 200
    
    # Skip based on job type
    if job_type == "initial" and record.get('first_sent_at'):
        return jsonify({"status": "already_sent_initial"}), 200
    elif job_type == "followup" and record.get('followup_sent'):
        return jsonify({"status": "already_sent_followup"}), 200
    
    # Select appropriate message template
    if job_type == "initial":
        message = random.choice(INITIAL_TEMPLATES).format(name=name)
    elif job_type == "followup":
        message = FOLLOWUP_TEMPLATE.format(name=name)
    else:
        return jsonify({"error": "Invalid job_type"}), 400
    
    # Initialize WebDriver
    driver = init_webdriver()
    if not driver:
        return jsonify({"error": "Failed to initialize WebDriver"}), 500
    
    try:
        # Send message
        result = send_whatsapp_message(driver, phone, message)
        
        # Update Supabase based on result
        if result == "success":
            if job_type == "initial":
                update_supabase_record(phone, {
                    "first_sent_at": datetime.utcnow().isoformat(),
                    "last_sent_at": datetime.utcnow().isoformat()
                })
            elif job_type == "followup":
                update_supabase_record(phone, {
                    "followup_sent": True,
                    "last_sent_at": datetime.utcnow().isoformat()
                })
            return jsonify({"status": "sent"}), 200
        else:
            # Record error
            update_supabase_record(phone, {
                "send_error": result
            })
            return jsonify({"status": "failed", "reason": result}), 200
            
    finally:
        driver.quit()
        # Add delay between sends
        time.sleep(random.uniform(8, 12))

@app.route('/stop', methods=['POST'])
def stop_sending():
    """Emergency stop endpoint"""
    global STOP_SENDING
    STOP_SENDING = True
    send_telegram_message(ADMIN_TELEGRAM_ID, "🛑 WhatsApp sending stopped manually")
    return jsonify({"status": "stopped"}), 200

@app.route('/start', methods=['POST'])
def start_sending():
    """Resume sending endpoint"""
    global STOP_SENDING
    STOP_SENDING = False
    send_telegram_message(ADMIN_TELEGRAM_ID, "✅ WhatsApp sending resumed")
    return jsonify({"status": "started"}), 200

def init_supabase_tables():
    """Initialize Supabase tables if they don't exist"""
    try:
        # Create sent_numbers table
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS sent_numbers (
          phone TEXT PRIMARY KEY,
          business_name TEXT,
          email TEXT,
          first_sent_at TIMESTAMP,
          last_sent_at TIMESTAMP,
          last_replied_at TIMESTAMP,
          initial_sent_batch TEXT,
          followup_sent BOOLEAN DEFAULT FALSE,
          replied BOOLEAN DEFAULT FALSE,
          send_error TEXT
        );
        """
        
        url = f"{SUPABASE_URL}/rest/v1/query"
        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json",
            "Prefer": "return=minimal"
        }
        
        data = {
            "query": create_table_sql
        }
        
        response = requests.post(url, headers=headers, json=data)
        logger.info(f"Sent_numbers table creation response: {response.status_code}")
        
        # Create index
        create_index_sql = "CREATE INDEX IF NOT EXISTS idx_first_sent_at ON sent_numbers(first_sent_at);"
        data = {
            "query": create_index_sql
        }
        response = requests.post(url, headers=headers, json=data)
        logger.info(f"Index creation response: {response.status_code}")
        
        # Create batches table
        create_batches_sql = """
        CREATE TABLE IF NOT EXISTS batches (
          id TEXT PRIMARY KEY,
          created_at TIMESTAMP DEFAULT now(),
          csv_filename TEXT,
          processed_count INTEGER DEFAULT 0
        );
        """
        
        data = {
            "query": create_batches_sql
        }
        response = requests.post(url, headers=headers, json=data)
        logger.info(f"Batches table creation response: {response.status_code}")
        
    except Exception as e:
        logger.error(f"Failed to initialize Supabase tables: {e}")

def background_reply_detector():
    """Background thread to detect replies"""
    driver = init_webdriver()
    if not driver:
        logger.error("Failed to initialize WebDriver for reply detection")
        return
        
    try:
        # Open WhatsApp Web
        driver.get("https://web.whatsapp.com")
        
        # Wait for user to scan QR code
        WebDriverWait(driver, 120).until(
            EC.presence_of_element_located((By.XPATH, '//div[@role="row"]'))
        )
        
        # Continuously check for replies
        while True:
            if not STOP_SENDING:
                detect_replies(driver)
            time.sleep(30)  # Check every 30 seconds
            
    except Exception as e:
        logger.error(f"Error in reply detector: {e}")
    finally:
        driver.quit()

if __name__ == '__main__':
    # Initialize Supabase tables
    init_supabase_tables()
    
    # Start background reply detector thread
    reply_thread = Thread(target=background_reply_detector, daemon=True)
    reply_thread.start()
    
    # Start Flask app
    app.run(host='0.0.0.0', port=8000)