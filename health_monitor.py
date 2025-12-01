#!/usr/bin/env python3
"""
Health monitoring script for WhatsApp automation system
"""

import requests
import time
import os
import json
from datetime import datetime

# Configuration
WHATSAPP_WORKER_URL = os.environ.get("WHATSAPP_WORKER_ENDPOINT", "http://localhost:8000")
N8N_URL = "http://localhost:5678"
UPTIME_PING_SECRET = os.environ.get("UPTIME_PING_SECRET")
ADMIN_TELEGRAM_ID = os.environ.get("ADMIN_TELEGRAM_ID")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")

def send_telegram_message(chat_id, text):
    """Send message to Telegram chat"""
    if not TELEGRAM_BOT_TOKEN or not chat_id:
        print("Telegram credentials not configured")
        return
    
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        data = {
            "chat_id": chat_id,
            "text": text
        }
        response = requests.post(url, data=data)
        print(f"Telegram message sent. Response: {response.status_code}")
    except Exception as e:
        print(f"Failed to send Telegram message: {e}")

def check_service_health(url, service_name):
    """Check if a service is healthy"""
    try:
        response = requests.get(f"{url}/health", timeout=10)
        return response.status_code == 200
    except Exception as e:
        print(f"Health check failed for {service_name}: {e}")
        return False

def send_uptime_ping():
    """Send uptime ping if configured"""
    if not UPTIME_PING_SECRET:
        return
    
    try:
        ping_url = f"https://uptime.betterstack.com/api/v1/heartbeat/{UPTIME_PING_SECRET}"
        response = requests.get(ping_url)
        if response.status_code == 200:
            print("Uptime ping sent successfully")
        else:
            print(f"Failed to send uptime ping: {response.status_code}")
    except Exception as e:
        print(f"Error sending uptime ping: {e}")

def trigger_n8n_workflow():
    """Manually trigger the n8n workflow"""
    try:
        # Trigger the workflow manually
        url = f"{N8N_URL}/workflows"
        headers = {
            "accept": "application/json"
        }
        
        # First, get the workflow ID
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            workflows = response.json()
            if workflows and len(workflows) > 0:
                workflow_id = workflows[0]['id']
                
                # Trigger the workflow
                trigger_url = f"{N8N_URL}/workflows/{workflow_id}/run"
                trigger_response = requests.post(trigger_url, headers=headers)
                
                if trigger_response.status_code == 200:
                    print("✅ n8n workflow triggered successfully")
                    send_telegram_message(ADMIN_TELEGRAM_ID, "🔄 Manual trigger: n8n workflow started processing")
                    return True
                else:
                    print(f"❌ Failed to trigger n8n workflow: {trigger_response.status_code}")
                    return False
            else:
                print("❌ No workflows found")
                return False
        else:
            print(f"❌ Failed to get workflows: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error triggering n8n workflow: {e}")
        return False

def main():
    """Main monitoring loop"""
    print("Starting health monitoring...")
    
    # Send startup notification
    send_telegram_message(ADMIN_TELEGRAM_ID, "🚀 WhatsApp automation system health monitor started")
    
    # Check if we should trigger workflow on startup (first run)
    first_run = True
    
    while True:
        try:
            # Check WhatsApp worker health
            whatsapp_healthy = check_service_health(WHATSAPP_WORKER_URL, "WhatsApp Worker")
            
            # Check n8n health
            n8n_healthy = check_service_health(N8N_URL, "n8n")
            
            # Overall system health
            system_healthy = whatsapp_healthy and n8n_healthy
            
            # Send uptime ping
            if system_healthy:
                send_uptime_ping()
            
            # On first run, if system is healthy, trigger workflow to process any pending CSV files
            if first_run and system_healthy:
                print("🔄 First run - triggering workflow to process any pending CSV files")
                trigger_n8n_workflow()
                first_run = False
            
            # Send alert if system is unhealthy
            if not system_healthy:
                alert_msg = f"🚨 System Alert ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')}):\n"
                if not whatsapp_healthy:
                    alert_msg += "- WhatsApp Worker is DOWN\n"
                if not n8n_healthy:
                    alert_msg += "- n8n is DOWN\n"
                
                send_telegram_message(ADMIN_TELEGRAM_ID, alert_msg)
            
            # Wait before next check
            time.sleep(300)  # Check every 5 minutes
            
        except KeyboardInterrupt:
            print("Health monitor stopped")
            send_telegram_message(ADMIN_TELEGRAM_ID, "🛑 WhatsApp automation system health monitor stopped")
            break
        except Exception as e:
            print(f"Error in health monitoring: {e}")
            time.sleep(60)  # Wait 1 minute before retrying

if __name__ == "__main__":
    main()