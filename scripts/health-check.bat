@echo off
REM Health Check Script for W3BHub WhatsApp Automation System
REM This script runs all health checks and generates a comprehensive report

echo 🏥 W3BHub Health Check
echo ======================

REM Create diagnostics directory
if not exist "diagnostics" mkdir diagnostics
if not exist "diagnostics\csv-fails" mkdir diagnostics\csv-fails

echo 1. Running Git Status Check...
git status > diagnostics\git-status.log 2>&1
echo    ✅ Git status check completed

echo 2. Running Build Check...
pip install --dry-run -r requirements.txt > diagnostics\build-check.log 2>&1
echo    ✅ Build check completed

echo 3. Running Python Health Checks...
python health-check.py > diagnostics\python-health-check.log 2>&1
echo    ✅ Python health checks completed

echo 4. Running Secrets Audit...
python secrets-audit.py > diagnostics\secrets-audit.log 2>&1
echo    ✅ Secrets audit completed

echo 5. Running CSV Validation...
python csv-validator.py > diagnostics\csv-validation.log 2>&1
echo    ✅ CSV validation completed

echo 6. Running WhatsApp Auth Test...
python whatsapp-auth-test.py > diagnostics\whatsapp-auth-test.log 2>&1
echo    ✅ WhatsApp auth test completed

echo.
echo 🎉 All health checks completed!
echo 📊 Check the diagnostics\ directory for detailed reports:
echo    - health-check.json - Main health check report
echo    - secrets-audit.json - Secrets audit report
echo    - csv-validation-report.json - CSV validation report
echo    - whatsapp-auth-test.json - WhatsApp authentication test report
echo    - And various .log files for detailed output