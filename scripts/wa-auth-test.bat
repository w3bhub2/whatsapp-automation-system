@echo off
REM WhatsApp Authentication Test Script
REM Tests the WhatsApp Web authentication status

echo 🔐 Testing WhatsApp Authentication...

REM Test worker health
echo 1. Testing WhatsApp Worker Health...
powershell -Command "Invoke-WebRequest -Uri 'http://localhost:8000/health' -Method GET -UseBasicParsing | Select-Object StatusCode"

REM Test auth status
echo 2. Checking Authentication Status...
powershell -Command "Invoke-WebRequest -Uri 'http://localhost:8000/check-auth' -Method GET -UseBasicParsing | Select-Object Content"

REM Try to start driver if not already running
echo 3. Attempting to Start Driver...
powershell -Command "Invoke-WebRequest -Uri 'http://localhost:8000/start' -Method POST -UseBasicParsing | Select-Object Content"

echo ✅ WhatsApp authentication test completed