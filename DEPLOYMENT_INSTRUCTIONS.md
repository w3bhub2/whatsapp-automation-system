# WhatsApp Automation System Deployment to Render

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

## Step 3: Scan WhatsApp QR Code
1. After deployment, access the WhatsApp worker shell:
   ```bash
   render ssh whatsapp-worker
   ```
2. Run the QR code generator:
   ```bash
   python -c "from worker import init_webdriver; driver = init_webdriver(); driver.get('https://web.whatsapp.com'); input('Press Enter after scanning QR code...'); driver.quit()"
   ```
3. Scan the QR code with your phone
4. Press Enter to continue

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
