#!/usr/bin/env python3
"""
WhatsApp Web Automation Worker

Flask-based worker that handles WhatsApp Web automation using Selenium
"""

import os
import time
import json
import random
import urllib.parse
import logging
from datetime import datetime, timedelta
from threading import Thread, Lock
from dotenv import load_dotenv

# Import Selenium
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.chrome.service import Service

# Import Flask
from flask import Flask, request, jsonify

# Import requests for Supabase
import requests

# Load environment variables
load_dotenv()

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

# Global variables for WebDriver and reply detection
driver = None
driver_lock = Lock()  # Thread lock for driver access
REPLY_DETECTION_ACTIVE = False

# Message templates
INITIAL_TEMPLATES = [
    "Hi {name}, this is W3BHub — we build clean, fast websites and WhatsApp automations for local businesses. If you want, we can make a free sample homepage for your business. View → https://w3bhub.co.in",
    "Hello {name}, W3BHub here — want a quick free sample of a website for your shop? We create websites that bring more customers. See our work: https://w3bhub.co.in",
    "Hey {name}, we help small businesses go online fast with simple websites + automation. Can I send a free sample homepage for your business? https://w3bhub.co.in",
    "Hi {name}, W3BHub — we build affordable websites & WhatsApp automations that get results. If you'd like, we can create a free sample homepage for your business. https://w3bhub.co.in",
    "🙂 Hi {name}, quick note from W3BHub — we design fast websites and setup automation to get customers. Want a free sample homepage? https://w3bhub.co.in",
    "Greetings {name}! 👋 W3BHub here - we specialize in creating high-converting websites for local businesses like yours. Would you be interested in a complimentary homepage sample? Check it out: https://w3bhub.co.in",
    "Dear {name}, this is W3BHub calling - we've helped hundreds of businesses increase their online presence with our custom website solutions. Want to see what we can do for you? Free sample: https://w3bhub.co.in",
    "🌟 {name}, your business deserves a professional online presence! W3BHub offers tailored website solutions with free samples. Interested? Visit: https://w3bhub.co.in",
    "Quick question {name} - does your business have a website that converts visitors to customers? W3BHub can help with a free sample. Details: https://w3bhub.co.in",
    "🤝 Hi {name}! W3BHub here - we're experts in local business websites & WhatsApp marketing automation. Free homepage sample available at: https://w3bhub.co.in"
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
    """Check if current time is within send window (9 AM - 6 PM IST)"""
    # Convert current UTC time to IST (UTC+5:30)
    ist_time = datetime.utcnow() + timedelta(hours=5, minutes=30)
    hour = ist_time.hour
    return 9 <= hour < 18

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
    """Initialize Chrome WebDriver with enhanced anti-detection features"""
    chrome_options = Options()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--user-data-dir=/chrome-profile")  # Persistent profile
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-plugins")
    chrome_options.add_argument("--disable-images")
    chrome_options.add_argument("--disable-javascript")  # Enable JavaScript after loading
    chrome_options.add_argument("--disable-popup-blocking")
    chrome_options.add_argument("--disable-background-timer-throttling")
    chrome_options.add_argument("--disable-renderer-backgrounding")
    chrome_options.add_argument("--disable-backgrounding-occluded-windows")
    chrome_options.add_argument("--disable-features=VizDisplayCompositor")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-infobars")
    chrome_options.add_argument("--disable-notifications")
    chrome_options.add_argument("--disable-web-security")
    chrome_options.add_argument("--allow-running-insecure-content")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--start-maximized")
    
    # Additional options for Docker environment
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--disable-application-cache")
    chrome_options.add_argument("--disable-extensions-http-throttling")
    chrome_options.add_argument("--disable-features=TranslateUI")
    chrome_options.add_argument("--disable-ipc-flooding-protection")
    chrome_options.add_argument("--disable-background-networking")
    chrome_options.add_argument("--disable-default-apps")
    chrome_options.add_argument("--disable-breakpad")
    chrome_options.add_argument("--disable-component-update")
    chrome_options.add_argument("--disable-domain-reliability")
    chrome_options.add_argument("--disable-sync")
    chrome_options.add_argument("--metrics-recording-only")
    chrome_options.add_argument("--no-first-run")
    chrome_options.add_argument("--safebrowsing-disable-auto-update")
    chrome_options.add_argument("--disable-logging")
    chrome_options.add_argument("--disable-crash-reporter")
    chrome_options.add_argument("--single-process")
    chrome_options.add_argument("--disable-hang-monitor")
    chrome_options.add_argument("--disable-background-timer-throttling")
    chrome_options.add_argument("--disable-browser-side-navigation")
    chrome_options.add_argument("--disable-dev-tools")
    
    try:
        driver = webdriver.Chrome(options=chrome_options)
        # Remove automation indicators
        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": """
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
                
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5]
                });
                
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['en-US', 'en']
                });
                
                window.chrome = {
                    runtime: {}
                };
                
                Object.defineProperty(navigator, 'permissions', {
                    get: () => ({
                        query: Promise.resolve.bind(Promise)
                    })
                });
                
                // Hide webdriver property
                delete navigator.__proto__.webdriver;
            """
        })
        return driver
    except Exception as e:
        logger.error(f"Failed to initialize Chrome driver: {e}")
        return None

def get_driver():
    """Get or create a singleton WebDriver instance"""
    global driver, driver_lock
    
    with driver_lock:
        if driver is None:
            logger.info("Initializing new Chrome driver...")
            driver = init_webdriver()
            if driver is None:
                logger.error("Failed to initialize Chrome driver")
                return None
            logger.info("Chrome driver initialized successfully")
        else:
            # Check if driver is still alive
            try:
                driver.current_url  # This will throw an exception if driver is dead
                logger.debug("Using existing Chrome driver")
            except:
                logger.info("Reinitializing Chrome driver...")
                try:
                    driver.quit()
                except:
                    pass
                driver = init_webdriver()
                if driver is None:
                    logger.error("Failed to reinitialize Chrome driver")
                    return None
                logger.info("Chrome driver reinitialized successfully")
        
        return driver

def send_whatsapp_message(phone, message):
    """Send WhatsApp message using Selenium with human-like behavior"""
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
    
    # Get or create WebDriver instance
    driver = get_driver()
    if driver is None:
        logger.error("Failed to get WebDriver instance")
        FAILURE_COUNT += 1
        return "driver_error"
    
    try:
        # Enable JavaScript for this session
        driver.execute_cdp_cmd("Emulation.setScriptExecutionDisabled", {"value": False})
        
        # Open WhatsApp Web with the phone number
        encoded_message = urllib.parse.quote(message)
        url = f"https://web.whatsapp.com/send?phone={phone}&text={encoded_message}"
        driver.get(url)
        
        # Human-like waiting with random variations
        time.sleep(random.uniform(3, 6))
        
        # Wait for the message input field to be ready
        wait = WebDriverWait(driver, 30)
        message_box = wait.until(EC.presence_of_element_located((By.XPATH, '//div[@contenteditable="true"][@data-tab="10"]')))
        
        # Simulate human typing behavior
        time.sleep(random.uniform(1, 3))
        
        # Check for limit/suspicious activity alerts
        try:
            alert = driver.find_element(By.XPATH, '//div[contains(text(), "too many requests") or contains(text(), "suspicious") or contains(text(), "blocked") or contains(text(), "Wait a moment")]')
            if alert:
                logger.warning("WhatsApp limit/suspicious activity detected")
                send_telegram_message(ADMIN_TELEGRAM_ID, f"🚨 WhatsApp limit/suspicious activity detected for {phone}")
                BLOCK_COUNT += 1
                return "limit_detected"
        except NoSuchElementException:
            pass
        
        # Simulate typing with random delays
        for char in "\n":  # Just press enter to send pre-filled message
            time.sleep(random.uniform(0.1, 0.3))
            message_box.send_keys(char)
        
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

def detect_replies():
    """Detect replies in WhatsApp Web (runs in background thread)"""
    global driver, REPLY_DETECTION_ACTIVE
    logger.info("Starting reply detection loop...")
    
    while REPLY_DETECTION_ACTIVE:
        try:
            # Initialize driver if not already done
            if driver is None:
                logger.info("Initializing driver for reply detection...")
                driver = init_webdriver()
                if driver is None:
                    logger.error("Failed to initialize Chrome driver for reply detection")
                    time.sleep(60)  # Wait longer before retrying
                    continue
                    
                # Navigate to WhatsApp Web if not already there
                try:
                    if driver.current_url != "https://web.whatsapp.com":
                        driver.get("https://web.whatsapp.com")
                        time.sleep(5)  # Wait for page to load
                except:
                    # If we can't navigate, try to recover
                    try:
                        driver.get("https://web.whatsapp.com")
                        time.sleep(5)
                    except Exception as e:
                        logger.error(f"Failed to navigate to WhatsApp Web: {e}")
                        time.sleep(60)  # Wait longer before retrying
                        continue
            
            # Check for new messages
            unread_chats = driver.find_elements(By.XPATH, '//div[@role="row"]//span[@aria-label="Unread"]')
            for chat in unread_chats:
                try:
                    # Click on the chat to open it
                    parent_chat = chat.find_element(By.XPATH, './ancestor::div[@role="row"]')
                    parent_chat.click()
                    time.sleep(2)
                    
                    # Get chat name/phone
                    try:
                        chat_header = driver.find_element(By.XPATH, '//div[@id="main"]//header//div[@data-testid="conversation-info-header"]')
                        chat_name = chat_header.text.split('\n')[0]
                    except:
                        chat_name = "Unknown"
                    
                    # Extract messages
                    messages = driver.find_elements(By.XPATH, '//div[@data-testid="msg-container"]')
                    if messages:
                        last_message = messages[-1].text
                        logger.info(f"New reply from {chat_name}: {last_message}")
                        
                        # Store in Supabase
                        store_reply(chat_name, last_message)
                        
                        # Send notification to admin
                        send_telegram_message(ADMIN_TELEGRAM_ID, f"📩 New reply from {chat_name}: {last_message}")
                except Exception as e:
                    logger.error(f"Error processing chat: {e}")
                    continue
            
            # Wait before next check
            time.sleep(30)  # Check every 30 seconds
        except Exception as e:
            logger.error(f"Error in reply detection loop: {e}")
            time.sleep(30)  # Continue checking even if there's an error

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "healthy"}), 200

@app.route('/send', methods=['POST'])
def send_message():
    """Send a WhatsApp message"""
    global DAILY_SENT_COUNT, FAILURE_COUNT, BLOCK_COUNT, STOP_SENDING
    
    # Check if we should stop sending
    if STOP_SENDING:
        return jsonify({"error": "Sending stopped due to safety triggers"}), 429
    
    # Check if within send window
    if not is_within_send_window():
        return jsonify({"error": "Outside send window (9 AM - 6 PM IST)"}), 429
    
    # Check daily limit
    if DAILY_SENT_COUNT >= get_daily_limit():
        return jsonify({"error": f"Daily limit reached ({get_daily_limit()} messages)"}), 429
    
    try:
        data = request.get_json()
        phone = data.get('phone')
        message = data.get('message')
        batch_id = data.get('batch_id', 'manual')
        
        if not phone or not message:
            return jsonify({"error": "Phone and message are required"}), 400
        
        # Add random delay between messages
        delay = random.randint(8, 12)
        logger.info(f"Waiting {delay} seconds before sending message...")
        time.sleep(delay)
        
        # Send the message
        result = send_whatsapp_message(phone, message)
        
        if result == "success":
            # Record in Supabase
            record_sent_number(phone, data.get('business_name', ''), data.get('email', ''), batch_id)
            return jsonify({"status": "sent", "phone": phone}), 200
        else:
            return jsonify({"error": f"Failed to send message: {result}"}), 500
            
    except Exception as e:
        logger.error(f"Error in send_message endpoint: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/stop', methods=['POST'])
def stop_sending():
    """Emergency stop endpoint"""
    global STOP_SENDING
    STOP_SENDING = True
    send_telegram_message(ADMIN_TELEGRAM_ID, "🛑 WhatsApp sending stopped manually")
    return jsonify({"status": "stopped"}), 200

@app.route('/start', methods=['POST'])
def start_driver():
    """Start Chrome driver for WhatsApp Web"""
    global driver, REPLY_DETECTION_ACTIVE
    try:
        if driver is None:
            logger.info("Initializing Chrome driver...")
            driver = init_webdriver()
            if driver is None:
                logger.error("Failed to initialize Chrome driver")
                return jsonify({"status": "error", "message": "Failed to initialize Chrome driver"}), 500
            
            # Navigate to WhatsApp Web
            driver.get("https://web.whatsapp.com")
            logger.info("Chrome driver initialized and navigated to WhatsApp Web")
            
            # Start reply detection thread
            if not REPLY_DETECTION_ACTIVE:
                reply_thread = threading.Thread(target=detect_replies, daemon=True)
                reply_thread.start()
                REPLY_DETECTION_ACTIVE = True
                logger.info("Reply detection thread started")
            
            return jsonify({"status": "success", "message": "Chrome driver started"}), 200
        else:
            logger.info("Chrome driver already running")
            return jsonify({"status": "success", "message": "Chrome driver already running"}), 200
    except Exception as e:
        logger.error(f"Error starting Chrome driver: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

def record_sent_number(phone, business_name, email, batch_id):
    """Record a sent number in Supabase"""
    try:
        # Prepare the data
        data = {
            "phone": phone,
            "business_name": business_name,
            "email": email,
            "first_sent_at": datetime.utcnow().isoformat(),
            "last_sent_at": datetime.utcnow().isoformat(),
            "initial_sent_batch": batch_id
        }
        
        # Insert into Supabase (will automatically create table if it doesn't exist)
        url = f"{SUPABASE_URL}/rest/v1/sent_numbers"
        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json",
            "Prefer": "resolution=merge-duplicates"
        }
        
        response = requests.post(url, headers=headers, json=data)
        if response.status_code in [200, 201]:
            logger.info(f"Recorded sent number {phone} in Supabase")
            return True
        else:
            logger.error(f"Failed to record sent number {phone}: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        logger.error(f"Error recording sent number {phone}: {e}")
        return False

def init_supabase_tables():
    """Initialize Supabase tables if they don't exist"""
    try:
        # First check if tables already exist by trying to query them
        url = f"{SUPABASE_URL}/rest/v1/sent_numbers?limit=1"
        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}"
        }
        
        response = requests.get(url, headers=headers)
        
        # If we get a 404, tables don't exist and we need to create them
        # If we get a 200, tables exist and we're good
        if response.status_code == 404:
            logger.info("Tables don't exist yet, they will be created automatically when data is inserted")
        elif response.status_code == 200:
            logger.info("Tables already exist")
        else:
            logger.info(f"Supabase check response: {response.status_code}")
            
    except Exception as e:
        logger.error(f"Failed to check Supabase tables: {e}")

if __name__ == '__main__':
    # Initialize Supabase tables
    init_supabase_tables()
    
    # Start Flask app (reply detection will be started on demand)
    app.run(host='0.0.0.0', port=8000, debug=False)
