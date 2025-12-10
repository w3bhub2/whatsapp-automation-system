#!/bin/bash

# WhatsApp Authentication Test Script
# Tests the WhatsApp Web authentication status

echo "🔐 Testing WhatsApp Authentication..."

# Test worker health
echo "1. Testing WhatsApp Worker Health..."
curl -s -o /dev/null -w "Status: %{http_code}\n" http://localhost:8000/health

# Test auth status
echo "2. Checking Authentication Status..."
curl -s http://localhost:8000/check-auth | python -m json.tool

# Try to start driver if not already running
echo "3. Attempting to Start Driver..."
curl -s -X POST http://localhost:8000/start | python -m json.tool

echo "✅ WhatsApp authentication test completed"