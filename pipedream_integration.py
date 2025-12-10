#!/usr/bin/env python3
"""
Pipedream Integration for W3BHub WhatsApp Automation System

This script creates a webhook endpoint that Pipedream can call to send CSV data
directly to the system, bypassing Telegram bot limitations.
"""

import json
import os
import uuid
import base64
import requests
from datetime import datetime
from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename

app = Flask(__name__)

# Directory to store received CSV files
CSV_UPLOAD_FOLDER = 'pipedream_csv'
os.makedirs(CSV_UPLOAD_FOLDER, exist_ok=True)

# Get WhatsApp worker endpoint from environment or default to localhost
WHATSAPP_WORKER_ENDPOINT = os.environ.get('WHATSAPP_WORKER_ENDPOINT', 'http://localhost:8000')

@app.route('/incoming/leads', methods=['POST'])
def incoming_leads():
    """Handle incoming leads from Pipedream - compatible with Pipedream's default endpoint"""
    try:
        print("📥 Received leads from Pipedream at /incoming/leads")
        
        # Get the JSON payload
        if request.is_json:
            data = request.get_json()
            print(f"   Payload: {json.dumps(data, indent=2)[:200]}...")
        else:
            # Handle form data or raw data
            data = request.get_data(as_text=True)
            print(f"   Raw data: {data[:200]}...")
        
        # Extract CSV content
        csv_content = None
        filename = None
        
        # Try different ways to extract CSV data
        if isinstance(data, dict):
            # If it's JSON, look for CSV content
            if 'csv' in data:
                csv_content = data['csv']
                filename = data.get('filename', f'pipedream_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv')
            elif 'content' in data:
                csv_content = data['content']
                filename = data.get('filename', f'pipedream_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv')
            elif 'file' in data:
                csv_content = data['file']
                filename = data.get('filename', f'pipedream_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv')
            else:
                # Assume the entire payload is CSV content
                csv_content = json.dumps(data)
                filename = f'pipedream_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        else:
            # If it's raw data, treat as CSV content
            csv_content = data
            filename = f'pipedream_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        
        # Secure the filename
        filename = secure_filename(filename)
        if not filename.endswith('.csv'):
            filename += '.csv'
        
        # Save CSV file
        filepath = os.path.join(CSV_UPLOAD_FOLDER, filename)
        
        # If content is base64 encoded, decode it
        if isinstance(csv_content, str) and csv_content.startswith('data:text/csv;base64,'):
            # Extract base64 part
            base64_data = csv_content.split(',')[1]
            csv_binary = base64.b64decode(base64_data)
            with open(filepath, 'wb') as f:
                f.write(csv_binary)
        elif isinstance(csv_content, str):
            # Write as text
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(csv_content)
        else:
            # Write as binary
            with open(filepath, 'wb') as f:
                f.write(csv_content)
        
        print(f"✅ CSV file saved: {filepath}")
        
        # Process the CSV file immediately
        process_csv_file(filepath)
        
        return jsonify({
            "status": "success",
            "message": f"Leads received and processed: {filename}",
            "filename": filename
        }), 200
        
    except Exception as e:
        print(f"❌ Error processing incoming leads: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route('/pipedream/webhook', methods=['POST'])
def receive_csv_from_pipedream():
    """Receive CSV data directly from Pipedream webhook"""
    try:
        print("📥 Received webhook from Pipedream")
        
        # Get the JSON payload
        if request.is_json:
            data = request.get_json()
            print(f"   Payload: {json.dumps(data, indent=2)[:200]}...")
        else:
            # Handle form data or raw data
            data = request.get_data(as_text=True)
            print(f"   Raw data: {data[:200]}...")
        
        # Extract CSV content
        csv_content = None
        filename = None
        
        # Try different ways to extract CSV data
        if isinstance(data, dict):
            # If it's JSON, look for CSV content
            if 'csv' in data:
                csv_content = data['csv']
                filename = data.get('filename', f'pipedream_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv')
            elif 'content' in data:
                csv_content = data['content']
                filename = data.get('filename', f'pipedream_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv')
            elif 'file' in data:
                csv_content = data['file']
                filename = data.get('filename', f'pipedream_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv')
            else:
                # Assume the entire payload is CSV content
                csv_content = json.dumps(data)
                filename = f'pipedream_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        else:
            # If it's raw data, treat as CSV content
            csv_content = data
            filename = f'pipedream_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        
        # Secure the filename
        filename = secure_filename(filename)
        if not filename.endswith('.csv'):
            filename += '.csv'
        
        # Save CSV file
        filepath = os.path.join(CSV_UPLOAD_FOLDER, filename)
        
        # If content is base64 encoded, decode it
        if isinstance(csv_content, str) and csv_content.startswith('data:text/csv;base64,'):
            # Extract base64 part
            base64_data = csv_content.split(',')[1]
            csv_binary = base64.b64decode(base64_data)
            with open(filepath, 'wb') as f:
                f.write(csv_binary)
        elif isinstance(csv_content, str):
            # Write as text
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(csv_content)
        else:
            # Write as binary
            with open(filepath, 'wb') as f:
                f.write(csv_content)
        
        print(f"✅ CSV file saved: {filepath}")
        
        # Process the CSV file immediately
        process_csv_file(filepath)
        
        return jsonify({
            "status": "success",
            "message": f"CSV file received and processed: {filename}",
            "filename": filename
        }), 200
        
    except Exception as e:
        print(f"❌ Error processing Pipedream webhook: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

def process_csv_file(filepath):
    """Process a CSV file using the existing system"""
    try:
        print(f"🔄 Processing CSV file: {filepath}")
        
        # Prepare the payload
        filename = os.path.basename(filepath)
        payload = {
            "filename": filepath,
            "batch_id": f"pipedream_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        }
        
        # Send request to WhatsApp worker using the configurable endpoint
        url = f"{WHATSAPP_WORKER_ENDPOINT}/process-csv"
        response = requests.post(url, json=payload, timeout=300)  # 5 minute timeout
        
        if response.status_code == 200:
            result = response.json()
            print("✅ CSV processing completed successfully!")
            print(f"   File: {result.get('filename')}")
            print(f"   Sent: {result.get('sent_count', 0)} messages")
            print(f"   Failed: {result.get('failed_count', 0)} messages")
            print(f"   Daily total: {result.get('daily_sent_count', 0)} messages")
            return True
        else:
            print(f"❌ Failed to process CSV: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error processing CSV: {e}")
        return False

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "service": "Pipedream Integration for W3BHub",
        "timestamp": datetime.now().isoformat()
    }), 200

@app.route('/', methods=['GET'])
def index():
    """Index page"""
    return jsonify({
        "message": "Pipedream Integration for W3BHub WhatsApp Automation System",
        "endpoint": "/pipedream/webhook",
        "method": "POST",
        "description": "Receive CSV data directly from Pipedream"
    }), 200

if __name__ == '__main__':
    # Use Render's PORT environment variable, default to 8001
    port = int(os.environ.get('PORT', 8001))
    
    print("🚀 Starting Pipedream Integration Server...")
    print(f"   Endpoint: http://localhost:{port}/pipedream/webhook")
    print(f"   Alternative Endpoint: http://localhost:{port}/incoming/leads")
    print(f"   Health check: http://localhost:{port}/health")
    print(f"   WhatsApp Worker Endpoint: {WHATSAPP_WORKER_ENDPOINT}")
    app.run(host='0.0.0.0', port=port, debug=False)