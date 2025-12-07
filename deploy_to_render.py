#!/usr/bin/env python3
"""
Deployment script for WhatsApp Automation System to Render
"""

import os
import json
import time
from pathlib import Path

def create_render_blueprint():
    """Create Render blueprint for deployment"""
    blueprint = {
        "version": "1",
        "services": [
            {
                "type": "web",
                "name": "whatsapp-worker",
                "env": "docker",
                "repo": "https://github.com/w3bhub2/whatsapp-automation-system.git",
                "region": "oregon",
                "plan": "free",
                "envVars": [
                    {"key": "TELEGRAM_BOT_TOKEN", "sync": False},
                    {"key": "TELEGRAM_CHANNEL_ID", "sync": False},
                    {"key": "SUPABASE_URL", "sync": False},
                    {"key": "SUPABASE_KEY", "sync": False},
                    {"key": "ADMIN_TELEGRAM_ID", "sync": False},
                    {"key": "UPTIME_PING_SECRET", "sync": False}
                ],
                "healthCheckPath": "/health"
            },
            {
                "type": "web",
                "name": "n8n",
                "env": "docker",
                "repo": "https://github.com/w3bhub2/whatsapp-automation-system.git",
                "region": "oregon",
                "plan": "free",
                "envVars": [
                    {"key": "GENERIC_TIMEZONE", "value": "Asia/Kolkata"},
                    {"key": "TZ", "value": "Asia/Kolkata"},
                    {"key": "N8N_ENCRYPTION_KEY", "sync": False},
                    {"key": "N8N_USER_MANAGEMENT_DISABLED", "value": "true"},
                    {"key": "N8N_API_KEY", "value": "supersecretkey"},
                    {"key": "TELEGRAM_BOT_TOKEN", "sync": False},
                    {"key": "TELEGRAM_CHANNEL_ID", "sync": False},
                    {"key": "SUPABASE_URL", "sync": False},
                    {"key": "SUPABASE_KEY", "sync": False},
                    {"key": "ADMIN_TELEGRAM_ID", "sync": False},
                    {"key": "WHATSAPP_WORKER_ENDPOINT", "value": "https://whatsapp-worker-w53e.onrender.com"}
                ],
                "healthCheckPath": "/healthz",
                "dockerCommand": "n8n"
            }
        ]
    }
    
    with open("render.yaml", "w") as f:
        json.dump(blueprint, f, indent=2)
    
    print("✅ Render blueprint created: render.yaml")
    return blueprint

def create_deployment_instructions():
    """Create detailed deployment instructions"""
    instructions = """# WhatsApp Automation System Deployment to Render

## Prerequisites
1. GitHub account
2. Render account (https://render.com)
3. Supabase account (https://supabase.com)
4. Telegram bot token and channel

## Step 1: Push to GitHub
1. Create a new repository on GitHub
2. Run these commands:
   ```bash
   git remote set-url origin https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
   git push -u origin main
   ```

## Step 2: Deploy to Render
1. Go to https://dashboard.render.com/select-repo?type=blueprint
2. Select your GitHub repository
3. Select the render.yaml file
4. Configure environment variables:
   - TELEGRAM_BOT_TOKEN: Your Telegram bot token
   - TELEGRAM_CHANNEL_ID: Your Telegram channel ID
   - SUPABASE_URL: Your Supabase project URL
   - SUPABASE_KEY: Your Supabase service key
   - ADMIN_TELEGRAM_ID: Your admin Telegram ID
   - UPTIME_PING_SECRET: Your uptime ping secret (optional)

## Step 3: WhatsApp Authentication
Due to WhatsApp Web security restrictions, you'll need to authenticate manually once after deployment. This cannot be automated.

## Step 4: Verify Deployment
1. Check service statuses on Render dashboard
2. Verify health endpoints:
   - WhatsApp Worker: https://YOUR-WORKER-URL.onrender.com/health
   - n8n: https://YOUR-N8N-URL.onrender.com/healthz

## Step 5: Test the System
1. Upload a CSV file to your Telegram channel
2. Wait 10 minutes for processing
3. Check Supabase for new records
4. Verify messages send between 9 AM - 6 PM IST

## Autonomous Operation
After initial setup, the system runs completely autonomously:
- No laptop dependency
- No manual intervention required
- Self-healing containers
- Automatic updates via GitHub

## Support
For assistance with setup or troubleshooting, message WebHub on WhatsApp:
https://wa.me/message/XDA2UCEQCOILO1
"""
    
    with open("DEPLOYMENT_INSTRUCTIONS.md", "w") as f:
        f.write(instructions)
    
    print("✅ Deployment instructions created: DEPLOYMENT_INSTRUCTIONS.md")

def main():
    """Main deployment function"""
    print("🚀 Creating deployment files for WhatsApp Automation System...")
    
    # Create Render blueprint
    create_render_blueprint()
    
    # Create deployment instructions
    create_deployment_instructions()
    
    print("\n✅ All deployment files created successfully!")
    print("\n📝 Next steps:")
    print("1. Push to GitHub:")
    print("   git remote set-url origin https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git")
    print("   git push -u origin main")
    print("\n2. Deploy to Render using the render.yaml file")
    print("3. Follow DEPLOYMENT_INSTRUCTIONS.md for complete setup")
    print("\nFor assistance, message WebHub on WhatsApp: https://wa.me/message/XDA2UCEQCOILO1")
    
    return True

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)