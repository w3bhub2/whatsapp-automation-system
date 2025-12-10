#!/usr/bin/env python3
"""
WhatsApp Authentication Test Script for W3BHub WhatsApp Automation System

This script implements the WhatsApp authentication investigation requirement:
- Attempt auth flow (dry-run) using existing env credentials
- Capture logs and exact response codes
- Report results
"""

import os
import sys
import json
import requests
import time
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def check_env_credentials():
    """Check if required environment variables are present"""
    required_vars = [
        'SUPABASE_URL',
        'SUPABASE_KEY',
        'TELEGRAM_BOT_TOKEN',
        'ADMIN_TELEGRAM_ID'
    ]
    
    missing_vars = []
    env_values = {}
    
    for var in required_vars:
        value = os.environ.get(var)
        if not value:
            missing_vars.append(var)
        else:
            env_values[var] = value
    
    return missing_vars, env_values

def test_whatsapp_worker_health():
    """Test if WhatsApp worker is running and healthy"""
    print("🔍 Testing WhatsApp Worker Health...")
    
    try:
        response = requests.get('http://localhost:8000/health', timeout=10)
        print(f"  Status Code: {response.status_code}")
        print(f"  Response: {response.text}")
        
        if response.status_code == 200:
            print("  ✅ WhatsApp Worker is healthy")
            return True, response
        else:
            print("  ❌ WhatsApp Worker is unhealthy")
            return False, response
    except requests.exceptions.ConnectionError:
        print("  ❌ Cannot connect to WhatsApp Worker (not running?)")
        return False, None
    except Exception as e:
        print(f"  ❌ Error testing WhatsApp Worker: {e}")
        return False, None

def test_whatsapp_worker_auth_status():
    """Check WhatsApp Web authentication status"""
    print("🔍 Checking WhatsApp Web Authentication Status...")
    
    try:
        response = requests.get('http://localhost:8000/check-auth', timeout=10)
        print(f"  Status Code: {response.status_code}")
        
        if response.status_code == 200:
            auth_data = response.json()
            print(f"  Authenticated: {auth_data.get('authenticated', False)}")
            print(f"  Message: {auth_data.get('message', 'No message')}")
            return True, auth_data
        else:
            print(f"  Response: {response.text}")
            return False, {'error': f'HTTP {response.status_code}'}
    except requests.exceptions.ConnectionError:
        print("  ❌ Cannot connect to WhatsApp Worker")
        return False, {'error': 'Connection error'}
    except Exception as e:
        print(f"  ❌ Error checking auth status: {e}")
        return False, {'error': str(e)}

def test_whatsapp_worker_start():
    """Try to start the WhatsApp worker driver"""
    print("🔍 Attempting to start WhatsApp Worker driver...")
    
    try:
        response = requests.post('http://localhost:8000/start', timeout=30)
        print(f"  Status Code: {response.status_code}")
        
        if response.status_code == 200:
            start_data = response.json()
            print(f"  Status: {start_data.get('status', 'Unknown')}")
            print(f"  Message: {start_data.get('message', 'No message')}")
            
            if 'qr_code_file' in start_data:
                print(f"  QR Code File: {start_data['qr_code_file']}")
                print("  💡 Scan the QR code with your WhatsApp mobile app to authenticate")
            
            return True, start_data
        else:
            print(f"  Response: {response.text}")
            return False, {'error': f'HTTP {response.status_code}', 'response': response.text}
    except requests.exceptions.ConnectionError:
        print("  ❌ Cannot connect to WhatsApp Worker")
        return False, {'error': 'Connection error'}
    except Exception as e:
        print(f"  ❌ Error starting worker: {e}")
        return False, {'error': str(e)}

def test_supabase_connection(supabase_url, supabase_key):
    """Test Supabase connection"""
    print("🔍 Testing Supabase Connection...")
    
    if not supabase_url or not supabase_key:
        print("  ❌ Supabase credentials not provided")
        return False, {'error': 'Missing credentials'}
    
    try:
        url = f"{supabase_url}/rest/v1/sent_numbers?limit=1"
        headers = {
            "apikey": supabase_key,
            "Authorization": f"Bearer {supabase_key}"
        }
        response = requests.get(url, headers=headers, timeout=10)
        print(f"  Status Code: {response.status_code}")
        
        if response.status_code == 200:
            print("  ✅ Supabase connection successful")
            return True, {'status': 'connected', 'record_count': len(response.json())}
        else:
            print(f"  Response: {response.text}")
            return False, {'error': f'HTTP {response.status_code}', 'response': response.text}
    except Exception as e:
        print(f"  ❌ Error connecting to Supabase: {e}")
        return False, {'error': str(e)}

