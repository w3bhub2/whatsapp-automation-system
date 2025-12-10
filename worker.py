#!/usr/bin/env python3
"""
WhatsApp Web Automation Worker

Flask-based worker that handles WhatsApp Web automation using Selenium

For support, message WebHub on WhatsApp: https://wa.me/message/XDA2UCEQCOILO1
"""

import os
import time
import json
import random
import urllib.parse
import logging
from datetime import datetime, timedelta
from threading import Thread, Lock, Timer
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
SUPABASE_URL = os.environ.get('SUPABASE_URL')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY')
ADMIN_TELEGRAM_ID = os.environ.get('ADMIN_TELEGRAM_ID')
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')

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

def send_uptime_ping():
    """Send uptime ping to BetterStack if UPTIME_PING_SECRET is configured"""
    global UPTIME_PING_THREAD
    
    # If no secret is configured, don't send pings
    if not UPTIME_PING_SECRET:
        logger.info("No UPTIME_PING_SECRET configured, skipping uptime pings")
        return
    
    try:
        # Send ping to BetterStack
        ping_url = f"https://uptime.betterstack.com/api/v1/heartbeat/{UPTIME_PING_SECRET}"
        response = requests.get(ping_url, timeout=10)
        
        if response.status_code == 200:
            logger.info("Uptime ping sent successfully")
        else:
            logger.warning(f"Uptime ping failed with status {response.status_code}")
    except Exception as e:
        logger.error(f"Failed to send uptime ping: {e}")
    
    # Schedule next ping in 5 minutes (300 seconds)
    UPTIME_PING_THREAD = Timer(300.0, send_uptime_ping)
    UPTIME_PING_THREAD.daemon = True
    UPTIME_PING_THREAD.start()

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
    """Initialize Chrome WebDriver with proper options for Docker environment"""
    try:
        logger.info("Initializing Chrome WebDriver...")
        chrome_options = Options()
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        # TEMPORARILY DISABLE HEADLESS MODE FOR AUTHENTICATION
        # chrome_options.add_argument("--headless=new")
        
        # Additional options for stability
        chrome_options.add_argument("--disable-background-timer-throttling")
        chrome_options.add_argument("--disable-renderer-backgrounding")
        chrome_options.add_argument("--disable-backgrounding-occluded-windows")
        
        # Set user agent to mimic a real browser
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
        
        # Set window size
        chrome_options.add_argument("--window-size=1920,1080")
        
        logger.info("Creating Chrome WebDriver instance...")
        driver = webdriver.Chrome(options=chrome_options)
        logger.info("Chrome WebDriver initialized successfully")
        return driver
    except Exception as e:
        logger.error(f"Failed to initialize Chrome driver: {str(e)}")
        logger.exception(e)
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
                current_url = driver.current_url  # This will throw an exception if driver is dead
                logger.debug(f"Using existing Chrome driver. Current URL: {current_url}")
            except Exception as e:
                logger.warning(f"Chrome driver appears to be dead: {str(e)}. Reinitializing...")
                try:
                    driver.quit()
                except Exception as quit_e:
                    logger.warning(f"Error quitting dead driver: {str(quit_e)}")
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
        logger.info(f"Navigating to WhatsApp Web URL: {url}")
        driver.get(url)
        
        # Human-like waiting with random variations
        wait_time = random.uniform(3, 6)
        logger.info(f"Waiting {wait_time:.2f} seconds for page to load...")
        time.sleep(wait_time)
        
        # Wait for the message input field to be ready
        logger.info("Waiting for message input field to be ready...")
        wait = WebDriverWait(driver, 30)
        message_box = wait.until(EC.presence_of_element_located((By.XPATH, '//div[@contenteditable="true"][@data-tab="10"]')))
        logger.info("Message input field is ready")
        
        # Simulate human typing behavior
        typing_delay = random.uniform(1, 3)
        logger.info(f"Simulating human typing behavior with {typing_delay:.2f} seconds delay...")
        time.sleep(typing_delay)
        
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
        logger.info("Sending message...")
        for char in "\n":  # Just press enter to send pre-filled message
            key_delay = random.uniform(0.1, 0.3)
            time.sleep(key_delay)
            message_box.send_keys(char)
        
        # Wait for confirmation that message was sent
        logger.info("Waiting for message confirmation...")
        wait.until(EC.presence_of_element_located((By.XPATH, '//span[@data-icon="msg-time" or @data-icon="check"]')))
        logger.info("Message confirmation received")
        
        # Update daily count
        with SEND_LOCK:
            DAILY_SENT_COUNT += 1
            
        logger.info(f"Message sent successfully to {phone}")
        return "success"
        
    except TimeoutException as te:
        logger.error(f"Timeout while sending message to {phone}: {str(te)}")
        FAILURE_COUNT += 1
        return "timeout"
    except NoSuchElementException as nse:
        logger.error(f"Element not found while sending message to {phone}: {str(nse)}")
        FAILURE_COUNT += 1
        return "element_not_found"
    except Exception as e:
        logger.error(f"Error sending message to {phone}: {str(e)}")
        logger.exception(e)  # Log full traceback
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
                        logger.info("Navigating to WhatsApp Web for reply detection...")
                        driver.get("https://web.whatsapp.com")
                        time.sleep(5)  # Wait for page to load
                except Exception as e:
                    # If we can't navigate, try to recover
                    logger.warning(f"Failed to navigate to WhatsApp Web: {str(e)}. Retrying...")
                    try:
                        driver.get("https://web.whatsapp.com")
                        time.sleep(5)
                    except Exception as e2:
                        logger.error(f"Failed to navigate to WhatsApp Web after retry: {str(e2)}")
                        time.sleep(60)  # Wait longer before retrying
                        continue
            
            # Check for new messages
            logger.info("Checking for unread messages...")
            unread_chats = driver.find_elements(By.XPATH, '//div[@role="row"]//span[@aria-label="Unread"]')
            logger.info(f"Found {len(unread_chats)} unread chats")
            
            for chat in unread_chats:
                try:
                    # Click on the chat to open it
                    parent_chat = chat.find_element(By.XPATH, './ancestor::div[@role="row"]')
                    logger.info("Opening chat to check for replies...")
                    parent_chat.click()
                    time.sleep(2)
                    
                    # Get chat name/phone
                    try:
                        chat_header = driver.find_element(By.XPATH, '//div[@id="main"]//header//div[@data-testid="conversation-info-header"]')
                        chat_name = chat_header.text.split('\n')[0]
                    except Exception as e:
                        logger.warning(f"Could not extract chat name: {str(e)}")
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
                    logger.error(f"Error processing chat: {str(e)}")
                    logger.exception(e)
                    continue
            
            # Wait before next check
            logger.info("Reply detection cycle completed. Waiting 30 seconds before next check...")
            time.sleep(30)  # Check every 30 seconds
        except Exception as e:
            logger.error(f"Error in reply detection loop: {str(e)}")
            logger.exception(e)
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

