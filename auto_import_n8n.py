#!/usr/bin/env python3
"""
Script to automatically import the WhatsApp campaign workflow into n8n
"""

import requests
import json
import time
import os
from pathlib import Path

def wait_for_n8n():
    """Wait for n8n to be ready"""
    max_attempts = 30
    for attempt in range(max_attempts):
        try:
            response = requests.get('http://localhost:5678/rest/healthz')
            if response.status_code == 200:
                print("n8n is ready!")
                return True
        except requests.exceptions.RequestException:
            pass
        
        print(f"Waiting for n8n to start... (attempt {attempt + 1}/{max_attempts})")
        time.sleep(2)
    
    print("n8n did not start in time")
    return False

def import_workflow():
    """Import the WhatsApp campaign workflow"""
    workflow_path = Path(__file__).parent / "whatsapp_campaign.json"
    
    if not workflow_path.exists():
        print(f"Workflow file not found: {workflow_path}")
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
            print("Workflow imported successfully!")
            return True
        else:
            print(f"Failed to import workflow: {response.status_code} - {response.text}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"Error importing workflow: {e}")
        return False

def set_environment_variables():
    """Set environment variables in n8n"""
    env_vars = {
        "TELEGRAM_BOT_TOKEN": os.environ.get("TELEGRAM_BOT_TOKEN"),
        "TELEGRAM_CHANNEL_ID": os.environ.get("TELEGRAM_CHANNEL_ID"),
        "SUPABASE_URL": os.environ.get("SUPABASE_URL"),
        "SUPABASE_KEY": os.environ.get("SUPABASE_KEY"),
        "ADMIN_TELEGRAM_ID": os.environ.get("ADMIN_TELEGRAM_ID"),
        "WHATSAPP_WORKER_ENDPOINT": os.environ.get("WHATSAPP_WORKER_ENDPOINT", "http://whatsapp-worker:8000"),
        "UPTIME_PING_SECRET": os.environ.get("UPTIME_PING_SECRET")
    }
    
    # Filter out None values
    env_vars = {k: v for k, v in env_vars.items() if v is not None}
    
    url = 'http://localhost:5678/rest/settings'
    headers = {
        'accept': 'application/json',
        'Content-Type': 'application/json'
    }
    
    payload = {
        "frontend": {
            "settings": {
                "enterprise": {
                    "features": {
                        "environmentVariables": {
                            "enabled": True,
                            "values": env_vars
                        }
                    }
                }
            }
        }
    }
    
    try:
        response = requests.patch(url, headers=headers, json=payload)
        if response.status_code == 200:
            print("Environment variables set successfully!")
            return True
        else:
            print(f"Failed to set environment variables: {response.status_code} - {response.text}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"Error setting environment variables: {e}")
        return False

def main():
    """Main function"""
    print("Starting n8n workflow auto-import...")
    
    # Wait for n8n to be ready
    if not wait_for_n8n():
        return False
    
    # Set environment variables
    if not set_environment_variables():
        return False
    
    # Import workflow
    if not import_workflow():
        return False
    
    print("n8n workflow auto-import completed successfully!")
    return True

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)