def test_telegram_bot(telegram_token):
    """Test Telegram bot connectivity"""
    print("🔍 Testing Telegram Bot Connectivity...")
    
    if not telegram_token:
        print("  ❌ Telegram bot token not provided")
        return False, {'error': 'Missing token'}
    
    try:
        url = f"https://api.telegram.org/bot{telegram_token}/getMe"
        response = requests.get(url, timeout=10)
        print(f"  Status Code: {response.status_code}")
        
        if response.status_code == 200:
            bot_info = response.json()
            if bot_info.get("ok"):
                print(f"  ✅ Bot authenticated: {bot_info['result']['username']}")
                return True, bot_info
            else:
                print(f"  Response: {response.text}")
                return False, {'error': 'Bot authentication failed', 'response': response.text}
        else:
            print(f"  Response: {response.text}")
            return False, {'error': f'HTTP {response.status_code}', 'response': response.text}
    except Exception as e:
        print(f"  ❌ Error testing Telegram bot: {e}")
        return False, {'error': str(e)}

def main():
    """Main function to test WhatsApp authentication"""
    print("🔐 WhatsApp Authentication Test")
    print("=" * 40)
    
    # Create diagnostics directory
    if not os.path.exists('diagnostics'):
        os.makedirs('diagnostics')
    
    # Check environment variables
    missing_vars, env_values = check_env_credentials()
    
    print(f"🔑 Environment Variables Check:")
    if missing_vars:
        print(f"  ❌ Missing variables: {', '.join(missing_vars)}")
        for var in missing_vars:
            print(f"     Please set {var} in your .env file")
    else:
        print("  ✅ All required environment variables are present")
    
    # Test results dictionary
    test_results = {
        'timestamp': datetime.now().isoformat(),
        'environment_check': {
            'missing_variables': missing_vars,
            'available_variables': list(env_values.keys())
        }
    }
    
    # Test WhatsApp worker health
    worker_healthy, worker_health_response = test_whatsapp_worker_health()
    test_results['worker_health'] = {
        'healthy': worker_healthy,
        'response': worker_health_response.text if worker_health_response else None,
        'status_code': worker_health_response.status_code if worker_health_response else None
    }
    
    # Test WhatsApp authentication status
    auth_checked, auth_status = test_whatsapp_worker_auth_status()
    test_results['auth_status'] = {
        'checked': auth_checked,
        'data': auth_status
    }
    
    # Try to start the worker driver
    driver_started, start_result = test_whatsapp_worker_start()
    test_results['driver_start'] = {
        'started': driver_started,
        'result': start_result
    }
    
    # Test Supabase connection
    supabase_connected, supabase_result = test_supabase_connection(
        env_values.get('SUPABASE_URL'), 
        env_values.get('SUPABASE_KEY')
    )
    test_results['supabase_connection'] = {
        'connected': supabase_connected,
        'result': supabase_result
    }
    
    # Test Telegram bot
    telegram_working, telegram_result = test_telegram_bot(
        env_values.get('TELEGRAM_BOT_TOKEN')
    )
    test_results['telegram_bot'] = {
        'working': telegram_working,
        'result': telegram_result
    }
    
    # Save results
    with open('diagnostics/whatsapp-auth-test.json', 'w') as f:
        json.dump(test_results, f, indent=2)
    
    # Print summary
    print("\n" + "=" * 40)
    print("AUTHENTICATION TEST SUMMARY")
    print("=" * 40)
    print(f"Worker Healthy: {'Yes' if worker_healthy else 'No'}")
    print(f"Authenticated: {'Yes' if auth_checked and auth_status.get('authenticated') else 'No'}")
    print(f"Driver Started: {'Yes' if driver_started else 'No'}")
    print(f"Supabase Connected: {'Yes' if supabase_connected else 'No'}")
    print(f"Telegram Working: {'Yes' if telegram_working else 'No'}")
    
    # Overall assessment
    print("\n📊 OVERALL ASSESSMENT:")
    if worker_healthy and auth_checked and auth_status.get('authenticated'):
        print("  ✅ WhatsApp is properly authenticated and ready to send messages")
    elif worker_healthy and driver_started:
        print("  ⚠️  WhatsApp worker is running but needs manual authentication")
        print("     Scan the QR code displayed in the start response")
    elif worker_healthy:
        print("  ⚠️  WhatsApp worker is running but driver needs to be started")
        print("     Call the /start endpoint to initialize the driver")
    else:
        print("  ❌ WhatsApp worker is not running or unhealthy")
        print("     Start the docker containers with: docker-compose up -d")
    
    print("=" * 40)
    print(f"💾 Detailed results saved to diagnostics/whatsapp-auth-test.json")
    
    return test_results

if __name__ == "__main__":
    main()