@app.route('/send-test', methods=['POST'])
def send_test_message():
    """Send a test WhatsApp message bypassing time restrictions for testing"""
    global DAILY_SENT_COUNT, FAILURE_COUNT, BLOCK_COUNT, STOP_SENDING
    
    # Check if we should stop sending
    if STOP_SENDING:
        return jsonify({"error": "Sending stopped due to safety triggers"}), 429
    
    # Skip time window check for testing
    # Check daily limit
    if DAILY_SENT_COUNT >= get_daily_limit():
        return jsonify({"error": f"Daily limit reached ({get_daily_limit()} messages)"}), 429
    
    try:
        data = request.get_json()
        phone = data.get('phone')
        message = data.get('message')
        batch_id = data.get('batch_id', 'test')
        
        if not phone or not message:
            return jsonify({"error": "Phone and message are required"}), 400
        
        # Add random delay between messages
        delay = random.randint(3, 5)  # Shorter delay for testing
        logger.info(f"Waiting {delay} seconds before sending test message...")
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
        logger.error(f"Error in send_test_message endpoint: {e}")
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
                reply_thread = Thread(target=detect_replies, daemon=True)
                reply_thread.start()
                REPLY_DETECTION_ACTIVE = True
                logger.info("Reply detection thread started")
            
            # Check if we're already logged in
            try:
                # Wait a moment for the page to load
                time.sleep(5)
                
                # Try to find the chat list (indicates we're logged in)
                chat_list = driver.find_element(By.XPATH, '//div[@role="listbox"]')
                logger.info("Already logged in to WhatsApp Web")
                return jsonify({
                    "status": "success", 
                    "message": "Chrome driver started and already logged in"
                }), 200
            except:
                # Try to find and save the QR code
                try:
                    logger.info("Not logged in to WhatsApp Web. Looking for QR code...")
                    # Wait for QR code to appear
                    wait = WebDriverWait(driver, 30)
                    # Try multiple selectors for QR code (WhatsApp Web sometimes changes UI)
                    qr_selectors = [
                        '//canvas[@alt="Scan me!"]',
                        '//div[@data-ref]//canvas',
                        '//div[contains(@class, "landing-wrapper")]//div[@data-ref]',
                        '//div[@role="button"][@class="cm280y3j fsmudhu6 l3k7h4x6 g9p5wyxn iezj4v4j jqgttzxe oy19ykas pdr474jm"]'
                    ]
                    
                    qr_element = None
                    for selector in qr_selectors:
                        try:
                            qr_element = wait.until(EC.presence_of_element_located((By.XPATH, selector)))
                            if qr_element:
                                logger.info(f"QR code found with selector: {selector}")
                                break
                        except:
                            continue
                    
                    if qr_element is None:
                        raise TimeoutException("QR code not found with any selector")
                    
                    # Save screenshot of the QR code to a location accessible from host
                    qr_filename = '/app/whatsapp_qr_code.png'
                    qr_element.screenshot(qr_filename)
                    logger.info(f"QR code saved to {qr_filename}")
                    
                    return jsonify({
                        "status": "success", 
                        "message": "Chrome driver started. QR code saved",
                        "qr_code_file": qr_filename,
                        "instruction": "Use 'docker cp whatsapp-worker:/app/whatsapp_qr_code.png .' to copy the QR code to your host machine and scan it with your WhatsApp mobile app."
                    }), 200
                except TimeoutException:
                    logger.error("QR code not found")
                    return jsonify({
                        "status": "success", 
                        "message": "Chrome driver started. Could not find QR code.",
                        "instruction": "Please check the container logs for more information."
                    }), 200
        else:
            logger.info("Chrome driver already running")
            return jsonify({"status": "success", "message": "Chrome driver already running"}), 200
    except Exception as e:
        logger.error(f"Error starting Chrome driver: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/get-qr', methods=['GET'])
def get_qr_code():
    """Get WhatsApp Web QR code for authentication"""
    global driver
    
    if driver is None:
        return jsonify({"error": "Driver not initialized. Call /start first."}), 400
    
    try:
        # Wait for QR code to appear with improved selectors
        wait = WebDriverWait(driver, 30)
        # Try multiple selectors for QR code (WhatsApp Web sometimes changes UI)
        qr_selectors = [
            '//canvas[@alt="Scan me!"]',
            '//div[@data-ref]//canvas',
            '//div[contains(@class, "landing-wrapper")]//div[@data-ref]',
            '//div[@role="button"][@class="cm280y3j fsmudhu6 l3k7h4x6 g9p5wyxn iezj4v4j jqgttzxe oy19ykas pdr474jm"]'
        ]
        
        qr_element = None
        for selector in qr_selectors:
            try:
                qr_element = wait.until(EC.presence_of_element_located((By.XPATH, selector)))
                if qr_element:
                    logger.info(f"QR code found with selector: {selector}")
                    break
            except:
                continue
        
        if qr_element is None:
            raise TimeoutException("QR code not found with any selector")
        
        # Get screenshot of the QR code
        qr_screenshot = qr_element.screenshot_as_base64
        
        return jsonify({
            "status": "success",
            "qr_code": qr_screenshot,
            "message": "Scan this QR code with your WhatsApp mobile app"
        }), 200
        
    except TimeoutException:
        return jsonify({"error": "QR code not found. Make sure you're not already logged in."}), 404
    except Exception as e:
        logger.error(f"Error getting QR code: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/save-qr', methods=['GET'])
def save_qr_code():
    """Save WhatsApp Web QR code to a file for authentication"""
    global driver
    
    if driver is None:
        return jsonify({"error": "Driver not initialized. Call /start first."}), 400
    
    try:
        # Wait for QR code to appear with improved selectors
        wait = WebDriverWait(driver, 30)
        # Try multiple selectors for QR code (WhatsApp Web sometimes changes UI)
        qr_selectors = [
            '//canvas[@alt="Scan me!"]',
            '//div[@data-ref]//canvas',
            '//div[contains(@class, "landing-wrapper")]//div[@data-ref]',
            '//div[@role="button"][@class="cm280y3j fsmudhu6 l3k7h4x6 g9p5wyxn iezj4v4j jqgttzxe oy19ykas pdr474jm"]'
        ]
        
        qr_element = None
        for selector in qr_selectors:
            try:
                qr_element = wait.until(EC.presence_of_element_located((By.XPATH, selector)))
                if qr_element:
                    logger.info(f"QR code found with selector: {selector}")
                    break
            except:
                continue
        
        if qr_element is None:
            raise TimeoutException("QR code not found with any selector")
        
        # Save screenshot of the QR code
        qr_element.screenshot('/app/qr_code.png')
        
        return jsonify({
            "status": "success",
            "message": "QR code saved to /app/qr_code.png",
            "instruction": "Copy this file from the container to your host machine to scan it"
        }), 200
        
    except TimeoutException:
        return jsonify({"error": "QR code not found. Make sure you're not already logged in."}), 404
    except Exception as e:
        logger.error(f"Error saving QR code: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/process-csv', methods=['POST'])
def process_csv_manually():
    """Process CSV file manually bypassing Telegram restrictions and send messages"""
    try:
        # Get the filename from the request
        data = request.get_json()
        filename = data.get('filename')
        batch_id = data.get('batch_id', 'manual_batch_' + datetime.now().strftime("%Y%m%d_%H%M%S"))
        
        if not filename:
            return jsonify({"error": "Filename is required"}), 400
        
        # Check if file exists
        if not os.path.exists(filename):
            return jsonify({"error": f"File {filename} not found"}), 404
        
        # Check if within send window
        if not is_within_send_window():
            return jsonify({"error": "Outside send window (9 AM - 6 PM IST)"}), 429
        
        # Check daily limit
        global DAILY_SENT_COUNT
        daily_limit = get_daily_limit()
        if DAILY_SENT_COUNT >= daily_limit:
            return jsonify({"error": f"Daily limit reached ({daily_limit} messages)"}), 429
        
        # Process the CSV file
        sent_count = 0
        failed_count = 0
        
        with open(filename, 'r', encoding='utf-8') as f:
            # Skip header
            header = f.readline().strip()
            if header != "phone,business_name,email":
                return jsonify({"error": "Invalid CSV format. Expected header: phone,business_name,email"}), 400
            
            # Process each line
            for line in f:
                line = line.strip()
                if not line:
                    continue
                    
                parts = line.split(',')
                if len(parts) != 3:
                    continue
                    
                phone, business_name, email = parts
                
                # Validate phone number (should be numeric and 10-15 digits)
                if not phone.isdigit() or len(phone) < 10 or len(phone) > 15:
                    failed_count += 1
                    continue
                
                # Check if we've reached the daily limit
                if DAILY_SENT_COUNT >= daily_limit:
                    break
                
                # Send message
                try:
                    # Select a random template
                    message_template = random.choice(INITIAL_TEMPLATES)
                    message = message_template.format(name=business_name)
                    
                    # Send the message
                    result = send_whatsapp_message(phone, message)
                    
                    if result == "success":
                        # Record in Supabase
                        record_sent_number(phone, business_name, email, batch_id)
                        sent_count += 1
                    else:
                        failed_count += 1
                        
                except Exception as e:
                    logger.error(f"Error sending message to {phone}: {e}")
                    failed_count += 1
        
        return jsonify({
            "status": "completed",
            "message": f"Processing completed for {filename}",
            "filename": filename,
            "sent_count": sent_count,
            "failed_count": failed_count,
            "daily_sent_count": DAILY_SENT_COUNT
        }), 200
        
    except Exception as e:
        logger.error(f"Error processing CSV: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/process-csv-test', methods=['POST'])
def process_csv_manually_test():
    """Process CSV file manually bypassing Telegram and time window restrictions for testing"""
    try:
        # Get the filename from the request
        data = request.get_json()
        filename = data.get('filename')
        batch_id = data.get('batch_id', 'test_batch_' + datetime.now().strftime("%Y%m%d_%H%M%S"))
        
        if not filename:
            return jsonify({"error": "Filename is required"}), 400
        
        # Check if file exists
        if not os.path.exists(filename):
            return jsonify({"error": f"File {filename} not found"}), 404
        
        # SKIP time window check for testing
        # SKIP daily limit check for testing
        
        # Process the CSV file
        sent_count = 0
        failed_count = 0
        
        with open(filename, 'r', encoding='utf-8') as f:
            # Skip header
            header = f.readline().strip()
            if header != "phone,business_name,email":
                return jsonify({"error": "Invalid CSV format. Expected header: phone,business_name,email"}), 400
            
            # Process each line
            for line in f:
                line = line.strip()
                if not line:
                    continue
                    
                parts = line.split(',')
                if len(parts) != 3:
                    continue
                    
                phone, business_name, email = parts
                
                # Validate phone number (should be numeric and 10-15 digits)
                if not phone.isdigit() or len(phone) < 10 or len(phone) > 15:
                    failed_count += 1
                    continue
                
                # Send message
                try:
                    # Select a random template
                    message_template = random.choice(INITIAL_TEMPLATES)
                    message = message_template.format(name=business_name)
                    
                    # Send the message
                    result = send_whatsapp_message(phone, message)
                    
                    if result == "success":
                        # Record in Supabase
                        record_sent_number(phone, business_name, email, batch_id)
                        sent_count += 1
                    else:
                        failed_count += 1
                        
                except Exception as e:
                    logger.error(f"Error sending message to {phone}: {e}")
                    failed_count += 1
        
        return jsonify({
            "status": "completed",
            "message": f"Processing completed for {filename}",
            "filename": filename,
            "sent_count": sent_count,
            "failed_count": failed_count,
            "daily_sent_count": DAILY_SENT_COUNT
        }), 200
        
    except Exception as e:
        logger.error(f"Error processing CSV: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/check-auth', methods=['GET'])
def check_authentication():
    """Check if WhatsApp Web is authenticated"""
    global driver
    
    if driver is None:
        return jsonify({"authenticated": False, "message": "Driver not initialized"}), 200
    
    try:
        # Check if we're logged in by looking for the chat list
        chat_list = driver.find_element(By.XPATH, '//div[@role="listbox"]')
        return jsonify({"authenticated": True, "message": "WhatsApp Web is authenticated"}), 200
    except:
        # Not logged in, check if QR code is visible
        try:
            # Try multiple selectors for QR code (WhatsApp Web sometimes changes UI)
            qr_selectors = [
                '//canvas[@alt="Scan me!"]',
                '//div[@data-ref]//canvas',
                '//div[contains(@class, "landing-wrapper")]//div[@data-ref]'
            ]
            
            qr_found = False
            for selector in qr_selectors:
                try:
                    qr_element = driver.find_element(By.XPATH, selector)
                    if qr_element:
                        qr_found = True
                        break
                except:
                    continue
            
            if qr_found:
                return jsonify({"authenticated": False, "message": "Not authenticated. QR code is visible."}), 200
            else:
                return jsonify({"authenticated": False, "message": "Not authenticated. QR code not found."}), 200
        except:
            return jsonify({"authenticated": False, "message": "Not authenticated. QR code not found."}), 200

# Authentication
# Due to WhatsApp Web security restrictions, authentication must be performed by messaging WebHub on WhatsApp
# Contact: https://wa.me/message/XDA2UCEQCOILO1

def record_sent_number(phone, business_name, email, batch_id):
    """Record a sent number in Supabase"""
    try:
        # Check if required environment variables are set
        if not SUPABASE_URL or not SUPABASE_KEY:
            logger.error("Supabase URL or Key not set")
            return False
            
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
        # Check if required environment variables are set
        if not SUPABASE_URL or not SUPABASE_KEY:
            logger.error("Supabase URL or Key not set")
            return
            
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
    
    # Use Render's PORT environment variable, default to 8000
    port = int(os.environ.get('PORT', 8000))
    
    # Start Flask app (reply detection will be started on demand)
    app.run(host='0.0.0.0', port=port, debug=False)
